from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from core.database import get_db
from schemas.sc_user import LoginUser, Token, CreateUser, UserResponse
from services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["autenticación"])

@router.post(
    "/register",
    response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def register(user_in: CreateUser, db: Session = Depends(get_db)):
    return AuthService.registrar_user(db=db, user_in=user_in)

@router.post("/login", response_model=Token)
def login(
    credentials: LoginUser,
    db: Session = Depends(get_db)
):
    return AuthService.autenticar_user(db=db, correo=credentials.correo, pwd = credentials.password)