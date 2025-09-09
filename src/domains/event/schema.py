# src/domains/event/schema.py
"""Schema definitions for the event management domain."""

DOMAIN_SCHEMA = {
    "create_venue": {
        "operation_type": "state_changing",
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
        "operation_type": "state_changing",
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
        "operation_type": "state_changing",
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
    },
    "find_venues": {
        "operation_type": "read_only",
        "dsl_syntax": "find_venues",
        "required": [],  # All parameters are optional for flexible search
        "optional": ["min_capacity", "has_av_system", "is_available", "name_contains"],
        "param_types": {
            "min_capacity": {
                "type": "number",
                "dsl_keyword": "min_capacity"
            },
            "has_av_system": {
                "type": "boolean",
                "dsl_keyword": "has_av_system"
            },
            "is_available": {
                "type": "boolean",
                "dsl_keyword": "is_available"
            },
            "name_contains": {
                "type": "string",
                "dsl_keyword": "name_contains"
            }
        },
        "permissions": ["admin", "scheduler", "viewer"]  # Anyone can search
    },
    "find_sessions": {
        "operation_type": "read_only",
        "dsl_syntax": "find_sessions",
        "required": [],  # All parameters are optional
        "optional": ["name_contains", "hosted_by", "in_venue", "min_attendees", "requires_av"],
        "param_types": {
            "name_contains": {
                "type": "string",
                "dsl_keyword": "name_contains"
            },
            "hosted_by": {
                "type": "string",
                "dsl_keyword": "hosted_by"
            },
            "in_venue": {
                "type": "string",  # Not venue_selection since we're searching
                "dsl_keyword": "in_venue"
            },
            "min_attendees": {
                "type": "number",
                "dsl_keyword": "min_attendees"
            },
            "requires_av": {
                "type": "boolean",
                "dsl_keyword": "requires_av"
            }
        },
        "permissions": ["admin", "scheduler", "viewer"]  # Anyone can search
    }
}