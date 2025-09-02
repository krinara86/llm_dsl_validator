# src/execution/executor.py
from typing import Dict
from ..core.config import AppConfig
from ..core.state_manager import StateManager
from ..core.dsl_builder import DSLBuilder
from ..framework.base_interpreter import execute_dsl
from ..domains.event.interpreter import EventInterpreter

class TaskExecutor:
    """Executes confirmed tasks using the DSL interpreter."""
    
    def __init__(self):
        self.state_manager = StateManager(AppConfig.STATE_FILE)
        self.dsl_builder = DSLBuilder()
    
    def execute(self, role: str, conversation_state: Dict) -> Dict:
        """Execute a confirmed task."""
        dsl_code = ""
        try:
            # Build DSL code
            dsl_code = self.dsl_builder.build(
                conversation_state["task_details"], 
                role
            )
            
            state = self.state_manager.load()
            interpreter = EventInterpreter(state, role)
            
            
            result = execute_dsl(
                dsl_code,
                AppConfig.get_grammar_path('event'),
                interpreter
            )
            
            
            self.state_manager.save(result['new_state'])
            
            
            action = conversation_state["task_details"].get("action", "").replace('_', ' ').title()
            name = conversation_state["task_details"].get("parameters", {}).get("name", "")
            success_msg = f"✅ Successfully completed: {action}"
            if name:
                success_msg += f" '{name}'"
            
            return {
                "status": "success",
                "message": success_msg,
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
        """Handle validation errors from the interpreter."""
        if "RoleMismatchError" in error_msg:
            return {
                "status": "error",
                "message": f"❌ Permission Error: {error_msg.split(':', 1)[1] if ':' in error_msg else error_msg}",
                "dsl_code": dsl_code
            }
        elif "ValidationError" in error_msg:
            return {
                "status": "error",
                "message": f"❌ Validation Failed: {error_msg.split(':', 1)[1] if ':' in error_msg else error_msg}",
                "dsl_code": dsl_code
            }
        else:
            return {
                "status": "error",
                "message": f"❌ Error: {error_msg}",
                "dsl_code": dsl_code
            }