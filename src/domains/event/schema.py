# src/domains/event/schema.py
"""Schema definitions for the event management domain."""

DOMAIN_SCHEMA = {
    "create_venue": {
        "dsl_syntax": "create_venue",
        "required": ["name", "capacity", "has_av_system"],
        "optional": [],
        "param_types": {
            "name": {
                "type": "string" 
            },
            "capacity": {
                "type": "number",
                "dsl_keyword": "capacity"
            },
            "has_av_system": {
                "type": "boolean",
                "dsl_keyword": "has_av_system"
            }
        },
        "permissions": ["admin"]
    },
    "modify_venue": {
        "dsl_syntax": "modify_venue",
        "required": ["name"],
        "optional": ["capacity", "has_av_system"],
        "param_types": {
            "name": {
                "type": "string"
            },
            "capacity": {
                "type": "number",
                "dsl_keyword": "capacity"
            },
            "has_av_system": {
                "type": "boolean",
                "dsl_keyword": "has_av_system"
            }
        },
        "permissions": ["admin"]
    },
    "schedule_session": {
        "dsl_syntax": "schedule_session",
        "required": ["name", "in_venue", "expected_attendees", "requires_av", "hosted_by"],
        "optional": [],
        "param_types": {
            "name": {
                "type": "string"
            },
            "in_venue": {
                "type": "venue_selection",
                "dsl_keyword": "in_venue"
            },
            "expected_attendees": {
                "type": "number",
                "dsl_keyword": "expected_attendees"
            },
            "requires_av": {
                "type": "boolean",
                "dsl_keyword": "requires_av"
            },
            "hosted_by": {
                "type": "string",
                "dsl_keyword": "hosted_by"
            }
        },
        "permissions": ["admin", "scheduler"]
    }
}