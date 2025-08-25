# src/conversation/extractor.py
import json
import re
from typing import Dict, Optional
from ..core.llm_client import LLMClient

class TaskExtractor:
    """Extracts structured task information from natural language."""
    
    @staticmethod
    def extract_task_details(query: str, model_name: str) -> Dict:
        """Extract task details from user query."""
        
        prompt = f"""
You are a highly accurate data extraction tool. Your only job is to extract specific parameters from a user's text and return them as a JSON object.

**Instructions:**
1. Analyze the user's text to determine the primary intent ("action"). It must be one of: `schedule_session`, `create_venue`, `modify_venue`, or `unknown`.
2. Extract parameters based on the action.
3. **Strictly adhere to these parameter names:** `name`, `hosted_by`, `in_venue`, `expected_attendees`, `requires_av`, `capacity`, `has_av_system`.
4. If a value is not present in the text, DO NOT include the key in the JSON.
5. Return a single JSON object with the keys "action" and "parameters".

**User Text:** "{query}"
**JSON Output:**
"""
        
        try:
            response_str = LLMClient.execute_request(
                prompt, model_name, is_json_format=True
            )
            return json.loads(response_str)
        except (json.JSONDecodeError, ConnectionError) as e:
            return {"action": "error", "parameters": {"details": str(e)}}
    
    @staticmethod
    def parse_boolean(value: str) -> bool:
        """Parse a string value to boolean."""
        return str(value).strip().lower() in ['true', 'yes', 'y', '1']
    
    @staticmethod
    def parse_number(value: str) -> Optional[int]:
        """Extract a number from string."""
        match = re.search(r'\d+', str(value))
        return int(match.group()) if match else None