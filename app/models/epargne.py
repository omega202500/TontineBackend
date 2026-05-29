# app/models/epargne.py

from sqlalchemy import Column, String, Numeric, ForeignKey, DateTime
from datetime import datetime
import uuid
from app.database import Base

from app.models.epargne import Epargne