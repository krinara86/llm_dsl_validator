# src/cycling_system.py
from typing import Dict, Any
from pathlib import Path
from lionweb.language import Property

from src.lionweb_app.engine.connector_loader import LionWebConnectorLoader
from src.lionweb_app.engine.lionweb_task_executor import LionWebTaskExecutor
# --- CHANGE: Import the new orchestrator ---
from src.lionweb_app.conversation.cycling_orchestrator import CyclingOrchestrator

class CyclingSystem:
    """Main system class for the Cycling domain, powered by LionWeb."""

    def __init__(self):
        project_root = Path(__file__).parent.parent
        self.loader = LionWebConnectorLoader(project_root)
        self.executor = LionWebTaskExecutor(self.loader)

        connector_path = project_root / "src" / "domains" / "cycling" / "nl_connector_m1.json"
        if not connector_path.exists():
            self.loader.generate_connector_m1("cycling")
        
        self.loader.load_all("cycling")

        connector_dict = self.loader.get_connector_as_dict("cycling")
        schema_dict = self.loader.get_schema_as_dict("cycling")

        # --- CHANGE: Instantiate the new orchestrator ---
        self.orchestrator = CyclingOrchestrator(connector=connector_dict, schema=schema_dict)

    def get_available_models(self) -> list:
        from src.core.llm_client import LLMClient
        return LLMClient.get_available_models()

    def process_query(self, query: str, role: str, model_name: str, 
                      conversation_state: Dict = None, pre_filled_details: Dict = None) -> Dict:
        return self.orchestrator.process_request(
            query, role, model_name, conversation_state, pre_filled_details
        )
    
    def execute_task(self, role: str, conversation_state: Dict) -> Dict:
        return self.executor.execute(role, conversation_state)

    def get_current_state(self) -> Dict:
        riders = self.loader.find_m1_instances("cycling", "Rider")
        teams = self.loader.find_m1_instances("cycling", "Team")
        
        state = {"riders": [], "teams": []}
        for node in riders:
            res = {}
            for feature in node.get_classifier().features:
                if isinstance(feature, Property):
                   res[feature.name] = node.get_property_value(feature)
            state["riders"].append(res)
            
        for node in teams:
            res = {}
            for feature in node.get_classifier().features:
                if isinstance(feature, Property):
                   res[feature.name] = node.get_property_value(feature)
            state["teams"].append(res)
            
        return state