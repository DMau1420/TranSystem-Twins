import os

class Settings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://gis:password@localhost:5432/gis"
    )
    SECRET_KEY: str = os.getenv("SECRET_KEY", "Bon Voyage")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")

settings = Settings()