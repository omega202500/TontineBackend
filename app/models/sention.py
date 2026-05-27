from sqlalchemy import Column, DateTime, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.types import Numeric
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.database import Base
from app.models.enums import MotifAide, StatutAide


class AideSention(Base):
    __tablename__ = "aides_sention"

    # ID principal
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Relation avec membres
    membre_id = Column(
        UUID(as_uuid=True),
        ForeignKey("membres.id"),
        nullable=False
    )

    # Relation avec tontines
    tontine_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tontines.id"),
        nullable=False
    )

    # Motif de l'aide/sanction
    motif = Column(
        SAEnum(MotifAide),
        nullable=False
    )

    # Montant
    montant = Column(
        Numeric(10, 2),
        nullable=False
    )

    # Description
    description = Column(
        Text,
        nullable=True
    )

    # Statut
    statut = Column(
        SAEnum(StatutAide),
        default=StatutAide.EN_ATTENTE
    )

    # Membre validateur
    valide_par = Column(
        UUID(as_uuid=True),
        ForeignKey("membres.id"),
        nullable=True
    )

    # Date de création
    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )