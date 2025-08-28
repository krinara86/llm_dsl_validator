# src/core/llm_client.py
import os
import requests
from typing import List
from .config import AppConfig

# --- MODIFIED ---
# Use InferenceApi for older library versions or InferenceClient for newer ones
try:
    from huggingface_hub import InferenceClient
    HUGGINGFACE_AVAILABLE = True
except ImportError:
    HUGGINGFACE_AVAILABLE = False

class LLMClient:
    """Handles communication with LLM APIs."""
    
    # --- MODIFIED ---
    @staticmethod
    def execute_request(prompt: str, model_name: str, 
                       is_json_format: bool = False) -> str:
        """Execute an LLM request to Ollama, Together AI, or Hugging Face."""
        
        if model_name.startswith("togetherai/"):
            return LLMClient._together_request(prompt, model_name, is_json_format)
        # --- NEW ---
        elif model_name.startswith("huggingface/"):
            return LLMClient._huggingface_request(prompt, model_name, is_json_format)
        else: # Default to Ollama
            return LLMClient._ollama_request(prompt, model_name, is_json_format)

    # --- NEW ---
    @staticmethod
    def _huggingface_request(prompt: str, model_name: str, 
                            is_json_format: bool) -> str:
        """Execute request to Hugging Face Inference API."""
        if not HUGGINGFACE_AVAILABLE:
            raise ConnectionError("The 'huggingface_hub' library is not installed.")

        hf_token = os.getenv("HUGGING_FACE_TOKEN")
        if not hf_token:
            raise ValueError("HUGGING_FACE_TOKEN not found. Please check your .env file.")

        hf_model = model_name.split("/", 1)[1]
        
        try:
            # Use the recommended InferenceClient
            client = InferenceClient(token=hf_token)
            
            # The free Inference API does not support enforced JSON mode.
            # We rely on the model's instruction-following capabilities.
            response = client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model=hf_model,
                max_tokens=1024,
            )
            return response.choices[0].message.content
        except Exception as e:
            raise ConnectionError(f"Hugging Face API request failed: {e}")

    @staticmethod
    def _together_request(prompt: str, model_name: str, 
                         is_json_format: bool) -> str:
        api_key = os.getenv("TOGETHER_API_KEY")
        if not api_key:
            raise ValueError("TOGETHER_API_KEY not found. Please check your .env file.")
        
        together_model = model_name.split("/", 1)[1]
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = { "model": together_model, "messages": [{"role": "user", "content": prompt}] }
        if is_json_format:
            payload["response_format"] = {"type": "json_object"}
        
        try:
            response = requests.post(AppConfig.TOGETHER_API_URL, headers=headers, json=payload, timeout=90)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Together AI API request failed: {e}")
    
    @staticmethod
    def _ollama_request(prompt: str, model_name: str, 
                       is_json_format: bool) -> str:
        payload = { "model": model_name, "prompt": prompt, "stream": False }
        if is_json_format:
            payload["format"] = "json"
        
        try:
            response = requests.post(AppConfig.LLM_API_URL, json=payload, timeout=90)
            response.raise_for_status()
            return response.json().get('response', '')
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Ollama API request failed: {e}")
    
    # --- MODIFIED ---
    @staticmethod
    def get_available_models():
        """Get a curated list of available models."""
        models = []
        
        try:
            response = requests.get('http://localhost:11434/api/tags')
            response.raise_for_status()
            ollama_models = response.json().get('models', [])
            models.extend([m['name'] for m in ollama_models])
        except requests.exceptions.RequestException:
            pass
        
        models.extend([
            'togetherai/meta-llama/Llama-3-8b-chat-hf',
            'togetherai/mistralai/Mixtral-8x7B-Instruct-v0.1',
        ])
        
        # --- NEW: Curated list for speed and reliability ---
        models.extend([
            'huggingface/meta-llama/Meta-Llama-3-8B-Instruct',
            'huggingface/mistralai/Mistral-7B-Instruct-v0.2',
            'huggingface/google/gemma-7b-it',
        ])
        
        return models if models else ['llama3:8b'] # Fallback