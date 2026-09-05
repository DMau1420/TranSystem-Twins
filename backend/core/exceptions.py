from fastapi import HTTPException, status


class EmailAlreadyRegisteredException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico ya se encuentra registrado.",
        )


class InvalidCredentialsException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas.",
            headers={"WWW-Authenticate": "Bearer"},
        )


class CantSavePointException(HTTPException):
    def __init__(self, point_id, err):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al guardar el archivo para el ID {point_id}: {str(err)}",
        )


class DoesntExistPointsException(HTTPException):
    def __init__(self, point_id):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontro ningun punt guardado con el ID {point_id}"
        )


class CantReadPointException(HTTPException):
    def __init__(self, point_id, err):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al leer el archivo {point_id}: {err}"
        )
