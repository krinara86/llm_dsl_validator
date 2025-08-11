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

    @staticmethod
    def get_grammar_path(grammar_file: str) -> str:
        """Constructs the full path to a grammar file."""
        return os.path.join(AppConfig.PROJECT_ROOT, grammar_file)

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
    interpreter_class: Any,
    model_name: str,
    dsl_extractor: Callable[[str], str]
) -> Dict[str, Any]:
    """
    Generic processor for handling user requests that are converted to a DSL.
    It can extract DSL from a raw string or assemble it from JSON.
    """
    prompt = prompt_template.format(user_query=user_query)
    llm_dsl_code = None
    
    try:
        is_json_mode = "json" in prompt.lower() # Heuristic to detect if JSON output is expected
        
        llm_raw_output = _execute_llm_request(prompt, model_name, is_json_mode)
        llm_dsl_code = dsl_extractor(llm_raw_output)

        if not llm_dsl_code:
            raise ValueError(f"Could not extract valid DSL code from the LLM's response. Full response: {llm_raw_output}")

        dsl_result = execute_dsl(llm_dsl_code, AppConfig.get_grammar_path(grammar_file), interpreter_class)
        return {"status": "success", "llm_generated_dsl": llm_dsl_code, "interpreter_result": dsl_result}
    except Exception as e:
        error_response = {"status": "error", "message": str(e)}
        if llm_dsl_code:
            error_response["llm_generated_dsl"] = llm_dsl_code
        return error_response

# --- DSL Extraction and Assembly ---
def extract_dsl_from_string(text: str, start_word: str) -> str:
    """Extracts a DSL code block from a string based on a starting keyword."""
    pattern = rf'{start_word}\s*(".*?"|\{{[^}}]*\}})'
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        pattern = rf'{start_word}\s+.*?\s*\{{[^}}]*\}}'
        match = re.search(pattern, text, re.DOTALL)
    return match.group(0) if match else None

def assemble_event_dsl_from_json(json_string: str) -> str:
    """Assembles the event planning DSL from a JSON string."""
    data = json.loads(json_string)
    dsl = []
    plan_name = data.get("plan_name", "Unnamed Plan")
    dsl.append(f'conference_plan "{plan_name}" {{')
    
    for venue in data.get("venues", []):
        dsl.append(f'  venue "{venue.get("name", "N/A")}" {{')
        dsl.append(f'    capacity: {venue.get("capacity", 0)}')
        dsl.append(f'    has_av_system: {str(venue.get("has_av_system", False)).lower()}')
        dsl.append('  }')

    for speaker in data.get("speakers", []):
        dsl.append(f'  speaker "{speaker.get("name", "N/A")}"')

    for session in data.get("sessions", []):
        dsl.append(f'  session "{session.get("name", "N/A")}" {{')
        if "hosted_by" in session: dsl.append(f'    hosted_by: "{session["hosted_by"]}"')
        if "in_venue" in session: dsl.append(f'    in_venue: "{session["in_venue"]}"')
        if "expected_attendees" in session: dsl.append(f'    expected_attendees: {session["expected_attendees"]}')
        if "requires_av" in session: dsl.append(f'    requires_av: {str(session["requires_av"]).lower()}')
        dsl.append('  }')
        
    dsl.append('}')
    return "\n".join(dsl)

# --- Public API ---
def process_event_plan_request(user_query: str, model_name: str = AppConfig.DEFAULT_MODEL) -> Dict[str, Any]:
    """Processes a user request to create an event plan by generating JSON and then a DSL."""
    prompt = """From the user's request, extract entities for a conference plan.
The possible entities are: plan_name, venues, speakers, and sessions.
- A venue has a `name`, `capacity` (number), and `has_av_system` (boolean).
- A session has a `name`, `hosted_by` (string), `in_venue` (string), `expected_attendees` (number), and `requires_av` (boolean).
Return a single JSON object.

User Request: "{user_query}"
JSON Response:"""
    return _process_dsl_request(
        user_query,
        prompt,
        'src/domains/event/grammar.dsl',
        EventInterpreter,
        model_name,
        dsl_extractor=assemble_event_dsl_from_json
    )

def process_order_request(user_query: str, model_name: str = AppConfig.DEFAULT_MODEL) -> Dict[str, Any]:
    """Processes a user request to create a bill by generating a DSL."""
    prompt = """You are an assistant that translates natural language into a DSL for a bill.
The DSL format is:
bill {{
  itemName: quantity * pricePerItem
}}
Translate the user order into this DSL.
User Order: "{user_query}"
DSL Response:"""
    return _process_dsl_request(
        user_query,
        prompt,
        'src/domains/tax/grammar.dsl',
        BillInterpreter,
        model_name,
        dsl_extractor=lambda text: extract_dsl_from_string(text, "bill")
    )

def process_ride_plan_request(user_query: str, model_name: str = AppConfig.DEFAULT_MODEL) -> Dict[str, Any]:
    """Processes a user request for a bike ride by generating a DSL."""
    prompt = """You are an assistant that translates natural language into a DSL for a bike ride.
The DSL format is:
ride {{
  terrain: flat | hilly | mountainous
  distance_km: number
}}
Translate the user request into this DSL.
User Request: "{user_query}"
DSL Response:"""
    return _process_dsl_request(
        user_query,
        prompt,
        'src/domains/cycling/grammar.dsl',
        RideInterpreter,
        model_name,
        dsl_extractor=lambda text: extract_dsl_from_string(text, "ride")
    )