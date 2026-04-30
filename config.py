import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o")
    MAX_TOKENS: int = 2048
    TEMPERATURE: float = 0.3
    NEWS_MAX_ARTICLES: int = int(os.getenv("NEWS_MAX_ARTICLES", "10"))
    SENTIMENT_ENABLED: bool = os.getenv("SENTIMENT_ENABLED", "true").lower() != "false"
    RAG_ENABLED: bool = os.getenv("RAG_ENABLED", "true").lower() != "false"
    RAG_PERSIST_DIR: str = os.getenv("RAG_PERSIST_DIR", "")  # 空=默认 data/chroma_db


config = Config()
