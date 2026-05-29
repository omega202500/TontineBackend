"""
app/routers/prets.py
Routes CRUD pour les demandes de prêt.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid

from app.database import get_db
from app.routers.auth import get_current_user, get_fondateur
from app.models.membre import Membre

router = APIRouter(prefix="/prets", tags=["Prêts"])


# ── Modèle Pret (si vous n'avez pas encore la table) ─────────────────────────
# Si app/models/pret.py existe déjà, supprimez ce bloc et importez le vôtre :
# from app.models.pret import Pret

from sqlalchemy import Column, String, Numeric, ForeignKey, DateTime, Enum as SAEnum
from app.database import Base
import enum

class StatutPret(str, enum.Enum):
    EN_ATTENTE = "EN_ATTENTE"
    APPROUVE   = "APPROUVE"
    REFUSE     = "REFUSE"
    EN_COURS   = "EN_COURS"
    REMBOURSE  = "REMBOURSE"
    DEFAUT     = "DEFAUT"

class Pret(Base):
    __tablename__ = "prets"

    id                 = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    emprunteur_id      = Column(String(36), ForeignKey("membres.id"), nullable=False)
    tontine_id         = Column(String(36), nullable=True)
    montant            = Column(Numeric(12, 2), nullable=False)
    montant_total_du   = Column(Numeric(12, 2), nullable=True)   # montant + intérêts
    montant_rembourse  = Column(Numeric(12, 2), default=0)
    date_echeance      = Column(String(20), nullable=False)
    motif              = Column(String(500), nullable=True)
    statut             = Column(SAEnum(StatutPret), default=StatutPret.EN_ATTENTE)
    valide_par         = Column(String(36), nullable=True)
    created_at         = Column(DateTime, default=datetime.utcnow)
    updated_at         = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── Schémas ───────────────────────────────────────────────────────────────────

class PretCreate(BaseModel):
    montant:       float
    date_echeance: str
    motif:         Optional[str] = None
    tontine_id:    Optional[str] = None

class PretReponse(BaseModel):
    pret_id: str
    accepte: bool


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/")
def list_prets(
    db: Session = Depends(get_db),
    membre: Membre = Depends(get_current_user),
):
    """Retourne tous les prêts du membre connecté."""
    prets = db.query(Pret).filter(
        Pret.emprunteur_id == str(membre.id)
    ).order_by(Pret.created_at.desc()).all()

    return [_format_pret(p) for p in prets]


@router.post("/")
def creer_pret(
    data: PretCreate,
    db: Session = Depends(get_db),
    membre: Membre = Depends(get_current_user),
):
    """Soumet une demande de prêt."""
    if data.montant <= 0:
        raise HTTPException(status_code=400, detail="Le montant doit être positif")

    # Taux 5%/mois — calculer le total dû
    montant_total = data.montant * 1.05

    pret = Pret(
        id=str(uuid.uuid4()),
        emprunteur_id=str(membre.id),
        tontine_id=data.tontine_id,
        montant=data.montant,
        montant_total_du=montant_total,
        montant_rembourse=0,
        date_echeance=data.date_echeance,
        motif=data.motif,
        statut=StatutPret.EN_ATTENTE,
    )
    db.add(pret)
    db.commit()
    db.refresh(pret)

    return {
        "message": "Demande de prêt soumise. En attente d'approbation du fondateur.",
        "pret":    _format_pret(pret),
    }


@router.get("/{pret_id}")
def get_pret(
    pret_id: str,
    db: Session = Depends(get_db),
    membre: Membre = Depends(get_current_user),
):
    pret = db.query(Pret).filter(Pret.id == pret_id).first()
    if not pret:
        raise HTTPException(status_code=404, detail="Prêt introuvable")
    if str(pret.emprunteur_id) != str(membre.id):
        raise HTTPException(status_code=403, detail="Accès interdit")
    return _format_pret(pret)


@router.post("/{pret_id}/approuver")
def approuver_pret(
    pret_id: str,
    db: Session = Depends(get_db),
    fondateur=Depends(get_fondateur),
):
    """Le fondateur approuve un prêt."""
    pret = db.query(Pret).filter(Pret.id == pret_id).first()
    if not pret:
        raise HTTPException(status_code=404, detail="Prêt introuvable")
    if pret.statut != StatutPret.EN_ATTENTE:
        raise HTTPException(status_code=400, detail="Ce prêt a déjà été traité")

    pret.statut     = StatutPret.APPROUVE
    pret.valide_par = str(fondateur.id)
    pret.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Prêt approuvé", "pret": _format_pret(pret)}


@router.post("/{pret_id}/refuser")
def refuser_pret(
    pret_id: str,
    db: Session = Depends(get_db),
    fondateur=Depends(get_fondateur),
):
    """Le fondateur refuse un prêt."""
    pret = db.query(Pret).filter(Pret.id == pret_id).first()
    if not pret:
        raise HTTPException(status_code=404, detail="Prêt introuvable")

    pret.statut     = StatutPret.REFUSE
    pret.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Prêt refusé", "pret": _format_pret(pret)}


# ── Helper ────────────────────────────────────────────────────────────────────

def _format_pret(p: Pret) -> dict:
    return {
        "id":                str(p.id),
        "montant":           float(p.montant),
        "montant_total_du":  float(p.montant_total_du or p.montant),
        "montant_rembourse": float(p.montant_rembourse or 0),
        "date_echeance":     p.date_echeance,
        "motif":             p.motif,
        "statut":            p.statut,
        "created_at":        p.created_at.isoformat() if p.created_at else None,
    }