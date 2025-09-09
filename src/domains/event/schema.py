
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
    },
    "find_venue": {
        "dsl_syntax": "find_venue",
        "required": [],
        "optional": ["name_pattern", "min_capacity", "max_capacity", "has_av_system"],
        "param_types": {
            "name_pattern": {
                "type": "string",
                "dsl_keyword": "name_pattern"
            },
            "min_capacity": {
                "type": "number",
                "dsl_keyword": "min_capacity"
            },
            "max_capacity": {
                "type": "number",
                "dsl_keyword": "max_capacity"
            },
            "has_av_system": {
                "type": "boolean",
                "dsl_keyword": "has_av"
            }
        },
        "permissions": ["admin", "scheduler"],
        "is_read_only": True
    },
    "find_session": {
        "dsl_syntax": "find_session",
        "required": [],
        "optional": ["name_pattern", "hosted_by_pattern", "in_venue", "min_attendees", "max_attendees", "requires_av"],
        "param_types": {
            "name_pattern": {
                "type": "string",
                "dsl_keyword": "name_pattern"
            },
            "hosted_by_pattern": {
                "type": "string",
                "dsl_keyword": "hosted_by_pattern"
            },
            "in_venue": {
                "type": "string",
                "dsl_keyword": "in_venue"
            },
            "min_attendees": {
                "type": "number",
                "dsl_keyword": "min_attendees"
            },
            "max_attendees": {
                "type": "number",
                "dsl_keyword": "max_attendees"
            },
            "requires_av": {
                "type": "boolean",
                "dsl_keyword": "requires_av"
            }
        },
        "permissions": ["admin", "scheduler"],
        "is_read_only": True
    }
}