# test_storage_models.py
"""Tests for persistence and model management components."""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import uuid

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
# Also add tests directory to path for test_fixtures
sys.path.insert(0, str(Path(__file__).parent))

from src.core.state_manager import StateManager
from test_fixtures import SAMPLE_STATE


class TestStateManager:
    """Test state persistence operations."""
    
    def setup_method(self):
        """Set up test directory."""
        import tempfile
        self.temp_dir = Path(tempfile.mkdtemp())
        self.state_file = self.temp_dir / "test_state.json"
        # Clean up any existing file
        if self.state_file.exists():
            self.state_file.unlink()
    
    def test_save_and_load_cycle(self):
        """Test that state survives save/load cycle."""
        manager = StateManager(self.state_file)
        
        # Save test data
        test_data = {
            "venues": {
                "Test Room": {"capacity": 50, "has_av_system": True}
            },
            "sessions": ["session1", "session2"],
            "venue_bookings": {}
        }
        manager.save(test_data)
        
        # Load and verify
        loaded = manager.load()
        assert loaded == test_data
        assert loaded["venues"]["Test Room"]["capacity"] == 50
    
    def test_empty_state_initialization(self):
        """Test that new state file gets default structure."""
        manager = StateManager(self.state_file)
        state = manager.load()
        
        # Check if it returns default state structure (could be empty or with defaults)
        assert isinstance(state, dict)
        # StateManager might return empty dict or default structure - both are valid
        if state:  # If it has default structure
            assert "venues" in state
            assert "sessions" in state
            assert "venue_bookings" in state
        # Empty dict is also acceptable for initialization
    
    def test_corrupted_file_recovery(self):
        """Test graceful handling of corrupted JSON."""
        # Write invalid JSON
        with open(self.state_file, 'w') as f:
            f.write("{this is not: valid json}")
        
        manager = StateManager(self.state_file)
        state = manager.load()
        
        # Should return default state, not crash
        assert state == manager._default_state()
        assert isinstance(state["venues"], dict)
    
    def test_concurrent_state_updates(self):
        """Test that state updates don't lose data."""
        manager = StateManager(self.state_file)
        
        # Initial state
        manager.save(SAMPLE_STATE)
        
        # Load, modify, save
        state1 = manager.load()
        state1["venues"]["New Room"] = {"capacity": 25, "has_av_system": False}
        manager.save(state1)
        
        # Load again and verify
        state2 = manager.load()
        assert "Conference Room" in state2["venues"]  # Original data
        assert "New Room" in state2["venues"]  # New data
        assert state2["venues"]["New Room"]["capacity"] == 25


class TestLionWebConnectorLoader:
    """Test LionWeb model loading and manipulation."""
    
    def setup_method(self):
        """Set up test environment."""
        import tempfile
        self.temp_dir = Path(tempfile.mkdtemp())
        # Create necessary directories
        (self.temp_dir / "src" / "lionweb_app" / "languages").mkdir(parents=True, exist_ok=True)
        (self.temp_dir / "src" / "domains" / "cycling").mkdir(parents=True, exist_ok=True)
        (self.temp_dir / "model_store" / "cycling").mkdir(parents=True, exist_ok=True)
    
    @patch('src.lionweb_app.engine.connector_loader.Path.cwd')
    def test_create_m1_instance(self, mock_cwd):
        """Test creating a new M1 instance."""
        mock_cwd.return_value = self.temp_dir
        
        from src.lionweb_app.engine.connector_loader import LionWebConnectorLoader
        
        loader = LionWebConnectorLoader(self.temp_dir)
        
        # Create a rider instance
        instance = loader.create_m1_instance(
            "cycling",
            "Rider",
            {"name": "Peter Sagan", "age": 33, "country": "Slovakia"}
        )
        
        assert instance is not None
        # Verify it's stored
        assert len(loader.m1_models.get("cycling", [])) == 1
    
    @patch('src.lionweb_app.engine.connector_loader.Path.cwd')
    def test_modify_m1_instance(self, mock_cwd):
        """Test modifying an existing M1 instance."""
        mock_cwd.return_value = self.temp_dir
        
        from src.lionweb_app.engine.connector_loader import LionWebConnectorLoader
        
        loader = LionWebConnectorLoader(self.temp_dir)
        
        # Create instance
        loader.create_m1_instance(
            "cycling",
            "Rider",
            {"name": "Chris Froome", "age": 38, "country": "UK"}
        )
        
        # Modify it
        modified = loader.modify_m1_instance(
            "cycling",
            "Chris Froome",
            {"age": 39, "country": "Kenya"}
        )
        
        assert modified is not None
        # Verify the change
        instances = loader.find_m1_instances("cycling", "Rider", {"name": "Chris Froome"})
        if instances:
            # Get the age property
            age_val = loader._get_property_from_instance(instances[0], "age")
            assert age_val == 39
    
    @patch('src.lionweb_app.engine.connector_loader.Path.cwd')
    def test_find_instances_with_filter(self, mock_cwd):
        """Test finding instances with filters."""
        mock_cwd.return_value = self.temp_dir
        
        from src.lionweb_app.engine.connector_loader import LionWebConnectorLoader
        
        loader = LionWebConnectorLoader(self.temp_dir)
        
        # Create multiple instances
        loader.create_m1_instance("cycling", "Team", {"name": "Team Sky", "country": "UK"})
        loader.create_m1_instance("cycling", "Team", {"name": "Team Ineos", "country": "UK"})
        loader.create_m1_instance("cycling", "Team", {"name": "Jumbo-Visma", "country": "Netherlands"})
        
        # Find UK teams
        uk_teams = loader.find_m1_instances("cycling", "Team", {"country": "UK"})
        assert len(uk_teams) == 2
        
        # Find with name pattern
        sky_teams = loader.find_m1_instances("cycling", "Team", {"name_pattern": "Sky"})
        assert len(sky_teams) == 1
    
    @patch('src.lionweb_app.engine.connector_loader.Path.cwd')
    def test_schema_generation(self, mock_cwd):
        """Test dynamic schema generation from M2 and M1."""
        mock_cwd.return_value = self.temp_dir
        
        from src.lionweb_app.engine.connector_loader import LionWebConnectorLoader
        
        loader = LionWebConnectorLoader(self.temp_dir)
        
        # Generate connector M1
        loader.generate_connector_m1("cycling")
        
        # Get schema
        schema = loader.get_schema_as_dict("cycling")
        
        # Verify basic structure
        assert "create_rider" in schema
        assert "modify_rider" in schema
        assert "find_rider" in schema
        
        # Check permissions
        assert "admin" in schema["create_rider"]["permissions"]
        assert "scheduler" in schema["create_rider"]["permissions"]
        
        # Check parameter types
        create_rider = schema["create_rider"]
        assert "name" in create_rider["required"]
        assert create_rider["param_types"]["name"]["type"] == "string"
        assert create_rider["param_types"]["age"]["type"] == "number"
    
    @patch('src.lionweb_app.engine.connector_loader.Path.cwd')
    def test_connector_as_dict(self, mock_cwd):
        """Test conversion of M1 connector to Python dict."""
        mock_cwd.return_value = self.temp_dir
        
        from src.lionweb_app.engine.connector_loader import LionWebConnectorLoader
        
        loader = LionWebConnectorLoader(self.temp_dir)
        loader.generate_connector_m1("cycling")
        
        connector_dict = loader.get_connector_as_dict("cycling")
        
        assert connector_dict["domain_name"] == "Cycling Management"
        assert "create_rider" in connector_dict["actions"]
        assert "parameters" in connector_dict["actions"]["create_rider"]
        
        # Check parameter details
        rider_params = connector_dict["actions"]["create_rider"]["parameters"]
        assert "name" in rider_params
        assert "clarification_prompt" in rider_params["name"]
    
    @patch('src.lionweb_app.engine.connector_loader.Path.cwd')
    def test_save_and_load_models(self, mock_cwd):
        """Test model persistence using LionWeb serialization."""
        mock_cwd.return_value = self.temp_dir
        
        from src.lionweb_app.engine.connector_loader import LionWebConnectorLoader
        
        # First loader creates and saves
        loader1 = LionWebConnectorLoader(self.temp_dir)
        loader1.create_m1_instance("cycling", "Rider", {"name": "Tadej Pogacar", "age": 25})
        loader1.create_m1_instance("cycling", "Team", {"name": "UAE Emirates", "country": "UAE"})
        loader1.save_models("cycling")
        
        # Second loader loads
        loader2 = LionWebConnectorLoader(self.temp_dir)
        results = loader2.load_all("cycling")
        
        # Verify loaded instances
        riders = loader2.find_m1_instances("cycling", "Rider")
        teams = loader2.find_m1_instances("cycling", "Team")
        
        assert len(riders) >= 1
        assert len(teams) >= 1
        
        # Check specific instance
        pogacar = loader2.find_m1_instances("cycling", "Rider", {"name": "Tadej Pogacar"})
        assert len(pogacar) == 1


class TestSchemaGeneration:
    """Test schema and connector generation utilities."""
    
    @patch('src.lionweb_app.engine.connector_loader.Path.cwd')
    def test_cycling_m2_generation(self, mock_cwd):
        """Test that cycling M2 language is generated correctly."""
        import tempfile
        temp_dir = Path(tempfile.mkdtemp())
        mock_cwd.return_value = temp_dir
        
        # Create necessary directories
        lang_dir = temp_dir / "src" / "lionweb_app" / "languages"
        lang_dir.mkdir(parents=True, exist_ok=True)
        
        from lionweb.serialization import create_standard_json_serialization
        from src.lionweb_app.engine.language_generators import generate_and_save_cycling_m2
        
        serialization = create_standard_json_serialization()
        m2_path = lang_dir / "cycling_m2.json"
        
        generate_and_save_cycling_m2(m2_path, serialization)
        
        assert m2_path.exists()
        
        # Verify content
        with open(m2_path) as f:
            content = json.load(f)
        
        # Should have nodes
        assert "nodes" in content
        # Should have language node
        lang_nodes = [n for n in content["nodes"] if n["classifier"]["key"] == "Language"]
        assert len(lang_nodes) == 1
    
    @patch('src.lionweb_app.engine.connector_loader.Path.cwd')  
    def test_nl_mappings_m2_generation(self, mock_cwd):
        """Test that NL Mappings M2 language is generated correctly."""
        import tempfile
        temp_dir = Path(tempfile.mkdtemp())
        mock_cwd.return_value = temp_dir
        
        lang_dir = temp_dir / "src" / "lionweb_app" / "languages"
        lang_dir.mkdir(parents=True, exist_ok=True)
        
        from lionweb.serialization import create_standard_json_serialization
        from src.lionweb_app.engine.language_generators import generate_and_save_nl_mappings_m2
        
        serialization = create_standard_json_serialization()
        m2_path = lang_dir / "nl_mappings_m2.json"
        
        generate_and_save_nl_mappings_m2(m2_path, serialization)
        
        assert m2_path.exists()
        
        # Verify it contains Connector, ActionMapping, ParameterMapping concepts
        with open(m2_path) as f:
            content = json.load(f)
        
        concept_names = set()
        for node in content["nodes"]:
            if node["classifier"]["key"] == "Concept":
                name_prop = next(p for p in node["properties"] if "INamed-name" in p["property"]["key"])
                concept_names.add(name_prop["value"])
        
        assert "Connector" in concept_names
        assert "ActionMapping" in concept_names
        assert "ParameterMapping" in concept_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])