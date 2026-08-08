"""
config.py — Configuration management
====================================
Loads environment variables from .env file and provides configuration values.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

class Config:
    """Config manager singleton."""
    
    @property
    def openai_api_key(self) -> str:
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            # We don't crash immediately on import, but we will raise an error when the key is requested.
            raise ValueError(
                "OPENAI_API_KEY is not set in environment or .env file. "
                "Please configure it to use the interview engine."
            )
        return key

    @property
    def anthropic_api_key(self) -> str:
        return os.getenv("ANTHROPIC_API_KEY", "")

    @property
    def llm_model(self) -> str:
        return os.getenv("LLM_MODEL", "gpt-4o-mini")

    @property
    def llm_temperature(self) -> float:
        try:
            return float(os.getenv("LLM_TEMPERATURE", "0.5"))
        except ValueError:
            return 0.5

# Singleton instance
settings = Config()
