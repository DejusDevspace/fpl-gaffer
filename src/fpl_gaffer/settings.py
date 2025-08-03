from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application settings
    app_name: str = "FPL Gaffer"

    # FPL API settings
    fpl_api_base_url: str = "https://fantasy.premierleague.com/api"

    # FPL News Searcher settings

settings = Settings()