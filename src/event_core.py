# src/event_core.py
import requests
import json
import re
import os
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

# --- SETUP AND CONFIGURATION ---

def load_api_key_manually():
    try:
        project_root = Path(__file__).parent.parent
        dotenv_path = project_root / '.env'
        if not dotenv_path.exists(): return
        with open(dotenv_path) as f:
            for line in f:
                if line.strip() and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    value = value.strip("'\"")
                    os.environ[key] = value
    except Exception:
        pass

load_api_key_manually()

from .framework.base_interpreter import execute_dsl
from .domains.event.interpreter import EventInterpreter

class AppConfig:
    LLM_API_URL = "http://localhost:11434/api/generate"
    DEFAULT_MODEL = "llama3:8b"
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    STATE_FILE = os.path.join(PROJECT_ROOT, "notebooks", "state.json")
    @staticmethod
    def get_grammar_path(grammar_file: str) -> str:
        return os.path.join(AppConfig.PROJECT_ROOT, grammar_file)

# --- STATE MANAGEMENT ---

def load_state() -> Dict[str, Any]:
    if not os.path.exists(AppConfig.STATE_FILE): 
        return {"venues": {}, "sessions": [], "venue_bookings": {}}
    try:
        with open(AppConfig.STATE_FILE, 'r') as f:
            content = f.read()
            if not content: 
                return {"venues": {}, "sessions": [], "venue_bookings": {}}
            return json.loads(content)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"venues": {}, "sessions": [], "venue_bookings": {}}

def save_state(state: Dict[str, Any]):
    with open(AppConfig.STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

# --- LLM COMMUNICATION ---

def _execute_llm_request(prompt: str, model_name: str, is_json_format: bool = False) -> str:
    if model_name.startswith("togetherai/"):
        api_key = os.getenv("TOGETHER_API_KEY")
        if not api_key: 
            raise ValueError("TOGETHER_API_KEY not found. Please check your .env file.")
        together_model_name = model_name.split("/", 1)[1]
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": together_model_name, "messages": [{"role": "user", "content": prompt}]}
        if is_json_format: 
            payload["response_format"] = {"type": "json_object"}
        try:
            response = requests.post("https://api.together.xyz/v1/chat/completions", 
                                    headers=headers, json=payload, timeout=90)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Together AI API request failed: {e}")
    else:
        try:
            payload = {"model": model_name, "prompt": prompt, "stream": False}
            if is_json_format: 
                payload["format"] = "json"
            response = requests.post(AppConfig.LLM_API_URL, json=payload, timeout=90)
            response.raise_for_status()
            return response.json().get('response', '')
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Ollama API request failed: {e}")

# --- SCHEMA DEFINITION ---

SCHEMA = {
    "create_venue": {
        "required": ["name", "capacity", "has_av_system"],
        "optional": [],
        "param_types": {
            "name": "text",
            "capacity": "number",
            "has_av_system": "boolean"
        }
    },
    "modify_venue": {
        "required": ["name"],
        "optional": ["capacity", "has_av_system"],
        "param_types": {
            "name": "text",
            "capacity": "number",
            "has_av_system": "boolean"
        }
    },
    "schedule_session": {
        "required": ["name", "in_venue", "expected_attendees", "requires_av"],
        "optional": ["hosted_by"],
        "param_types": {
            "name": "text",
            "in_venue": "venue_selection",
            "expected_attendees": "number",
            "requires_av": "boolean",
            "hosted_by": "text"
        }
    }
}

# --- DSL ASSEMBLY ---

def _normalize_string(value: str) -> str:
    return str(value).strip().strip("'\"")

def assemble_event_dsl_from_json(task_details: Dict, role: str) -> str:
    action = task_details.get("action")
    params = task_details.get("parameters", {})
    dsl = [f'role "{role}" {{']

    if action == "create_venue":
        dsl.append(f'  create_venue "{_normalize_string(params.get("name", "N/A"))}" {{')
        if "capacity" in params: 
            dsl.append(f'    capacity: {params["capacity"]}')
        if "has_av_system" in params: 
            dsl.append(f'    has_av_system: {str(params["has_av_system"]).lower()}')
        dsl.append('  }')
    elif action == "modify_venue":
        dsl.append(f'  modify_venue "{_normalize_string(params.get("name", "N/A"))}" {{')
        if "capacity" in params: 
            dsl.append(f'    capacity: {params["capacity"]}')
        if "has_av_system" in params: 
            dsl.append(f'    has_av_system: {str(params["has_av_system"]).lower()}')
        dsl.append('  }')
    elif action == "schedule_session":
        dsl.append(f'  schedule_session "{_normalize_string(params.get("name", "N/A"))}" {{')
        if "hosted_by" in params: 
            dsl.append(f'    hosted_by: "{_normalize_string(params["hosted_by"])}"')
        if "in_venue" in params: 
            dsl.append(f'    in_venue: "{_normalize_string(params["in_venue"])}"')
        if "expected_attendees" in params: 
            dsl.append(f'    expected_attendees: {params["expected_attendees"]}')
        if "requires_av" in params: 
            dsl.append(f'    requires_av: {str(params["requires_av"]).lower()}')
        dsl.append('  }')
    dsl.append('}')
    return "\n".join(dsl)

# --- EXTRACTION AND PARSING ---

def extract_task_details(query: str, model_name: str) -> Dict:
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
        response_str = _execute_llm_request(prompt, model_name, is_json_format=True)
        return json.loads(response_str)
    except (json.JSONDecodeError, ConnectionError) as e:
        return {"action": "error", "parameters": {"details": str(e)}}

def parse_boolean(value: str) -> bool:
    return str(value).strip().lower() in ['true', 'yes', 'y', '1']

def parse_number(value: str) -> Optional[int]:
    match = re.search(r'\d+', str(value))
    return int(match.group()) if match else None

# --- FORMATTED RESPONSE GENERATION ---

def format_understanding(task_details: Dict, role: str) -> Dict:
    """Format the extracted task details into a structured response."""
    action = task_details.get("action", "unknown")
    params = task_details.get("parameters", {})
    
    if action not in SCHEMA:
        return {
            "formatted_html": "<b>Error:</b> Unable to understand the request.",
            "missing_params": [],
            "available_params": {}
        }
    
    schema = SCHEMA[action]
    required = schema["required"]
    optional = schema.get("optional", [])
    param_types = schema.get("param_types", {})
    
    # Categorize parameters
    available_params = {}
    missing_params = []
    
    for param in required:
        if param in params and params[param] not in [None, ""]:
            available_params[param] = params[param]
        else:
            missing_params.append(param)
    
    for param in optional:
        if param in params and params[param] not in [None, ""]:
            available_params[param] = params[param]
    
    # Build HTML response
    html = f"""
    <div style='background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin: 10px 0;'>
        <h4 style='margin-top: 0;'>Here is what I understood:</h4>
        <p><b>Role:</b> {role}</p>
        <p><b>Action:</b> {action.replace('_', ' ').title()}</p>
        
        <div style='margin: 10px 0;'>
            <b>Available Input:</b>
            <ul style='margin: 5px 0;'>
    """
    
    if available_params:
        for key, value in available_params.items():
            display_key = key.replace('_', ' ').title()
            html += f"<li>{display_key}: <code>{value}</code></li>"
    else:
        html += "<li><i>None provided yet</i></li>"
    
    html += "</ul></div>"
    
    if missing_params:
        html += """
        <div style='margin: 10px 0;'>
            <b>Missing Input:</b>
            <ul style='margin: 5px 0;'>
        """
        for param in missing_params:
            display_param = param.replace('_', ' ').title()
            param_type = param_types.get(param, "text")
            
            # Add guidance based on parameter type
            if param_type == "boolean":
                guidance = "(Please answer: yes/no)"
            elif param_type == "number":
                guidance = "(Please provide a number)"
            elif param_type == "venue_selection":
                guidance = "(I'll show you available options)"
            else:
                guidance = "(Please provide the text)"
            
            html += f"<li>{display_param} {guidance}</li>"
        
        html += "</ul></div>"
    
    html += "</div>"
    
    return {
        "formatted_html": html,
        "missing_params": missing_params,
        "available_params": available_params
    }

def generate_clarification_message(missing_params: List[str], task_details: Dict, 
                                  role: str, model_name: str) -> str:
    """Generate a helpful clarification message for missing parameters."""
    state = load_state()
    messages = []
    
    for param in missing_params:
        param_type = SCHEMA.get(task_details.get("action", ""), {}).get("param_types", {}).get(param, "text")
        
        if param == "in_venue":
            # Special handling for venue selection
            attendees_req = task_details.get("parameters", {}).get("expected_attendees", 0)
            av_req = task_details.get("parameters", {}).get("requires_av", False)
            
            suitable_venues = []
            for name, props in state.get("venues", {}).items():
                if name not in state.get("venue_bookings", {}):
                    capacity = props.get("capacity", 0)
                    has_av = props.get("has_av_system", False)
                    if capacity >= attendees_req and (not av_req or has_av):
                        suitable_venues.append((name, capacity, has_av))
            
            if suitable_venues:
                msg = "<b>Please select a venue from the available options:</b><br>"
                msg += "<ul style='margin: 5px 0;'>"
                for venue_name, capacity, has_av in suitable_venues:
                    av_text = "Has A/V" if has_av else "No A/V"
                    msg += f"<li><b>{venue_name}</b> (Capacity: {capacity}, {av_text})</li>"
                msg += "</ul>"
                msg += "<i>Type the exact name of your chosen venue.</i>"
            else:
                msg = "<b>No venues currently meet your requirements.</b><br>"
                msg += "Please create a suitable venue first or adjust your requirements."
            messages.append(msg)
            
        elif param == "name":
            messages.append("<b>Please provide the name:</b><br><i>Type the exact name you want to use.</i>")
            
        elif param == "capacity" or param == "expected_attendees":
            messages.append(f"<b>Please provide the {param.replace('_', ' ')}:</b><br><i>Enter a number (e.g., 50)</i>")
            
        elif param == "has_av_system" or param == "requires_av":
            messages.append(f"<b>Does it {param.replace('_', ' ').replace('has', 'have').replace('requires', 'require')}?</b><br><i>Answer: yes or no</i>")
            
        elif param == "hosted_by":
            messages.append("<b>Who is hosting this session?</b><br><i>Enter the host's name</i>")
    
    return "<br><br>".join(messages)

# --- MAIN ORCHESTRATION ---

def orchestrate_request(query: str, role: str, model_name: str, 
                        conversation_state: Dict = None) -> Dict:
    """Main orchestration function with improved structure."""
    
    if not conversation_state:
        conversation_state = {
            "status": "awaiting_query",
            "task_details": {},
            "history": [],
            "missing_params": []
        }
    
    conversation_state["history"].append({"role": "user", "content": query})
    
    # Handle clarification responses
    if conversation_state.get("status") == "awaiting_clarification":
        missing_params = conversation_state.get("missing_params", [])
        if missing_params:
            current_param = missing_params[0]
            task_details = conversation_state.get("task_details", {})
            action = task_details.get("action")
            param_type = SCHEMA.get(action, {}).get("param_types", {}).get(current_param, "text")
            
            # Parse the response based on parameter type
            if param_type == "boolean":
                value = parse_boolean(query)
            elif param_type == "number":
                value = parse_number(query)
            elif param_type == "venue_selection":
                # Check if the query contains a valid venue name
                state = load_state()
                value = None
                for venue_name in state.get("venues", {}).keys():
                    if venue_name.lower() in query.lower():
                        value = venue_name
                        break
                if not value:
                    value = query.strip()
            else:
                value = query.strip()
            
            # Update task details
            if "parameters" not in task_details:
                task_details["parameters"] = {}
            task_details["parameters"][current_param] = value
            conversation_state["task_details"] = task_details
    else:
        # New request - extract task details
        extracted_info = extract_task_details(query, model_name)
        if extracted_info.get("action") in [None, "unknown", "error"]:
            return {
                "status": "error",
                "message": "I couldn't understand your request. Please try rephrasing.",
                "new_state": {}
            }
        conversation_state["task_details"] = extracted_info
        conversation_state["status"] = "processing"
    
    # Format understanding and check for missing parameters
    understanding = format_understanding(conversation_state["task_details"], role)
    
    if understanding["missing_params"]:
        # Still have missing parameters
        conversation_state["status"] = "awaiting_clarification"
        conversation_state["missing_params"] = understanding["missing_params"]
        
        clarification_msg = generate_clarification_message(
            [understanding["missing_params"][0]],  # Ask for one param at a time
            conversation_state["task_details"],
            role,
            model_name
        )
        
        return {
            "status": "clarification_needed",
            "understanding_html": understanding["formatted_html"],
            "message": clarification_msg,
            "new_state": conversation_state
        }
    
    # All parameters collected - ready for confirmation
    conversation_state["status"] = "awaiting_confirmation"
    conversation_state["missing_params"] = []
    
    confirmation_msg = """
    <div style='background-color: #d4edda; padding: 10px; border-radius: 5px; margin: 10px 0;'>
        <b>Ready to execute!</b><br>
        Please review the details above and confirm if you want to proceed.
    </div>
    """
    
    return {
        "status": "confirmation_needed",
        "understanding_html": understanding["formatted_html"],
        "message": confirmation_msg,
        "new_state": conversation_state
    }

def execute_confirmed_task(role: str, conversation_state: Dict) -> Dict:
    """Execute the confirmed task and return results with DSL."""
    dsl_code = ""
    try:
        dsl_code = assemble_event_dsl_from_json(
            conversation_state["task_details"], 
            role
        )
        state = load_state()
        interpreter = EventInterpreter(state, role)
        dsl_result = execute_dsl(
            dsl_code, 
            AppConfig.get_grammar_path('src/domains/event/grammar.dsl'), 
            interpreter
        )
        save_state(dsl_result['new_state'])
        
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
    except (ValueError, ConnectionError) as e:
        return {
            "status": "error",
            "message": f"❌ Error: {e}",
            "dsl_code": dsl_code
        }

def process_long_document(full_text: str, role: str, model_name: str) -> Dict:
    """Process documents that may contain multiple tasks."""
    
    prompt = f"""
You are a task extraction assistant. Extract ALL distinct event management tasks from the following text.
Each task should be a separate action that can be performed.

Return a JSON object with a "tasks" array, where each task is a string describing one action.
Focus on concrete actions like creating venues, modifying venues, or scheduling sessions.

Text: "{full_text}"

Return format:
{{
  "tasks": ["task 1 description", "task 2 description", ...]
}}
"""
    
    try:
        response_str = _execute_llm_request(prompt, model_name, is_json_format=True)
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