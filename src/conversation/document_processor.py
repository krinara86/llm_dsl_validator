# src/conversation/document_processor.py
import json
import re
from typing import Dict, List

# Handle both relative and absolute imports
try:
    from ..core.llm_client import LLMClient
except (ImportError, ValueError):
    from core.llm_client import LLMClient

class DocumentProcessor:
    """Processes documents containing multiple tasks."""

    def extract_tasks(self, document: str, model_name: str, connector: Dict = None) -> Dict:
        """Extract multiple tasks from a document into structured objects."""
        
        # Build dynamic action list and parameter guidance from connector
        action_list = []
        param_examples = {}
        
        if connector and "actions" in connector:
            action_list = list(connector["actions"].keys())
            
            # Build parameter examples from connector
            for action_name, action_details in connector["actions"].items():
                params = action_details.get("parameters", {})
                if params:
                    param_names = list(params.keys())
                    param_examples[action_name] = param_names

        # Create action string for prompt
        action_str = ", ".join([f"`{a}`" for a in action_list]) if action_list else "actions defined in your domain"
        
        # Build parameter guidance string
        param_guidance = ""
        if param_examples:
            param_guidance = "\n**Parameter examples by action type:**\n"
            for action, params in param_examples.items():
                param_str = ", ".join([f"`{p}`" for p in params])
                param_guidance += f"- {action}: {param_str}\n"

        prompt = f"""
You are an expert assistant. Your task is to analyze the document below and extract all distinct tasks into a structured JSON format.

**CRITICAL INSTRUCTIONS:**
1. Read the entire document carefully.
2. **EVERY individual entity creation/modification is a SEPARATE task**:
   - If the document mentions creating/modifying multiple items, each one is a separate task
   - "Create A and B" = TWO separate tasks
   - "Register the following items: A, B, C, D" = FOUR separate tasks
3. **IMPORTANT: When an entity is described with its properties, it's ONE creation task**:
   - "Room A - 10 seats, with AV" = ONE create task with all properties
   - "Create rider John aged 25 from USA" = ONE create task with all properties
   - Do NOT split an entity and its initial properties into separate create and modify tasks
4. Identify actions from this list: {action_str}
5. For EACH individual task, create a separate JSON object with:
   - "task_description": Brief summary of just that one task
   - "action": The specific action from the list above (usually create_* for new entities)
   - "details": ALL properties mentioned for that entity in one object
6. NEVER combine multiple entities into arrays - each needs its own task object
7. Watch for phrases like "First", "Second", "Third", "Another", "Also", numbered lists, bullet points - these indicate separate tasks
8. Common patterns:
   - "X with Y and Z" = create X with properties Y and Z (ONE task)
   - "X. Modify it to have Y" = create X (one task), then modify X (second task)
   - List of items with descriptions = one create task per item WITH all its properties

{param_guidance}

**Example**: 
Input: "Room A - 50 seats, with AV system. Room B - 20 seats, no AV."
Output: 
{{
  "tasks": [
    {{"task_description": "Create Room A", "action": "create_venue", "details": {{"name": "Room A", "capacity": 50, "has_av_system": true}}}},
    {{"task_description": "Create Room B", "action": "create_venue", "details": {{"name": "Room B", "capacity": 20, "has_av_system": false}}}}
  ]
}}

**Document:**
---
{document}
---

Return ONLY the JSON with separate task objects for each entity. Include ALL mentioned properties in the details for each entity's creation task."""
        
        try:
            response_str = LLMClient.execute_request(
                prompt, model_name, is_json_format=True
            )
            
            # More robust JSON extraction
            # Try to find a complete JSON object starting with { and ending with }
            # Handle nested braces properly
            start_idx = response_str.find('{')
            if start_idx == -1:
                raise json.JSONDecodeError("No JSON object found in response", response_str, 0)
            
            # Count braces to find the complete JSON object
            brace_count = 0
            end_idx = start_idx
            for i in range(start_idx, len(response_str)):
                if response_str[i] == '{':
                    brace_count += 1
                elif response_str[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i + 1
                        break
            
            if brace_count != 0:
                # Fallback to simpler extraction if brace counting fails
                json_match = re.search(r'\{[^{}]*"tasks"[^{}]*:\s*\[[^\]]*\][^{}]*\}', response_str, re.DOTALL)
                if json_match:
                    clean_json_str = json_match.group(0)
                else:
                    raise json.JSONDecodeError("Could not extract valid JSON", response_str, 0)
            else:
                clean_json_str = response_str[start_idx:end_idx]
            
            # Parse the extracted JSON
            result = json.loads(clean_json_str)
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

        except json.JSONDecodeError as e:
            # Provide more detailed error info for debugging
            preview = response_str[:500] if len(response_str) > 500 else response_str
            return {
                "status": "error",
                "message": f"Failed to parse JSON: {str(e)}. Response preview: {preview}",
                "tasks": []
            }
        except ConnectionError as e:
            return {
                "status": "error",
                "message": f"LLM connection failed: {e}",
                "tasks": []
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Unexpected error: {e}",
                "tasks": []
            }