# src/conversation/orchestrator.py
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
                       conversation_state: Dict = None) -> Dict:
        """Process a user request through the conversation flow."""
        
        if not conversation_state:
            conversation_state = self._new_conversation_state()
        
        conversation_state["history"].append({"role": "user", "content": query})
        
        # Handle clarification responses
        if conversation_state.get("status") == "awaiting_clarification":
            conversation_state = self._handle_clarification(
                query, conversation_state, model_name
            )
        else:
            # New request - extract task details
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
        
        # Check permissions
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
        
        # Additional validation can be added here
        return {"status": "ok"}
    
    def _handle_clarification(self, query: str, conversation_state: Dict,
                            model_name: str) -> Dict:
        """Handle a clarification response from the user."""
        missing_params = conversation_state.get("missing_params", [])
        if not missing_params:
            return conversation_state
        
        current_param = missing_params[0]
        task_details = conversation_state.get("task_details", {})
        action = task_details.get("action")
        param_type = DOMAIN_SCHEMA.get(action, {}).get(
            "param_types", {}
        ).get(current_param, "text")
        
        # Parse the response based on parameter type
        if param_type == "boolean":
            value = TaskExtractor.parse_boolean(query)
        elif param_type == "number":
            value = TaskExtractor.parse_number(query)
        elif param_type == "venue_selection":
            # Try to match venue name
            state = self.state_manager.load()
            value = None
            for venue_name in state.get("venues", {}).keys():
                if venue_name.lower() in query.lower():
                    value = venue_name
                    break
            if not value:
                value = query.strip()
        else:
            value = query.strip()
        
        # Update task details
        if "parameters" not in task_details:
            task_details["parameters"] = {}
        task_details["parameters"][current_param] = value
        conversation_state["task_details"] = task_details
        
        return conversation_state
    
    def _request_clarification(self, understanding: Dict,
                             conversation_state: Dict,
                             role: str, model_name: str) -> Dict:
        """Request clarification for missing parameters."""
        conversation_state["status"] = "awaiting_clarification"
        conversation_state["missing_params"] = understanding["missing_params"]
        
        clarification_msg = self.clarifier.generate_message(
            [understanding["missing_params"][0]],
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