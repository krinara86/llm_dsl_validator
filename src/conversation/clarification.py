# src/conversation/clarification.py
from typing import Dict, List
from ..domains.event.schema import DOMAIN_SCHEMA

class ClarificationGenerator:
    """Generates clarification messages for missing parameters."""
    
    def __init__(self, state_manager):
        self.state_manager = state_manager
    
    def generate_message(self, missing_params: List[str], 
                        task_details: Dict, role: str, 
                        model_name: str) -> str:
        """Generate a clarification message for missing parameters."""
        
        messages = []
        state = self.state_manager.load()
        
        for param in missing_params:
            action = task_details.get("action", "")
            param_type = DOMAIN_SCHEMA.get(action, {}).get(
                "param_types", {}
            ).get(param, "text")
            
            if param == "in_venue":
                msg = self._venue_clarification(task_details, state)
            elif param == "name":
                msg = "<b>Please provide the name:</b><br><i>Type the exact name you want to use.</i>"
            elif param in ["capacity", "expected_attendees"]:
                msg = f"<b>Please provide the {param.replace('_', ' ')}:</b><br><i>Enter a number (e.g., 50)</i>"
            elif param in ["has_av_system", "requires_av"]:
                question = param.replace('_', ' ').replace('has', 'have').replace('requires', 'require')
                msg = f"<b>Does it {question}?</b><br><i>Answer: yes or no</i>"
            elif param == "hosted_by":
                msg = "<b>Who is hosting this session?</b><br><i>Enter the host's name</i>"
            else:
                msg = f"<b>Please provide {param.replace('_', ' ')}:</b><br><i>Enter the value</i>"
            
            messages.append(msg)
        
        return "<br><br>".join(messages)
    
    def _venue_clarification(self, task_details: Dict, state: Dict) -> str:
        """Generate venue selection clarification."""
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
            msg = "<b>Please select a venue from the available options:</b><br>"
            msg += "<ul style='margin: 5px 0;'>"
            for venue_name, capacity, has_av in suitable_venues:
                av_text = "Has A/V" if has_av else "No A/V"
                msg += f"<li><b>{venue_name}</b> (Capacity: {capacity}, {av_text})</li>"
            msg += "</ul>"
            msg += "<i>Type the exact name of your chosen venue.</i>"
        else:
            msg = "<b>No venues currently meet your requirements.</b><br>"
            msg += "Please create a suitable venue first or adjust your requirements."
        
        return msg