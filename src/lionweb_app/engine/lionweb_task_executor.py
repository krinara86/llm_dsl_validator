# src/lionweb_app/engine/lionweb_task_executor.py
from typing import Dict, Any

class LionWebTaskExecutor:
    """Executes tasks by interacting with the LionWebConnectorLoader."""

    def __init__(self, loader):
        self.loader = loader

    def execute(self, role: str, conversation_state: Dict) -> Dict:
        """Executes a validated task by calling loader methods."""
        try:
            task_details = conversation_state["task_details"]
            action = task_details.get("action")
            params = task_details.get("parameters", {})
            
            # Note: Role-based permissions are checked in the Orchestrator
            # A more robust system might double-check them here.

            if action.startswith("find_"):
                concept_name = "Rider" if "rider" in action else "Team"
                results = self.loader.find_m1_instances("cycling", concept_name, params)
                
                # Convert DynamicNodes to simple dicts for display
                dict_results = []
                for node in results:
                    res = {}
                    for feature in node.get_classifier().features:
                        if isinstance(feature, Property):
                           res[feature.name] = node.get_property_value(feature)
                    dict_results.append(res)

                return {
                    "status": "success",
                    "message": f"Found {len(dict_results)} result(s).",
                    "results": dict_results,
                    "action_type": "query"
                }

            elif action.startswith("create_"):
                concept_name = "Rider" if "rider" in action else "Team"
                self.loader.create_m1_instance("cycling", concept_name, params)
                self.loader.save_models("cycling")
                return self._success_response(action, params.get("name"))

            elif action.startswith("modify_"):
                instance_name = params.pop("name", None)
                if not instance_name:
                    raise ValueError("'name' parameter is required to modify an instance.")
                
                self.loader.modify_m1_instance("cycling", instance_name, params)
                self.loader.save_models("cycling")
                return self._success_response(action, instance_name)

            else:
                raise ValueError(f"Unknown action type: {action}")

        except Exception as e:
            return {"status": "error", "message": f"❌ Execution Error: {e}"}

    def _success_response(self, action: str, name: str) -> Dict:
        """Formats a standard success message for mutation actions."""
        action_title = action.replace('_', ' ').title()
        success_msg = f"✅ Successfully completed: {action_title}"
        if name:
            success_msg += f" '{name}'"
        return {"status": "success", "message": success_msg, "action_type": "mutation"}