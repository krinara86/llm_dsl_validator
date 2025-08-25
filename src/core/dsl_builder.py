# src/core/dsl_builder.py
"""DSL building logic for converting task details to DSL code."""

from typing import Dict

class DSLBuilder:
    """Builds DSL code from structured task details."""
    
    @staticmethod
    def build(task_details: Dict, role: str) -> str:
        """Build DSL code from task details and role."""
        action = task_details.get("action")
        params = task_details.get("parameters", {})
        
        builder = DSLBuilder()
        
        if action == "create_venue":
            return builder._build_create_venue(params, role)
        elif action == "modify_venue":
            return builder._build_modify_venue(params, role)
        elif action == "schedule_session":
            return builder._build_schedule_session(params, role)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    def _build_create_venue(self, params: Dict, role: str) -> str:
        """Build DSL for create_venue action."""
        dsl = [f'role "{role}" {{']
        dsl.append(f'  create_venue "{self._normalize(params.get("name", ""))}" {{')
        
        if "capacity" in params:
            dsl.append(f'    capacity: {params["capacity"]}')
        if "has_av_system" in params:
            dsl.append(f'    has_av_system: {str(params["has_av_system"]).lower()}')
        
        dsl.append('  }')
        dsl.append('}')
        return "\n".join(dsl)
    
    def _build_modify_venue(self, params: Dict, role: str) -> str:
        """Build DSL for modify_venue action."""
        dsl = [f'role "{role}" {{']
        dsl.append(f'  modify_venue "{self._normalize(params.get("name", ""))}" {{')
        
        if "capacity" in params:
            dsl.append(f'    capacity: {params["capacity"]}')
        if "has_av_system" in params:
            dsl.append(f'    has_av_system: {str(params["has_av_system"]).lower()}')
        
        dsl.append('  }')
        dsl.append('}')
        return "\n".join(dsl)
    
    def _build_schedule_session(self, params: Dict, role: str) -> str:
        """Build DSL for schedule_session action."""
        dsl = [f'role "{role}" {{']
        dsl.append(f'  schedule_session "{self._normalize(params.get("name", ""))}" {{')
        
        if "hosted_by" in params:
            dsl.append(f'    hosted_by: "{self._normalize(params["hosted_by"])}"')
        if "in_venue" in params:
            dsl.append(f'    in_venue: "{self._normalize(params["in_venue"])}"')
        if "expected_attendees" in params:
            dsl.append(f'    expected_attendees: {params["expected_attendees"]}')
        if "requires_av" in params:
            dsl.append(f'    requires_av: {str(params["requires_av"]).lower()}')
        
        dsl.append('  }')
        dsl.append('}')
        return "\n".join(dsl)
    
    def _normalize(self, value: str) -> str:
        """Normalize string values by removing quotes and whitespace."""
        return str(value).strip().strip("'\"")