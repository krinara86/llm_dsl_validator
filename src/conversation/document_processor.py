# src/conversation/document_processor.py
import json
from typing import Dict, List
from ..core.llm_client import LLMClient

class DocumentProcessor:
    """Processes documents containing multiple tasks."""

    def extract_tasks(self, document: str, model_name: str) -> Dict:
        """Extract multiple tasks from a document into structured objects."""

        prompt = f"""
You are an expert event management assistant. Your task is to analyze the document below and extract all distinct event management tasks into a structured JSON format.

**Instructions:**
1.  Read the entire document carefully.
2.  Identify every distinct action requested. The "action" MUST be one of: `create_venue`, `modify_venue`, `schedule_session`.
3.  **CRITICAL RULE: If a single sentence or paragraph asks to create or schedule multiple items (e.g., 'Set up Room A and Room B'), you MUST treat each item as a completely separate task. Generate one JSON object for Room A and a second, distinct JSON object for Room B.**
4.  For each individual task, create a JSON object.
5.  Inside each object, include:
    - "task_description": A concise summary of the user's request for that task (e.g., "Create a venue for Room A").
    - "action": The specific action identified (e.g., "create_venue").
    - "details": An object containing any parameters you can extract for that task from the text. Use the parameter names ONLY: `name`, `capacity`, `has_av_system`, `in_venue`, `expected_attendees`, `requires_av`, `hosted_by`.
6.  If a parameter value is not mentioned for a task, do not include its key in the "details" object.
7.  Return a single JSON object with a "tasks" key, which holds an array of these structured task objects.

**Document:**
---
{document}
---

**JSON Output Format:**
{{
  "tasks": [
    {{
      "task_description": "A summary of the first task",
      "action": "create_venue",
      "details": {{
        "name": "Value from document",
        "capacity": 100
      }}
    }}
  ]
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