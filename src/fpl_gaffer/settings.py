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
    FPL_MANAGER_ID: int =  2723529

    # Messages settings
    MESSAGES_AFTER_SUMMARY: int = 2
    MESSAGES_SUMMARY_TRIGGER: int = 4

    # FPL Official API settings
    FPL_API_BASE_URL: str = "https://fantasy.premierleague.com/api"

    # FPL News Search Client settings
    TAVILY_API_KEY: str
    TAVILY_SEARCH_DEPTH: str = "advanced"
    TAVILY_MAX_SEARCH_RESULTS: int = 3
    TAVILY_SEARCH_TOPIC: str = "news"
    INCLUDE_LLM_SUMMARY: str | bool = "advanced"

    # Groq API settings
    GROQ_API_KEY: str
    GROQ_MODEL_NAME: str = "llama-3.3-70b-versatile"
    GROQ_MODEL_TEMPERATURE: float = 0.0

    # Resource limits
    MAX_RETRIES: int = 1

    # Memory settings
    SHORT_TERM_MEMORY_DB_PATH: str = "./src/fpl_gaffer/data/memory.db"

    # ---------- API SETTINGS ---------- #
    # FastAPI Settings
    DEBUG: bool = True

    # LangFuse Settings
    LANGFUSE_ENABLED: bool = False
    LANGFUSE_API_KEY: str | None

    # Database Settings
    DATABASE_URL: str

    # Metrics settings
    MODEL_COST_PER_1K: float = 0.0

    # Supabase settings
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str

    # WhatsApp/Twilio settings
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_NUMBER: str = ""
    WHATSAPP_VERIFY_TOKEN: str = ""


settings = Settings()
