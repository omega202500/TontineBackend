from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.types import Numeric
from app.database import Base
from app.models.enums import MotifAide, StatutAide
from datetime import datetime
import uuid

class AideSention(Base):
    __tablename__ = "aides_sention"

    id          = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    membre_id   = Column(String(36), ForeignKey("membres.id"), nullable=False)
    tontine_id  = Column(String(36), ForeignKey("tontines.id"), nullable=False)
    motif       = Column(SAEnum(MotifAide), nullable=False)
    montant     = Column(Numeric(10, 2), nullable=False)
    description = Column(Text, nullable=True)
    statut      = Column(SAEnum(StatutAide), default=StatutAide.EN_ATTENTE)
    valide_par  = Column(String(36), ForeignKey("membres.id"), nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)