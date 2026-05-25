from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.types import Numeric
from app.database import Base
from app.models.enums import StatutSeance
from datetime import datetime
import uuid

class Seance(Base):
    __tablename__ = "seances"

    id              = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tontine_id      = Column(String(36), ForeignKey("tontines.id"), nullable=False)
    lot_id          = Column(String(36), ForeignKey("lots.id"), nullable=False)
    date_seance     = Column(String(10), nullable=False)
    heure_ouverture = Column(String(5), nullable=False, default="08:00")
    heure_cloture   = Column(String(5), nullable=False, default="18:00")
    statut          = Column(SAEnum(StatutSeance), default=StatutSeance.PLANIFIEE)
    bouffeur_id     = Column(String(36), ForeignKey("membres.id"), nullable=True)
    montant_pot     = Column(Numeric(10, 2), nullable=True)
    pv_url          = Column(String(255), nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)