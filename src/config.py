import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    gemini_api_key: str
    gemini_model: str
    db_path: str
    demo_mode: bool
    demo_daily_call_limit: int


def get_config() -> Config:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    return Config(
        gemini_api_key=api_key,
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        db_path=os.getenv("DB_PATH", "data/feedback.db"),
        demo_mode=os.getenv("DEMO_MODE", "false").strip().lower() == "true",
        demo_daily_call_limit=int(os.getenv("DEMO_DAILY_CALL_LIMIT", "300")),
    )
