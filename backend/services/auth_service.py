from sqlalchemy.orm import Session

from core.exceptions import EmailAlreadyRegisteredException, InvalidCredentialsException
from core.security import create_access_token, hash_password, verifica_password
from models.md_user import User
from schemas.sc_user import Token, CreateUser

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
                "rol": usuario.rol,
                "nombre": usuario.nombre,
                "apodo": usuario.apodo,
                "correo": usuario.correo,
            }
        )
        return Token(access_token = access_token, token_type="bearer")