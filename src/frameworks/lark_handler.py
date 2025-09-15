# src/frameworks/lark_handler.py
"""Lark-specific domain handler that wraps existing functionality."""

from typing import Dict, List, Any
from pathlib import Path
from .base_handler import BaseDomainHandler
from ..core.state_manager import StateManager
from ..core.config import AppConfig
from ..core.dsl_builder import DSLBuilder
from ..core.connector_loader import load_connector
from ..framework.base_interpreter import execute_dsl
from ..domains.event.interpreter import EventInterpreter
from ..domains.event.schema import DOMAIN_SCHEMA

class LarkDomainHandler(BaseDomainHandler):
    """Handler for Lark-based domains (preserves existing functionality)."""
    
    def __init__(self, domain: str):
        """Initialize with existing components."""
        self.domain = domain
        self.state_manager = StateManager(AppConfig.STATE_FILE)
        self.dsl_builder = DSLBuilder()
        self.connector = load_connector(domain)
        # Import domain-specific schema dynamically
        if domain == 'event':
            from ..domains.event.schema import DOMAIN_SCHEMA
            self.schema = DOMAIN_SCHEMA
        else:
            raise ValueError(f"Unknown Lark domain: {domain}")
    
    def load_mappings(self) -> Dict[str, Any]:
        """Return the existing connector data."""
        return self.connector
    
    def get_schema(self) -> Dict[str, Any]:
        """Return the domain schema."""
        return self.schema
    
    def validate_params(self, action: str, params: Dict[str, Any], role: str) -> Dict[str, Any]:
        """Validate using existing schema logic."""
        if action not in self.schema:
            return {
                'valid': False,
                'missing': [],
                'errors': [f"Unknown action: {action}"]
            }
        
        action_schema = self.schema[action]
        
        # Check permissions
        allowed_roles = action_schema.get("permissions", [])
        if role not in allowed_roles:
            return {
                'valid': False,
                'missing': [],
                'errors': [f"Role '{role}' not authorized for action '{action}'"]
            }
        
        # Check required params
        required = action_schema.get("required", [])
        missing = []
        for param in required:
            if param not in params or params[param] in [None, "", "unknown", "N/A"]:
                missing.append(param)
        
        return {
            'valid': len(missing) == 0,
            'missing': missing,
            'errors': []
        }
    
    def build_artifact(self, task_details: Dict[str, Any], role: str) -> str:
        """Build DSL code using existing DSLBuilder."""
        return self.dsl_builder.build(task_details, role)
    
    def execute(self, artifact: str, role: str, task_details: Dict[str, Any]) -> Dict[str, Any]:
        """Execute DSL code using existing interpreter."""
        try:
            state = self.state_manager.load()
            
            # Use domain-specific interpreter
            if self.domain == 'event':
                interpreter = EventInterpreter(state, role)
            else:
                raise ValueError(f"No interpreter for domain: {self.domain}")
            
            result = execute_dsl(
                artifact,
                AppConfig.get_grammar_path(self.domain),
                interpreter
            )
            
            if "results" in result:
                # Query operation
                return {
                    "status": "success",
                    "message": result.get("message", "Query successful."),
                    "results": result.get("results", []),
                    "action_type": "query"
                }
            else:
                # Mutation operation
                self.state_manager.save(result['new_state'])
                return {
                    "status": "success", 
                    "message": result.get("message", "Execution successful."),
                    "new_state": result['new_state'],
                    "action_type": "mutation"
                }
                
        except ValueError as e:
            error_msg = str(e)
            if "RoleMismatchError" in error_msg:
                return {
                    "status": "error",
                    "message": f"Permission Error: {error_msg.split(':', 1)[1] if ':' in error_msg else error_msg}"
                }
            elif "ValidationError" in error_msg:
                return {
                    "status": "error",
                    "message": f"Validation Failed: {error_msg.split(':', 1)[1] if ':' in error_msg else error_msg}"
                }
            else:
                return {
                    "status": "error",
                    "message": f"Error: {error_msg}"
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Unexpected Error: {e}"
            }
    
    def get_state(self) -> Dict[str, Any]:
        """Get current state from state manager."""
        return self.state_manager.load()
    
    def save_state(self, state: Dict[str, Any]):
        """Save state using state manager."""
        self.state_manager.save(state)
    
    def get_state_manager(self):
        """Return state manager for backward compatibility."""
        return self.state_manager