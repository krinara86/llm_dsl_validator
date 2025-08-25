# src/event_system.py
"""Main entry point for the event management system."""

# Use absolute imports when the module will be imported from notebooks
from src.core.config import AppConfig
from src.core.state_manager import StateManager
from src.core.llm_client import LLMClient
from src.conversation.orchestrator import ConversationOrchestrator
from src.conversation.document_processor import DocumentProcessor
from src.execution.executor import TaskExecutor

class EventSystem:
    """Main system coordinator."""
    
    def __init__(self):
        self.orchestrator = ConversationOrchestrator()
        self.executor = TaskExecutor()
        self.document_processor = DocumentProcessor()
        self.state_manager = StateManager(AppConfig.STATE_FILE)
    
    def process_query(self, query: str, role: str, model_name: str,
                     conversation_state: dict = None, pre_filled_details: dict = None) -> dict:
        return self.orchestrator.process_request(
            query, role, model_name, conversation_state, pre_filled_details
        )
    
    def execute_task(self, role: str, conversation_state: dict) -> dict:
        """Execute a confirmed task."""
        return self.executor.execute(role, conversation_state)
    
    def process_document(self, document: str, role: str, model_name: str) -> dict:
        return self.document_processor.extract_tasks(document, model_name)
    
    def get_current_state(self) -> dict:
        """Get the current system state."""
        return self.state_manager.load()
    
    def get_available_models(self) -> list:
        """Get list of available LLM models."""
        return LLMClient.get_available_models()