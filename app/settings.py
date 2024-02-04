from pathlib import Path

from pydantic import BaseSettings, Field
from pydantic.main import BaseConfig


class Settings(BaseSettings):
    class Config(BaseConfig):
        parent_path = Path(__file__).parent
        env_file = f"{parent_path}/../.env"
        env_file_encoding = "utf-8"

    TARGET_ENV: str = Field(default="local-dev", env="TARGET_ENV")

    DB_NAME: str = Field(..., env="POSTGRES_DB")
    DB_USER: str = Field(..., env="FASTAPI_DB_USER")
    DB_PASSWORD: str = Field(..., env="FASTAPI_DB_PASSWORD")

    DB_HOST: str = Field(default="localhost", env="POSTGRES_HOST")
    DB_PORT: int = Field(default=5432, env="POSTGRES_PORT")

    DB_POOL_SIZE: int = Field(default=4, env="DB_POOL_SIZE")
    DB_MAX_OVERFLOW: int = Field(default=2, env="DB_MAX_OVERFLOW")

    BASE_URL = Field(default="0.0.0.0")
    PORT = Field(default=8000)
    NUM_WORKERS = Field(default=2)

    API_VERSION: str = Field(default="0.1.0", env="API_VERSION")
    IMAGE_TAG: str = Field(default="local-latest", env="IMAGE_TAG")


config = Settings()
