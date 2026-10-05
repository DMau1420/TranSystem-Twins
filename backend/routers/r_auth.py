from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from core.database import get_db
from core.exceptions import InvalidCredentialsException
from models.md_user import User
from schemas.sc_user import CreateUser, LoginUser, Token, UpdateUser, UserResponse
from services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["autenticación"])

@router.post(
    "/register",
    response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def register(user_in: CreateUser, db: Session = Depends(get_db)):
    return AuthService.registrar_user(db=db, user_in=user_in)

@router.post("/login", response_model=Token, summary="Iniciar sesión")
async def login(
    request: Request,
    db: Session = Depends(get_db),
):
    content_type = request.headers.get("content-type", "")
    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        correo = form.get("username") or form.get("correo")
        password = form.get("password")
    else:
        body = await request.json()
        correo = body.get("correo") or body.get("username")
        password = body.get("password")

    if not correo or not password:
        raise InvalidCredentialsException()

    return AuthService.autenticar_user(db=db, correo=str(correo), pwd=str(password))

@router.put("/me", response_model=UserResponse, summary="Modificar datos del usuario autenticado (PUT)")
@router.patch("/me", response_model=UserResponse, summary="Modificar datos del usuario autenticado (PATCH)")
def update_current_user(
    user_in: UpdateUser,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.obtener_usuario_actual),
):
    return AuthService.modificar_user(db=db, usuario=current_user, user_in=user_in)

@router.delete("/me", summary="Eliminar el usuario autenticado (DELETE)")
def delete_current_user(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.obtener_usuario_actual),
):
    AuthService.eliminar_user(db=db, usuario=current_user)
    return {"mensaje": "Usuario eliminado correctamente"}