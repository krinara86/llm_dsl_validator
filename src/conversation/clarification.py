# src/conversation/clarification.py
from typing import Dict, List, Any
from ..core.config import AppConfig

class ClarificationGenerator:
    """Generates clarification messages for missing parameters."""
    
    def __init__(self, state_manager, schema_provider=None):
        self.state_manager = state_manager
        self.schema_provider = schema_provider
    
    def get_schema(self) -> Dict:
        """Get schema from provider or fall back to domain imports."""
        if self.schema_provider:
            return self.schema_provider.get_schema()
        
        if AppConfig.DOMAIN == 'event':
            from ..domains.event.schema import DOMAIN_SCHEMA
            return DOMAIN_SCHEMA
        
        return {}
    
    def generate_message(self, missing_params: List[str], 
                        task_details: Dict, role: str, 
                        model_name: str, connector: Dict[str, Any]) -> Dict:
        """Generate a structured definition for a clarification form."""
        
        if not missing_params:
            return {}

        state = self.state_manager.load() if hasattr(self.state_manager, 'load') else self.state_manager.get_state()
        action = task_details.get("action", "")
        
        schema = self.get_schema()
        action_schema = schema.get(action, {})
        action_connector = connector.get("actions", {}).get(action, {})
        
        form_fields = []
        for param in missing_params:
            param_schema = action_schema.get("param_types", {}).get(param, {})
            param_connector = action_connector.get("parameters", {}).get(param, {})
            
            param_type = param_schema.get("type", "string") if isinstance(param_schema, dict) else "string"
            
            field = {
                "name": param,
                "type": param_type,
                "label": param.replace('_', ' ').title(),
                "prompt": param_connector.get("clarification_prompt", f"Please provide a value for '{param}'.")
            }
            
            if field["type"] == "venue_selection":
                field["options"] = self._get_suitable_venues(task_details, state)
            
            form_fields.append(field)
        
        return {
            "message": f"<b>To proceed with '{action.replace('_', ' ').title()}', please provide the following details:</b>",
            "form_fields": form_fields
        }

    def _get_suitable_venues(self, task_details: Dict, state: Dict) -> List[str]:
        """Get a list of suitable venues based on current task details."""
        attendees_req = task_details.get("parameters", {}).get("expected_attendees", 0)
        av_req = task_details.get("parameters", {}).get("requires_av", False)
        
        suitable_venues = []
        for name, props in state.get("venues", {}).items():
            if name not in state.get("venue_bookings", {}):
                capacity = props.get("capacity", 0)
                has_av = props.get("has_av_system", False)
                if capacity >= attendees_req and (not av_req or has_av):
                    suitable_venues.append(name)
        
        return suitable_venues if suitable_venues else ["No suitable venues available"]