from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://campushire:change_me@postgres:5432/opportunity_db"
    identity_service_url: str = "http://identity-service:8001"
    rabbitmq_url: str = "amqp://campushire:change_me@rabbitmq:5672/"
    storage_backend: str = "local"
    local_storage_path: str = "/data/uploads"
    azure_storage_connection_string: str = ""
    azure_storage_container: str = "campushire"
    cors_origins: str = "http://localhost:3000"


settings = Settings()
