from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.routers.auth import get_current_membre, get_fondateur
from app.models.sention import AideSention
from app.models.paiement import Paiement
from app.models.enums import MotifAide, StatutAide, TypeNotif
from app.models.notification import Notification
from app.models.membre import Membre
import uuid

router = APIRouter(prefix="/sention", tags=["Sention"])

class AideCreate(BaseModel):
    motif: str
    montant: float
    description: Optional[str] = None
    tontine_id: Optional[str] = None

@router.get("/solde")
def get_solde_sention(db: Session = Depends(get_db), membre=Depends(get_current_membre)):
    """Solde de la caisse sention = somme des sentions perçues."""
    paiements = db.query(Paiement).filter(Paiement.statut == "VALIDE").all()
    solde = sum(float(p.montant_sention) for p in paiements if p.montant_sention)
    # Déduire les aides déjà versées
    aides = db.query(AideSention).filter(AideSention.statut == StatutAide.VERSEE).all()
    total_verse = sum(float(a.montant) for a in aides)
    return {"solde": max(0, solde - total_verse)}

@router.get("/mes-aides")
def mes_aides(db: Session = Depends(get_db), membre=Depends(get_current_membre)):
    aides = db.query(AideSention).filter(
        AideSention.membre_id == membre.id
    ).order_by(AideSention.created_at.desc()).all()
    return [{
        "id": a.id,
        "motif": a.motif,
        "montant": float(a.montant),
        "description": a.description,
        "statut": a.statut,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    } for a in aides]

@router.post("/demander-aide")
def demander_aide(data: AideCreate, db: Session = Depends(get_db), membre=Depends(get_current_membre)):
    # Récupérer la première tontine disponible si pas précisée
    tontine_id = data.tontine_id
    if not tontine_id:
        from app.models.lot import AdhesionLot, Lot
        adhesion = db.query(AdhesionLot).filter(
            AdhesionLot.membre_id == membre.id
        ).first()
        if adhesion:
            lot = db.query(Lot).filter(Lot.id == adhesion.lot_id).first()
            if lot:
                tontine_id = lot.tontine_id

    if not tontine_id:
        raise HTTPException(status_code=400, detail="Vous n'êtes membre d'aucune tontine")

    aide = AideSention(
        id=str(uuid.uuid4()),
        membre_id=membre.id,
        tontine_id=tontine_id,
        motif=data.motif,
        montant=data.montant,
        description=data.description,
        statut=StatutAide.EN_ATTENTE,
    )
    db.add(aide)

    # Notifier les fondateurs
    from app.models.membre import StatutMembre
    fondateurs = db.query(Membre).filter(
        Membre.est_fondateur == True,
        Membre.statut == StatutMembre.ACTIF
    ).all()
    for f in fondateurs:
        notif = Notification(
            id=str(uuid.uuid4()),
            membre_id=f.id,
            tontine_id=tontine_id,
            type_notif=TypeNotif.AIDE_SENTION,
            titre="🆘 Demande d'aide ",
            message=f"{membre.prenom} {membre.nom} demande {data.montant:,.0f} FCFA "
                    f"pour : {data.motif} — {data.description or ''}",
        )
        db.add(notif)
    db.commit()
    return {"message": "Demande d'aide soumise avec succès"}

@router.get("/toutes-aides")
def toutes_aides(db: Session = Depends(get_db), fondateur=Depends(get_fondateur)):
    aides = db.query(AideSention).order_by(AideSention.created_at.desc()).all()
    result = []
    for a in aides:
        m = db.query(Membre).filter(Membre.id == a.membre_id).first()
        result.append({
            "id": a.id,
            "membre": f"{m.prenom} {m.nom}" if m else "Inconnu",
            "telephone": m.telephone if m else None,
            "motif": a.motif,
            "montant": float(a.montant),
            "description": a.description,
            "statut": a.statut,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        })
    return result

@router.put("/approuver/{aide_id}")
def approuver_aide(aide_id: str, db: Session = Depends(get_db), fondateur=Depends(get_fondateur)):
    aide = db.query(AideSention).filter(AideSention.id == aide_id).first()
    if not aide:
        raise HTTPException(status_code=404, detail="Aide introuvable")
    aide.statut = StatutAide.VERSEE
    aide.valide_par = fondateur.id
    # Notifier le membre
    notif = Notification(
        id=str(uuid.uuid4()),
        membre_id=aide.membre_id,
        tontine_id=aide.tontine_id,
        type_notif=TypeNotif.AIDE_SENTION,
        titre="✅ sention approuvée",
        message=f"Votre demande d'aide de {float(aide.montant):,.0f} FCFA ({aide.motif}) "
                f"a été approuvée. Le montant sera versé sous peu.",
    )
    db.add(notif)
    db.commit()
    return {"message": "Aide approuvée et membre notifié"}

@router.put("/refuser/{aide_id}")
def refuser_aide(aide_id: str, db: Session = Depends(get_db), fondateur=Depends(get_fondateur)):
    aide = db.query(AideSention).filter(AideSention.id == aide_id).first()
    if not aide:
        raise HTTPException(status_code=404, detail="Aide introuvable")
    aide.statut = StatutAide.REFUSEE
    db.commit()
    return {"message": "Aide refusée"}