from sqlalchemy import Column, DateTime, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.database import Base
from app.models.enums import TypeLitige, StatutLitige


class Litige(Base):
    __tablename__ = "litiges"

    # ID principal
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Membre ayant signalé le litige
    signale_par = Column(
        UUID(as_uuid=True),
        ForeignKey("membres.id"),
        nullable=False
    )

    # Tontine concernée
    tontine_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tontines.id"),
        nullable=False
    )

    # Type de litige
    type_litige = Column(
        SAEnum(TypeLitige),
        nullable=False
    )

    # Description
    description = Column(
        Text,
        nullable=False
    )

    # Statut
    statut = Column(
        SAEnum(StatutLitige),
        default=StatutLitige.OUVERT
    )

    # Décision finale
    decision = Column(
        Text,
        nullable=True
    )

    # Date limite de traitement
    date_limite = Column(
        DateTime,
        nullable=True
    )

    # Date de création
    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )