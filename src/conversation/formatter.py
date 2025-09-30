# src/conversation/formatter.py
from typing import Dict, List

# Handle both relative and absolute imports
try:
    from ..domains.event.schema import DOMAIN_SCHEMA
except (ImportError, ValueError):
    # When used with LionWeb, schema is passed dynamically
    DOMAIN_SCHEMA = {}

class MessageFormatter:
    """Formats messages and UI elements for the conversation."""
    
    @staticmethod
    def format_understanding(task_details: Dict, role: str) -> Dict:
        """Format the extracted task details into a structured response."""
        action = task_details.get("action", "unknown")
        params = task_details.get("parameters", {})
        
        if action not in DOMAIN_SCHEMA:
            return {
                "formatted_html": "<b>Error:</b> Unable to understand the request.",
                "missing_params": [],
                "available_params": {}
            }
        
        schema = DOMAIN_SCHEMA[action]
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
                elif param_type == "venue_selection":
                    guidance = "(I'll show you available options)"
                
                html += f"<li>{display_param} {guidance}</li>"
            
            html += "</ul></div>"
        
        html += "</div>"
        
        return {
            "formatted_html": html,
            "missing_params": missing_params,
            "available_params": available_params
        }
    
    @staticmethod
    def format_error(title: str, message: str, details: str = "") -> str:
        """Format an error message."""
        html = (
            f"<div style='background-color: #ffebee; padding: 10px; "
            f"border-radius: 5px; border-left: 4px solid #f44336; margin: 10px 0;'>"
            f"<b>❌ {title}</b><br>{message}"
        )
        if details:
            html += f"<br><br>{details}"
        html += "</div>"
        return html
    
    @staticmethod
    def format_confirmation() -> str:
        """Format a confirmation message."""
        return """
        <div style='background-color: #d4edda; padding: 10px; border-radius: 5px; margin: 10px 0;'>
            <b>Ready to execute!</b><br>
            Please review the details above and confirm if you want to proceed.
        </div>
        """