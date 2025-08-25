# src/conversation/orchestrator.py
import re
from typing import Dict, List
from ..core.state_manager import StateManager
from ..core.config import AppConfig
from ..domains.event.schema import DOMAIN_SCHEMA
from .extractor import TaskExtractor
from .formatter import MessageFormatter
from .clarification import ClarificationGenerator

class ConversationOrchestrator:
    """Orchestrates the conversation flow."""
    
    def __init__(self):
        self.state_manager = StateManager(AppConfig.STATE_FILE)
        self.extractor = TaskExtractor()
        self.formatter = MessageFormatter()
        self.clarifier = ClarificationGenerator(self.state_manager)
    
    def process_request(self, query: str, role: str, model_name: str,
                       conversation_state: Dict = None, pre_filled_details: Dict = None) -> Dict:
        """Process a user request through the conversation flow."""
        
        if not conversation_state:
            conversation_state = self._new_conversation_state()
        
        conversation_state["history"].append({"role": "user", "content": query})
        
        # Handle clarification responses
        if conversation_state.get("status") == "awaiting_clarification":
            conversation_state = self._handle_clarification(
                query, conversation_state
            )
        else:
            # New request - determine task details
            if pre_filled_details and pre_filled_details.get('action') != 'unknown':
                extracted = pre_filled_details
            else:
                extracted = self.extractor.extract_task_details(query, model_name)
            
            if extracted.get("action") in [None, "unknown", "error"]:
                return self._error_response(
                    "I couldn't understand your request. Please try rephrasing."
                )
            conversation_state["task_details"] = extracted
            conversation_state["status"] = "processing"
        
        # Validate permissions and requirements
        validation_result = self._validate_request(
            conversation_state["task_details"], role
        )
        if validation_result["status"] == "error":
            return validation_result
        
        # Format understanding and check for missing parameters
        understanding = self.formatter.format_understanding(
            conversation_state["task_details"], role
        )
        
        if understanding["missing_params"]:
            # Need clarification
            return self._request_clarification(
                understanding, conversation_state, role, model_name
            )
        
        # Ready for confirmation
        conversation_state["status"] = "awaiting_confirmation"
        conversation_state["missing_params"] = []
        
        return {
            "status": "confirmation_needed",
            "understanding_html": understanding["formatted_html"],
            "message": self.formatter.format_confirmation(),
            "new_state": conversation_state
        }
    
    def _validate_request(self, task_details: Dict, role: str) -> Dict:
        """Validate the request against permissions and state."""
        action = task_details.get("action")
        
        if action in DOMAIN_SCHEMA:
            allowed_roles = DOMAIN_SCHEMA[action].get("permissions", [])
            if role not in allowed_roles:
                return {
                    "status": "error",
                    "message": self.formatter.format_error(
                        "Permission Denied",
                        f"The action '{action.replace('_', ' ').title()}' "
                        f"requires one of these roles: {', '.join(allowed_roles)}",
                        f"Your current role is: {role}"
                    ),
                    "new_state": {}
                }
        
        return {"status": "ok"}

    def _handle_clarification(self, query: str, conversation_state: Dict) -> Dict:
        """Handle a batch clarification response from the user."""
        missing_params = conversation_state.get("missing_params", [])
        if not missing_params:
            return conversation_state

        task_details = conversation_state.get("task_details", {})
        action = task_details.get("action")
        param_types = DOMAIN_SCHEMA.get(action, {}).get("param_types", {})
        
        updated_params = {}
        
        # Try to parse key:value pairs
        lines = query.strip().split('\n')
        key_value_pattern = re.compile(r"([\w\s_]+)\s*:\s*(.+)")
        
        found_key_value = False
        for line in lines:
            match = key_value_pattern.match(line.strip())
            if match:
                found_key_value = True
                key = match.group(1).strip().replace(' ', '_').lower()
                raw_value = match.group(2).strip()
                for param in missing_params:
                    if param.lower() == key:
                        updated_params[param] = raw_value
                        break
        
        # If no key:value pairs found AND only one thing was missing,
        # assume the whole query is the value for that single parameter.
        if not found_key_value and len(missing_params) == 1:
            param = missing_params[0]
            updated_params[param] = query.strip()
        
        # Update task details with parsed values
        if "parameters" not in task_details:
            task_details["parameters"] = {}
            
        for param, raw_value in updated_params.items():
            param_type = param_types.get(param, "text")
            value = None

            if param_type == "boolean":
                value = TaskExtractor.parse_boolean(raw_value)
            elif param_type == "number":
                value = TaskExtractor.parse_number(raw_value)
            elif param_type == "venue_selection":
                state = self.state_manager.load()
                # Prioritize exact match, then case-insensitive, then substring
                exact_match = next((v for v in state.get("venues", {}) if v == raw_value), None)
                case_match = next((v for v in state.get("venues", {}) if v.lower() == raw_value.lower()), None)
                substring_match = next((v for v in state.get("venues", {}) if raw_value.lower() in v.lower()), None)
                value = exact_match or case_match or substring_match or raw_value
            else:
                value = raw_value
                
            task_details["parameters"][param] = value

        conversation_state["task_details"] = task_details
        return conversation_state

    def _request_clarification(self, understanding: Dict,
                             conversation_state: Dict,
                             role: str, model_name: str) -> Dict:
        """Request clarification for all missing parameters at once."""
        missing_params = understanding["missing_params"]
        conversation_state["status"] = "awaiting_clarification"
        conversation_state["missing_params"] = missing_params
        
        clarification_msg = self.clarifier.generate_message(
            missing_params,
            conversation_state["task_details"],
            role,
            model_name
        )
        
        return {
            "status": "clarification_needed",
            "understanding_html": understanding["formatted_html"],
            "message": clarification_msg,
            "new_state": conversation_state
        }
    
    def _new_conversation_state(self) -> Dict:
        """Create a new conversation state."""
        return {
            "status": "awaiting_query",
            "task_details": {},
            "history": [],
            "missing_params": []
        }
    
    def _error_response(self, message: str) -> Dict:
        """Create an error response."""
        return {
            "status": "error",
            "message": message,
            "new_state": {}
        }