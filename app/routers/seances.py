from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.database import get_db
from app.routers.auth import get_current_membre, get_fondateur
from app.models.seance import Seance
from app.models.lot import Lot, AdhesionLot
from app.models.enums import StatutSeance, TypeNotif
from app.models.notification import Notification
from app.models.membre import Membre
import uuid

router = APIRouter(prefix="/seances", tags=["Séances"])

# ── Schémas ──
class SeanceCreate(BaseModel):
    lot_id: str
    date_seance: str
    heure_ouverture: str = "08:00"
    heure_cloture: str = "18:00"

class SeanceResponse(BaseModel):
    id: str
    lot_id: str
    date_seance: str
    heure_ouverture: str
    heure_cloture: str
    statut: str
    bouffeur_nom: Optional[str] = None
    montant_pot: Optional[float] = None
    lot_nom: Optional[str] = None

    class Config:
        from_attributes = True

# ── Lister les séances ──
@router.get("/", response_model=List[SeanceResponse])
def get_seances(db: Session = Depends(get_db), membre=Depends(get_current_membre)):
    seances = db.query(Seance).order_by(Seance.date_seance.desc()).all()
    result = []
    for s in seances:
        lot = db.query(Lot).filter(Lot.id == s.lot_id).first()
        bouffeur_nom = None
        if s.bouffeur_id:
            b = db.query(Membre).filter(Membre.id == s.bouffeur_id).first()
            if b:
                bouffeur_nom = f"{b.prenom} {b.nom}"
        result.append(SeanceResponse(
            id=s.id, lot_id=s.lot_id, date_seance=s.date_seance,
            heure_ouverture=s.heure_ouverture, heure_cloture=s.heure_cloture,
            statut=s.statut, bouffeur_nom=bouffeur_nom,
            montant_pot=float(s.montant_pot) if s.montant_pot else None,
            lot_nom=lot.nom if lot else None,
        ))
    return result

# ── Planifier une séance ──
@router.post("/")
def planifier_seance(data: SeanceCreate, db: Session = Depends(get_db), fondateur=Depends(get_fondateur)):
    lot = db.query(Lot).filter(Lot.id == data.lot_id).first()
    if not lot:
        raise HTTPException(status_code=404, detail="Lot introuvable")

    # Récupérer tontine_id depuis le lot
    seance = Seance(
        id=str(uuid.uuid4()),
        tontine_id=lot.tontine_id,
        lot_id=data.lot_id,
        date_seance=data.date_seance,
        heure_ouverture=data.heure_ouverture,
        heure_cloture=data.heure_cloture,
        statut=StatutSeance.PLANIFIEE,
    )
    db.add(seance)
    db.commit()
    db.refresh(seance)
    return {"message": "Séance planifiée avec succès", "id": seance.id}

# ── Ouvrir une séance ──
@router.put("/{seance_id}/ouvrir")
def ouvrir_seance(seance_id: str, db: Session = Depends(get_db), fondateur=Depends(get_fondateur)):
    seance = db.query(Seance).filter(Seance.id == seance_id).first()
    if not seance:
        raise HTTPException(status_code=404, detail="Séance introuvable")
    if seance.statut != StatutSeance.PLANIFIEE:
        raise HTTPException(status_code=400, detail="La séance n'est pas dans l'état PLANIFIEE")

    seance.statut = StatutSeance.OUVERTE
    db.commit()

    # Notifier tous les membres du lot
    adhesions = db.query(AdhesionLot).filter(AdhesionLot.lot_id == seance.lot_id).all()
    lot = db.query(Lot).filter(Lot.id == seance.lot_id).first()
    for a in adhesions:
        notif = Notification(
            id=str(uuid.uuid4()),
            membre_id=a.membre_id,
            tontine_id=seance.tontine_id,
            type_notif=TypeNotif.RAPPEL_COTISATION,
            titre="📢 Séance ouverte",
            message=f"La séance du {seance.date_seance} est ouverte. Versez votre cotisation avant {seance.heure_cloture}. Montant : {float(lot.montant_cotisation):,.0f} FCFA",
        )
        db.add(notif)
    db.commit()
    return {"message": "Séance ouverte — membres notifiés"}

# ── Clôturer une séance + bouffement automatique ──
@router.put("/{seance_id}/cloturer")
def cloturer_seance(seance_id: str, db: Session = Depends(get_db), fondateur=Depends(get_fondateur)):
    seance = db.query(Seance).filter(Seance.id == seance_id).first()
    if not seance:
        raise HTTPException(status_code=404, detail="Séance introuvable")
    if seance.statut != StatutSeance.OUVERTE:
        raise HTTPException(status_code=400, detail="La séance doit être ouverte pour être clôturée")

    lot = db.query(Lot).filter(Lot.id == seance.lot_id).first()

    # Calculer le pot total (somme paiements validés de la séance)
    paiements = db.query(paiements).filter(
        paiements.seance_id == seance_id,
        paiements.statut == "VALIDE"
    ).all()
    montant_pot = sum(float(p.montant_lot) for p in paiements)
    seance.montant_pot = montant_pot

    # Trouver le prochain bouffeur (rang non encore bouffé, le plus petit)
    prochain = db.query(AdhesionLot).filter(
        AdhesionLot.lot_id == seance.lot_id,
        AdhesionLot.a_bouffe == False,
        AdhesionLot.numero_tirage != None,
    ).order_by(AdhesionLot.numero_tirage).first()

    if prochain:
        # Appliquer l'option d'intégration si option DEDUCTION
        montant_verse = montant_pot
        if lot.option_integration == "DEDUCTION" and prochain.membres_passes > 0:
            deduction = prochain.membres_passes * float(lot.montant_cotisation)
            montant_verse = montant_pot - deduction

        # Marquer comme bouffé
        prochain.a_bouffe = True
        prochain.date_bouffement = datetime.utcnow()
        seance.bouffeur_id = prochain.membre_id

        # Notifier le bouffeur
        bouffeur = db.query(Membre).filter(Membre.id == prochain.membre_id).first()
        notif = Notification(
            id=str(uuid.uuid4()),
            membre_id=prochain.membre_id,
            tontine_id=seance.tontine_id,
            type_notif=TypeNotif.BOUFFEMENT,
            titre="🎉 C'est votre tour de bouffer !",
            message=f"Félicitations {bouffeur.prenom} ! Vous recevez {montant_verse:,.0f} FCFA pour la séance du {seance.date_seance}.",
        )
        db.add(notif)

        # Mettre à jour prochain bouffeur dans le lot
        suivant = db.query(AdhesionLot).filter(
            AdhesionLot.lot_id == seance.lot_id,
            AdhesionLot.a_bouffe == False,
            AdhesionLot.numero_tirage != None,
        ).order_by(AdhesionLot.numero_tirage).first()
        lot.prochain_bouffeur_id = suivant.membre_id if suivant else None

    seance.statut = StatutSeance.CLOTUREE
    db.commit()

    return {
        "message": "Séance clôturée",
        "montant_pot": montant_pot,
        "bouffeur_id": prochain.membre_id if prochain else None,
    }

# ── Séances d'un lot spécifique ──
@router.get("/lot/{lot_id}")
def seances_par_lot(lot_id: str, db: Session = Depends(get_db), membre=Depends(get_current_membre)):
    seances = db.query(Seance).filter(Seance.lot_id == lot_id).order_by(Seance.date_seance).all()
    return [{"id": s.id, "date": s.date_seance, "statut": s.statut,
             "heure_ouverture": s.heure_ouverture, "heure_cloture": s.heure_cloture,
             "montant_pot": float(s.montant_pot) if s.montant_pot else None} for s in seances]