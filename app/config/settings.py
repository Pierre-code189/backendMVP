from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "MVP API"
    debug: bool = False

    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "mvp_db"
    postgres_host: str = "db"
    postgres_port: int = 5432

    class Config:
        env_file = ".env"


settings = Settings()
