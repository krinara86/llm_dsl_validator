# src/core.py
import requests
import json
import re
import os
from .interpreters.base_interpreter import execute_dsl
from .interpreters.tax_interpreter import BillInterpreter
from .interpreters.cycling_interpreter import RideInterpreter
from .interpreters.turtle_interpreter import TurtleInterpreter

def extract_dsl_from_string(text, start_word):
    pattern = rf'{start_word}\s*\{{[^}}]*\}}'
    match = re.search(pattern, text, re.DOTALL)
    return match.group(0) if match else None

def _process_request(user_query, prompt_template, dsl_start_word, grammar_file, interpreter_class):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    grammar_path = os.path.join(project_root, grammar_file)
    prompt = prompt_template.format(user_query=user_query)
    
    try:
        api_response_stream = requests.post('http://localhost:11434/api/generate', json={"model": "llama3:8b", "prompt": prompt, "stream": True}, stream=True)
        api_response_stream.raise_for_status()
        llm_raw_output = "".join(json.loads(chunk).get('response', '') for chunk in api_response_stream.iter_lines() if chunk)
        
        if not llm_raw_output.strip(): raise ValueError("The LLM returned an empty response.")
        llm_dsl_code = extract_dsl_from_string(llm_raw_output, dsl_start_word)
        if not llm_dsl_code: raise ValueError(f"Could not find valid DSL code in the LLM's response. Full response: {llm_raw_output}")
        
        dsl_result = execute_dsl(llm_dsl_code, grammar_path, interpreter_class)
        return {"status": "success", "llm_generated_dsl": llm_dsl_code, "interpreter_result": dsl_result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def process_order_request(user_query: str) -> dict:
    prompt = """You are a helpful assistant that translates natural language into a custom DSL.
The DSL format is:
bill {{
  itemName: quantity * pricePerItem
  anotherItemName: price
}}
Translate the following user order into this DSL. The item names should be simple, lowercase words like 'burger' or 'soda'.
User Order: "{user_query}"
DSL Response:"""
    return _process_request(user_query, prompt, "bill", 'tax_rules.dsl', BillInterpreter)

def process_ride_plan_request(user_query: str) -> dict:
    prompt = """You are a helpful assistant that translates natural language into a custom DSL for planning a bike ride.
The DSL format is:
ride {{
  terrain: flat | hilly | mountainous
  distance_km: number
}}
Translate the following user request into this DSL. The 'terrain' value must be an unquoted word.
User Request: "{user_query}"
DSL Response:"""
    return _process_request(user_query, prompt, "ride", 'cycling_planner.dsl', RideInterpreter)

def process_turtle_request(user_query: str) -> dict:
    prompt = """You are a helpful assistant that translates natural language drawing instructions into a simple, one-letter command DSL for a turtle graphics program, wrapped in a `draw` block.

The DSL format is:
draw {{
  c "color"
  f number
  r number
  ...
}}

Available commands:
- c "color": Change color (e.g., c "red", c "blue")
- f number: Move forward
- b number: Move backward
- r number: Turn right by degrees
- l number: Turn left by degrees
- u: Pen up (no drawing)
- d: Pen down (resume drawing)

Translate the following user request into this DSL.

User Request: "{user_query}"
DSL Response:"""
    return _process_request(user_query, prompt, "draw", 'turtle_dsl.dsl', TurtleInterpreter)
