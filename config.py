import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o")
    MAX_TOKENS: int = 2048
    TEMPERATURE: float = 0.3


config = Config()
