"""
app/routers/epargne.py
Routes pour la gestion de l'épargne des membres.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

from app.database import get_db
from app.routers.auth import get_current_user
from app.models.membre import Membre
from app.models.paiement import Paiement
from app.models.enums import StatutPaiement

router = APIRouter(prefix="/epargne", tags=["Épargne"])


# ── Modèle Epargne en base (si vous n'avez pas encore la table) ──────────────
# Si vous avez déjà un modèle Epargne, supprimez ce bloc et importez le vôtre.

from sqlalchemy import Column, String, Numeric, ForeignKey, DateTime
from app.database import Base

class Epargne(Base):
    """Table d'épargne : un enregistrement par membre."""
    __tablename__ = "epargnes"
    __table_args__ = {'extend_existing': True}  

    id         = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    membre_id  = Column(String(36), ForeignKey("membres.id"), unique=True, nullable=False)
    solde      = Column(Numeric(12, 2), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── Schémas ───────────────────────────────────────────────────────────────────

class DepotRequest(BaseModel):
    montant: float


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/")
def get_epargne(
    db: Session = Depends(get_db),
    membre: Membre = Depends(get_current_user),
):
    """Retourne le solde épargne du membre connecté."""
    # Créer l'enregistrement s'il n'existe pas encore
    epargne = db.query(Epargne).filter(Epargne.membre_id == str(membre.id)).first()
    if not epargne:
        epargne = Epargne(
            id=str(uuid.uuid4()),
            membre_id=str(membre.id),
            solde=0,
        )
        db.add(epargne)
        db.commit()
        db.refresh(epargne)

    return {
        "membre_id": str(membre.id),
        "solde":     float(epargne.solde),
        "updated_at": epargne.updated_at.isoformat() if epargne.updated_at else None,
    }


@router.post("/deposer")
def deposer_epargne(
    data: DepotRequest,
    db: Session = Depends(get_db),
    membre: Membre = Depends(get_current_user),
):
    """
    Enregistre un dépôt d'épargne (appelé après confirmation PawaPay).
    En production ce endpoint est appelé automatiquement par /payments/status
    via _enregistrer_epargne(). Ce endpoint reste utile pour les tests manuels.
    """
    if data.montant <= 0:
        raise HTTPException(status_code=400, detail="Le montant doit être positif")

    epargne = db.query(Epargne).filter(Epargne.membre_id == str(membre.id)).first()
    if not epargne:
        epargne = Epargne(
            id=str(uuid.uuid4()),
            membre_id=str(membre.id),
            solde=0,
        )
        db.add(epargne)
        db.flush()

    epargne.solde      = float(epargne.solde) + data.montant
    epargne.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(epargne)

    return {
        "message":    "Dépôt enregistré",
        "solde":      float(epargne.solde),
        "montant":    data.montant,
    }


@router.post("/retirer")
def retirer_epargne(
    data: DepotRequest,
    db: Session = Depends(get_db),
    membre: Membre = Depends(get_current_user),
):
    """Retire un montant de l'épargne (après payout PawaPay confirmé)."""
    epargne = db.query(Epargne).filter(Epargne.membre_id == str(membre.id)).first()
    if not epargne or float(epargne.solde) < data.montant:
        raise HTTPException(status_code=400, detail={
            "code":    "SOLDE_INSUFFISANT",
            "message": f"Solde insuffisant. Disponible : {float(epargne.solde) if epargne else 0:,.0f} FCFA",
        })

    epargne.solde      = float(epargne.solde) - data.montant
    epargne.updated_at = datetime.utcnow()
    db.commit()

    return {
        "message": "Retrait enregistré",
        "solde":   float(epargne.solde),
    }