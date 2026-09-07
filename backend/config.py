from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./florida_freediving.db"
    officer_password_hash: str = ""
    session_secret: str = "development-only-change-me"
    cookie_secure: bool = False
    allowed_origins: str = "http://localhost:5173,http://localhost:8000"

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    @model_validator(mode="after")
    def reject_unsafe_production_defaults(self):
        if self.cookie_secure and (
            not self.officer_password_hash or self.session_secret == "development-only-change-me"
        ):
            raise ValueError(
                "Production requires an officer password hash and unique session secret"
            )
        return self

    @property
    def origins(self) -> set[str]:
        return {origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()}

    @property
    def cookie_name(self) -> str:
        return "__Host-officer_session" if self.cookie_secure else "officer_session"


@lru_cache
def get_settings() -> Settings:
    return Settings()
