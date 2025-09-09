# src/conversation/extractor.py
import json
import re
from typing import Dict, Optional, Any
from ..core.llm_client import LLMClient

class TaskExtractor:
    """Extracts structured task information from natural language."""
    
    @staticmethod
    def extract_task_details(query: str, model_name: str, connector: Dict[str, Any]) -> Dict:
        
        action_names = list(connector.get("actions", {}).keys())
        
        all_params = {}
        for action_details in connector.get("actions", {}).values():
            for param_name, param_details in action_details.get("parameters", {}).items():
                if param_name not in all_params:
                    all_params[param_name] = param_details.get("description", "No description.")
        
        param_guidance = []
        for param_name, param_desc in all_params.items():
            param_guidance.append(f'* `{param_name}`: {param_desc}')

        prompt = f"""
You are a highly accurate data extraction assistant. Your single purpose is to extract the user's intent and its associated parameters from the text provided.
You MUST respond with only a single, valid JSON object and nothing else. Do not provide any conversational text, explanations, or markdown.

Your response must be a JSON object with two keys:
1.  `"action"`: The user's primary intent. This value MUST be one of the following strings: {action_names} or "unknown".
2.  `"parameters"`: A JSON object containing ONLY the parameters you can extract from the user's text.

**CRITICAL RULE:** If you cannot find a value for a parameter in the user text, you MUST NOT include its key in the `"parameters"` object. Do not guess or invent values. Do not use placeholders like "unknown" or "N/A". For numeric or boolean parameters, if a value is not explicitly mentioned, omit the key entirely.

## Parameter Guidance
{"\n".join(param_guidance)}

## User Text
"{query}"

## JSON Output
"""
        
        try:
            response_str = LLMClient.execute_request(
                prompt, model_name, is_json_format=True
            )
            
            json_match = re.search(r'\{.*\}', response_str, re.DOTALL)
            
            if not json_match:
                raise json.JSONDecodeError("No JSON object found in the model's response.", response_str, 0)
            
            clean_json_str = json_match.group(0)
            return json.loads(clean_json_str)
            
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