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
                extracted = self.extractor.extract_task_details(query, model_name, self.connector)
            
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
            
            # Handle special cases for primary parameters
            action = task_details.get("action", "")
            params = task_details.get("parameters", {})
            
            # For modify operations, we need the ID as the primary parameter
            if action.startswith("modify_"):
                if action == "modify_rider" and "rider_id" not in task_details:
                    task_details["rider_id"] = params.get("rider_id", 0)
                elif action == "modify_team" and "team_id" not in task_details:
                    task_details["team_id"] = params.get("team_id", 0)
                elif action == "modify_race" and "race_id" not in task_details:
                    task_details["race_id"] = params.get("race_id", 0)
            
            # For add operations, we need a name
            elif action.startswith("add_"):
                if "name" not in task_details:
                    if action == "add_rider":
                        first = params.get("first_name", "")
                        last = params.get("last_name", "")
                        task_details["name"] = f"{first} {last}".strip()
                    elif action == "add_team":
                        task_details["name"] = params.get("name", "New Team")
                    elif action == "add_race":
                        task_details["name"] = params.get("name", "New Race")
            
            # For document_entity, we need a description
            elif action == "document_entity" and "description" not in task_details:
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