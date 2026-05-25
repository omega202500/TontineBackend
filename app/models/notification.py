from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Enum as SAEnum
from app.database import Base
from app.models.enums import TypeNotif
from datetime import datetime
import uuid

class Notification(Base):
    __tablename__ = "notifications"

    id         = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    membre_id  = Column(String(36), ForeignKey("membres.id"), nullable=False)
    tontine_id = Column(String(36), ForeignKey("tontines.id"), nullable=True)
    type_notif = Column(SAEnum(TypeNotif), nullable=False)
    titre      = Column(String(200), nullable=False)
    message    = Column(Text, nullable=False)
    canal      = Column(String(255), default="PUSH")
    lu         = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)