# src/cycling_system.py
"""Main entry point for the cycling management system."""

from pathlib import Path
from typing import Dict, List, Any
from src.core.config import AppConfig
from src.core.llm_client import LLMClient
from src.core.connector_loader import load_connector
from src.core.dsl_builder import DSLBuilder
from src.domains.cycling.interpreter import CyclingInterpreter
from src.domains.cycling.schema import DOMAIN_SCHEMA
from src.framework.base_interpreter import execute_dsl
from src.conversation.extractor import TaskExtractor
from src.conversation.formatter import MessageFormatter
from src.conversation.document_processor import DocumentProcessor

class CyclingSystem:
    """Main system coordinator for cycling domain."""
    
    def __init__(self, data_file: Path = None):
        # Use provided data file or default
        if data_file is None:
            data_file = AppConfig.PROJECT_ROOT / "notebooks" / "cycling_data.json"
        
        self.data_file = data_file
        self.connector = load_connector('cycling')
        self.dsl_builder = DSLBuilder()
        self.extractor = TaskExtractor()
        self.formatter = MessageFormatter()
        self.document_processor = DocumentProcessor()
        self.conversation_state = {}
        
        # Verify connector loaded
        if not self.connector or 'actions' not in self.connector:
            raise ValueError("Failed to load cycling connector")
    
    def process_query(self, query: str, role: str, model_name: str,
                 conversation_state: dict = None, pre_filled_details: dict = None) -> dict:
        """Process a natural language query."""
        
        if not conversation_state:
            conversation_state = {"status": "processing", "history": [], "task_details": {}}
        
        self.conversation_state = conversation_state
        
        # Handle clarification responses
        if conversation_state.get("status") == "awaiting_clarification":
            # Parse the clarification response
            missing_params = conversation_state.get("missing_params", [])
            task_details = conversation_state.get("task_details", {})
            
            # Simple parsing of key:value pairs from the query
            lines = query.strip().split('\n')
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().replace(' ', '_').lower()
                    value = value.strip()
                    
                    # Update task details
                    if "parameters" not in task_details:
                        task_details["parameters"] = {}
                    task_details["parameters"][key] = value
            
            conversation_state["task_details"] = task_details
        else:
            # Extract task details from query
            if pre_filled_details and pre_filled_details.get('action') != 'unknown':
                extracted = pre_filled_details
            else:
                # Debug: Check connector is loaded
                if not self.connector or 'actions' not in self.connector:
                    print(f"Warning: Connector not properly loaded. Reloading...")
                    self.connector = load_connector('cycling')
                
                extracted = self.extractor.extract_task_details(query, model_name, self.connector)
                
                # Clean up extracted parameters for cycling domain
                if extracted.get("action") == "find_rider" and extracted.get("parameters"):
                    params = extracted["parameters"]
                    
                    # Remove nonsensical name_patterns that are really about location
                    if "name_pattern" in params:
                        pattern = params["name_pattern"].lower()
                        # If the pattern mentions countries or locations, remove it
                        if any(word in pattern for word in ["from", "in", "riders", "all", "french", "france", 
                                                        "american", "usa", "italian", "italy", "spanish"]):
                            del params["name_pattern"]
                    
                    # Convert country names to codes if needed
                    if "country" in params:
                        country_map = {
                            "france": "FR", "french": "FR",
                            "usa": "US", "america": "US", "american": "US", 
                            "italy": "IT", "italian": "IT",
                            "spain": "ES", "spanish": "ES",
                            "netherlands": "NL", "dutch": "NL",
                            "belgium": "BE", "belgian": "BE",
                            "germany": "DE", "german": "DE",
                            "uk": "GB", "british": "GB",
                        }
                        country = params["country"].lower()
                        if country in country_map:
                            params["country"] = country_map[country]
                        elif len(country) > 2:
                            # If it's not a code and not in map, try to extract from context
                            for key, code in country_map.items():
                                if key in country:
                                    params["country"] = code
                                    break
                
                # For add_rider, if we got a name_pattern, split it into first/last names
                if extracted.get("action") == "add_rider" and extracted.get("parameters"):
                    params = extracted["parameters"]
                    if "name_pattern" in params and "first_name" not in params:
                        # Split the name pattern into first and last
                        name_parts = params["name_pattern"].split()
                        if len(name_parts) >= 2:
                            params["first_name"] = name_parts[0]
                            params["last_name"] = " ".join(name_parts[1:])
                        del params["name_pattern"]
            
            if extracted.get("action") in [None, "unknown", "error"]:
                return {
                    "status": "error",
                    "message": "I couldn't understand your request. Please try rephrasing.",
                    "new_state": conversation_state
                }
            
            conversation_state["task_details"] = extracted
        
        # Check for missing parameters
        task_details = conversation_state["task_details"]
        action = task_details.get("action")
        
        # IMPORTANT: Set the name parameter for add_rider BEFORE checking for missing params
        if action == "add_rider":
            params = task_details.get("parameters", {})
            if "first_name" in params and "last_name" in params:
                task_details["name"] = f"{params['first_name']} {params['last_name']}"
        
        if action in DOMAIN_SCHEMA:
            schema = DOMAIN_SCHEMA[action]
            required = schema.get("required", [])
            params = task_details.get("parameters", {})
            
            # Filter out the main parameter (first positional arg in DSL)
            actual_required = [p for p in required if p != "name" and p != "rider_id" 
                            and p != "team_id" and p != "race_id" and p != "description"]
            
            missing = [p for p in actual_required if p not in params]
            
            if missing:
                conversation_state["status"] = "awaiting_clarification"
                conversation_state["missing_params"] = missing
                
                # Build form-based clarification
                form_fields = []
                for param in missing:
                    param_info = self.connector['actions'][action]['parameters'].get(param, {})
                    param_type = schema.get("param_types", {}).get(param, {}).get("type", "string")
                    
                    field = {
                        "name": param,
                        "type": param_type,
                        "label": param.replace('_', ' ').title(),
                        "prompt": param_info.get("clarification_prompt", f"Please provide {param}")
                    }
                    
                    # Add special handling for certain fields
                    if param == "country":
                        field["placeholder"] = "e.g., FR, US, NL"
                    elif param == "birth_date":
                        field["placeholder"] = "YYYY-MM-DD"
                    
                    form_fields.append(field)
                
                return {
                    "status": "clarification_needed",
                    "message": f"<b>To complete '{action.replace('_', ' ')}', please provide:</b>",
                    "form_fields": form_fields,
                    "new_state": conversation_state
                }
        
        # Check if this is a read-only query
        if DOMAIN_SCHEMA.get(action, {}).get("is_read_only"):
            conversation_state["status"] = "ready_to_execute"
            return {
                "status": "direct_execute",
                "message": "Executing search...",
                "new_state": conversation_state
            }
        
        # Ready for confirmation
        conversation_state["status"] = "awaiting_confirmation"
        
        # Format understanding
        understanding = self._format_understanding(task_details, role)
        
        return {
            "status": "confirmation_needed",
            "understanding": understanding,
            "message": "Ready to execute. Please confirm or cancel.",
            "new_state": conversation_state
        }

    def execute_task(self, role: str, conversation_state: dict = None) -> dict:
        """Execute a confirmed task."""
        if conversation_state:
            self.conversation_state = conversation_state
        
        try:
            # Build DSL code
            task_details = self.conversation_state.get("task_details", {})
            action = task_details.get("action", "")
            params = task_details.get("parameters", {})
            
            # ALWAYS set the name/id parameters right before building DSL
            if action == "add_rider":
                # Always build name from first_name and last_name
                first = params.get("first_name", "")
                last = params.get("last_name", "")
                task_details["name"] = f"{first} {last}".strip()
            elif action == "add_team":
                # For add_team, use the name from parameters
                task_details["name"] = params.get("name", "New Team")
            elif action == "add_race":
                # For add_race, use the name from parameters
                task_details["name"] = params.get("name", "New Race")
            elif action == "modify_rider":
                task_details["rider_id"] = params.get("rider_id", 0)
            elif action == "modify_team":
                task_details["team_id"] = params.get("team_id", 0)
            elif action == "modify_race":
                task_details["race_id"] = params.get("race_id", 0)
            elif action == "document_entity":
                entity_type = params.get("entity_type", "entity")
                entity_id = params.get("entity_id", 0)
                task_details["description"] = f"Document {entity_type} {entity_id}"
            
            dsl_code = self.dsl_builder.build(task_details, role)
            
            # Execute DSL
            interpreter = CyclingInterpreter(self.data_file, role)
            
            result = execute_dsl(
                dsl_code,
                AppConfig.PROJECT_ROOT / "src" / "domains" / "cycling" / "grammar.dsl",
                interpreter
            )
            
            # Handle results
            if "results" in result:
                return {
                    "status": "success",
                    "message": result.get("message", "Query successful."),
                    "results": result.get("results", []),
                    "action_type": "query",
                    "dsl_code": dsl_code
                }
            else:
                action_name = task_details.get("action", "").replace('_', ' ').title()
                return {
                    "status": "success",
                    "message": f"✅ Successfully completed: {action_name}",
                    "action_type": "mutation",
                    "dsl_code": dsl_code
                }
        
        except ValueError as e:
            error_msg = str(e)
            if "RoleMismatchError" in error_msg:
                return {
                    "status": "error",
                    "message": f"❌ Permission Error: {error_msg.split(':', 1)[1]}"
                }
            elif "ValidationError" in error_msg:
                return {
                    "status": "error",
                    "message": f"❌ Validation Failed: {error_msg.split(':', 1)[1]}"
                }
            else:
                return {
                    "status": "error",
                    "message": f"❌ Error: {error_msg}"
                }
        
        except Exception as e:
            return {
                "status": "error",
                "message": f"❌ Unexpected Error: {e}"
            }
            
    def process_document(self, document: str, role: str, model_name: str) -> dict:
        """Process a document containing multiple tasks."""
        return self.document_processor.extract_tasks(document, model_name)
    
    def _format_understanding(self, task_details: dict, role: str) -> str:
        """Format the understanding of the task."""
        action = task_details.get("action", "unknown")
        params = task_details.get("parameters", {})
        
        html = f"""
        <div style='background-color: #f8f9fa; padding: 15px; border-radius: 8px;'>
            <h4>Understanding:</h4>
            <p><b>Role:</b> {role}</p>
            <p><b>Action:</b> {action.replace('_', ' ').title()}</p>
            <p><b>Parameters:</b></p>
            <ul>
        """
        
        if params:
            for key, value in params.items():
                display_key = key.replace('_', ' ').title()
                html += f"<li>{display_key}: <code>{value}</code></li>"
        else:
            html += "<li><i>None</i></li>"
        
        html += "</ul></div>"
        return html
    
    def get_available_models(self) -> list:
        """Get list of available LLM models."""
        return LLMClient.get_available_models()