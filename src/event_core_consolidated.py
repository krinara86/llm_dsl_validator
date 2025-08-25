# src/event_core_consolidated.py
"""
Consolidated module that combines all refactored components.
This is a temporary solution for testing while transitioning to the full refactored structure.
"""

import os
import json
import re
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# ============== CONFIG ==============

class AppConfig:
    """Central configuration."""
    LLM_API_URL = "http://localhost:11434/api/generate"
    DEFAULT_MODEL = "llama3:8b"
    TOGETHER_API_URL = "https://api.together.xyz/v1/chat/completions"
    PROJECT_ROOT = Path(__file__).parent.parent
    STATE_FILE = PROJECT_ROOT / "notebooks" / "state.json"
    DOCUMENT_LENGTH_THRESHOLD = 300
    
    @staticmethod
    def get_grammar_path(domain: str) -> Path:
        return AppConfig.PROJECT_ROOT / "src" / "domains" / domain / "grammar.dsl"
    
    @staticmethod
    def load_api_key():
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

AppConfig.load_api_key()

# ============== SCHEMA ==============

DOMAIN_SCHEMA = {
    "create_venue": {
        "required": ["name", "capacity", "has_av_system"],
        "optional": [],
        "param_types": {
            "name": "text",
            "capacity": "number",
            "has_av_system": "boolean"
        },
        "permissions": ["admin"]
    },
    "modify_venue": {
        "required": ["name"],
        "optional": ["capacity", "has_av_system"],
        "param_types": {
            "name": "text",
            "capacity": "number",
            "has_av_system": "boolean"
        },
        "permissions": ["admin"]
    },
    "schedule_session": {
        "required": ["name", "in_venue", "expected_attendees", "requires_av"],
        "optional": ["hosted_by"],
        "param_types": {
            "name": "text",
            "in_venue": "venue_selection",
            "expected_attendees": "number",
            "requires_av": "boolean",
            "hosted_by": "text"
        },
        "permissions": ["admin", "scheduler"]
    }
}

# ============== STATE MANAGER ==============

class StateManager:
    """Manages persistent state."""
    def __init__(self, state_file: Path):
        self.state_file = state_file
        self._ensure_state_file()
    
    def _ensure_state_file(self):
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.state_file.exists():
            self.save({})
    
    def load(self) -> Dict[str, Any]:
        try:
            with open(self.state_file, 'r') as f:
                content = f.read()
                if not content:
                    return self._default_state()
                return json.loads(content)
        except (json.JSONDecodeError, FileNotFoundError):
            return self._default_state()
    
    def save(self, state: Dict[str, Any]):
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def _default_state(self) -> Dict[str, Any]:
        return {"venues": {}, "sessions": [], "venue_bookings": {}}

# Continue with other components...
# This would include LLMClient, TaskExtractor, MessageFormatter, etc.

