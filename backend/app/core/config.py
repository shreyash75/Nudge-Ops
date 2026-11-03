from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    openrouter_api_key: str = ""
    openrouter_model: str = ""
    kubeconfig_path: str = ""
    backend_cors_origins: str = "http://localhost:3000"
    database_url: str = "postgresql+psycopg://nudgeops:nudgeops@localhost:5432/nudgeops"
    auth_secret: str = ""
    jwt_secret_path: str = "data/jwt-secret.key"
    auth_token_expire_minutes: int = 60 * 24 * 7

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


settings = Settings()
