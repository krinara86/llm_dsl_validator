# src/event_core.py
import requests
import json
import re
import os
from typing import Dict, Any, List

from .framework.base_interpreter import execute_dsl
from .domains.event.interpreter import EventInterpreter

# --- Configuration & State Management ---
class AppConfig:
    LLM_API_URL = "http://localhost:11434/api/generate"
    DEFAULT_MODEL = "llama3:8b"
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    STATE_FILE = os.path.join(PROJECT_ROOT, "notebooks", "state.json")
    @staticmethod
    def get_grammar_path(grammar_file: str) -> str:
        return os.path.join(AppConfig.PROJECT_ROOT, grammar_file)

def load_state() -> Dict[str, Any]:
    if not os.path.exists(AppConfig.STATE_FILE): return {"venues": {}, "sessions": [], "venue_bookings": {}}
    try:
        with open(AppConfig.STATE_FILE, 'r') as f:
            content = f.read()
            if not content: return {"venues": {}, "sessions": [], "venue_bookings": {}}
            return json.loads(content)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"venues": {}, "sessions": [], "venue_bookings": {}}

def save_state(state: Dict[str, Any]):
    with open(AppConfig.STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

# --- Core Logic ---
def _execute_llm_request(prompt: str, model_name: str, is_json_format: bool = False) -> str:
    """LLM request handler with a timeout to prevent freezing."""
    try:
        payload = {"model": model_name, "prompt": prompt, "stream": False}
        if is_json_format: payload["format"] = "json"
        response = requests.post(AppConfig.LLM_API_URL, json=payload, timeout=90)
        response.raise_for_status()
        return response.json().get('response', '')
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"API request failed: {e}")

def _normalize_string(value: str) -> str:
    return str(value).strip().strip("'\"")

def assemble_event_dsl_from_json(json_string: str, role: str) -> str:
    try:
        data = json.loads(json_string)
    except json.JSONDecodeError:
        raise ValueError("The LLM returned invalid JSON.")
    if not any(key in data and data[key] for key in ["create_venues", "schedule_sessions"]):
        raise ValueError("The LLM could not identify a valid action in your request.")
    dsl = [f'role "{role}" {{']
    for venue in data.get("create_venues", []):
        dsl.append(f'  create_venue "{_normalize_string(venue.get("name", "N/A"))}" {{')
        if "capacity" in venue: dsl.append(f'    capacity: {venue["capacity"]}')
        if "has_av_system" in venue: dsl.append(f'    has_av_system: {str(venue["has_av_system"]).lower()}')
        dsl.append('  }')
    for session in data.get("schedule_sessions", []):
        dsl.append(f'  schedule_session "{_normalize_string(session.get("name", "N/A"))}" {{')
        if "hosted_by" in session: dsl.append(f'    hosted_by: "{_normalize_string(session["hosted_by"])}"')
        if "in_venue" in session: dsl.append(f'    in_venue: "{_normalize_string(session["in_venue"])}"')
        if "expected_attendees" in session: dsl.append(f'    expected_attendees: {session["expected_attendees"]}')
        if "requires_av" in session: dsl.append(f'    requires_av: {str(session["requires_av"]).lower()}')
        dsl.append('  }')
    dsl.append('}')
    return "\n".join(dsl)

def generate_clarification_prompt_for_missing_venue(user_query: str, state: dict) -> str:
    context = ""
    attendees_match = re.search(r"(\d+)\s*(people|seats|attendees)", user_query, re.IGNORECASE)
    attendees_req = int(attendees_match.group(1)) if attendees_match else 0
    av_req = "av" in user_query.lower() or "audio visual" in user_query.lower()

    suggestions = []
    for name, props in state.get("venues", {}).items():
        if name not in state.get("venue_bookings", {}) and props.get("capacity", 0) >= attendees_req:
            if av_req and not props.get("has_av_system", False): continue
            suggestions.append(f"- '{name}' (Capacity: {int(props.get('capacity',0))}, Has A/V: {props.get('has_av_system')})")
    
    if suggestions:
        context = "Based on your request, here are some available venues that might work:\n" + "\n".join(suggestions)
    else:
        context = "Unfortunately, no currently available venues meet the requirements."

    return f"""You are an event planning assistant. Your goal is to respond to a user who tried to schedule an event without a venue.
Your task:
1. Briefly explain that a venue is required.
2. Present the suggested venues from the context below.
3. Ask the user which venue they would like to book.
**IMPORTANT:** Respond ONLY with the direct message to the user. Do NOT include your own reasoning or any text that is not part of the final user-facing message.
Context with suggestions:
{context}
Your response to the user:
"""

def process_event_request_simple(conversation_history: List[Dict], role: str, model_name: str) -> Dict:
    state = load_state()
    latest_user_query = conversation_history[-1]['content']
    
    # This logic combines the conversation history to form a complete request
    query_to_process = latest_user_query
    if len(conversation_history) > 2:
        last_assistant_message = conversation_history[-2]['content'].lower()
        # Checks if the assistant's last message was a question asking to choose a venue
        if "which one would you like" in last_assistant_message or "which venue" in last_assistant_message:
            # If so, combine the user's original request with their new answer
            original_user_request = conversation_history[-3]['content']
            query_to_process = f"{original_user_request} Please schedule it in the '{latest_user_query}'."

    # Proactive check for missing venue
    is_scheduling_request = any(keyword in query_to_process.lower() for keyword in ["schedule", "book", "session", "talk"])
    if is_scheduling_request:
        venues = state.get("venues", {})
        is_venue_mentioned = any(venue.lower() in query_to_process.lower() for venue in venues)
        if not is_venue_mentioned:
            clarification_prompt = generate_clarification_prompt_for_missing_venue(query_to_process, state)
            final_message = _execute_llm_request(clarification_prompt, model_name)
            return {"status": "clarification_needed", "message": final_message}

    # Standard logic now uses the combined query, which is much easier for the LLM
    prompt_template = f"""You are a system that translates a user's request into a single, structured JSON command.
Create a JSON command for the following request. The JSON should only have one of these top-level keys: "create_venues" or "schedule_sessions".

User Request: "{query_to_process}"

JSON Response:"""

    try:
        llm_json_output = _execute_llm_request(prompt_template, model_name, is_json_format=True)
        llm_dsl_code = assemble_event_dsl_from_json(llm_json_output, role)
        interpreter = EventInterpreter(state, role)
        dsl_result = execute_dsl(llm_dsl_code, AppConfig.get_grammar_path('src/domains/event/grammar.dsl'), interpreter)
        save_state(dsl_result['new_state'])
        return {"status": "success", "message": dsl_result['message']}

    except (ValueError, ConnectionError) as e:
        return {"status": "error", "message": f"🔴 Validation Error: {e}"}