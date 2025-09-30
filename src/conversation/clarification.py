# src/conversation/clarification.py
from typing import Dict, List, Any

# Handle both relative and absolute imports
try:
    from ..domains.event.schema import DOMAIN_SCHEMA
except (ImportError, ValueError):
    # When used with LionWeb, schema is passed dynamically
    DOMAIN_SCHEMA = {}

class ClarificationGenerator:
    """Generates clarification messages for missing parameters."""
    
    def __init__(self, state_manager):
        self.state_manager = state_manager
    
    def generate_message(self, missing_params: List[str], 
                        task_details: Dict, role: str, 
                        model_name: str, connector: Dict[str, Any]) -> Dict:
        """Generate a structured definition for a clarification form."""
        
        if not missing_params:
            return {}

        # Get state only if state_manager exists
        state = self.state_manager.load() if self.state_manager else {}
        action = task_details.get("action", "")
        
        # Try to get schema from DOMAIN_SCHEMA first (for event domain)
        # For LionWeb domains, this will be empty and we rely on the connector
        action_schema = DOMAIN_SCHEMA.get(action, {})
        action_connector = connector.get("actions", {}).get(action, {})
        
        form_fields = []
        for param in missing_params:
            param_schema = action_schema.get("param_types", {}).get(param, {})
            param_connector = action_connector.get("parameters", {}).get(param, {})
            
            field = {
                "name": param,
                "type": param_schema.get("type", "string"),
                "label": param.replace('_', ' ').title(),
                "prompt": param_connector.get("clarification_prompt", f"Please provide a value for '{param}'.")
            }
            
            if field["type"] == "venue_selection":
                field["options"] = self._get_suitable_venues(task_details, state)
            elif field["type"] == "team_selection":
                field["options"] = self._get_available_teams(state)
            
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
            # Venue must be available
            if name not in state.get("venue_bookings", {}):
                capacity = props.get("capacity", 0)
                has_av = props.get("has_av_system", False)
                # Check if venue meets requirements
                if capacity >= attendees_req and (not av_req or has_av):
                    suitable_venues.append(name)
        
        return suitable_venues if suitable_venues else ["No suitable venues available"]
    
    def _get_available_teams(self, state: Dict) -> List[str]:
        """Get a list of available teams (for cycling domain)."""
        # This would be populated by the cycling system
        # For now, return a placeholder
        return ["No teams available"]