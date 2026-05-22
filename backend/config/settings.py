import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    ACTIVE_PROVIDER: str = os.getenv("ACTIVE_PROVIDER", "")
    MODEL: str = os.getenv("MODEL", "claude-sonnet-4-6")

    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY", "")
    TOGETHER_API_KEY: str = os.getenv("TOGETHER_API_KEY", "")

    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

    BROWSER_USE_MAX_STEPS: int = int(os.getenv("BROWSER_USE_MAX_STEPS", "20"))
    SEARCH_ROOT: str = os.getenv("SEARCH_ROOT","~/Documents")
    NEWS_API_KEY: str = os.getenv("NEWS_API_KEY")


settings = Settings()

