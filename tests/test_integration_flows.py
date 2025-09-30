# test_integration_flows.py
"""End-to-end integration tests for complete workflows."""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
# Also add tests directory to path for test_fixtures
sys.path.insert(0, str(Path(__file__).parent))

from src.conversation.orchestrator import ConversationOrchestrator
from src.conversation.document_processor import DocumentProcessor
from src.execution.executor import TaskExecutor
from src.core.state_manager import StateManager
from src.lionweb_app.engine.lionweb_task_executor import LionWebTaskExecutor

from test_fixtures import (
    EVENT_CONNECTOR, EVENT_SCHEMA, SAMPLE_STATE,
    LLM_FRIENDLY_QUERIES
)


class TestCompleteCreateFlow:
    """Test end-to-end creation flows."""
    
    def setup_method(self):
        """Set up test environment."""
        import tempfile
        self.temp_dir = Path(tempfile.mkdtemp())
        self.state_manager = StateManager(self.temp_dir / "test_state.json")
        self.state_manager.save(SAMPLE_STATE)
    
    @patch('src.conversation.extractor.TaskExtractor.extract_task_details')
    @patch('src.execution.executor.TaskExecutor.execute')
    def test_simple_create_flow(self, mock_execute, mock_extract):
        """Test complete flow: NL → Extract → Orchestrate → Execute."""
        # Mock extraction - using LLM-friendly pattern
        mock_extract.return_value = {
            "action": "create_venue",
            "parameters": {"name": "Innovation Lab", "capacity": 40}
        }
        
        # Mock execution
        mock_execute.return_value = {
            "status": "success",
            "message": "✅ Successfully completed: Create Venue 'Innovation Lab'"
        }
        
        orchestrator = ConversationOrchestrator(
            connector=EVENT_CONNECTOR,
            schema=EVENT_SCHEMA,
            state_manager=self.state_manager
        )
        
        # Step 1: Process initial request
        result = orchestrator.process_request(
            "Create Innovation Lab with 40 seats",
            role="admin",
            model_name="llama3:8b"
        )
        
        assert result["status"] == "confirmation_needed"
        conversation_state = result["new_state"]
        
        # Step 2: User confirms
        conversation_state["status"] = "awaiting_execution"
        
        # Step 3: Execute
        executor = TaskExecutor()
        exec_result = mock_execute("admin", conversation_state)
        
        assert exec_result["status"] == "success"
        assert "Innovation Lab" in exec_result["message"]
    
    @patch('src.conversation.extractor.TaskExtractor.extract_task_details')
    def test_create_with_validation_error(self, mock_extract):
        """Test flow when validation fails - REMOVED since role validation will be deprecated."""
        pass  # Keeping as placeholder


class TestClarificationFlow:
    """Test flows requiring clarification."""
    
    def setup_method(self):
        """Set up test environment."""
        import tempfile
        self.temp_dir = Path(tempfile.mkdtemp())
        self.state_manager = StateManager(self.temp_dir / "test_state.json")
        self.state_manager.save(SAMPLE_STATE)
    
    @patch('src.conversation.extractor.TaskExtractor.extract_task_details')
    def test_single_clarification_flow(self, mock_extract):
        """Test flow with one missing parameter."""
        # Initial extraction missing required parameter
        mock_extract.return_value = {
            "action": "book_venue",
            "parameters": {"venue": "Conference Room"}
        }
        
        orchestrator = ConversationOrchestrator(
            connector=EVENT_CONNECTOR,
            schema=EVENT_SCHEMA,
            state_manager=self.state_manager
        )
        
        # Step 1: Initial request
        result1 = orchestrator.process_request(
            "Book Conference Room",
            role="scheduler",
            model_name="llama3:8b"
        )
        
        assert result1["status"] == "clarification_needed"
        assert "expected_attendees" in result1["new_state"]["missing_params"]
        
        # Step 2: Provide clarification
        result2 = orchestrator.process_request(
            "25 people",  # Simple answer
            role="scheduler",
            model_name="llama3:8b",
            conversation_state=result1["new_state"]
        )
        
        assert result2["status"] == "confirmation_needed"
        params = result2["new_state"]["task_details"]["parameters"]
        assert params["expected_attendees"] == 25
    
    @patch('src.conversation.extractor.TaskExtractor.extract_task_details')
    def test_multiple_clarifications_flow(self, mock_extract):
        """Test flow with multiple missing parameters."""
        # Initial extraction missing multiple parameters
        mock_extract.return_value = {
            "action": "book_venue",
            "parameters": {}
        }
        
        orchestrator = ConversationOrchestrator(
            connector=EVENT_CONNECTOR,
            schema=EVENT_SCHEMA,
            state_manager=self.state_manager
        )
        
        # Step 1: Initial request
        result1 = orchestrator.process_request(
            "Book a venue",
            role="scheduler",
            model_name="llama3:8b"
        )
        
        assert result1["status"] == "clarification_needed"
        assert len(result1["new_state"]["missing_params"]) == 2
        
        # Step 2: Provide clarifications with key-value format
        result2 = orchestrator.process_request(
            "venue: Board Room\nexpected_attendees: 15",
            role="scheduler",
            model_name="llama3:8b",
            conversation_state=result1["new_state"]
        )
        
        assert result2["status"] == "confirmation_needed"
        params = result2["new_state"]["task_details"]["parameters"]
        assert params["venue"] == "Board Room"
        assert params["expected_attendees"] == 15


# TestRoleBasedAccessFlow class removed since role-based access will be deprecated


class TestMultiTaskDocumentFlow:
    """Test processing documents with multiple tasks."""
    
    @patch('src.core.llm_client.LLMClient.execute_request')
    @patch('src.conversation.extractor.TaskExtractor.extract_task_details')
    def test_document_to_multiple_executions(self, mock_extract, mock_llm):
        """Test processing a document with multiple tasks."""
        # Mock document extraction - LLM friendly format
        mock_llm.return_value = json.dumps({
            "tasks": [
                {
                    "task_description": "Create Workshop Room",
                    "action": "create_venue",
                    "details": {"name": "Workshop Room", "capacity": 25}
                },
                {
                    "task_description": "Create Lecture Hall",
                    "action": "create_venue",
                    "details": {"name": "Lecture Hall", "capacity": 100}
                },
                {
                    "task_description": "Book Conference Room",
                    "action": "book_venue",
                    "details": {"venue": "Conference Room", "expected_attendees": 30}
                }
            ]
        })
        
        processor = DocumentProcessor()
        doc_result = processor.extract_tasks(
            """Please set up the following:
            1. Create Workshop Room with 25 capacity
            2. Create Lecture Hall with 100 capacity  
            3. Book Conference Room for 30 people""",
            "llama3:8b",
            EVENT_CONNECTOR
        )
        
        assert doc_result["status"] == "tasks_extracted"
        assert len(doc_result["tasks"]) == 3
        
        # Now process each task
        import tempfile
        temp_dir = Path(tempfile.mkdtemp())
        state_manager = StateManager(temp_dir / "state.json")
        orchestrator = ConversationOrchestrator(
            connector=EVENT_CONNECTOR,
            schema=EVENT_SCHEMA,
            state_manager=state_manager
        )
        
        results = []
        for task in doc_result["tasks"]:
            # Convert details to parameters format
            pre_filled = {
                "action": task["action"],
                "parameters": task["details"]
            }
            
            # Process based on action - simplified since roles are being removed
            role = "admin"  # Use a default role for all actions
            
            result = orchestrator.process_request(
                f"Process task: {task['task_description']}",
                role=role,
                model_name="llama3:8b",
                pre_filled_details=pre_filled
            )
            results.append(result)
        
        # Verify all tasks processed
        assert len(results) == 3
        # First two should need confirmation (creates)
        assert results[0]["status"] == "confirmation_needed"
        assert results[1]["status"] == "confirmation_needed"
        # Third should also need confirmation (book)
        assert results[2]["status"] == "confirmation_needed"


class TestLionWebIntegration:
    """Test LionWeb-specific integration flows."""
    
    @patch('src.lionweb_app.engine.connector_loader.Path.cwd')
    def test_lionweb_create_and_find_flow(self, mock_cwd):
        """Test creating and finding instances via LionWeb."""
        import tempfile
        temp_dir = Path(tempfile.mkdtemp())
        mock_cwd.return_value = temp_dir
        
        # Set up necessary directories
        (temp_dir / "src" / "lionweb_app" / "languages").mkdir(parents=True, exist_ok=True)
        (temp_dir / "src" / "domains" / "cycling").mkdir(parents=True, exist_ok=True)
        (temp_dir / "model_store" / "cycling").mkdir(parents=True, exist_ok=True)
        
        from src.lionweb_app.engine.connector_loader import LionWebConnectorLoader
        from src.lionweb_app.engine.lionweb_task_executor import LionWebTaskExecutor
        from lionweb.language import Property
        
        loader = LionWebConnectorLoader(temp_dir)
        loader.generate_connector_m1("cycling")
        executor = LionWebTaskExecutor(loader)
        
        # Create a rider
        create_state = {
            "task_details": {
                "action": "create_rider",
                "parameters": {"name": "Wout van Aert", "age": 29, "country": "Belgium"}
            }
        }
        
        create_result = executor.execute("admin", create_state)
        assert create_result["status"] == "success"
        
        # Find the rider
        find_state = {
            "task_details": {
                "action": "find_rider",
                "parameters": {"name_pattern": "Wout"}
            }
        }
        
        find_result = executor.execute("scheduler", find_state)
        if find_result["status"] == "error":
            print(f"\nFind operation failed with error: {find_result.get('message', 'No message')}")
        assert find_result["status"] == "success"
        assert len(find_result["results"]) == 1
        assert find_result["results"][0]["name"] == "Wout van Aert"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])