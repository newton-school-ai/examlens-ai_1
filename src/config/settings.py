"""ExamLens AI configuration."""

from enum import Enum
from pydantic_settings import BaseSettings


class ExamType(str, Enum):
    UNIVERSITY = "university"
    JEE = "jee"
    NEET = "neet"
    GATE = "gate"
    CAT = "cat"
    UPSC = "upsc"
    SSC = "ssc"
    BANKING = "banking"
    CUSTOM = "custom"


class QuestionType(str, Enum):
    MCQ = "mcq"
    SUBJECTIVE = "subjective"
    NUMERICAL = "numerical"
    TRUE_FALSE = "true_false"
    FILL_BLANK = "fill_blank"
    MATCH = "match"


class UserRole(str, Enum):
    STUDENT = "student"
    CONTRIBUTOR = "contributor"
    ADMIN = "admin"


class Settings(BaseSettings):
    """Application settings loaded from .env file."""

    # Database
    database_url: str = "postgresql://localhost/examlens_dev"

    # LLM
    llm_provider: str = "groq"
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-70b-versatile"

    # OCR
    ocr_primary: str = "tesseract"
    ocr_fallback: str = "easyocr"
    ocr_confidence_threshold: float = 0.7
    ocr_languages: list[str] = ["en", "hi"]

    # Handwritten OCR
    trocr_model: str = "microsoft/trocr-base-handwritten"

    # Math extraction
    math_extractor: str = "pix2tex"

    # Layout detection
    layout_model: str = "yolov8"
    layout_confidence: float = 0.5

    # Scraper
    scraper_rate_limit: int = 2  # seconds between requests
    scraper_max_pages: int = 50

    # Answer generation
    answer_max_tokens: int = 2000
    answer_temperature: float = 0.3
    verification_sources: int = 2  # number of sources to cross-check

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
