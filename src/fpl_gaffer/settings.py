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

    # User settings
    FPL_MANAGER_ID: int = 2723529

    # FPL API settings
    fpl_api_base_url: str = "https://fantasy.premierleague.com/api"

    # FPL News Searcher settings
    TAVILY_API_KEY: str
    tavily_search_depth: str = "advanced"
    tavily_max_search_results: int = 3
    tavily_search_topic: str = "news"

settings = Settings()
