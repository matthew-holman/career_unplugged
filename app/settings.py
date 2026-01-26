from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

env_path = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=env_path,
        env_file_encoding="utf-8",
        extra="allow",
    )

    TARGET_ENV: str = Field(default="local-dev")

    DB_NAME: str = Field(default="fastapi_db")
    DB_USER: str = Field(default="postgres")
    DB_PASSWORD: str = Field(default="postgres")

    DB_HOST: str = Field(default="0.0.0.0")
    DB_PORT: int = Field(default=5432)

    DB_POOL_SIZE: int = Field(default=4)
    DB_MAX_OVERFLOW: int = Field(default=2)
    DB_BATCH_SIZE: int = Field(default=500)
    ATS_SCRAPER_DELAY_SECONDS: float = Field(default=0.2)

    BASE_URL: str = Field(default="0.0.0.0")
    PORT: int = Field(default=5005)
    NUM_WORKERS: int = Field(default=0)

    API_VERSION: str = Field(default="0.1.0")
    IMAGE_TAG: str = Field(default="local-latest")

    RUN_NETWORK_TESTS: str = Field(default="true")


settings = Settings()
