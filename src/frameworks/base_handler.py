# src/frameworks/base_handler.py
"""Abstract base class for domain handlers (Lark, LionWeb, etc.)"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

class BaseDomainHandler(ABC):
    """Abstract interface for domain-specific handlers."""
    
    @abstractmethod
    def __init__(self, domain: str):
        """Initialize handler for a specific domain."""
        pass
    
    @abstractmethod
    def load_mappings(self) -> Dict[str, Any]:
        """Load NL mappings (connector.yml or JSON mappings)."""
        pass
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """Get domain schema information for validation."""
        pass
    
    @abstractmethod
    def validate_params(self, action: str, params: Dict[str, Any], role: str) -> Dict[str, Any]:
        """
        Validate parameters for an action.
        Returns: {
            'valid': bool,
            'missing': List[str],
            'errors': List[str]
        }
        """
        pass
    
    @abstractmethod
    def build_artifact(self, task_details: Dict[str, Any], role: str) -> str:
        """
        Build execution artifact (DSL text for Lark, JSON for LionWeb).
        Returns the artifact as a string.
        """
        pass
    
    @abstractmethod
    def execute(self, artifact: str, role: str, task_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the artifact and return results.
        Returns: {
            'status': 'success' | 'error',
            'message': str,
            'new_state': Dict (for mutations),
            'results': List (for queries)
        }
        """
        pass
    
    @abstractmethod
    def get_state(self) -> Dict[str, Any]:
        """Get current domain state."""
        pass
    
    @abstractmethod
    def save_state(self, state: Dict[str, Any]):
        """Save domain state."""
        pass
    
    def get_state_manager(self):
        """Get state manager (for backward compatibility)."""
        # Default implementation for compatibility
        return self