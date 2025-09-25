# src/conversation/lionweb_orchestrator.py
"""
Modified orchestrator that supports both Lark DSL and LionWeb modes.
"""

import re
from typing import Dict, List, Optional
from pathlib import Path
from ..lionweb_engine.connector_loader import LionWebConnectorLoader
from ..core.llm_client import LLMClient
from .formatter import MessageFormatter
from .extractor import TaskExtractor
from ..core.config import AppConfig


class LionWebOrchestrator:
    """Orchestrator that can work with both DSL and LionWeb backends."""
    
    def __init__(self, mode: str = "lionweb", domain: str = "cycling"):
        """Initialize the orchestrator.
        
        Args:
            mode: Either "lionweb" or "dsl"
            domain: The domain to work with
        """
        self.mode = mode
        self.domain = domain
        
        if mode == "lionweb":
            # Initialize LionWeb loader
            self.loader = LionWebConnectorLoader(Path(__file__).parent.parent.parent)
            self.loader.load_all(domain)
            self.connector = self.loader.m1_connectors.get(domain)
        else:
            # Load traditional connector.yml
            from ..core.connector_loader import load_connector
            self.connector = load_connector(domain)
        
        self.extractor = TaskExtractor()
        self.formatter = MessageFormatter()
    
    def process_request(self, query: str, role: str, model_name: str,
                       conversation_state: Dict = None, pre_filled_details: Dict = None) -> Dict:
        """Process a user request."""
        
        if not conversation_state:
            conversation_state = self._new_conversation_state()
        
        conversation_state["history"].append({"role": "user", "content": query})
        
        # Handle clarification flow
        if conversation_state.get("status") == "awaiting_clarification":
            conversation_state = self._handle_clarification(query, conversation_state)
        else:
            # Extract task details
            if pre_filled_details and pre_filled_details.get('action') != 'unknown':
                extracted = pre_filled_details
            else:
                extracted = self._extract_task_lionweb(query, model_name)
            
            if extracted.get("action") in [None, "unknown", "error"]:
                return self._error_response(
                    "I couldn't understand your request. Please try rephrasing."
                )
            
            conversation_state["task_details"] = extracted
            conversation_state["status"] = "processing"
        
        # Check for missing parameters
        missing_params = self._find_missing_params(conversation_state["task_details"])
        
        if missing_params:
            return self._request_clarification(missing_params, conversation_state, role, model_name)
        
        # Check if this is a query action
        action_name = conversation_state["task_details"].get("action")
        if action_name and action_name.startswith("find_"):
            conversation_state["status"] = "awaiting_execution"
            return {
                "status": "direct_execute",
                "understanding_html": self._format_understanding_lionweb(conversation_state["task_details"], role),
                "message": "Executing query...",
                "new_state": conversation_state
            }
        
        # Ready for confirmation
        conversation_state["status"] = "awaiting_confirmation"
        
        return {
            "status": "confirmation_needed",
            "understanding_html": self._format_understanding_lionweb(conversation_state["task_details"], role),
            "message": self._format_confirmation(),
            "new_state": conversation_state
        }
    
    def execute(self, role: str, conversation_state: Dict) -> Dict:
        """Execute a confirmed task using LionWeb."""
        
        task_details = conversation_state.get("task_details", {})
        action = task_details.get("action")
        params = task_details.get("parameters", {})
        
        try:
            if self.mode == "lionweb":
                result = self._execute_lionweb_action(action, params)
            else:
                # Fall back to DSL execution
                from ..execution.executor import TaskExecutor
                executor = TaskExecutor()
                result = executor.execute(role, conversation_state)
            
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"⚠️ Error: {str(e)}"
            }
    
    def _extract_task_lionweb(self, query: str, model_name: str) -> Dict:
        """Extract task details using LionWeb connector information."""
        
        if not self.connector:
            return {"action": "error", "parameters": {"details": "No connector loaded"}}
        
        # Build action list from connector
        action_names = list(self.connector.get("actions", {}).keys())
        
        # Build parameter descriptions
        all_params = {}
        for action_name, action_data in self.connector.get("actions", {}).items():
            for param_name, param_data in action_data.get("parameters", {}).items():
                if param_name not in all_params:
                    all_params[param_name] = param_data.get("description", "No description")
        
        prompt = f"""
You are a data extraction assistant. Extract the user's intent and parameters from the text.

Respond with ONLY a valid JSON object with two keys:
1. "action": One of {action_names} or "unknown"
2. "parameters": A JSON object with extracted parameters (omit missing ones)

Available parameters:
{chr(10).join([f'* {k}: {v}' for k, v in all_params.items()])}

User text: "{query}"

JSON Output:"""
        
        try:
            response_str = LLMClient.execute_request(prompt, model_name, is_json_format=True)
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_str, re.DOTALL)
            if not json_match:
                return {"action": "unknown", "parameters": {}}
            
            import json
            result = json.loads(json_match.group(0))
            
            # Filter out invalid values
            if "parameters" in result:
                filtered_params = {}
                invalid_values = [None, "", "unknown", "N/A", "TBD"]
                
                for key, value in result.get("parameters", {}).items():
                    str_value = str(value).strip() if value is not None else ""
                    if str_value and str_value not in invalid_values:
                        filtered_params[key] = value
                
                result["parameters"] = filtered_params
            
            return result
            
        except Exception as e:
            return {"action": "error", "parameters": {"details": str(e)}}
    
    def _execute_lionweb_action(self, action: str, params: Dict) -> Dict:
        """Execute an action using LionWeb operations."""
        
        if action == "create_rider":
            instance = self.loader.create_m1_instance(
                domain=self.domain,
                concept="Rider",
                properties=params
            )
            name = params.get("name", "Unnamed")
            return {
                "status": "success",
                "message": f"✅ Successfully created rider '{name}'",
                "action_type": "mutation"
            }
        
        elif action == "create_team":
            instance = self.loader.create_m1_instance(
                domain=self.domain,
                concept="Team",
                properties=params
            )
            name = params.get("name", "Unnamed")
            return {
                "status": "success",
                "message": f"✅ Successfully created team '{name}'",
                "action_type": "mutation"
            }
        
        elif action == "modify_rider":
            name = params.pop("name", None)
            if not name:
                return {"status": "error", "message": "Rider name required for modification"}
            
            modified = self.loader.modify_m1_instance(
                domain=self.domain,
                instance_name=name,
                properties=params
            )
            
            if modified:
                return {
                    "status": "success",
                    "message": f"✅ Successfully modified rider '{name}'",
                    "action_type": "mutation"
                }
            else:
                return {"status": "error", "message": f"Rider '{name}' not found"}
        
        elif action == "modify_team":
            name = params.pop("name", None)
            if not name:
                return {"status": "error", "message": "Team name required for modification"}
            
            modified = self.loader.modify_m1_instance(
                domain=self.domain,
                instance_name=name,
                properties=params
            )
            
            if modified:
                return {
                    "status": "success",
                    "message": f"✅ Successfully modified team '{name}'",
                    "action_type": "mutation"
                }
            else:
                return {"status": "error", "message": f"Team '{name}' not found"}
        
        elif action == "find_rider":
            # Convert search params to filters
            filters = {}
            if "name_pattern" in params:
                filters["name_pattern"] = params["name_pattern"]
            if "country" in params:
                filters["country"] = params["country"]
            
            results = self.loader.find_m1_instances(
                domain=self.domain,
                concept="Rider",
                filters=filters
            )
            
            # Format results
            formatted_results = []
            for instance in results:
                formatted_results.append({
                    "name": self.loader._get_instance_property(instance, "name"),
                    "age": self.loader._get_instance_property(instance, "age"),
                    "country": self.loader._get_instance_property(instance, "country")
                })
            
            return {
                "status": "success",
                "message": f"Found {len(formatted_results)} rider(s)",
                "results": formatted_results,
                "action_type": "query"
            }
        
        elif action == "find_team":
            # Convert search params to filters
            filters = {}
            if "name_pattern" in params:
                filters["name_pattern"] = params["name_pattern"]
            if "country" in params:
                filters["country"] = params["country"]
            
            results = self.loader.find_m1_instances(
                domain=self.domain,
                concept="Team",
                filters=filters
            )
            
            # Format results
            formatted_results = []
            for instance in results:
                formatted_results.append({
                    "name": self.loader._get_instance_property(instance, "name"),
                    "country": self.loader._get_instance_property(instance, "country"),
                    "budget": self.loader._get_instance_property(instance, "budget"),
                    "founded": self.loader._get_instance_property(instance, "founded")
                })
            
            return {
                "status": "success",
                "message": f"Found {len(formatted_results)} team(s)",
                "results": formatted_results,
                "action_type": "query"
            }
        
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}
    
    def _find_missing_params(self, task_details: Dict) -> List[str]:
        """Find missing required parameters."""
        action = task_details.get("action")
        params = task_details.get("parameters", {})
        
        if not self.connector:
            return []
        
        action_data = self.connector.get("actions", {}).get(action)
        if not action_data:
            return []
        
        missing = []
        for param_name, param_data in action_data.get("parameters", {}).items():
            if param_data.get("required", False) and param_name not in params:
                missing.append(param_name)
        
        return missing
    
    def _request_clarification(self, missing_params: List[str], conversation_state: Dict,
                             role: str, model_name: str) -> Dict:
        """Request clarification for missing parameters."""
        conversation_state["status"] = "awaiting_clarification"
        conversation_state["missing_params"] = missing_params
        
        action = conversation_state["task_details"].get("action")
        action_data = self.connector.get("actions", {}).get(action, {})
        
        clarification_data = {
            "message": f"<b>To proceed with '{action.replace('_', ' ').title()}', please provide:</b>",
            "form_fields": []
        }
        
        for param in missing_params:
            param_data = action_data.get("parameters", {}).get(param, {})
            field = {
                "name": param,
                "type": "text",  # Simplified for now
                "label": param.replace('_', ' ').title(),
                "prompt": param_data.get("clarification_prompt", f"Please provide {param}")
            }
            clarification_data["form_fields"].append(field)
        
        return {
            "status": "clarification_needed",
            "understanding_html": self._format_understanding_lionweb(
                conversation_state["task_details"], role
            ),
            "clarification_data": clarification_data,
            "new_state": conversation_state
        }
    
    def _handle_clarification(self, query: str, conversation_state: Dict) -> Dict:
        """Handle clarification responses."""
        missing_params = conversation_state.get("missing_params", [])
        if not missing_params:
            return conversation_state
        
        task_details = conversation_state.get("task_details", {})
        
        # Parse the clarification response
        lines = query.strip().split('\n')
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()
                
                # Try to match with missing params
                for param in missing_params:
                    if param.lower() == key:
                        if "parameters" not in task_details:
                            task_details["parameters"] = {}
                        
                        # Convert value type if needed
                        if value.isdigit():
                            value = int(value)
                        elif value.lower() in ['true', 'false']:
                            value = value.lower() == 'true'
                        
                        task_details["parameters"][param] = value
                        break
        
        conversation_state["task_details"] = task_details
        return conversation_state
    
    def _format_understanding_lionweb(self, task_details: Dict, role: str) -> str:
        """Format understanding for LionWeb actions."""
        action = task_details.get("action", "unknown")
        params = task_details.get("parameters", {})
        
        html = f"""
        <div style='background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin: 10px 0;'>
            <h4 style='margin-top: 0;'>I understood:</h4>
            <p><b>Action:</b> {action.replace('_', ' ').title()}</p>
            <p><b>Parameters:</b></p>
            <ul style='margin: 5px 0;'>
        """
        
        if params:
            for key, value in params.items():
                display_key = key.replace('_', ' ').title()
                html += f"<li>{display_key}: <code>{value}</code></li>"
        else:
            html += "<li><i>None provided yet</i></li>"
        
        html += "</ul></div>"
        return html
    
    def _format_confirmation(self) -> str:
        """Format confirmation message."""
        return """
        <div style='background-color: #d4edda; padding: 10px; border-radius: 5px; margin: 10px 0;'>
            <b>Ready to execute!</b><br>
            Please review the details above and confirm if you want to proceed.
        </div>
        """
    
    def _new_conversation_state(self) -> Dict:
        """Create a new conversation state."""
        return {
            "status": "awaiting_query",
            "task_details": {},
            "history": [],
            "missing_params": []
        }
    
    def _error_response(self, message: str) -> Dict:
        """Create an error response."""
        return {
            "status": "error",
            "message": message,
            "new_state": {}
        }
    
    def get_current_state(self) -> Dict:
        """Get current state (all M1 instances)."""
        if self.mode == "lionweb":
            riders = self.loader.find_m1_instances(self.domain, "Rider")
            teams = self.loader.find_m1_instances(self.domain, "Team")
            
            return {
                "riders": [
                    {
                        "name": self.loader._get_instance_property(r, "name"),
                        "age": self.loader._get_instance_property(r, "age"),
                        "country": self.loader._get_instance_property(r, "country")
                    }
                    for r in riders
                ],
                "teams": [
                    {
                        "name": self.loader._get_instance_property(t, "name"),
                        "country": self.loader._get_instance_property(t, "country"),
                        "budget": self.loader._get_instance_property(t, "budget"),
                        "founded": self.loader._get_instance_property(t, "founded")
                    }
                    for t in teams
                ]
            }
        else:
            # Fall back to state manager for DSL mode
            from ..core.state_manager import StateManager
            state_manager = StateManager(AppConfig.STATE_FILE)
            return state_manager.load()
    
    def save_state(self):
        """Save current state to model store."""
        if self.mode == "lionweb":
            self.loader.save_models(self.domain)