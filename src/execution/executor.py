# src/execution/executor.py
from typing import Dict
from ..core.config import AppConfig
from ..frameworks.lark_handler import LarkDomainHandler
from ..frameworks.lionweb_handler import LionWebHandler

class TaskExecutor:
    def __init__(self):
        if AppConfig.FRAMEWORK == "lark":
            self.handler = LarkDomainHandler(AppConfig.DOMAIN)
        elif AppConfig.FRAMEWORK == "lionweb":
            self.handler = LionWebHandler(AppConfig.DOMAIN)
        else:
            raise ValueError(f"Unknown framework: {AppConfig.FRAMEWORK}")
    
    def execute(self, role: str, conversation_state: Dict) -> Dict:
        artifact = ""
        try:
            artifact = self.handler.build_artifact(
                conversation_state["task_details"], 
                role
            )
            
            result = self.handler.execute(
                artifact, 
                role,
                conversation_state["task_details"]
            )
            
            if result.get("action_type") == "query":
                return {
                    "status": "success",
                    "message": result.get("message", "Query successful."),
                    "results": result.get("results", []),
                    "action_type": "query", 
                    "dsl_code": artifact 
                }
            else:
                action = conversation_state["task_details"].get("action", "").replace('_', ' ').title()
                name = conversation_state["task_details"].get("parameters", {}).get("name", "")
                
                success_msg = f"✅ Successfully completed: {action}"
                if name:
                    success_msg += f" '{name}'"
                
                if result.get("message") and "Successfully" in result.get("message"):
                    success_msg = f"✅ {result['message']}"
                
                return {
                    "status": "success",
                    "message": success_msg,
                    "action_type": "mutation",
                    "dsl_code": artifact  
                }
            
        except ValueError as e:
            return self._handle_validation_error(str(e), artifact)
        except Exception as e:
            return {
                "status": "error",
                "message": f"❌ Unexpected Error: {e}",
                "dsl_code": artifact
            }
    
    def _handle_validation_error(self, error_msg: str, artifact: str) -> Dict:
        if "RoleMismatchError" in error_msg:
            return {
                "status": "error", 
                "message": f"❌ Permission Error: {error_msg.split(':', 1)[1] if ':' in error_msg else error_msg}", 
                "dsl_code": artifact
            }
        elif "ValidationError" in error_msg:
            return {
                "status": "error", 
                "message": f"❌ Validation Failed: {error_msg.split(':', 1)[1] if ':' in error_msg else error_msg}", 
                "dsl_code": artifact
            }
        else:
            return {
                "status": "error", 
                "message": f"❌ Error: {error_msg}", 
                "dsl_code": artifact
            }