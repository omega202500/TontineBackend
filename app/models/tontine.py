from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.types import Numeric
from app.database import Base
from app.models.enums import FrequenceTontine, StatutTontine
from datetime import datetime
import uuid

class Tontine(Base):
    __tablename__ = 'tontines'

    id              = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nom             = Column(String(100), nullable=False)
    description     = Column(Text, nullable=True)
    frequence       = Column(SAEnum(FrequenceTontine), default=FrequenceTontine.HEBDOMADAIRE)
    jour_semaine    = Column(String(20), nullable=True)
    heure_debut     = Column(String(5), nullable=False, default='08:00')
    heure_fin       = Column(String(5), nullable=False, default='18:00')
    date_debut      = Column(String(10), nullable=False)
    reglement       = Column(Text, nullable=True)
    statut          = Column(SAEnum(StatutTontine), default=StatutTontine.ACTIVE)
    fondateur_id    = Column(String(36), ForeignKey('membres.id'), nullable=False)
    nb_max_membres  = Column(Integer, default=30)
    montant_sention = Column(Numeric(10, 2), default=500)
    delai_grace_h   = Column(Integer, default=24)
    delai_echange_h = Column(Integer, default=48)
    quorum_vote     = Column(Integer, default=50)
    duree_vote_h    = Column(Integer, default=72)
    created_at      = Column(DateTime, default=datetime.utcnow)
