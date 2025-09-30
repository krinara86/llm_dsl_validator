# src/conversation/orchestrator.py
import re
from typing import Dict, List, Optional

# Handle both relative and absolute imports
try:
    from ..core.state_manager import StateManager
    from ..core.config import AppConfig
    from .extractor import TaskExtractor
    from .formatter import MessageFormatter
    from .clarification import ClarificationGenerator
except (ImportError, ValueError):
    # Fallback to absolute imports when relative imports fail
    from core.state_manager import StateManager
    from core.config import AppConfig
    from conversation.extractor import TaskExtractor
    from conversation.formatter import MessageFormatter
    from conversation.clarification import ClarificationGenerator

class ConversationOrchestrator:
    """Orchestrates the conversation flow."""
    
    def __init__(self, connector: Dict = None, schema: Dict = None, 
                 state_manager: StateManager = None):
        """
        Initialize the orchestrator with domain-specific dependencies.
        
        Args:
            connector: Domain connector dictionary (from YAML or LionWeb)
            schema: Domain schema dictionary (from Python or LionWeb)
            state_manager: Optional state manager (defaults to file-based)
        """
        # Use provided dependencies or fall back to event domain defaults
        if connector is None:
            from ..core.connector_loader import load_connector
            connector = load_connector('event')
        if schema is None:
            from ..domains.event.schema import DOMAIN_SCHEMA
            schema = DOMAIN_SCHEMA
        if state_manager is None:
            state_manager = StateManager(AppConfig.STATE_FILE)
            
        self.connector = connector
        self.schema = schema
        self.state_manager = state_manager
        self.extractor = TaskExtractor()
        self.formatter = MessageFormatter()
        self.clarifier = ClarificationGenerator(state_manager)
    
    def _request_clarification(self, understanding: Dict,
                             conversation_state: Dict,
                             role: str, model_name: str) -> Dict:
        missing_params = understanding["missing_params"]
        conversation_state["status"] = "awaiting_clarification"
        conversation_state["missing_params"] = missing_params
        
        clarification_data = self.clarifier.generate_message(
            missing_params,
            conversation_state["task_details"],
            role,
            model_name,
            self.connector
        )
        
        return {
            "status": "clarification_needed",
            "understanding_html": understanding["formatted_html"],
            "clarification_data": clarification_data, 
            "new_state": conversation_state
        }
        
    def process_request(self, query: str, role: str, model_name: str,
                       conversation_state: Dict = None, pre_filled_details: Dict = None) -> Dict:
        if not conversation_state:
            conversation_state = self._new_conversation_state()
        
        conversation_state["history"].append({"role": "user", "content": query})
        
        if conversation_state.get("status") == "awaiting_clarification":
            conversation_state = self._handle_clarification(
                query, conversation_state
            )
        else:
            if pre_filled_details and pre_filled_details.get('action') != 'unknown':
                extracted = pre_filled_details
            else:
                extracted = self.extractor.extract_task_details(query, model_name, self.connector)
            
            if extracted.get("action") in [None, "unknown", "error"]:
                return self._error_response(
                    "I couldn't understand your request. Please try rephrasing."
                )
            conversation_state["task_details"] = extracted
            conversation_state["status"] = "processing"
        
        validation_result = self._validate_request(
            conversation_state["task_details"], role
        )
        if validation_result["status"] == "error":
            return validation_result
        
        understanding = self._format_understanding(
            conversation_state["task_details"], role
        )
        
        if understanding["missing_params"]:
            return self._request_clarification(
                understanding, conversation_state, role, model_name
            )
        
        action = conversation_state["task_details"].get("action")
        if self.schema.get(action, {}).get("is_read_only"):
            conversation_state["status"] = "awaiting_execution"
            return {
                "status": "direct_execute",
                "understanding_html": understanding["formatted_html"],
                "message": "This is a read-only query. Executing directly...",
                "new_state": conversation_state
            }

        conversation_state["status"] = "awaiting_confirmation"
        conversation_state["missing_params"] = []
        
        return {
            "status": "confirmation_needed",
            "understanding_html": understanding["formatted_html"],
            "message": self.formatter.format_confirmation(),
            "new_state": conversation_state
        }
    
    def _format_understanding(self, task_details: Dict, role: str) -> Dict:
        """Format the extracted task details into a structured response."""
        action = task_details.get("action", "unknown")
        params = task_details.get("parameters", {})
        
        if action not in self.schema:
            return {
                "formatted_html": "<b>Error:</b> Unable to understand the request.",
                "missing_params": [],
                "available_params": {}
            }
        
        schema = self.schema[action]
        required = schema["required"]
        optional = schema.get("optional", [])
        param_types = schema.get("param_types", {})
        
        available_params = {}
        missing_params = []
        
        invalid_values = ["unknown", "N/A", "n/a", "Unknown", "TBD", "tbd", 
                        "placeholder", "Placeholder", "UNKNOWN", "None", "none"]
        
        for param in required:
            if param in params:
                value = params[param]
                str_value = str(value).strip() if value not in [None, ""] else ""
                
                if str_value and str_value not in invalid_values:
                    available_params[param] = value
                else:
                    missing_params.append(param)
            else:
                missing_params.append(param)
        
        for param in optional:
            if param in params:
                value = params[param]
                str_value = str(value).strip() if value not in [None, ""] else ""
                
                if str_value and str_value not in invalid_values:
                    available_params[param] = value
        
        html = f"""
        <div style='background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin: 10px 0;'>
            <h4 style='margin-top: 0;'>Here is what I understood:</h4>
            <p><b>Role:</b> {role}</p>
            <p><b>Action:</b> {action.replace('_', ' ').title()}</p>
            
            <div style='margin: 10px 0;'>
                <b>Available Input:</b>
                <ul style='margin: 5px 0;'>
        """
        
        if available_params:
            for key, value in available_params.items():
                display_key = key.replace('_', ' ').title()
                html += f"<li>{display_key}: <code>{value}</code></li>"
        else:
            html += "<li><i>None provided yet</i></li>"
        
        html += "</ul></div>"
        
        if missing_params:
            html += """
            <div style='margin: 10px 0;'>
                <b>Missing Input:</b>
                <ul style='margin: 5px 0;'>
            """
            for param in missing_params:
                display_param = param.replace('_', ' ').title()
                param_type = param_types.get(param, {}).get("type", "text")
                
                guidance = ""
                if param_type == "boolean":
                    guidance = "(Please answer: yes/no)"
                elif param_type == "number":
                    guidance = "(Please provide a number)"
                elif param_type in ["venue_selection", "team_selection"]:
                    guidance = "(I'll show you available options)"
                
                html += f"<li>{display_param} {guidance}</li>"
            
            html += "</ul></div>"
        
        html += "</div>"
        
        return {
            "formatted_html": html,
            "missing_params": missing_params,
            "available_params": available_params
        }
    
    def _validate_request(self, task_details: Dict, role: str) -> Dict:
        action = task_details.get("action")
        
        if action in self.schema:
            allowed_roles = self.schema[action].get("permissions", [])
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
        missing_params = conversation_state.get("missing_params", [])
        if not missing_params:
            return conversation_state

        task_details = conversation_state.get("task_details", {})
        action = task_details.get("action")
        param_types = self.schema.get(action, {}).get("param_types", {})
        
        updated_params = {}
        
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
        
        if not found_key_value and len(missing_params) == 1:
            param = missing_params[0]
            updated_params[param] = query.strip()
        
        if "parameters" not in task_details:
            task_details["parameters"] = {}
            
        for param, raw_value in updated_params.items():
            param_type = param_types.get(param, {}).get("type", "text")
            value = None

            if param_type == "boolean":
                value = TaskExtractor.parse_boolean(raw_value)
            elif param_type == "number":
                value = TaskExtractor.parse_number(raw_value)
            elif param_type in ["venue_selection", "team_selection"]:
                # For team selection in cycling domain
                if param_type == "team_selection":
                    # Just use the raw value for now
                    value = raw_value
                else:
                    # Original venue selection logic
                    state = self.state_manager.load()
                    exact_match = next((v for v in state.get("venues", {}) if v == raw_value), None)
                    case_match = next((v for v in state.get("venues", {}) if v.lower() == raw_value.lower()), None)
                    substring_match = next((v for v in state.get("venues", {}) if raw_value.lower() in v.lower()), None)
                    value = exact_match or case_match or substring_match or raw_value
            else:
                value = raw_value
                
            task_details["parameters"][param] = value

        conversation_state["task_details"] = task_details
        return conversation_state
    
    def _new_conversation_state(self) -> Dict:
        return {
            "status": "awaiting_query",
            "task_details": {},
            "history": [],
            "missing_params": []
        }
    
    def _error_response(self, message: str) -> Dict:
        return {
            "status": "error",
            "message": message,
            "new_state": {}
        }