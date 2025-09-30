# test_fixtures.py
"""Shared test data and utilities for the test suite."""

import json
from pathlib import Path
from typing import Dict, Any

# Sample connector for event domain
EVENT_CONNECTOR = {
    "domain_name": "Event Management",
    "actions": {
        "create_venue": {
            "description": "Creates a new venue",
            "parameters": {
                "name": {
                    "description": "Venue name",
                    "clarification_prompt": "What is the venue's name?"
                },
                "capacity": {
                    "description": "Maximum capacity",
                    "clarification_prompt": "How many people can it hold?"
                },
                "has_av_system": {
                    "description": "Has audio/video equipment",
                    "clarification_prompt": "Does it have AV equipment? (yes/no)"
                }
            }
        },
        "book_venue": {
            "description": "Books a venue for an event",
            "parameters": {
                "venue": {
                    "description": "Venue to book",
                    "clarification_prompt": "Which venue would you like to book?"
                },
                "expected_attendees": {
                    "description": "Number of attendees",
                    "clarification_prompt": "How many people will attend?"
                },
                "requires_av": {
                    "description": "Needs AV equipment",
                    "clarification_prompt": "Do you need AV equipment? (yes/no)"
                }
            }
        },
        "find_venues": {
            "description": "Search for venues",
            "parameters": {
                "name_pattern": {
                    "description": "Name to search for",
                    "clarification_prompt": "What venue name should I search for?"
                }
            }
        }
    }
}

# Sample schema for event domain
EVENT_SCHEMA = {
    "create_venue": {
        "permissions": ["admin"],
        "is_read_only": False,
        "required": ["name"],
        "optional": ["capacity", "has_av_system"],
        "param_types": {
            "name": {"type": "string", "dsl_keyword": "name"},
            "capacity": {"type": "number", "dsl_keyword": "capacity"},
            "has_av_system": {"type": "boolean", "dsl_keyword": "av"}
        },
        "dsl_syntax": "create_venue"
    },
    "book_venue": {
        "permissions": ["admin", "scheduler"],
        "is_read_only": False,
        "required": ["venue", "expected_attendees"],
        "optional": ["requires_av"],
        "param_types": {
            "venue": {"type": "venue_selection", "dsl_keyword": "venue"},
            "expected_attendees": {"type": "number", "dsl_keyword": "attendees"},
            "requires_av": {"type": "boolean", "dsl_keyword": "av"}
        },
        "dsl_syntax": "book_venue"
    },
    "find_venues": {
        "permissions": ["admin", "scheduler", "viewer"],
        "is_read_only": True,
        "required": [],
        "optional": ["name_pattern"],
        "param_types": {
            "name_pattern": {"type": "string", "dsl_keyword": "pattern"}
        },
        "dsl_syntax": "find_venues"
    }
}

# Sample state data
SAMPLE_STATE = {
    "venues": {
        "Conference Room": {"capacity": 50, "has_av_system": True},
        "Board Room": {"capacity": 20, "has_av_system": True},
        "Training Hall": {"capacity": 100, "has_av_system": False},
        "Small Room": {"capacity": 10, "has_av_system": False}
    },
    "sessions": [],
    "venue_bookings": {
        "Board Room": {"event": "Strategy Meeting", "attendees": 15}
    }
}

# LLM-friendly test queries (patterns that work well)
LLM_FRIENDLY_QUERIES = {
    # Clear action verbs at the start work best
    "simple_create": "Create a venue called Main Hall",
    "create_with_number": "Create Conference Room with 50 seats",
    "create_full": "Create Auditorium with 200 capacity and AV system",
    
    # Booking patterns that work well
    "book_simple": "Book Conference Room for 30 people",
    "book_with_av": "Reserve Board Room for 15 attendees with AV equipment",
    
    # Search patterns
    "find_simple": "Find all venues",
    "find_pattern": "Search for rooms with Conference in the name",
    
    # Multi-task patterns (clear sentence boundaries)
    "multi_create": "Create Room A with 30 seats. Create Room B with 20 seats.",
    "multi_mixed": "Create Team Sky. Then find all riders."
}

# Mock LLM responses for deterministic testing
MOCK_LLM_RESPONSES = {
    "create_venue_simple": json.dumps({
        "action": "create_venue",
        "parameters": {"name": "Main Hall"}
    }),
    "create_venue_full": json.dumps({
        "action": "create_venue",
        "parameters": {"name": "Auditorium", "capacity": 200, "has_av_system": True}
    }),
    "book_venue": json.dumps({
        "action": "book_venue",
        "parameters": {"venue": "Conference Room", "expected_attendees": 30}
    }),
    "unknown_action": json.dumps({
        "action": "unknown",
        "parameters": {}
    })
}

def create_test_state_manager(temp_dir: Path):
    """Create a StateManager with test data."""
    from src.core.state_manager import StateManager
    
    state_file = temp_dir / "test_state.json"
    manager = StateManager(state_file)
    manager.save(SAMPLE_STATE)
    return manager

def mock_llm_execute(prompt: str, model_name: str, is_json_format: bool = False):
    """Mock LLM execution for testing."""
    # Return predetermined responses based on prompt content
    if "Main Hall" in prompt:
        return MOCK_LLM_RESPONSES["create_venue_simple"]
    elif "Auditorium" in prompt:
        return MOCK_LLM_RESPONSES["create_venue_full"]
    elif "Conference Room" in prompt and "30" in prompt:
        return MOCK_LLM_RESPONSES["book_venue"]
    else:
        return MOCK_LLM_RESPONSES["unknown_action"]