from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://campushire:change_me@postgres:5432/communications_db"
    rabbitmq_url: str = "amqp://campushire:change_me@rabbitmq:5672/"
    smtp_host: str = "sandbox.smtp.mailtrap.io"
    smtp_port: int = 2525
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@campushire.local"
    cors_origins: str = "http://localhost:3000"


settings = Settings()
