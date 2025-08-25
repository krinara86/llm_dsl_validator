# src/core/state_manager.py
import json
from typing import Dict, Any
from pathlib import Path

class StateManager:
    """Manages persistent state for the application."""
    
    def __init__(self, state_file: Path):
        self.state_file = state_file
        self._ensure_state_file()
    
    def _ensure_state_file(self):
        """Ensure the state file and its directory exist."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.state_file.exists():
            self.save({})
    
    def load(self) -> Dict[str, Any]:
        """Load state from file."""
        try:
            with open(self.state_file, 'r') as f:
                content = f.read()
                if not content:
                    return self._default_state()
                return json.loads(content)
        except (json.JSONDecodeError, FileNotFoundError):
            return self._default_state()
    
    def save(self, state: Dict[str, Any]):
        """Save state to file."""
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def _default_state(self) -> Dict[str, Any]:
        """Return the default state structure."""
        return {
            "venues": {},
            "sessions": [],
            "venue_bookings": {}
        }