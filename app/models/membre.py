from click import UUID
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Enum as SAEnum
from app.database import Base
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum

class StatutMembre(str, enum.Enum):
    EN_ATTENTE = "EN_ATTENTE"   # demande soumise, en attente de validation
    ACTIF      = "ACTIF"        # approuvé et actif
    SUSPENDU   = "SUSPENDU"     # inactif (ne cotise plus)
    REFUSE     = "REFUSE"       # demande rejetée
    ARCHIVE    = "ARCHIVE"      # décès ou exclusion définitive

class Membre(Base):
    __tablename__ = "membres"

    id = Column(UUID(as_uuid=True),primary_key=True, default=uuid.uuid4)
    nom           = Column(String(100), nullable=False)
    prenom        = Column(String(100), nullable=False)
    age           = Column(Integer, nullable=True)
    ville         = Column(String(100), nullable=True)
    telephone     = Column(String(20), unique=True, nullable=False, index=True)
    numero_cni    = Column(String(50), nullable=True)
    photo_url     = Column(String(255), nullable=True)

    # ✅ Le mot de passe est défini dès la demande (hashé)
    # Il reste inutilisable tant que statut = EN_ATTENTE
    password      = Column(String(255), nullable=True)

    est_fondateur = Column(Boolean, default=False)
    statut        = Column(SAEnum(StatutMembre), default=StatutMembre.EN_ATTENTE)
    lot_souhaite  = Column(String(255), nullable=True)
    mobile_money  = Column(String(20), nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)