from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application settings
    APP_NAME: str = "FPL Gaffer"

    # User data settings
    FPL_MANAGER_ID: int = 2723529


    # FPL Official API settings
    FPL_API_BASE_URL: str = "https://fantasy.premierleague.com/api"

    # FPL News Search Client settings
    TAVILY_API_KEY: str
    TAVILY_SEARCH_DEPTH: str = "advanced"
    TAVILY_MAX_SEARCH_RESULTS: int = 3
    TAVILY_SEARCH_TOPIC: str = "news"
    INCLUDE_LLM_SUMMARY: str | bool = "advanced"

settings = Settings()
