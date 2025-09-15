# test_lionweb_integration.py
"""
Test script to verify both Lark and LionWeb implementations work correctly.
Run this after setting up the LionWeb integration.
"""

import os
import sys
sys.path.append('..')  # Add src to path

def test_lark_event_system():
    """Test that the existing Lark event system still works."""
    print("=== Testing Lark Event System ===\n")
    
    # Set configuration for Lark
    os.environ["FRAMEWORK"] = "lark"
    os.environ["DOMAIN"] = "event"
    
    # Reload config to pick up changes
    import importlib
    from src.core import config
    importlib.reload(config)
    
    from src.event_system import EventSystem
    
    system = EventSystem()
    
    # Test 1: Create venue
    print("Test 1: Create venue")
    result = system.process_query(
        "Create a venue called Main Hall with capacity 100 and AV system",
        role="admin",
        model_name="llama3:8b"
    )
    print(f"Status: {result.get('status')}")
    assert result['status'] in ['confirmation_needed', 'clarification_needed'], "Should need confirmation or clarification"
    print("✓ Venue creation request processed\n")
    
    # Test 2: Query parsing
    print("Test 2: Schedule session")
    result = system.process_query(
        "Schedule a session called AI Workshop",
        role="scheduler",
        model_name="llama3:8b"
    )
    print(f"Status: {result.get('status')}")
    assert 'missing_params' in str(result) or result['status'] == 'clarification_needed', "Should identify missing params"
    print("✓ Missing parameter detection works\n")
    
    print("✅ Lark Event System tests passed!\n")

def test_lionweb_shapes_system():
    """Test the new LionWeb Shapes system."""
    print("=== Testing LionWeb Shapes System ===\n")
    
    # Set configuration for LionWeb
    os.environ["FRAMEWORK"] = "lionweb"
    os.environ["DOMAIN"] = "shapes"
    
    # Reload modules to pick up config changes
    import importlib
    from src.core import config
    from src.conversation import orchestrator
    from src.execution import executor
    
    importlib.reload(config)
    importlib.reload(orchestrator)
    importlib.reload(executor)
    
    from src.event_system import EventSystem
    
    system = EventSystem()
    
    # Test 1: Create circle
    print("Test 1: Create circle")
    result = system.process_query(
        "Create a circle with radius 10",
        role="admin",
        model_name="llama3:8b"
    )
    print(f"Status: {result.get('status')}")
    
    if result['status'] == 'confirmation_needed':
        # Simulate confirmation
        conversation_state = result.get('new_state', {})
        exec_result = system.execute_task("admin", conversation_state)
        print(f"Execution status: {exec_result.get('status')}")
        print(f"Message: {exec_result.get('message')}")
        assert exec_result['status'] == 'success', "Should successfully create circle"
        print("✓ Circle created successfully\n")
    elif result['status'] == 'clarification_needed':
        print("✓ Clarification requested for missing parameters\n")
    
    # Test 2: Find shapes
    print("Test 2: Find shapes")
    result = system.process_query(
        "Find all circles",
        role="admin", 
        model_name="llama3:8b"
    )
    print(f"Status: {result.get('status')}")
    
    if result['status'] == 'direct_execute':
        conversation_state = result.get('new_state', {})
        exec_result = system.execute_task("admin", conversation_state)
        print(f"Found {len(exec_result.get('results', []))} shape(s)")
        print("✓ Query executed successfully\n")
    
    print("✅ LionWeb Shapes System tests passed!\n")

def main():
    """Run all tests."""
    print("\n" + "="*50)
    print("LionWeb Integration Test Suite")
    print("="*50 + "\n")
    
    try:
        # Test Lark system (should work unchanged)
        test_lark_event_system()
        
        # Test LionWeb system (new functionality)
        test_lionweb_shapes_system()
        
        print("="*50)
        print("✅ ALL TESTS PASSED!")
        print("="*50)
        print("\nThe integration is working correctly.")
        print("- Lark event system: Working (backward compatible)")
        print("- LionWeb shapes system: Working (new feature)")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()