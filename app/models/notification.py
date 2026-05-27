from sqlalchemy import UUID, Column, String, Boolean, DateTime, ForeignKey, Text, Enum as SAEnum
from app.database import Base
from app.models.enums import TypeNotif
from datetime import datetime
import uuid

class Notification(Base):
    __tablename__ = "notifications"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    membre_id  = Column(UUID(as_uuid=True), ForeignKey("membres.id"), nullable=False)
    tontine_id = Column(UUID(as_uuid=True), ForeignKey("tontines.id"), nullable=True)
    type_notif = Column(SAEnum(TypeNotif), nullable=False)
    titre      = Column(String(200), nullable=False)
    message    = Column(Text, nullable=False)
    canal      = Column(String(255), default="PUSH")
    lu         = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)