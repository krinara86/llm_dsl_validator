# src/domains/event/schema.py
"""Schema definitions for the event management domain."""

DOMAIN_SCHEMA = {
    "create_venue": {
        "required": ["name", "capacity", "has_av_system"],
        "optional": [],
        "param_types": {
            "name": "text",
            "capacity": "number",
            "has_av_system": "boolean"
        },
        "permissions": ["admin"]
    },
    "modify_venue": {
        "required": ["name"],
        "optional": ["capacity", "has_av_system"],
        "param_types": {
            "name": "text",
            "capacity": "number",
            "has_av_system": "boolean"
        },
        "permissions": ["admin"]
    },
    "schedule_session": {
        "required": ["name", "in_venue", "expected_attendees", "requires_av"],
        "optional": ["hosted_by"],
        "param_types": {
            "name": "text",
            "in_venue": "venue_selection",
            "expected_attendees": "number",
            "requires_av": "boolean",
            "hosted_by": "text"
        },
        "permissions": ["admin", "scheduler"]
    }
}