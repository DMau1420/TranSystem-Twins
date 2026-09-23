import uuid6
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base

class User(Base):
    __tablename__ = "usuarios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid6.uuid7)
    nombre = Column(String(255), nullable=False)
    apodo = Column(String(255), nullable=True)
    correo = Column(String(255), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    rol = Column(String(50), nullable=False, default="Investigador")