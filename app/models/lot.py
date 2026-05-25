from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.types import Numeric
from app.database import Base
from app.models.enums import StatutLot, OptionIntegration
from datetime import datetime
import uuid

class Lot(Base):
    __tablename__ = "lots"

    id                   = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tontine_id           = Column(String(36), ForeignKey("tontines.id"), nullable=False)
    nom                  = Column(String(100), nullable=False)
    montant_cotisation   = Column(Numeric(10, 2), nullable=False)
    nb_max_membres       = Column(Integer, default=30)
    cycle_actuel         = Column(Integer, default=1)
    option_integration   = Column(SAEnum(OptionIntegration), default=OptionIntegration.ANTICIPEE)
    statut               = Column(SAEnum(StatutLot), default=StatutLot.ACTIF)
    prochain_bouffeur_id = Column(String(36), ForeignKey("membres.id"), nullable=True)
    created_at           = Column(DateTime, default=datetime.utcnow)


class AdhesionLot(Base):
    __tablename__ = "adhesions_lot"

    id              = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    membre_id       = Column(String(36), ForeignKey("membres.id"), nullable=False)
    lot_id          = Column(String(36), ForeignKey("lots.id"), nullable=False)
    numero_tirage   = Column(Integer, nullable=True)
    a_bouffe        = Column(Boolean, default=False)
    date_bouffement = Column(DateTime, nullable=True)
    statut          = Column(String(255), default="ACTIF")
    membres_passes  = Column(Integer, default=0)
    date_adhesion   = Column(DateTime, default=datetime.utcnow)