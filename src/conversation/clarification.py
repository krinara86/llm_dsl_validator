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
        """Generate a single clarification message for all missing parameters."""
        
        if not missing_params:
            return ""

        state = self.state_manager.load()
        action = task_details.get("action", "")
        
        # Introduction
        messages = [
            f"<b>To proceed with '{action.replace('_', ' ').title()}', please provide the following details.</b>",
            "<i>Reply with each item on a new line, like this:</i>",
            "<pre style='background-color:#f5f5f5; padding:5px; border-radius:3px;'>parameter_name: your_value</pre>"
        ]

        # Individual parameter prompts
        for param in missing_params:
            param_type = DOMAIN_SCHEMA.get(action, {}).get(
                "param_types", {}
            ).get(param, "text")
            
            msg = ""
            if param == "in_venue":
                msg = self._venue_clarification(task_details, state)
            elif param in ["capacity", "expected_attendees"]:
                msg = f"• <b>{param}</b>: (Enter a number, e.g., 50)"
            elif param in ["has_av_system", "requires_av"]:
                msg = f"• <b>{param}</b>: (Answer 'yes' or 'no')"
            elif param == "hosted_by":
                msg = f"• <b>{param}</b>: (Enter the host's name)"
            else: # Catches 'name' and any other text fields
                msg = f"• <b>{param}</b>: (Enter the desired text)"
            
            if msg:
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
        
        msg = f"• <b>in_venue</b>: (Choose from the available options below)"
        if suitable_venues:
            msg += "<ul style='margin-top: 4px;'>"
            for venue_name, capacity, has_av in suitable_venues:
                av_text = "Has A/V" if has_av else "No A/V"
                msg += f"<li><code>{venue_name}</code> (Capacity: {capacity}, {av_text})</li>"
            msg += "</ul>"
        else:
            msg += "<br><i>(No suitable venues are currently available.)</i>"
        
        return msg