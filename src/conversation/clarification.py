# src/conversation/clarification.py
from typing import Dict, List, Any, Optional

# Handle both relative and absolute imports
try:
    from .selection_provider import SelectionProvider, NullSelectionProvider
except (ImportError, ValueError):
    from conversation.selection_provider import SelectionProvider, NullSelectionProvider


class ClarificationGenerator:
    """Generates clarification messages for missing parameters."""
    
    def __init__(self, selection_provider: Optional[SelectionProvider] = None):
        """
        Initialize with a selection provider.
        
        Args:
            selection_provider: Provider for dropdown options, or None for no dropdowns
        """
        self.selection_provider = selection_provider or NullSelectionProvider()
    
    def generate_message(self, missing_params: List[str], 
                        task_details: Dict, role: str, 
                        model_name: str, connector: Dict[str, Any],
                        schema: Dict[str, Any] = None,
                        available_params: Dict[str, Any] = None) -> Dict:
        """
        Generate a structured definition for a clarification form.
        
        Args:
            missing_params: List of parameter names that are missing
            task_details: Current task details including action and partial parameters
            role: User's role
            model_name: LLM model being used
            connector: Connector dictionary with clarification prompts
            schema: Schema dictionary with parameter types (optional)
            available_params: Dictionary of already extracted parameters (optional)
        """
        
        # If no params at all (shouldn't happen), return empty
        if not missing_params and not available_params:
            return {}

        action = task_details.get("action", "")
        action_connector = connector.get("actions", {}).get(action, {})
        
        # Get parameter types from schema if provided
        param_types = {}
        if schema and action in schema:
            param_types = schema[action].get("param_types", {})
        
        form_fields = []
        
        # First, add fields for extracted parameters (if any)
        if available_params:
            for param, value in available_params.items():
                param_connector = action_connector.get("parameters", {}).get(param, {})
                param_type_info = param_types.get(param, {})
                
                field = {
                    "name": param,
                    "type": param_type_info.get("type", "string"),
                    "label": param.replace('_', ' ').title() + " (Extracted - edit if incorrect)",
                    "prompt": param_connector.get("clarification_prompt", f"Current value for '{param}'."),
                    "value": value,  # Pre-populate with extracted value
                    "is_extracted": True
                }
                
                # Handle selection fields using the provider
                if field["type"].endswith("_selection"):
                    context = {
                        "task_details": task_details,
                        "action": action,
                        "param": param
                    }
                    field["options"] = self.selection_provider.get_options(
                        field["type"], 
                        context
                    )
                
                form_fields.append(field)
        
        # Then, add fields for missing parameters
        for param in missing_params:
            param_connector = action_connector.get("parameters", {}).get(param, {})
            param_type_info = param_types.get(param, {})
            
            field = {
                "name": param,
                "type": param_type_info.get("type", "string"),
                "label": param.replace('_', ' ').title(),
                "prompt": param_connector.get("clarification_prompt", f"Please provide a value for '{param}'."),
                "is_extracted": False
            }
            
            # Handle selection fields using the provider
            if field["type"].endswith("_selection"):
                context = {
                    "task_details": task_details,
                    "action": action,
                    "param": param
                }
                field["options"] = self.selection_provider.get_options(
                    field["type"], 
                    context
                )
            
            form_fields.append(field)
        
        return {
            "message": f"<b>Review and confirm details for '{action.replace('_', ' ').title()}':</b>",
            "form_fields": form_fields
        }