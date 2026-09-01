"""Application configuration."""
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_PATH = os.getenv("DATABASE_PATH", "waraqah.db")
SYMBOLS_PATH = os.getenv("SYMBOLS_PATH", "symbols.csv")
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
