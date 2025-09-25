# src/cycling_system.py
"""Main entry point for the cycling management system with LionWeb."""

from pathlib import Path
from src.core.llm_client import LLMClient
from src.conversation.lionweb_orchestrator import LionWebOrchestrator


class CyclingSystem:
    """Main system coordinator for cycling domain using LionWeb."""
    
    def __init__(self, mode: str = "lionweb"):
        """Initialize the cycling system.
        
        Args:
            mode: Either "lionweb" or "dsl"
        """
        self.orchestrator = LionWebOrchestrator(mode=mode, domain="cycling")
    
    def process_query(self, query: str, role: str = "admin", model_name: str = "llama3:8b",
                     conversation_state: dict = None, pre_filled_details: dict = None) -> dict:
        """Process a natural language query."""
        return self.orchestrator.process_request(
            query, role, model_name, conversation_state, pre_filled_details
        )
    
    def execute_task(self, role: str, conversation_state: dict) -> dict:
        """Execute a confirmed task."""
        return self.orchestrator.execute(role, conversation_state)
    
    def get_current_state(self) -> dict:
        """Get the current system state (all riders and teams)."""
        return self.orchestrator.get_current_state()
    
    def save_state(self):
        """Save current state to model store."""
        self.orchestrator.save_state()
    
    def get_available_models(self) -> list:
        """Get list of available LLM models."""
        return LLMClient.get_available_models()
    
    def get_stats(self) -> dict:
        """Get statistics about the current state."""
        state = self.get_current_state()
        return {
            "total_riders": len(state.get("riders", [])),
            "total_teams": len(state.get("teams", [])),
            "countries": len(set(
                [r.get("country", "Unknown") for r in state.get("riders", [])] +
                [t.get("country", "Unknown") for t in state.get("teams", [])]
            ))
        }