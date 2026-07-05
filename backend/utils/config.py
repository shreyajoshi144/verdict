"""
NOTE: backend/utils/config.py and backend/utils/logger.py weren't part of the
files you shared, so these are minimal, best-guess implementations that match
what every other backend file expects (settings.DB_HOST, settings.GROQ_MODEL,
get_logger(__name__), etc.). If you already have working versions of these two
files, keep yours and ignore these — everything else in this drop only depends
on the attribute/function names below, not the implementation.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_NAME: str = os.getenv("DB_NAME", "verdict")
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")

    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama3-70b-8192")

    APP_ENV: str = os.getenv("APP_ENV", "development")

    JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-only-insecure-secret-change-me")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", str(60 * 24 * 7)))  # 7 days

    def __post_init_checks__(self):
        if self.APP_ENV == "production" and self.JWT_SECRET == "dev-only-insecure-secret-change-me":
            raise RuntimeError(
                "JWT_SECRET is still the development default in a production environment. "
                "Set a real secret via the JWT_SECRET env var."
            )


settings = Settings()
settings.__post_init_checks__()
