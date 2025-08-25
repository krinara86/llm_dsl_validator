# src/core/config.py
import os
from pathlib import Path

class AppConfig:
    """Central configuration for the application."""
    
    # API Configuration
    LLM_API_URL = "http://localhost:11434/api/generate"
    DEFAULT_MODEL = "llama3:8b"
    TOGETHER_API_URL = "https://api.together.xyz/v1/chat/completions"
    
    # Path Configuration
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    STATE_FILE = PROJECT_ROOT / "notebooks" / "state.json"
    
    # Document Processing
    DOCUMENT_LENGTH_THRESHOLD = 300
    
    @staticmethod
    def get_grammar_path(domain: str) -> Path:
        """Get the path to a domain's grammar file."""
        return AppConfig.PROJECT_ROOT / "src" / "domains" / domain / "grammar.dsl"
    
    @staticmethod
    def load_api_key():
        """Load API keys from .env file."""
        try:
            dotenv_path = AppConfig.PROJECT_ROOT / '.env'
            if not dotenv_path.exists():
                return
            
            with open(dotenv_path) as f:
                for line in f:
                    if line.strip() and not line.strip().startswith('#'):
                        key, value = line.strip().split('=', 1)
                        value = value.strip("'\"")
                        os.environ[key] = value
        except Exception:
            pass

# Load API keys on module import
AppConfig.load_api_key()
