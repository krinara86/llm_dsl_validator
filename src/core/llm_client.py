# src/core/llm_client.py
import os
import requests
from typing import Optional
from .config import AppConfig

class LLMClient:
    """Handles communication with LLM APIs."""
    
    @staticmethod
    def execute_request(prompt: str, model_name: str, 
                       is_json_format: bool = False) -> str:
        """Execute an LLM request to either Ollama or Together AI."""
        
        if model_name.startswith("togetherai/"):
            return LLMClient._together_request(prompt, model_name, is_json_format)
        else:
            return LLMClient._ollama_request(prompt, model_name, is_json_format)
    
    @staticmethod
    def _together_request(prompt: str, model_name: str, 
                         is_json_format: bool) -> str:
        """Execute request to Together AI."""
        api_key = os.getenv("TOGETHER_API_KEY")
        if not api_key:
            raise ValueError("TOGETHER_API_KEY not found. Please check your .env file.")
        
        together_model = model_name.split("/", 1)[1]
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": together_model,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        if is_json_format:
            payload["response_format"] = {"type": "json_object"}
        
        try:
            response = requests.post(
                AppConfig.TOGETHER_API_URL,
                headers=headers,
                json=payload,
                timeout=90
            )
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Together AI API request failed: {e}")
    
    @staticmethod
    def _ollama_request(prompt: str, model_name: str, 
                       is_json_format: bool) -> str:
        """Execute request to Ollama."""
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False
        }
        
        if is_json_format:
            payload["format"] = "json"
        
        try:
            response = requests.post(
                AppConfig.LLM_API_URL,
                json=payload,
                timeout=90
            )
            response.raise_for_status()
            return response.json().get('response', '')
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Ollama API request failed: {e}")
    
    @staticmethod
    def get_available_models():
        """Get list of available models from Ollama and Together AI."""
        models = []
        
        # Try to get Ollama models
        try:
            response = requests.get('http://localhost:11434/api/tags')
            response.raise_for_status()
            ollama_models = response.json().get('models', [])
            models.extend([m['name'] for m in ollama_models])
        except requests.exceptions.RequestException:
            pass
        
        # Add Together AI models
        models.extend([
            'togetherai/meta-llama/Llama-3-8b-chat-hf',
            'togetherai/mistralai/Mixtral-8x7B-Instruct-v0.1',
            'togetherai/Qwen/Qwen1.5-7B-Chat'
        ])
        
        return models if models else ['llama3:8b']