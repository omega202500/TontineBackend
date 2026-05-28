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
from app.models.paiement import Paiement
import uuid

router = APIRouter(prefix="/seances", tags=["Séances"])


# ─────────────────────────────
# SCHÉMAS
# ─────────────────────────────

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


# ─────────────────────────────
# LISTER LES SÉANCES
# ─────────────────────────────

@router.get("/", response_model=List[SeanceResponse])
def get_seances(
    db: Session = Depends(get_db),
    membre=Depends(get_current_membre)
):
    seances = db.query(Seance).order_by(
        Seance.date_seance.desc()
    ).all()

    result = []

    for s in seances:

        lot = db.query(Lot).filter(
            Lot.id == s.lot_id
        ).first()

        bouffeur_nom = None

        if s.bouffeur_id:
            b = db.query(Membre).filter(
                Membre.id == s.bouffeur_id
            ).first()

            if b:
                bouffeur_nom = f"{b.prenom} {b.nom}"

        result.append(
            SeanceResponse(
                id=str(s.id),
                lot_id=str(s.lot_id),
                date_seance=str(s.date_seance),
                heure_ouverture=str(s.heure_ouverture),
                heure_cloture=str(s.heure_cloture),
                statut=str(s.statut),
                bouffeur_nom=bouffeur_nom,
                montant_pot=float(s.montant_pot) if s.montant_pot else 0,
                lot_nom=lot.nom if lot else None,
            )
        )

    return result


# ─────────────────────────────
# PLANIFIER UNE SÉANCE
# ─────────────────────────────

@router.post("/")
def planifier_seance(
    data: SeanceCreate,
    db: Session = Depends(get_db),
    fondateur=Depends(get_fondateur)
):

    lot = db.query(Lot).filter(
        Lot.id == data.lot_id
    ).first()

    if not lot:
        raise HTTPException(
            status_code=404,
            detail="Lot introuvable"
        )

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

    return {
        "message": "Séance planifiée avec succès",
        "id": str(seance.id)
    }


# ─────────────────────────────
# OUVRIR UNE SÉANCE
# ─────────────────────────────

@router.put("/{seance_id}/ouvrir")
def ouvrir_seance(
    seance_id: str,
    db: Session = Depends(get_db),
    fondateur=Depends(get_fondateur)
):

    seance = db.query(Seance).filter(
        Seance.id == seance_id
    ).first()

    if not seance:
        raise HTTPException(
            status_code=404,
            detail="Séance introuvable"
        )

    if seance.statut != StatutSeance.PLANIFIEE:
        raise HTTPException(
            status_code=400,
            detail="La séance n'est pas PLANIFIEE"
        )

    seance.statut = StatutSeance.OUVERTE

    db.commit()

    adhesions = db.query(AdhesionLot).filter(
        AdhesionLot.lot_id == seance.lot_id
    ).all()

    lot = db.query(Lot).filter(
        Lot.id == seance.lot_id
    ).first()

    for a in adhesions:

        notif = Notification(
            id=str(uuid.uuid4()),
            membre_id=a.membre_id,
            tontine_id=seance.tontine_id,
            type_notif=TypeNotif.RAPPEL_COTISATION,
            titre="Séance ouverte",
            message=f"La séance du {seance.date_seance} est ouverte."
        )

        db.add(notif)

    db.commit()

    return {
        "message": "Séance ouverte avec succès"
    }


# ─────────────────────────────
# CLÔTURER UNE SÉANCE
# ─────────────────────────────

@router.put("/{seance_id}/cloturer")
def cloturer_seance(
    seance_id: str,
    db: Session = Depends(get_db),
    fondateur=Depends(get_fondateur)
):

    seance = db.query(Seance).filter(
        Seance.id == seance_id
    ).first()

    if not seance:
        raise HTTPException(
            status_code=404,
            detail="Séance introuvable"
        )

    if seance.statut != StatutSeance.OUVERTE:
        raise HTTPException(
            status_code=400,
            detail="La séance doit être OUVERTE"
        )

    lot = db.query(Lot).filter(
        Lot.id == seance.lot_id
    ).first()

    paiements = db.query(Paiement).filter(
        Paiement.seance_id == seance_id,
        Paiement.statut == "VALIDE"
    ).all()

    montant_pot = sum(
        float(p.montant_lot)
        for p in paiements
    )

    seance.montant_pot = montant_pot

    prochain = db.query(AdhesionLot).filter(
        AdhesionLot.lot_id == seance.lot_id,
        AdhesionLot.a_bouffe == False,
        AdhesionLot.numero_tirage != None,
    ).order_by(
        AdhesionLot.numero_tirage
    ).first()

    if prochain:

        prochain.a_bouffe = True
        prochain.date_bouffement = datetime.utcnow()

        seance.bouffeur_id = prochain.membre_id

    seance.statut = StatutSeance.CLOTUREE

    db.commit()

    return {
        "message": "Séance clôturée",
        "montant_pot": montant_pot,
        "bouffeur_id": str(prochain.membre_id) if prochain else None
    }


# ─────────────────────────────
# SÉANCES D'UN LOT
# ─────────────────────────────

@router.get("/lot/{lot_id}")
def seances_par_lot(
    lot_id: str,
    db: Session = Depends(get_db),
    membre=Depends(get_current_membre)
):

    seances = db.query(Seance).filter(
        Seance.lot_id == lot_id
    ).order_by(
        Seance.date_seance
    ).all()

    return [
        {
            "id": str(s.id),
            "date": str(s.date_seance),
            "statut": str(s.statut),
            "heure_ouverture": str(s.heure_ouverture),
            "heure_cloture": str(s.heure_cloture),
            "montant_pot": float(s.montant_pot) if s.montant_pot else 0
        }
        for s in seances
    ]