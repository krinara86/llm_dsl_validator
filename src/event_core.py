# src/event_core.py
import requests
import json
import re
import os
from typing import Dict, Any, List

# NEW: Import the dotenv library
from dotenv import load_dotenv

from .framework.base_interpreter import execute_dsl
from .domains.event.interpreter import EventInterpreter

# NEW: Load variables from the .env file into the environment
load_dotenv()

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
    """
    Handles LLM requests for BOTH local Ollama and remote Together AI models.
    """
    if model_name.startswith("togetherai/"):
        # The os.getenv call now reads the key loaded from the .env file
        api_key = os.getenv("TOGETHER_API_KEY")
        if not api_key:
            raise ValueError("TOGETHER_API_KEY not found. Please create a .env file with your key.")
        
        together_model_name = model_name.split("/", 1)[1]
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": together_model_name,
            "messages": [{"role": "user", "content": prompt}],
        }
        if is_json_format:
            payload["response_format"] = {"type": "json_object"}
            
        try:
            response = requests.post("https://api.together.xyz/v1/chat/completions", headers=headers, json=payload, timeout=90)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Together AI API request failed: {e}")

    else: # Fallback to existing Ollama logic
        try:
            payload = {"model": model_name, "prompt": prompt, "stream": False}
            if is_json_format: payload["format"] = "json"
            response = requests.post(AppConfig.LLM_API_URL, json=payload, timeout=90)
            response.raise_for_status()
            return response.json().get('response', '')
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Ollama API request failed: {e}")

# --- The rest of the file remains the same ---
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
    if suggestions: context = "Based on the request, here are some available venues that might work:\n" + "\n".join(suggestions)
    else: context = "Unfortunately, no currently available venues meet the requirements."
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
    if len(conversation_history) <= 2:
        is_scheduling_request = any(keyword in latest_user_query.lower() for keyword in ["schedule", "book", "session", "talk"])
        venues = state.get("venues", {})
        is_venue_mentioned = any(venue.lower() in latest_user_query.lower() for venue in venues)
        if is_scheduling_request and not is_venue_mentioned:
            clarification_prompt = generate_clarification_prompt_for_missing_venue(latest_user_query, state)
            final_message = _execute_llm_request(clarification_prompt, model_name)
            return {"status": "clarification_needed", "message": final_message}
    history_str = ""
    for turn in conversation_history:
        speaker = "User" if turn['role'] == 'user' else 'Assistant'
        history_str += f"{speaker}: {turn['content']}\n"
    prompt_template = f"""You are a system that translates a user's request into a single, structured JSON command. Analyze the user's LATEST message in the context of the ENTIRE conversation history to gather all necessary details. If the latest message is a response to your question, you MUST combine the information from the history to form a complete command.
---
[EXAMPLE]
CONVERSATION HISTORY:
Assistant: Hello! I'm ready to help you plan your event.
User: I need to schedule a talk on 'Advanced AI' for 150 people. It needs AV.
Assistant: I can help with that. To proceed, we'll need to know which venue you'd like to book.
User: Let's use the Lecture Hall.
JSON FOR LATEST MESSAGE ("Let's use the Lecture Hall."):
{{
  "schedule_sessions": [
    {{
      "name": "Advanced AI",
      "expected_attendees": 150,
      "requires_av": true,
      "in_venue": "Lecture Hall"
    }}
  ]
}}
---
[CURRENT TASK]
CONVERSATION HISTORY:
{history_str}
JSON FOR LATEST MESSAGE ("{latest_user_query}"):
"""
    try:
        llm_json_output = _execute_llm_request(prompt_template, model_name, is_json_format=True)
        llm_dsl_code = assemble_event_dsl_from_json(llm_json_output, role)
        interpreter = EventInterpreter(state, role)
        dsl_result = execute_dsl(llm_dsl_code, AppConfig.get_grammar_path('src/domains/event/grammar.dsl'), interpreter)
        save_state(dsl_result['new_state'])
        return {"status": "success", "message": dsl_result['message']}
    except (ValueError, ConnectionError) as e:
        return {"status": "error", "message": f"🔴 Validation Error: {e}"}