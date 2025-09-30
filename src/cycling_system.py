# src/cycling_system.py
"""Main entry point for the cycling management system using LionWeb."""

from typing import Dict, List, Any, Optional
from pathlib import Path
from lionweb.language import Property

from lionweb_app.engine.connector_loader import LionWebConnectorLoader
from conversation.orchestrator import ConversationOrchestrator
from conversation.document_processor import DocumentProcessor
from core.llm_client import LLMClient


class CyclingSystem:
    """Main system for managing cycling data using LionWeb models."""
    
    def __init__(self, project_root: Path = None):
        """Initialize the cycling system with LionWeb backend."""
        self.loader = LionWebConnectorLoader(project_root)
        
        # Ensure the cycling domain directory exists
        (self.loader.domains_dir / "cycling").mkdir(parents=True, exist_ok=True)
        
        # Generate the M1 connector if it doesn't exist
        connector_path = self.loader.domains_dir / "cycling" / "nl_connector_m1.json"
        if not connector_path.exists():
            self.loader.generate_connector_m1("cycling")
        
        # Load all LionWeb artifacts
        self.loader.load_all("cycling")
        
        # Get connector and schema as dictionaries for the conversation layer
        self.connector = self.loader.get_connector_as_dict("cycling")
        self.schema = self.loader.get_schema_as_dict("cycling")
        
        # Initialize the orchestrator with cycling-specific dependencies
        # Note: We pass None for state_manager since LionWeb handles persistence
        self.orchestrator = ConversationOrchestrator(
            connector=self.connector,
            schema=self.schema,
            state_manager=None  # LionWeb handles its own persistence
        )
        
        # Document processor for handling multi-task documents
        self.document_processor = DocumentProcessor()
    
    def process_query(self, query: str, role: str, model_name: str,
                     conversation_state: Dict = None, pre_filled_details: Dict = None) -> Dict:
        """Process a user query through the conversation orchestrator."""
        return self.orchestrator.process_request(
            query, role, model_name, conversation_state, pre_filled_details
        )
    
    def process_document(self, document: str, role: str, model_name: str) -> Dict:
        """Process a document containing multiple tasks."""
        # Pass the connector to document processor for domain-aware extraction
        result = self.document_processor.extract_tasks(document, model_name, self.connector)
        
        # The result contains extracted tasks in the same format as event system
        # So it will work with the existing task processing flow
        return result
    
    def execute_task(self, role: str, conversation_state: Dict) -> Dict:
        """Execute a validated task by calling LionWeb loader methods."""
        try:
            task_details = conversation_state.get("task_details", {})
            action = task_details.get("action")
            params = task_details.get("parameters", {})
            
            # Map actions to LionWeb operations
            if action == "create_rider":
                instance = self.loader.create_m1_instance("cycling", "Rider", params)
                self.loader.save_models("cycling")
                instance_dict = self._convert_node_to_dict(instance)
                return {
                    "status": "success",
                    "message": f"✅ Successfully created rider '{params.get('name')}'",
                    "action_type": "mutation",
                    "instance": instance_dict
                }
                
            elif action == "modify_rider":
                instance_name = params.pop("name", None)
                if not instance_name:
                    return {"status": "error", "message": "❌ Rider name is required for modification."}
                
                modified = self.loader.modify_m1_instance("cycling", instance_name, params)
                if modified:
                    self.loader.save_models("cycling")
                    instance_dict = self._convert_node_to_dict(modified)
                    return {
                        "status": "success",
                        "message": f"✅ Successfully modified rider '{instance_name}'",
                        "action_type": "mutation",
                        "instance": instance_dict
                    }
                else:
                    return {"status": "error", "message": f"❌ Could not find rider '{instance_name}'."}
                    
            elif action == "create_team":
                instance = self.loader.create_m1_instance("cycling", "Team", params)
                self.loader.save_models("cycling")
                instance_dict = self._convert_node_to_dict(instance)
                return {
                    "status": "success",
                    "message": f"✅ Successfully created team '{params.get('name')}'",
                    "action_type": "mutation",
                    "instance": instance_dict
                }
                
            elif action == "find_rider":
                results = self.loader.find_m1_instances("cycling", "Rider", filters=params)
                dict_results = self._convert_nodes_to_dicts(results)
                return {
                    "status": "success",
                    "message": f"Found {len(dict_results)} rider(s).",
                    "results": dict_results,
                    "action_type": "query"
                }
                
            elif action == "find_team":
                results = self.loader.find_m1_instances("cycling", "Team", filters=params)
                dict_results = self._convert_nodes_to_dicts(results)
                return {
                    "status": "success",
                    "message": f"Found {len(dict_results)} team(s).",
                    "results": dict_results,
                    "action_type": "query"
                }
                
            else:
                return {"status": "error", "message": f"❌ Unknown action: {action}"}
                
        except Exception as e:
            return {"status": "error", "message": f"❌ Execution Error: {e}"}
    
    def _convert_nodes_to_dicts(self, nodes: List) -> List[Dict]:
        """Convert DynamicNodes to simple dictionaries for display."""
        dict_results = []
        for node in nodes:
            dict_results.append(self._convert_node_to_dict(node))
        return dict_results
    
    def _convert_node_to_dict(self, node) -> Dict:
        """Convert a single DynamicNode to a dictionary."""
        result = {}
        for feature in node.get_classifier().features:
            if isinstance(feature, Property):
                result[feature.name] = node.get_property_value(feature)
        return result
    
    def _success_response(self, action: str, name: str) -> Dict:
        """Format a standard success message for mutation actions."""
        action_title = action.replace('_', ' ').title()
        success_msg = f"✅ Successfully completed: {action_title}"
        if name:
            success_msg += f" '{name}'"
        return {
            "status": "success",
            "message": success_msg,
            "action_type": "mutation"
        }
    
    def get_current_state(self) -> Dict:
        """Get the current state of all cycling data."""
        riders = self.loader.find_m1_instances("cycling", "Rider")
        teams = self.loader.find_m1_instances("cycling", "Team")
        
        riders_dict = self._convert_nodes_to_dicts(riders)
        teams_dict = self._convert_nodes_to_dicts(teams)
        
        return {
            "riders": riders_dict,
            "teams": teams_dict
        }
    
    def get_available_models(self) -> List[str]:
        """Get list of available LLM models."""
        return LLMClient.get_available_models()