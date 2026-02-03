from pydantic_settings import BaseSettings
from pydantic import SecretStr

class Settings(BaseSettings):
    DRIVER_BOT_TOKEN: SecretStr
    ADMIN_BOT_TOKEN: SecretStr
    
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "teamhub"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    
    # Only Group ID is used for auth
    ADMIN_GROUP_ID: int

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
