
import os
from dotenv import load_dotenv
from sqlalchemy.engine import URL

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

    SQLALCHEMY_DATABASE_URI = URL.create(
        drivername="mysql+pymysql",
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.getenv("DB_NAME"),
        query={"charset": "utf8mb4"},
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"

    JWT_ACCESS_TOKEN_EXPIRES = 60 * 60 * 8

    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000"
        ).split(",")
        if origin.strip()
    ]

    DB_SSL_CA = os.getenv("DB_SSL_CA", "").strip()

    if DB_SSL_CA:
        ca_path = (
            DB_SSL_CA
            if os.path.isabs(DB_SSL_CA)
            else os.path.join(BASE_DIR, DB_SSL_CA)
        )

        SQLALCHEMY_ENGINE_OPTIONS = {
            "connect_args": {
                "ssl": {
                    "ca": os.path.abspath(ca_path)
                }
            }
        }

    @classmethod
    def validate(cls):
        required = {
            "SECRET_KEY": cls.SECRET_KEY,
            "JWT_SECRET_KEY": cls.JWT_SECRET_KEY,
            "DB_HOST": os.getenv("DB_HOST"),
            "DB_USER": os.getenv("DB_USER"),
            "DB_NAME": os.getenv("DB_NAME"),
            "DB_PASSWORD": os.getenv("DB_PASSWORD"),
            "FIELD_ENCRYPTION_KEY": os.getenv("FIELD_ENCRYPTION_KEY"),
        }

        missing = [
            name for name, value in required.items()
            if not value or len(value) < 32
            if name in ("SECRET_KEY", "JWT_SECRET_KEY")
        ]

        missing.extend(
            name for name, value in required.items()
            if name not in ("SECRET_KEY", "JWT_SECRET_KEY")
            and not value
        )

        if missing:
            raise RuntimeError(
                "Missing or weak environment variables: "
                + ", ".join(missing)
            )

        if not cls.DB_SSL_CA:
            raise RuntimeError("DB_SSL_CA is missing from .env")

        ca_path = (
            cls.DB_SSL_CA
            if os.path.isabs(cls.DB_SSL_CA)
            else os.path.join(BASE_DIR, cls.DB_SSL_CA)
        )

        if not os.path.isfile(ca_path):
            raise RuntimeError(
                f"Aiven CA certificate not found: {ca_path}"
            )
