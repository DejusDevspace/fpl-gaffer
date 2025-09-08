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


    # FPL API settings
    FPL_API_BASE_URL: str = "https://fantasy.premierleague.com/api"

    # FPL News Searcher settings
    TAVILY_API_KEY: str
    TAVILY_SEARCH_DEPTH: str = "advanced"
    TAVILY_MAX_SEARCH_RESULTS: int = 3
    TAVILY_SEARCH_TOPIC: str = "news"

    # TODO: Change params case to uppercase
    # FPL News Processor settings
    user_player_relevance_score: int = 3
    user_team_relevance_score: int = 1
    fpl_news_relevance_score: int = 2
    max_relevant_news: int = 15

settings = Settings()
