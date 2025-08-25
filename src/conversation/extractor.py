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
1.  Analyze the user's text to determine the primary intent ("action"). It must be one of: `schedule_session`, `create_venue`, `modify_venue`, or `unknown`.
2.  Extract parameters based on the action, using the guidance below.
3.  Return a single JSON object with the keys "action" and "parameters". If a value is not present, DO NOT include its key in the JSON.

**Parameter Guidance:**
* `name`: The official title of the session or venue. E.g., "Introduction to AI", "Main Auditorium".
* `hosted_by`: The person or organization presenting the session. E.g., "Jane Doe", "AI Corp".
* `in_venue`: The specific location or room for the session. E.g., "Room 5", "Conference Hall A".
* `expected_attendees`: The number of people expected to attend.
* `requires_av`: A boolean (true/false) indicating if the session needs audio/visual equipment.
* `capacity`: The maximum number of people a venue can hold.
* `has_av_system`: A boolean (true/false) indicating if a venue has audio/visual equipment.

**Strictly adhere to the parameter names listed above.**

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