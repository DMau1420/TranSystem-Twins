from uuid import UUID
import jwt
from fastapi import Depends
from sqlalchemy.orm import Session

from core.database import get_db
from core.exceptions import (
    EmailAlreadyRegisteredException,
    InvalidCredentialsException,
    InvalidTokenException,
    UserNotFoundException,
)
from core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    oauth2_scheme,
    verifica_password,
)
from models.md_user import User
from schemas.sc_user import CreateUser, Token, UpdateUser

class AuthService:
    @staticmethod
    def registrar_user(db: Session, user_in: CreateUser) -> User:
        usuario_existente = db.query(User).filter(User.correo == user_in.correo).first()

        if usuario_existente:
            raise EmailAlreadyRegisteredException()
            
        nuevo_usuario = User(
            nombre = user_in.nombre,
            apodo = user_in.apodo,
            correo = user_in.correo,
            password = hash_password(user_in.password),
            rol = user_in.rol
        )
        db.add(nuevo_usuario)
        db.commit()
        db.refresh(nuevo_usuario)
        return nuevo_usuario

    @staticmethod
    def autenticar_user(db: Session, correo: str, pwd: str) -> Token:
        usuario = db.query(User).filter(User.correo == correo).first()
        if not usuario or not verifica_password(pwd, usuario.password):
            raise InvalidCredentialsException()

        access_token = create_access_token(
            data={
                "sub": str(usuario.id),
                "uuid": str(usuario.id),
                "rol": usuario.rol,
                "nombre": usuario.nombre,
                "apodo": usuario.apodo,
                "correo": usuario.correo,
            }
        )
        return Token(access_token = access_token, token_type="bearer")

    @staticmethod
    def obtener_usuario_actual(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db),
    ) -> User:
        try:
            payload = decode_access_token(token)
            user_uuid_str = payload.get("uuid") or payload.get("sub")
            if not user_uuid_str:
                raise InvalidTokenException()
            user_uuid = UUID(user_uuid_str)
        except (jwt.PyJWTError, ValueError):
            raise InvalidTokenException()

        usuario = db.query(User).filter(User.id == user_uuid).first()
        if not usuario:
            raise UserNotFoundException()
        return usuario

    @staticmethod
    def modificar_user(db: Session, usuario: User, user_in: UpdateUser) -> User:
        if user_in.correo and user_in.correo != usuario.correo:
            usuario_existente = (
                db.query(User)
                .filter(User.correo == user_in.correo, User.id != usuario.id)
                .first()
            )
            if usuario_existente:
                raise EmailAlreadyRegisteredException()
            usuario.correo = user_in.correo

        if user_in.nombre is not None:
            usuario.nombre = user_in.nombre
        if user_in.apodo is not None:
            usuario.apodo = user_in.apodo
        if user_in.password is not None:
            usuario.password = hash_password(user_in.password)
        if user_in.rol is not None:
            usuario.rol = user_in.rol

        db.commit()
        db.refresh(usuario)
        return usuario

    @staticmethod
    def eliminar_user(db: Session, usuario: User) -> None:
        db.delete(usuario)
        db.commit()

get_current_user = AuthService.obtener_usuario_actual