# src/lark_engine/executor.py

import importlib # --- NEW: Add this import
from typing import Dict
from ..core.config import AppConfig
from ..core.state_manager import StateManager
from .dsl_builder import DSLBuilder 
from ..framework.base_interpreter import execute_dsl

class LarkTaskExecutor:
    def __init__(self, domain: str):
        self.domain = domain
        self.state_manager = StateManager(AppConfig.STATE_FILE)
        self.dsl_builder = DSLBuilder()
    
    def execute(self, role: str, conversation_state: Dict) -> Dict:
        dsl_code = ""
        try:
            dsl_code = self.dsl_builder.build(
                conversation_state["task_details"], 
                role
            )
            
            state = self.state_manager.load()
            
            try:
                interpreter_module = importlib.import_module(f"src.domains.{self.domain}.interpreter")
                
                interpreter_class_name = f"{self.domain.capitalize()}Interpreter"
                InterpreterClass = getattr(interpreter_module, interpreter_class_name)
                
                interpreter = InterpreterClass(state, role)
            except (ModuleNotFoundError, AttributeError) as e:
                raise NotImplementedError(f"Could not find a valid interpreter for domain '{self.domain}': {e}")
            
            result = execute_dsl(
                dsl_code,
                AppConfig.get_grammar_path(self.domain),
                interpreter
            )
            
            
            if "results" in result: 
                return {
                    "status": "success",
                    "message": result.get("message", "Query successful."),
                    "results": result.get("results", []),
                    "action_type": "query", 
                    "dsl_code": dsl_code
                }
            else: 
                self.state_manager.save(result['new_state'])
                
                action = conversation_state["task_details"].get("action", "").replace('_', ' ').title()
                name = conversation_state["task_details"].get("parameters", {}).get("name", "")
                success_msg = f"✅ Successfully completed: {action}"
                if name:
                    success_msg += f" '{name}'"
                
                return {
                    "status": "success",
                    "message": success_msg,
                    "action_type": "mutation",
                    "dsl_code": dsl_code
                }
            
        except ValueError as e:
            return self._handle_validation_error(str(e), dsl_code)
        except Exception as e:
            return {
                "status": "error",
                "message": f"❌ Unexpected Error: {e}",
                "dsl_code": dsl_code
            }
            
    def _handle_validation_error(self, error_msg: str, dsl_code: str) -> Dict:
        if "RoleMismatchError" in error_msg:
            return {"status": "error", "message": f"❌ Permission Error: {error_msg.split(':', 1)[1] if ':' in error_msg else error_msg}", "dsl_code": dsl_code}
        elif "ValidationError" in error_msg:
            return {"status": "error", "message": f"❌ Validation Failed: {error_msg.split(':', 1)[1] if ':' in error_msg else error_msg}", "dsl_code": dsl_code}
        else:
            return {"status": "error", "message": f"❌ Error: {error_msg}", "dsl_code": dsl_code}