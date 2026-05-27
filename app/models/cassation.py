from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.types import Numeric
from app.database import Base
from app.models.enums import TypeCassation, StatutCassation
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
import uuid

class Cassation(Base):
    __tablename__ = "cassations"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=lambda: uuid.uuid4())
    tontine_id         = Column(String(36), ForeignKey("tontines.id"), nullable=False)
    lot_id             = Column(String(36), ForeignKey("lots.id"), nullable=True)
    type_cassation     = Column(SAEnum(TypeCassation), nullable=False)
    montant_total      = Column(Numeric(10, 2), nullable=True)
    montant_par_membre = Column(Numeric(10, 2), nullable=True)
    date_distribution  = Column(String(10), nullable=False)
    statut             = Column(SAEnum(StatutCassation), default=StatutCassation.PLANIFIEE)
    created_at         = Column(DateTime, default=datetime.utcnow)