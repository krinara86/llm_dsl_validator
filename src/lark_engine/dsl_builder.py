# src/core/dsl_builder.py
"""Generic DSL building logic for converting task details to DSL code."""

from typing import Dict
from ..domains.event.schema import DOMAIN_SCHEMA 

class DSLBuilder:
    """Builds DSL code from structured task details using schema metadata."""
    
    def build(self, task_details: Dict, role: str) -> str:
        """
        Builds a DSL string dynamically based on the action's definition
        in the DOMAIN_SCHEMA.
        """
        action_name = task_details.get("action")
        params = task_details.get("parameters", {})
        
        if not action_name or action_name not in DOMAIN_SCHEMA:
            raise ValueError(f"Unknown or missing action: {action_name}")
            
        action_schema = DOMAIN_SCHEMA[action_name]
        action_syntax = action_schema.get("dsl_syntax")
        if not action_syntax:
            raise ValueError(f"Action '{action_name}' is missing 'dsl_syntax' in schema.")

        dsl = [f'role "{self._normalize(role)}" {{']
        
        main_param_name = None
        for p_name, p_details in action_schema["param_types"].items():
            if "dsl_keyword" not in p_details:
                main_param_name = p_name
                break
        
        if main_param_name:
            if main_param_name not in params:
                 raise ValueError(f"Main parameter '{main_param_name}' not found for action '{action_name}'.")

            main_param_value = self._normalize(params[main_param_name])
            dsl.append(f'  {action_syntax} "{main_param_value}" {{')
        else:
            dsl.append(f'  {action_syntax} {{')

        for param_name, param_value in params.items():
            if param_name == main_param_name:
                continue 

            param_schema = action_schema["param_types"].get(param_name)
            if not param_schema or "dsl_keyword" not in param_schema:
                continue

            keyword = param_schema["dsl_keyword"]
            param_type = param_schema.get("type", "string")

            if param_type == "boolean":
                formatted_value = str(param_value).lower()
                dsl.append(f'    {keyword}: {formatted_value}')
            elif param_type == "number":
                dsl.append(f'    {keyword}: {param_value}')
            else: 
                formatted_value = self._normalize(param_value)
                dsl.append(f'    {keyword}: "{formatted_value}"')
        
        dsl.append('  }')
        dsl.append('}')
        return "\n".join(dsl)

    def _normalize(self, value: str) -> str:
        return str(value).strip().strip("'\"")