"""
Test script for the refactored LionWeb connector loader.
"""

import sys
from pathlib import Path

from lionweb.language import Concept

# Add the 'src' directory to the Python path
src_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(src_path))

# Update the import path for the refactored loader
from lionweb_app.engine.connector_loader import LionWebConnectorLoader


def test_lionweb_operations():
    """Test M1 instance operations using LionWeb library."""
    print("=" * 60)
    print("LionWeb Library Serialization Test")
    print("=" * 60)
    
    project_root = src_path.parent
    
    print("\n0. Preparing for test by deleting old files...")
    languages_dir = project_root / "src" / "lionweb_app" / "languages"
    cycling_m2_path = languages_dir / "cycling_m2.json"
    if cycling_m2_path.exists():
        cycling_m2_path.unlink()
        print(f"   - Deleted existing '{cycling_m2_path.name}'.")
        
    nl_mappings_m2_path = languages_dir / "nl_mappings_m2.json"
    if nl_mappings_m2_path.exists():
        nl_mappings_m2_path.unlink()
        print(f"   - Deleted existing '{nl_mappings_m2_path.name}'.")
        
    model_file_path = project_root / "model_store" / "cycling" / "models.json"
    if model_file_path.exists():
        model_file_path.unlink()
        print(f"   - Deleted existing '{model_file_path.name}'.")

    connector_m1_path = project_root / "src" / "domains" / "cycling" / "nl_connector_m1.json"
    if connector_m1_path.exists():
        connector_m1_path.unlink()
        print(f"   - Deleted existing '{connector_m1_path.name}'.")

    loader = LionWebConnectorLoader(project_root)
    
    print("\n1. Generating M1 Connector...")
    # The loader now handles the generation internally
    loader.generate_connector_m1("cycling")

    print("\n2. Loading all languages and models...")
    if cycling_m2_path.exists():
        print(f"   ✅ 'cycling_m2.json' was created successfully.")
    if nl_mappings_m2_path.exists():
        print(f"   ✅ 'nl_mappings_m2.json' was created successfully.")
    
    results = loader.load_all("cycling")
    print(f"   Language Info: Loaded languages: {list(loader.languages.keys())}")
    if results['connector']: print(f"   Connector: {results['connector']}")
    if results['models']: print(f"   Models: {results['models']}")
    if results['errors']: 
        print(f"   ❌ Warnings/Errors: {results['errors']}")
    else:
        print(f"   ✅ No validation errors.")

    # ... The rest of the test script remains the same ...
    print("\n3. Creating riders with DynamicNode...")
    loader.create_m1_instance("cycling", "Rider", {"name": "Peter Sagan", "age": 33, "country": "Slovakia"})
    print(f"   ✅ Created: Peter Sagan")
    
    loader.create_m1_instance("cycling", "Rider", {"name": "Chris Froome", "age": 38, "country": "UK"})
    print(f"   ✅ Created: Chris Froome")
    
    print("\n4. Creating team with DynamicNode...")
    loader.create_m1_instance("cycling", "Team", {"name": "Team Sky", "country": "UK", "budget": 40, "founded": 2010})
    print(f"   ✅ Created: Team Sky")
    
    print("\n5. Modifying DynamicNode instance...")
    loader.modify_m1_instance("cycling", "Peter Sagan", {"age": 34})
    print(f"   ✅ Modified Peter Sagan's age to 34")
    
    print("\n6. Finding DynamicNode instances...")
    all_riders = loader.find_m1_instances("cycling", concept_name="Rider")
    print(f"   Found {len(all_riders)} riders.")
    
    print("\n7. Testing LionWeb serialization...")
    loader.save_models("cycling")
    if model_file_path.exists():
        print(f"   ✅ Serialized model to: {model_file_path.name}")
    
    print("\n8. Testing LionWeb deserialization...")
    new_loader = LionWebConnectorLoader(project_root)
    new_loader.load_all("cycling")
    riders = new_loader.find_m1_instances("cycling", "Rider")
    print(f"   ✅ Deserialized {len(riders)} riders successfully.")
    
    print("\n" + "=" * 60)
    print("✅ LionWeb Library Serialization Test Complete!")
    print("=" * 60)


def display_language_info():
    """Display information about the programmatically created languages."""
    print("\n" + "=" * 60)
    print("Language Information (Loaded from Files)")
    print("=" * 60)
    
    src_path = Path(__file__).parent.parent.parent
    project_root = src_path.parent
    loader = LionWebConnectorLoader(project_root)
    
    for lang_name, lang in loader.languages.items():
        print(f"\n--- Language: {lang.name} ---")
        for concept in lang.elements:
            if isinstance(concept, Concept):
                print(f"  > Concept: {concept.name} (Partition: {concept.partition})")


if __name__ == "__main__":
    try:
        src_path = Path(__file__).parent.parent.parent
        project_root = src_path.parent

        (project_root / "model_store" / "cycling").mkdir(parents=True, exist_ok=True)
        (project_root / "src" / "domains" / "cycling").mkdir(parents=True, exist_ok=True)
        (project_root / "src" / "lionweb_app" / "languages").mkdir(parents=True, exist_ok=True)
        
        test_lionweb_operations()
        display_language_info()
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()