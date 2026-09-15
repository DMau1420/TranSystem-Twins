from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr

class CreateUser(BaseModel):
    nombre: str
    correo: EmailStr
    password: str
    rol:str = "Investigador"

class UserResponse(BaseModel):
    id: UUID
    nombre: str
    correo: EmailStr
    rol: str
    
    model_config = ConfigDict(from_attributes=True)

class LoginUser(BaseModel):
    correo: EmailStr
    password: str

class Token(BaseModel):
    access_token : str
    token_type: str