# src/conversation/clarification.py
from typing import Dict, List, Any
from ..domains.event.schema import DOMAIN_SCHEMA

class ClarificationGenerator:
    """Generates clarification messages for missing parameters."""
    
    def __init__(self, state_manager):
        self.state_manager = state_manager
    
   
    def generate_message(self, missing_params: List[str], 
                        task_details: Dict, role: str, 
                        model_name: str, connector: Dict[str, Any]) -> str:
        """Generate a single clarification message for all missing parameters using the connector."""
        
        if not missing_params:
            return ""

        state = self.state_manager.load()
        action = task_details.get("action", "")
        action_connector = connector.get("actions", {}).get(action, {})
        
       
        messages = [
            f"<b>To proceed with '{action.replace('_', ' ').title()}', I need a bit more information.</b>",
            "<i>You can reply with each item on a new line, like this:</i>",
            "<pre style='background-color:#f5f5f5; padding:5px; border-radius:3px;'>parameter_name: your_value</pre>"
        ]
        for param in missing_params:
            param_connector = action_connector.get("parameters", {}).get(param, {})
            prompt = param_connector.get("clarification_prompt", f"Please provide a value for '{param}'.")
            
            msg = f"• <b>{param}</b>: {prompt}"
            
            if param == "in_venue":
                msg += self._venue_clarification(task_details, state)
            
            messages.append(msg)
        
        return "<br>".join(messages)
    
    def _venue_clarification(self, task_details: Dict, state: Dict) -> str:
        """Generate venue selection clarification with available options."""
        attendees_req = task_details.get("parameters", {}).get("expected_attendees", 0)
        av_req = task_details.get("parameters", {}).get("requires_av", False)
        
        suitable_venues = []
        for name, props in state.get("venues", {}).items():
            if name not in state.get("venue_bookings", {}):
                capacity = props.get("capacity", 0)
                has_av = props.get("has_av_system", False)
                if capacity >= attendees_req and (not av_req or has_av):
                    suitable_venues.append((name, capacity, has_av))
        
        if suitable_venues:
            venue_list_html = "<ul style='margin-top: 4px;'>"
            for venue_name, capacity, has_av in suitable_venues:
                av_text = "Has A/V" if has_av else "No A/V"
                venue_list_html += f"<li><code>{venue_name}</code> (Capacity: {capacity}, {av_text})</li>"
            venue_list_html += "</ul>"
            return venue_list_html
        else:
            return "<br><i>(No suitable venues are currently available.)</i>"