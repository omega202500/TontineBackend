from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.types import Numeric
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.database import Base
from app.models.enums import TypeCassation, StatutCassation


class Cassation(Base):
    __tablename__ = "cassations"

    # ID principal
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Relation avec tontines
    tontine_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tontines.id"),
        nullable=False
    )

    # Relation avec lots
    lot_id = Column(
        UUID(as_uuid=True),
        ForeignKey("lots.id"),
        nullable=False
    )

    # Type de cassation
    type_cassation = Column(
        SAEnum(TypeCassation),
        nullable=False
    )

    # Montants
    montant_total = Column(
        Numeric(10, 2),
        nullable=True
    )

    montant_par_membre = Column(
        Numeric(10, 2),
        nullable=True
    )

    # Date prévue de distribution
    date_distribution = Column(
        String(10),
        nullable=False
    )

    # Statut
    statut = Column(
        SAEnum(StatutCassation),
        default=StatutCassation.PLANIFIEE
    )

    # Date de création
    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )