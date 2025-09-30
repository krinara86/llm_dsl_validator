# src/event_system.py
"""Main entry point for the event management system."""

# Use consistent imports - either all absolute or all relative
try:
    # Try relative imports first (when running as module)
    from .core.config import AppConfig
    from .core.state_manager import StateManager
    from .core.llm_client import LLMClient
    from .conversation.orchestrator import ConversationOrchestrator
    from .conversation.document_processor import DocumentProcessor
    from .conversation.selection_provider import StateBasedSelectionProvider
    from .core.connector_loader import load_connector
    from .domains.event.schema import DOMAIN_SCHEMA
    from .execution.executor import TaskExecutor
except ImportError:
    # Fall back to absolute imports (when running from notebooks)
    from core.config import AppConfig
    from core.state_manager import StateManager
    from core.llm_client import LLMClient
    from conversation.orchestrator import ConversationOrchestrator
    from conversation.document_processor import DocumentProcessor
    from conversation.selection_provider import StateBasedSelectionProvider
    from core.connector_loader import load_connector
    from domains.event.schema import DOMAIN_SCHEMA
    from execution.executor import TaskExecutor

class EventSystem:
    """Main system coordinator."""
    
    def __init__(self):
        # Initialize state manager first
        self.state_manager = StateManager(AppConfig.STATE_FILE)
        
        # Load connector and schema
        self.connector = load_connector('event')
        self.schema = DOMAIN_SCHEMA
        
        # Create selection provider for state-based system
        selection_provider = StateBasedSelectionProvider(self.state_manager)
        
        # CRITICAL: Pass ALL parameters to orchestrator
        self.orchestrator = ConversationOrchestrator(
            connector=self.connector,
            schema=self.schema,
            state_manager=self.state_manager,
            selection_provider=selection_provider  # This was missing!
        )
        
        # Initialize other components
        self.executor = TaskExecutor()
        self.document_processor = DocumentProcessor()
    
    def process_query(self, query: str, role: str, model_name: str,
                     conversation_state: dict = None, pre_filled_details: dict = None) -> dict:
        return self.orchestrator.process_request(
            query, role, model_name, conversation_state, pre_filled_details
        )
    
    def execute_task(self, role: str, conversation_state: dict) -> dict:
        """Execute a confirmed task."""
        return self.executor.execute(role, conversation_state)
    
    def process_document(self, document: str, role: str, model_name: str) -> dict:
        result = self.document_processor.extract_tasks(document, model_name, self.connector)
        return result
    
    def get_current_state(self) -> dict:
        """Get the current system state."""
        return self.state_manager.load()
    
    def get_available_models(self) -> list:
        """Get list of available LLM models."""
        return LLMClient.get_available_models()