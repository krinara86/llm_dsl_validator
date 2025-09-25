# src/lionweb_engine/test_loader_simple.py
"""
Simplified test script for LionWeb connector loader.
This version works with raw JSON without requiring the lionweb-python library.
"""

import json
import sys
from pathlib import Path

# Add parent directory to path to import connector_loader
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from connector_loader import LionWebConnectorLoader


def create_test_files():
    """Create the necessary JSON files for testing."""
    project_root = Path(__file__).parent.parent.parent
    
    # Create directories
    languages_dir = project_root / "src" / "lionweb" / "languages"
    languages_dir.mkdir(parents=True, exist_ok=True)
    
    cycling_dir = project_root / "src" / "domains" / "cycling"
    cycling_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a minimal cycling_m2.json
    cycling_m2 = {
        "serializationFormatVersion": "2024.1",
        "languages": [{"key": "cycling", "version": "1"}],
        "nodes": []  # Minimal for testing
    }
    
    with open(languages_dir / "cycling_m2.json", "w") as f:
        json.dump(cycling_m2, f, indent=2)
    
    # Create a minimal nl_connector_m1.json
    nl_connector = {
        "serializationFormatVersion": "2024.1",
        "languages": [{"key": "nl_mappings", "version": "1"}],
        "nodes": [
            {
                "id": "cycling-connector",
                "classifier": {"language": "nl_mappings", "version": "1", "key": "Connector"},
                "properties": [
                    {"property": {"key": "Connector-domainName"}, "value": "Cycling Management"},
                    {"property": {"key": "Connector-targetLanguage"}, "value": "cycling"}
                ],
                "containments": [
                    {"containment": {"key": "Connector-actions"}, "children": ["create-rider-action"]}
                ]
            },
            {
                "id": "create-rider-action",
                "classifier": {"key": "ActionMapping"},
                "properties": [
                    {"property": {"key": "ActionMapping-actionName"}, "value": "create_rider"},
                    {"property": {"key": "ActionMapping-targetConcept"}, "value": "Rider"},
                    {"property": {"key": "ActionMapping-description"}, "value": "Creates a new rider"}
                ],
                "containments": [
                    {"containment": {"key": "ActionMapping-parameters"}, "children": ["param-name"]}
                ]
            },
            {
                "id": "param-name",
                "classifier": {"key": "ParameterMapping"},
                "properties": [
                    {"property": {"key": "ParameterMapping-parameterName"}, "value": "name"},
                    {"property": {"key": "ParameterMapping-targetFeature"}, "value": "Rider-name"},
                    {"property": {"key": "ParameterMapping-description"}, "value": "Rider name"},
                    {"property": {"key": "ParameterMapping-clarificationPrompt"}, "value": "What is the rider's name?"},
                    {"property": {"key": "ParameterMapping-required"}, "value": True}
                ]
            }
        ]
    }
    
    with open(cycling_dir / "nl_connector_m1.json", "w") as f:
        json.dump(nl_connector, f, indent=2)
    
    print("✅ Test files created successfully")


def test_basic_loading():
    """Test basic loading functionality."""
    print("\n" + "=" * 60)
    print("Testing Basic Loading")
    print("=" * 60)
    
    project_root = Path(__file__).parent.parent.parent
    loader = LionWebConnectorLoader(project_root)
    
    # Test loading
    results = loader.load_all("cycling")
    
    print(f"\n✅ Loaded M2 languages: {list(results['m2_languages'].keys())}")
    print(f"✅ Connector status: {results['connector']}")
    
    if results['errors']:
        print("\n⚠️ Errors encountered:")
        for error in results['errors']:
            print(f"  - {error}")
    
    return loader


def test_m1_operations(loader):
    """Test M1 instance operations."""
    print("\n" + "=" * 60)
    print("Testing M1 Instance Operations")
    print("=" * 60)
    
    # Create a rider
    print("\n1. Creating a rider...")
    rider = loader.create_m1_instance(
        domain="cycling",
        concept="Rider",
        properties={"name": "Test Rider", "age": 25}
    )
    print(f"   Created: {loader._get_instance_property(rider, 'name')}")
    
    # Modify the rider
    print("\n2. Modifying the rider...")
    modified = loader.modify_m1_instance(
        domain="cycling",
        instance_name="Test Rider",
        properties={"age": 26}
    )
    if modified:
        print(f"   Updated age to: {loader._get_instance_property(modified, 'age')}")
    
    # Find riders
    print("\n3. Finding all riders...")
    riders = loader.find_m1_instances(domain="cycling", concept="Rider")
    print(f"   Found {len(riders)} rider(s)")
    
    # Save models
    print("\n4. Saving models...")
    loader.save_models("cycling")
    model_file = loader.model_store_dir / "cycling" / "models.json"
    if model_file.exists():
        print(f"   ✅ Saved to: {model_file}")
    
    return loader


def test_connector_structure(loader):
    """Test the connector structure."""
    print("\n" + "=" * 60)
    print("Testing Connector Structure")
    print("=" * 60)
    
    if not loader.m1_connectors.get("cycling"):
        print("❌ No connector loaded")
        return
    
    connector = loader.m1_connectors["cycling"]
    print(f"\nConnector Details:")
    print(f"  Domain Name: {connector.get('domain_name')}")
    print(f"  Target Language: {connector.get('target_language')}")
    print(f"  Actions: {list(connector.get('actions', {}).keys())}")
    
    # Show first action details
    for action_name, action_data in list(connector.get('actions', {}).items())[:1]:
        print(f"\n  Action '{action_name}':")
        print(f"    Target: {action_data.get('target_concept')}")
        print(f"    Description: {action_data.get('description')}")
        params = action_data.get('parameters', {})
        if params:
            print(f"    Parameters: {list(params.keys())}")


if __name__ == "__main__":
    try:
        print("🚀 LionWeb Connector Loader Test (Simplified)")
        print("=" * 60)
        
        # Create test files
        create_test_files()
        
        # Run tests
        loader = test_basic_loading()
        loader = test_m1_operations(loader)
        test_connector_structure(loader)
        
        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()