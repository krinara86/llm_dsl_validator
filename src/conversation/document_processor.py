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
3. Identify actions from this list: {action_str}
4. For EACH individual task, create a separate JSON object with:
   - "task_description": Brief summary of just that one task
   - "action": The specific action from the list above
   - "details": Parameters for that ONE entity only (as a flat object, not arrays)
5. NEVER combine multiple entities into arrays - each needs its own task object
6. Watch for phrases like "First", "Second", "Third", "Another", "Also", numbered lists, bullet points - these indicate separate tasks

{param_guidance}

**Generic Example**: 
Input: "Create entity A with property X. Create entity B with property Y."
Output: 
{{
  "tasks": [
    {{"task_description": "Create entity A", "action": "create_something", "details": {{"name": "A", "property": "X"}}}},
    {{"task_description": "Create entity B", "action": "create_something", "details": {{"name": "B", "property": "Y"}}}}
  ]
}}

**Document:**
---
{document}
---

Return ONLY the JSON with separate task objects for each entity. Each task must have action, task_description, and details fields."""
        
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