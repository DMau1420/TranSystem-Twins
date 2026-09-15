class Settings:
    DATABASE_URL: str = "postgresql://gis:password@localhost:5432/gis"
    SECRET_KEY: str = "Bon Voyage"
    ALGORITHM: str = "HS256"

settings = Settings()