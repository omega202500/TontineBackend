
from sqlalchemy import Column, String, Numeric, ForeignKey, DateTime
from datetime import datetime
import uuid
from app.database import Base

class Epargne(Base):
    __tablename__ = "epargnes"

    id         = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    membre_id  = Column(String(36), ForeignKey("membres.id"), unique=True, nullable=False)
    solde      = Column(Numeric(12, 2), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)