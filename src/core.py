# src/core.py
import requests
import json
import re
import os 
from .interpreter import calculate_bill_from_dsl

def extract_dsl_from_string(text):
    match = re.search(r'bill\s*\{[^}]*\}', text, re.DOTALL)
    return match.group(0) if match else None

def process_order_request(user_query: str) -> dict:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    grammar_path = os.path.join(project_root, 'tax_rules.dsl')

    prompt = f"""
    You are a helpful assistant that translates natural language into a custom DSL.
    The DSL format is:
    bill {{
      itemName: quantity * pricePerItem
      anotherItemName: price
    }}
    
    Translate the following user order into this DSL. The item names should be simple, lowercase words like 'burger' or 'soda'.

    User Order: "{user_query}"
    
    DSL Response:
    """
    
    try:
        api_response_stream = requests.post(
            'http://localhost:11434/api/generate',
            json={"model": "llama3:8b", "prompt": prompt, "stream": True},
            stream=True
        )
        api_response_stream.raise_for_status()
        
        llm_raw_output = "".join(json.loads(chunk).get('response', '') for chunk in api_response_stream.iter_lines() if chunk)
        
        if not llm_raw_output.strip():
            raise ValueError("The LLM returned an empty response.")

        llm_dsl_code = extract_dsl_from_string(llm_raw_output)
        if not llm_dsl_code:
            raise ValueError(f"Could not find valid DSL code in the LLM's response. Full response: {llm_raw_output}")

        dsl_result = calculate_bill_from_dsl(llm_dsl_code, grammar_path)
        
        return {
            "status": "success",
            "llm_generated_dsl": llm_dsl_code,
            "interpreter_result": dsl_result
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }