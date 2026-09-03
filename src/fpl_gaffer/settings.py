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

    # Messages settings
    MESSAGES_AFTER_SUMMARY: int = 2

    # FPL Official API settings
    FPL_API_BASE_URL: str = "https://fantasy.premierleague.com/api"
    FPL_API_TIMEOUT_SECONDS: float = 10.0
    FPL_BOOTSTRAP_CACHE_TTL_SECONDS: int = 3600  # 1 hour
    FPL_FIXTURES_CACHE_TTL_SECONDS: int = 3600  # 1 hour

    # FPL News Search Client settings
    TAVILY_API_KEY: str = ""
    TAVILY_SEARCH_DEPTH: str = "advanced"
    TAVILY_MAX_SEARCH_RESULTS: int = 3
    TAVILY_SEARCH_TOPIC: str = "news"
    INCLUDE_LLM_SUMMARY: str | bool = "advanced"

    # Expert / scout source allow-list for the expert tips tool.
    FPL_EXPERT_DOMAINS: list[str] = [
        "fantasyfootballscout.co.uk",
        "premierleague.com",
        "fplreview.com",
        "fantasyfootballpundit.com",
        "fplgeneral.co.uk",
    ]

    # Tool limits
    MAX_FORM_GAMEWEEKS: int = 10
    MAX_COMPARE_PLAYERS: int = 5
    MAX_CAPTAIN_HISTORY_GAMEWEEKS: int = 8

    # LLM provider settings
    LLM_PROVIDER: str = "groq"  # "groq" | "openai"
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    LLM_TEMPERATURE: float = 0.2

    # Provider API keys (only the active provider's key needs to be set)
    GROQ_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # Resource limits
    MAX_RETRIES: int = 1

    # Cost control limits (single global tier today; see core/limits.py for the per-user hook)
    MAX_TOOL_CALLS_PER_TURN: int = 6
    MAX_CONTEXT_TOKENS_BEFORE_SUMMARY: int = 100000

    # Subscription tier limits
    TIER_LIMITS: dict = {
        "free": {
            "daily_turn_limit": 15,
            "max_tool_calls_per_turn": 6,
            "reasoning_effort": "low",
        },  # Increased temporarily for launch
        "basic": {"daily_turn_limit": 10, "max_tool_calls_per_turn": 6, "reasoning_effort": "medium"},
        "pro": {"daily_turn_limit": 20, "max_tool_calls_per_turn": 10, "reasoning_effort": "high"},
    }

    # Billing settings
    STRIPE_API_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_BASIC_PRICE_ID: str = ""

    PAYSTACK_SECRET_KEY: str = ""
    PAYSTACK_BASIC_PLAN_CODE: str = ""

    # Memory settings
    SHORT_TERM_MEMORY_DB_PATH: str = "./src/fpl_gaffer/data/memory.db"

    # ---------- API SETTINGS ---------- #
    # FastAPI Settings
    DEBUG: bool = True

    # LangFuse Settings
    LANGFUSE_ENABLED: bool = False
    LANGFUSE_API_KEY: str | None = None

    # Database Settings
    DATABASE_URL: str = ""

    # Metrics settings
    MODEL_COST_PER_1K: float = 0.0

    # Supabase settings
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # WhatsApp/Twilio settings
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_NUMBER: str = ""
    TWILIO_VERIFY_SERVICE_SID: str = ""
    TWILIO_VERIFY_CHANNEL: str = "whatsapp"
    WHATSAPP_VERIFY_TOKEN: str = ""

    # Onboarding settings
    ONBOARDING_URL: str = ""


settings = Settings()
