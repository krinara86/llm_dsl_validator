# src/core.py
import requests
import json
import re
import os
from typing import Dict, Any, Callable

from .framework.base_interpreter import execute_dsl
from .domains.tax.interpreter import BillInterpreter
from .domains.cycling.interpreter import RideInterpreter
from .domains.event.interpreter import EventInterpreter

# --- Configuration ---
class AppConfig:
    """Centralized configuration for the application."""
    LLM_API_URL = "http://localhost:11434/api/generate"
    DEFAULT_MODEL = "llama3:8b"
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    STATE_FILE = os.path.join(PROJECT_ROOT, "notebooks", "state.json")

    @staticmethod
    def get_grammar_path(grammar_file: str) -> str:
        """Constructs the full path to a grammar file."""
        return os.path.join(AppConfig.PROJECT_ROOT, grammar_file)

# --- State Management ---
def load_state() -> Dict[str, Any]:
    """Loads the conference state from a JSON file."""
    if os.path.exists(AppConfig.STATE_FILE):
        try:
            with open(AppConfig.STATE_FILE, 'r') as f:
                content = f.read()
                if not content: # Handle empty file case
                    return {"venues": {}, "sessions": [], "venue_bookings": {}}
                return json.loads(content)
        except json.JSONDecodeError:
             return {"venues": {}, "sessions": [], "venue_bookings": {}} # Handle malformed JSON
    # Return a default initial state if the file doesn't exist
    return {"venues": {}, "sessions": [], "venue_bookings": {}}

def save_state(state: Dict[str, Any]):
    """Saves the conference state to a JSON file."""
    with open(AppConfig.STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

# --- Core LLM Interaction ---
def _execute_llm_request(prompt: str, model_name: str, is_json_format: bool = False) -> str:
    """Handles the request to the local LLM API."""
    try:
        payload = {"model": model_name, "prompt": prompt, "stream": True}
        if is_json_format:
            payload["format"] = "json"

        api_response_stream = requests.post(AppConfig.LLM_API_URL, json=payload, stream=True)
        api_response_stream.raise_for_status()

        llm_raw_output = "".join(json.loads(chunk).get('response', '') for chunk in api_response_stream.iter_lines() if chunk)

        if not llm_raw_output.strip():
            raise ValueError("The LLM returned an empty response.")
        return llm_raw_output
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"API request failed: {e}") from e

def _process_dsl_request(
    user_query: str,
    prompt_template: str,
    grammar_file: str,
    interpreter_factory: Callable[[], Any],
    model_name: str,
    dsl_extractor: Callable[[str, str], str]
) -> Dict[str, Any]:
    """
    Generic processor for handling user requests that are converted to a DSL.
    """
    prompt = prompt_template.format(user_query=user_query)
    llm_dsl_code = None
    
    try:
        is_json_mode = "json" in prompt.lower()
        
        llm_raw_output = _execute_llm_request(prompt, model_name, is_json_mode)
        llm_dsl_code = dsl_extractor(llm_raw_output, user_query)

        if not llm_dsl_code:
            raise ValueError(f"Could not extract valid DSL code from the LLM's response. Full response: {llm_raw_output}")

        interpreter = interpreter_factory()
        dsl_result = execute_dsl(llm_dsl_code, AppConfig.get_grammar_path(grammar_file), interpreter)
        
        return {"status": "success", "llm_generated_dsl": llm_dsl_code, "interpreter_result": dsl_result}
    except Exception as e:
        error_response = {"status": "error", "message": str(e)}
        if llm_dsl_code:
            error_response["llm_generated_dsl"] = llm_dsl_code
        return error_response

# --- DSL Extraction and Assembly ---

def _normalize_string(value: str) -> str:
    """Removes leading/trailing whitespace and surrounding quotes."""
    return str(value).strip().strip("'\"")

def extract_dsl_from_string(text: str, start_word: str, user_query: str = None) -> str:
    """Extracts a DSL code block from a string based on a starting keyword."""
    pattern = rf'{start_word}\s*(".*?"|\{{[^}}]*\}})'
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        pattern = rf'{start_word}\s+.*?\s*\{{[^}}]*\}}'
        match = re.search(pattern, text, re.DOTALL)
    return match.group(0) if match else None

def assemble_event_dsl_from_json(json_string: str, user_query: str) -> str:
    """Assembles the event planning DSL from a JSON string and validates that actions exist."""
    try:
        data = json.loads(json_string)
    except json.JSONDecodeError:
        raise ValueError(f"LLM returned invalid JSON: {json_string}")

    action_keys = ["create_venues", "modify_venues", "schedule_sessions"]
    has_actions = any(key in data and data[key] for key in action_keys)
    if not has_actions:
         raise ValueError("The LLM could not identify any valid actions from your request. This can happen with ambiguous queries or if the requested action conflicts with the selected role. Please try rephrasing your query or running it again.")

    dsl = []
    role = data.get("role")
    if not role:
        if "create" in user_query.lower() or "modify" in user_query.lower() or "add" in user_query.lower():
            role = "admin"
        else:
            role = "scheduler"
            
    dsl.append(f'role "{role}" {{')

    for venue in data.get("create_venues", []):
        name = _normalize_string(venue.get("name", "N/A"))
        dsl.append(f'  create_venue "{name}" {{')
        if venue.get("capacity") is not None:
            dsl.append(f'    capacity: {venue["capacity"]}')
        if venue.get("has_av_system") is not None:
            dsl.append(f'    has_av_system: {str(venue["has_av_system"]).lower()}')
        dsl.append('  }')

    for venue in data.get("modify_venues", []):
        name = _normalize_string(venue.get("name", "N/A"))
        dsl.append(f'  modify_venue "{name}" {{')
        if venue.get("capacity") is not None:
            dsl.append(f'    capacity: {venue["capacity"]}')
        if venue.get("has_av_system") is not None:
            dsl.append(f'    has_av_system: {str(venue["has_av_system"]).lower()}')
        dsl.append('  }')

    for session in data.get("schedule_sessions", []):
        name = _normalize_string(session.get("name", "N/A"))
        dsl.append(f'  schedule_session "{name}" {{')
        if session.get("hosted_by"):
            hosted_by = _normalize_string(session["hosted_by"])
            dsl.append(f'    hosted_by: "{hosted_by}"')
        if session.get("in_venue"):
            in_venue = _normalize_string(session["in_venue"])
            dsl.append(f'    in_venue: "{in_venue}"')
        if session.get("expected_attendees") is not None:
            dsl.append(f'    expected_attendees: {session["expected_attendees"]}')
        if session.get("requires_av") is not None:
            dsl.append(f'    requires_av: {str(session["requires_av"]).lower()}')
        dsl.append('  }')
        
    dsl.append('}')
    return "\n".join(dsl)

def process_event_plan_request(user_query: str, role: str, model_name: str = AppConfig.DEFAULT_MODEL) -> Dict[str, Any]:
    """Processes a user request to manage an event plan by generating JSON and then a DSL."""
    prompt = f"""You are an assistant that translates natural language into a structured JSON command for an event management system.

The user has the role: "{role}".

Possible actions are:
1. "create_venues": For adding new venues. Admins only.
2. "modify_venues": For changing existing venues. Admins only.
3. "schedule_sessions": For booking sessions in venues. Schedulers and Admins.

A venue has a `name` (string), `capacity` (number), and `has_av_system` (boolean).
A session has a `name` (string), `hosted_by` (string), `in_venue` (string), `expected_attendees` (number), and `requires_av` (boolean).

From the user's request, identify the actions and extract the entities into a single JSON object. The top-level keys must be one or more of "create_venues", "modify_venues", or "schedule_sessions".
Do not include keys in the JSON if the information is not present in the user's request. For example, if the user doesn't mention attendees, do not include the 'expected_attendees' key.
Include the user's role in the JSON output as a top-level key "role".

User Request: "{{user_query}}"
JSON Response:"""
    
    state = load_state()
    interpreter_factory = lambda: EventInterpreter(state, role)

    result = _process_dsl_request(
        user_query,
        prompt,
        'src/domains/event/grammar.dsl',
        interpreter_factory,
        model_name,
        dsl_extractor=assemble_event_dsl_from_json
    )

    if result["status"] == "success":
        new_state = result['interpreter_result']['new_state']
        save_state(new_state)

    return result

def process_order_request(user_query: str, model_name: str = AppConfig.DEFAULT_MODEL) -> Dict[str, Any]:
    """Processes a user request to create a bill by generating a DSL."""
    prompt = """You are an assistant that translates natural language into a DSL for a bill...
Translate the user order into this DSL.
User Order: "{user_query}"
DSL Response:"""
    return _process_dsl_request(
        user_query,
        prompt,
        'src/domains/tax/grammar.dsl',
        lambda: BillInterpreter(),
        model_name,
        dsl_extractor=lambda text, q: extract_dsl_from_string(text, "bill")
    )

def process_ride_plan_request(user_query: str, model_name: str = AppConfig.DEFAULT_MODEL) -> Dict[str, Any]:
    """Processes a user request for a bike ride by generating a DSL."""
    prompt = """You are an assistant that translates natural language into a DSL for a bike ride...
Translate the user request into this DSL.
User Request: "{user_query}"
DSL Response:"""
    return _process_dsl_request(
        user_query,
        prompt,
        'src/domains/cycling/grammar.dsl',
        lambda: RideInterpreter(),
        model_name,
        dsl_extractor=lambda text, q: extract_dsl_from_string(text, "ride")
    )