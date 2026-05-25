from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Enum as SAEnum
from app.database import Base
from app.models.enums import TypeLitige, StatutLitige
from datetime import datetime
import uuid

class Litige(Base):
    __tablename__ = "litiges"

    id          = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    signale_par = Column(String(36), ForeignKey("membres.id"), nullable=False)
    tontine_id  = Column(String(36), ForeignKey("tontines.id"), nullable=False)
    type_litige = Column(SAEnum(TypeLitige), nullable=False)
    description = Column(Text, nullable=False)
    statut      = Column(SAEnum(StatutLitige), default=StatutLitige.OUVERT)
    decision    = Column(Text, nullable=True)
    date_limite = Column(DateTime, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)