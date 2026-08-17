from datetime import datetime, timedelta, timezone
import jwt
from pwdlib import PasswordHash
from core.config import settings

pwd_context = PasswordHash.recommended()

def hash_password(password: str):
    return pwd_context.hash(password)

def verifica_password(plain_pwd: str, hashed_pwd: str) -> bool:
    return pwd_context.verify(plain_pwd, hashed_pwd)

def create_access_token(data: dict, expires_delta:timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + ( expires_delta or timedelta(minutes=60))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)