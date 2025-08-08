# src/core.py
import requests
import json
import re
import os
from .framework.base_interpreter import execute_dsl
from .domains.tax.interpreter import BillInterpreter
from .domains.cycling.interpreter import RideInterpreter
from .domains.event.interpreter import EventInterpreter


def extract_dsl_from_string(text, start_word):
    pattern = rf'{start_word}\s*(".*?"|\{{[^}}]*\}})'
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        pattern = rf'{start_word}\s+.*?\s*\{{[^}}]*\}}'
        match = re.search(pattern, text, re.DOTALL)
    return match.group(0) if match else None

def _process_request(user_query, prompt_template, dsl_start_word, grammar_file, interpreter_class, model_name="llama3:8b"):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    grammar_path = os.path.join(project_root, grammar_file)
    prompt = prompt_template.format(user_query=user_query)
    llm_dsl_code = None 
    
    try:
        api_response_stream = requests.post('http://localhost:11434/api/generate', json={"model": model_name, "prompt": prompt, "stream": True}, stream=True)
        api_response_stream.raise_for_status()
        llm_raw_output = "".join(json.loads(chunk).get('response', '') for chunk in api_response_stream.iter_lines() if chunk)
        
        if not llm_raw_output.strip(): raise ValueError("The LLM returned an empty response.")
        llm_dsl_code = extract_dsl_from_string(llm_raw_output, dsl_start_word)
        if not llm_dsl_code: raise ValueError(f"Could not find valid DSL code in the LLM's response. Full response: {llm_raw_output}")
        
        dsl_result = execute_dsl(llm_dsl_code, grammar_path, interpreter_class)
        return {"status": "success", "llm_generated_dsl": llm_dsl_code, "interpreter_result": dsl_result}
    except Exception as e:
        error_response = {"status": "error", "message": str(e)}
        if llm_dsl_code:
            error_response["llm_generated_dsl"] = llm_dsl_code
        return error_response

def _process_with_json_assembler(user_query: str, prompt_template: str, grammar_file: str, interpreter_class, dsl_assembler_func, model_name="llama3:8b"):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    grammar_path = os.path.join(project_root, grammar_file)
    prompt = prompt_template.format(user_query=user_query)
    llm_dsl_code = None
    
    try:
        api_response_stream = requests.post('http://localhost:11434/api/generate', json={"model": model_name, "prompt": prompt, "stream": True, "format": "json"}, stream=True)
        api_response_stream.raise_for_status()
        llm_raw_output = "".join(json.loads(chunk).get('response', '') for chunk in api_response_stream.iter_lines() if chunk)
        
        if not llm_raw_output.strip(): raise ValueError("The LLM returned an empty JSON response.")
        extracted_data = json.loads(llm_raw_output)

        llm_dsl_code = dsl_assembler_func(extracted_data)

        dsl_result = execute_dsl(llm_dsl_code, grammar_path, interpreter_class)
        return {"status": "success", "llm_generated_dsl": llm_dsl_code, "interpreter_result": dsl_result}
    except Exception as e:
        error_response = {"status": "error", "message": str(e)}
        if llm_dsl_code:
            error_response["llm_generated_dsl"] = llm_dsl_code
        return error_response

def assemble_event_dsl(data: dict) -> str:
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

def process_event_plan_request(user_query: str, model_name: str = "llama3:8b") -> dict:
    prompt = """From the user's request, extract entities for a conference plan.
The possible entities are: plan_name, venues, speakers, and sessions.
- A venue has a `name`, `capacity` (number), and `has_av_system` (boolean).
- A session has a `name`, `hosted_by` (string), `in_venue` (string), `expected_attendees` (number), and `requires_av` (boolean).
Return a single JSON object.

User Request: "{user_query}"
JSON Response:"""
    return _process_with_json_assembler(user_query, prompt, 'src/domains/event/grammar.dsl', EventInterpreter, assemble_event_dsl, model_name)

def process_order_request(user_query: str, model_name: str = "llama3:8b") -> dict:
    prompt = """You are an assistant that translates natural language into a DSL for a bill.
The DSL format is:
bill {{
  itemName: quantity * pricePerItem
}}
Translate the user order into this DSL.
User Order: "{user_query}"
DSL Response:"""
    return _process_request(user_query, prompt, "bill", 'src/domains/tax/grammar.dsl', BillInterpreter, model_name)

def process_ride_plan_request(user_query: str, model_name: str = "llama3:8b") -> dict:
    prompt = """You are an assistant that translates natural language into a DSL for a bike ride.
The DSL format is:
ride {{
  terrain: flat | hilly | mountainous
  distance_km: number
}}
Translate the user request into this DSL.
User Request: "{user_query}"
DSL Response:"""
    return _process_request(user_query, prompt, "ride", 'src/domains/cycling/grammar.dsl', RideInterpreter, model_name)
