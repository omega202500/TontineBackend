from click import UUID
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.types import Numeric
from app.database import Base
from app.models.enums import StatutPaiement, ModePaiement
from datetime import datetime
import uuid

class Paiement(Base):
    __tablename__ = "paiements"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    membre_id             = Column(UUID(as_uuid=True), ForeignKey("membres.id"), nullable=False)
    seance_id             = Column(UUID(as_uuid=True), ForeignKey("seances.id"), nullable=False)
    lot_id                = Column(UUID(as_uuid=True), ForeignKey("lots.id"), nullable=False)
    montant_lot           = Column(Numeric(10, 2), nullable=False)
    montant_sention       = Column(Numeric(10, 2), default=0)
    montant_total         = Column(Numeric(10, 2), nullable=False)
    heure_envoi           = Column(DateTime, nullable=False)
    retard                = Column(Boolean, default=False)
    mode_paiement         = Column(SAEnum(ModePaiement), default=ModePaiement.MOBILE_MONEY)
    reference_transaction = Column(String(255), nullable=True)
    statut                = Column(SAEnum(StatutPaiement), default=StatutPaiement.EN_ATTENTE)
    motif_rejet           = Column(String(255), nullable=True)
    confirme_par          = Column(String(255), nullable=True)
    created_at            = Column(DateTime, default=datetime.utcnow)