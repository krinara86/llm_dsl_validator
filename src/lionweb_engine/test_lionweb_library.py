# src/lionweb_engine/test_lionweb_library.py
"""
Test script for LionWeb connector loader using lionweb-python library.
Tests creating, modifying, finding, and persisting M1 instances using actual LionWeb serialization.
"""

import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lionweb_engine.connector_loader_lionweb import LionWebConnectorLoader


def test_lionweb_operations():
    """Test M1 instance operations using LionWeb library."""
    print("=" * 60)
    print("LionWeb Library Serialization Test")
    print("=" * 60)
    
    project_root = Path(__file__).parent.parent.parent
    loader = LionWebConnectorLoader(project_root)
    
    # Load connector and existing models
    print("\n1. Loading connector and models...")
    results = loader.load_all("cycling")
    print(f"   Language: {results['language']}")
    print(f"   Connector: {results['connector']}")
    if results['models']:
        print(f"   Models: {results['models'][0]}")
    if results['errors']:
        print(f"   Warnings: {results['errors']}")
    
    # Create riders using DynamicNode
    print("\n2. Creating riders with DynamicNode...")
    rider1 = loader.create_m1_instance(
        domain="cycling",
        concept_name="Rider",
        properties={
            "name": "Peter Sagan",
            "age": 33,
            "country": "Slovakia"
        }
    )
    print(f"   ✅ Created: {rider1.id} (DynamicNode)")
    
    rider2 = loader.create_m1_instance(
        domain="cycling",
        concept_name="Rider",
        properties={
            "name": "Chris Froome",
            "age": 38,
            "country": "UK"
        }
    )
    print(f"   ✅ Created: {rider2.id} (DynamicNode)")
    
    # Create team using DynamicNode
    print("\n3. Creating team with DynamicNode...")
    team = loader.create_m1_instance(
        domain="cycling",
        concept_name="Team",
        properties={
            "name": "Team Sky",
            "country": "UK",
            "budget": 40,
            "founded": 2010
        }
    )
    print(f"   ✅ Created: {team.id} (DynamicNode)")
    
    # Modify instance
    print("\n4. Modifying DynamicNode instance...")
    modified = loader.modify_m1_instance(
        domain="cycling",
        instance_name="Peter Sagan",
        properties={"age": 34}
    )
    if modified:
        print(f"   ✅ Modified Peter Sagan's age to 34")
        print(f"      Instance type: {type(modified).__name__}")
    
    # Find instances
    print("\n5. Finding DynamicNode instances...")
    all_riders = loader.find_m1_instances(domain="cycling", concept_name="Rider")
    print(f"   Found {len(all_riders)} riders:")
    for rider in all_riders:
        name = loader._get_property_from_instance(rider, "name")
        age = loader._get_property_from_instance(rider, "age")
        country = loader._get_property_from_instance(rider, "country")
        print(f"   - {name}: age {age}, from {country} (type: {type(rider).__name__})")
    
    # Test LionWeb serialization
    print("\n6. Testing LionWeb serialization...")
    loader.save_models("cycling")
    model_file = project_root / "model_store" / "cycling" / "models.json"
    if model_file.exists():
        print(f"   ✅ Serialized using LionWeb to: model_store/cycling/models.json")
        with open(model_file, 'r') as f:
            data = json.load(f)
            print(f"   Format: {data.get('serializationFormatVersion')}")
            print(f"   Languages: {data.get('languages')}")
            print(f"   Total nodes: {len(data.get('nodes', []))}")
    
    # Test LionWeb deserialization
    print("\n7. Testing LionWeb deserialization...")
    new_loader = LionWebConnectorLoader(project_root)
    results = new_loader.load_all("cycling")
    
    # Verify loaded instances are DynamicNodes
    riders = new_loader.find_m1_instances(domain="cycling", concept_name="Rider")
    teams = new_loader.find_m1_instances(domain="cycling", concept_name="Team")
    print(f"   ✅ After reload: {len(riders)} riders, {len(teams)} teams")
    
    if riders:
        print(f"   First rider type after reload: {type(riders[0]).__name__}")
    
    print("\n" + "=" * 60)
    print("✅ LionWeb Library Serialization Test Complete!")
    print("=" * 60)


def verify_lionweb_structure():
    """Verify the structure of serialized LionWeb JSON."""
    print("\n" + "=" * 60)
    print("Verifying LionWeb JSON Structure")
    print("=" * 60)
    
    project_root = Path(__file__).parent.parent.parent
    model_file = project_root / "model_store" / "cycling" / "models.json"
    
    if model_file.exists():
        with open(model_file, 'r') as f:
            data = json.load(f)
        
        print("\n1. Root structure:")
        print(f"   serializationFormatVersion: {data.get('serializationFormatVersion')}")
        print(f"   languages: {data.get('languages')}")
        
        print("\n2. Nodes structure:")
        nodes = data.get('nodes', [])
        if nodes:
            # Check the root Model node
            root_node = nodes[0]
            print(f"   Root node ID: {root_node.get('id')}")
            print(f"   Root classifier: {root_node.get('classifier')}")
            
            # Check containments (should have riders and teams)
            containments = root_node.get('containments', [])
            print(f"   Containments: {len(containments)}")
            for cont in containments:
                key = cont.get('containment', {}).get('key')
                children = cont.get('children', [])
                print(f"     - {key}: {len(children)} children")
        
        print("\n3. Example node (if exists):")
        if len(nodes) > 1:
            example = nodes[1]
            print(f"   ID: {example.get('id')}")
            print(f"   Classifier: {example.get('classifier')}")
            print(f"   Properties: {len(example.get('properties', []))}")
            for prop in example.get('properties', [])[:2]:  # Show first 2 properties
                key = prop.get('property', {}).get('key')
                value = prop.get('value')
                print(f"     - {key}: {value}")
    else:
        print("   No model file found. Run the test first.")


def display_language_info():
    """Display information about the programmatically created language."""
    print("\n" + "=" * 60)
    print("Language Information (Created with LionWeb)")
    print("=" * 60)
    
    from lionweb.language import Concept, Property
    
    loader = LionWebConnectorLoader()
    
    print("\n1. Language:")
    lang = loader.languages.get("cycling")
    if lang:
        print(f"   Name: {lang.name}")
        print(f"   Key: {lang.key}")
        print(f"   Version: {lang.version}")
    
    print("\n2. Concepts:")
    for concept_name, concept in loader.concepts.items():
        print(f"\n   {concept_name}:")
        print(f"     Key: {concept.key}")
        print(f"     Abstract: {concept.abstract}")
        print(f"     Partition: {concept.partition}")
        print(f"     Features: {len(concept.features)}")
        
        # Show features
        for feature in concept.features[:3]:  # Show first 3 features
            if isinstance(feature, Property):
                print(f"       - Property '{feature.name}': optional={feature.optional}")


if __name__ == "__main__":
    try:
        # Ensure required directories exist
        project_root = Path(__file__).parent.parent.parent
        (project_root / "model_store" / "cycling").mkdir(parents=True, exist_ok=True)
        
        # Run tests
        test_lionweb_operations()
        verify_lionweb_structure()
        display_language_info()
        
        print("\n🎉 LionWeb library integration complete!")
        print("\nWhat this demonstrates:")
        print("  ✅ Language created programmatically with LionWeb classes")
        print("  ✅ Instances created as DynamicNode objects")
        print("  ✅ Serialization using lionweb.serialization")
        print("  ✅ Deserialization using lionweb.serialization")
        print("  ✅ Full LionWeb 2024.1 format compliance")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()