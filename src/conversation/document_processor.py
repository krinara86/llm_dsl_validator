# src/conversation/document_processor.py
import json
from typing import Dict, List
from ..core.llm_client import LLMClient

class DocumentProcessor:
    """Processes documents containing multiple tasks."""
    
    def extract_tasks(self, document: str, model_name: str) -> Dict:
        """Extract multiple tasks from a document."""
        
        prompt = f"""
You are a task extraction assistant. Extract ALL distinct event management tasks from the following text.
Each task should be a separate action that can be performed.

Return a JSON object with a "tasks" array, where each task is a string describing one action.
Focus on concrete actions like creating venues, modifying venues, or scheduling sessions.

Text: "{document}"

Return format:
{{
  "tasks": ["task 1 description", "task 2 description", ...]
}}
"""
        
        try:
            response_str = LLMClient.execute_request(
                prompt, model_name, is_json_format=True
            )
            result = json.loads(response_str)
            tasks = result.get("tasks", [])
            
            if not tasks:
                return {
                    "status": "no_tasks",
                    "message": "No actionable tasks found in the document.",
                    "tasks": []
                }
            
            return {
                "status": "tasks_extracted",
                "message": f"Found {len(tasks)} task(s) in the document. I'll process them one by one.",
                "tasks": tasks
            }
            
        except (json.JSONDecodeError, ConnectionError) as e:
            return {
                "status": "error",
                "message": f"Failed to process document: {e}",
                "tasks": []
            }