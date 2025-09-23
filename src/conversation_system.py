# src/conversation_system.py
"""Main entry point for the conversational system."""

from .core.config import AppConfig
from .core.state_manager import StateManager
from .core.llm_client import LLMClient
from .conversation.orchestrator import ConversationOrchestrator
from .conversation.document_processor import DocumentProcessor

# --- MODIFIED: Import specific engine components ---
from .lark_engine.executor import LarkTaskExecutor

class ConversationSystem:
    """Main system coordinator for any DSL engine."""
    
    def __init__(self, engine: str, domain: str):
        """
        Initializes the system with a specific engine and domain.

        Args:
            engine: The DSL engine to use ('lark' or 'lionweb').
            domain: The domain to operate on (e.g., 'event', 'shapes').
        """
        self.engine = engine
        self.domain = domain
        
        # The orchestrator is now aware of the engine/domain to load the correct connector.
        self.orchestrator = ConversationOrchestrator(engine, domain)
        self.document_processor = DocumentProcessor()
        self.state_manager = StateManager(AppConfig.STATE_FILE)

        # --- NEW: Conditional engine initialization ---
        if engine == 'lionweb':
            # Placeholder for the LionWeb executor we will build.
            # self.executor = LionWebExecutor(domain)
            raise NotImplementedError("LionWeb engine not yet implemented.")
        elif engine == 'lark':
            self.executor = LarkTaskExecutor(domain)
        else:
            raise ValueError(f"Unknown engine type: {engine}")
    
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
        if self.engine == 'lark':
            return self.state_manager.load()
        # Add logic for LionWeb state later
        return {}
    
    def get_available_models(self) -> list:
        """Get list of available LLM models."""
        return LLMClient.get_available_models()