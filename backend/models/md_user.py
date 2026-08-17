from sqlalchemy.sql.expression import null
import uuid6
from sqlalchemy import Column, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base

class User(Base):
    __tablename__ = "usuarios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid6.uuid7)
    nombre = Column(String(255), nullable=False)
    correo = Column(String(255), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    rol = Column(String(255), nullable=False, default="Investigador")