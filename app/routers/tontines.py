from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.database import get_db
from app.routers.auth import get_current_membre, get_fondateur
from app.models.tontine import Tontine
from app.models.lot import Lot, AdhesionLot
from app.models.enums import StatutTontine
from app.models.membre import Membre
import uuid

router = APIRouter(prefix="/tontines", tags=["Tontines"])

# ── Schémas ──
class TontineCreate(BaseModel):
    nom: str
    description: Optional[str] = None
    frequence: str = "HEBDOMADAIRE"
    jour_semaine: Optional[str] = "LUNDI"
    heure_debut: str = "08:00"
    heure_fin: str = "18:00"
    date_debut: str
    reglement: Optional[str] = None
    nb_max_membres: int = 30

class TontineResponse(BaseModel):
    id: str
    nom: str
    description: Optional[str]
    frequence: str
    jour_semaine: Optional[str]
    heure_debut: str
    heure_fin: str
    date_debut: str
    statut: str
    nb_lots: Optional[int] = 0
    nb_membres: Optional[int] = 0

    class Config:
        from_attributes = True

# ── Créer une tontine ──
@router.post("/")
def creer_tontine(
    data: TontineCreate,
    db: Session = Depends(get_db),
    fondateur=Depends(get_fondateur)
):
    tontine = Tontine(
        id=str(uuid.uuid4()),
        nom=data.nom,
        description=data.description,
        frequence=data.frequence,
        jour_semaine=data.jour_semaine,
        heure_debut=data.heure_debut,
        heure_fin=data.heure_fin,
        date_debut=data.date_debut,
        reglement=data.reglement,
        nb_max_membres=data.nb_max_membres,
        fondateur_id=fondateur.id,
    )
    db.add(tontine)
    db.commit()
    db.refresh(tontine)
    return {"message": f"Tontine '{tontine.nom}' créée", "id": tontine.id}

# ── Lister toutes les tontines ──
@router.get("/", response_model=List[TontineResponse])
def get_tontines(
    db: Session = Depends(get_db),
    membre=Depends(get_current_membre)
):
    tontines = db.query(Tontine).filter(
        Tontine.statut != StatutTontine.CLOTUREE
    ).all()
    result = []
    for t in tontines:
        nb_lots = db.query(Lot).filter(Lot.tontine_id == t.id).count()
        # Compter membres uniques via adhésions
        lots_ids = [l.id for l in db.query(Lot).filter(Lot.tontine_id == t.id).all()]
        nb_membres = 0
        if lots_ids:
            nb_membres = db.query(AdhesionLot).filter(
                AdhesionLot.lot_id.in_(lots_ids)
            ).distinct(AdhesionLot.membre_id).count()
        result.append(TontineResponse(
            id=t.id, nom=t.nom, description=t.description,
            frequence=t.frequence, jour_semaine=t.jour_semaine,
            heure_debut=t.heure_debut, heure_fin=t.heure_fin,
            date_debut=t.date_debut, statut=t.statut,
            nb_lots=nb_lots, nb_membres=nb_membres,
        ))
    return result

# ── Tontines du membre connecté ──
@router.get("/mes-tontines")
def mes_tontines(
    db: Session = Depends(get_db),
    membre=Depends(get_current_membre)
):
    # Récupérer les lots où le membre est adhérent
    adhesions = db.query(AdhesionLot).filter(
        AdhesionLot.membre_id == membre.id
    ).all()
    lots_ids = [a.lot_id for a in adhesions]
    tontines_ids = set()
    for lot_id in lots_ids:
        lot = db.query(Lot).filter(Lot.id == lot_id).first()
        if lot:
            tontines_ids.add(lot.tontine_id)

    result = []
    for tid in tontines_ids:
        t = db.query(Tontine).filter(Tontine.id == tid).first()
        if t:
            # Lots du membre dans cette tontine
            mes_lots = []
            for lot_id in lots_ids:
                lot = db.query(Lot).filter(
                    Lot.id == lot_id,
                    Lot.tontine_id == tid
                ).first()
                if lot:
                    adhesion = db.query(AdhesionLot).filter(
                        AdhesionLot.lot_id == lot_id,
                        AdhesionLot.membre_id == membre.id
                    ).first()
                    mes_lots.append({
                        "lot_id": lot.id,
                        "nom": lot.nom,
                        "montant": float(lot.montant_cotisation),
                        "numero_tirage": adhesion.numero_tirage if adhesion else None,
                        "a_bouffe": adhesion.a_bouffe if adhesion else False,
                    })
            result.append({
                "id": t.id, "nom": t.nom,
                "jour": t.jour_semaine,
                "heure_debut": t.heure_debut,
                "heure_fin": t.heure_fin,
                "statut": t.statut,
                "mes_lots": mes_lots,
            })
    return result

# ── Détail d'une tontine ──
@router.get("/{tontine_id}")
def get_tontine(
    tontine_id: str,
    db: Session = Depends(get_db),
    membre=Depends(get_current_membre)
):
    t = db.query(Tontine).filter(Tontine.id == tontine_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tontine introuvable")
    lots = db.query(Lot).filter(Lot.tontine_id == tontine_id).all()
    return {
        "id": t.id, "nom": t.nom, "description": t.description,
        "frequence": t.frequence, "jour_semaine": t.jour_semaine,
        "heure_debut": t.heure_debut, "heure_fin": t.heure_fin,
        "date_debut": t.date_debut, "statut": t.statut,
        "reglement": t.reglement,
        "lots": [{"id": l.id, "nom": l.nom, "montant": float(l.montant_cotisation),
                  "statut": l.statut} for l in lots],
    }

# ── Stats globales (fondateur) ──
@router.get("/stats/globales")
def stats_globales(
    db: Session = Depends(get_db),
    fondateur=Depends(get_fondateur)
):
    from app.models.tontine import Paiement, Seance
    tontines = db.query(Tontine).filter(Tontine.fondateur_id == fondateur.id).all()
    total_caisse = 0
    for t in tontines:
        paiements = db.query(Paiement).join(
            Seance, Paiement.seance_id == Seance.id
        ).filter(
            Seance.tontine_id == t.id,
            Paiement.statut == "VALIDE"
        ).all()
        total_caisse += sum(float(p.montant_total) for p in paiements)
    return {
        "nb_tontines": len(tontines),
        "total_caisse": total_caisse,
    }