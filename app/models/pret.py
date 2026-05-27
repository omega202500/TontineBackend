from sqlalchemy import Column, Integer, DateTime, ForeignKey, Text, Enum as SAEnum, String
from sqlalchemy.types import Numeric
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.database import Base
from app.models.enums import StatutPret


class Pret(Base):
    __tablename__ = "prets"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    emprunteur_id = Column(
        UUID(as_uuid=True),
        ForeignKey("membres.id"),
        nullable=False
    )

    tontine_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tontines.id"),
        nullable=False
    )

    montant = Column(Numeric(10, 2), nullable=False)

    taux_interet = Column(
        Numeric(5, 2),
        default=5.0
    )

    penalite_retard = Column(
        Numeric(10, 2),
        default=1000
    )

    montant_total_du = Column(
        Numeric(10, 2),
        nullable=True
    )

    montant_rembourse = Column(
        Numeric(10, 2),
        default=0
    )

    date_echeance = Column(
        String(10),
        nullable=False
    )

    motif = Column(Text, nullable=True)

    statut = Column(
        SAEnum(StatutPret),
        default=StatutPret.EN_ATTENTE
    )

    nb_relances = Column(
        Integer,
        default=0
    )

    valide_par = Column(
        UUID(as_uuid=True),
        ForeignKey("membres.id"),
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


class Remboursement(Base):
    __tablename__ = "remboursements"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    pret_id = Column(
        UUID(as_uuid=True),
        ForeignKey("prets.id"),
        nullable=False
    )

    montant = Column(
        Numeric(10, 2),
        nullable=False
    )

    date_paiement = Column(
        DateTime,
        default=datetime.utcnow
    )

    type_remboursement = Column(
        String(255),
        default="PARTIEL"
    )