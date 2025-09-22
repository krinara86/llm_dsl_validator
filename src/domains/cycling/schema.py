"""Schema definitions for the cycling management domain."""

DOMAIN_SCHEMA = {
    "find_rider": {
        "dsl_syntax": "find_rider",
        "required": [],
        "optional": ["name_pattern", "country", "team_id", "min_rank", "max_rank", "min_points", "max_points", "documented"],
        "param_types": {
            "name_pattern": {
                "type": "string",
                "dsl_keyword": "name_pattern"
            },
            "country": {
                "type": "string",
                "dsl_keyword": "country"
            },
            "team_id": {
                "type": "number",
                "dsl_keyword": "team_id"
            },
            "min_rank": {
                "type": "number",
                "dsl_keyword": "min_rank"
            },
            "max_rank": {
                "type": "number",
                "dsl_keyword": "max_rank"
            },
            "min_points": {
                "type": "number",
                "dsl_keyword": "min_points"
            },
            "max_points": {
                "type": "number",
                "dsl_keyword": "max_points"
            },
            "documented": {
                "type": "boolean",
                "dsl_keyword": "documented"
            }
        },
        "permissions": ["admin", "analyst", "viewer"],
        "is_read_only": True
    },
    "find_team": {
        "dsl_syntax": "find_team",
        "required": [],
        "optional": ["name_pattern", "country", "bike", "has_rider"],
        "param_types": {
            "name_pattern": {
                "type": "string",
                "dsl_keyword": "name_pattern"
            },
            "country": {
                "type": "string",
                "dsl_keyword": "country"
            },
            "bike": {
                "type": "string",
                "dsl_keyword": "bike"
            },
            "has_rider": {
                "type": "number",
                "dsl_keyword": "has_rider"
            }
        },
        "permissions": ["admin", "analyst", "viewer"],
        "is_read_only": True
    },
    "find_race": {
        "dsl_syntax": "find_race",
        "required": [],
        "optional": ["name_pattern", "country", "class", "start_date", "end_date", "year"],
        "param_types": {
            "name_pattern": {
                "type": "string",
                "dsl_keyword": "name_pattern"
            },
            "country": {
                "type": "string",
                "dsl_keyword": "country"
            },
            "class": {
                "type": "string",
                "dsl_keyword": "class"
            },
            "start_date": {
                "type": "string",
                "dsl_keyword": "start_date"
            },
            "end_date": {
                "type": "string",
                "dsl_keyword": "end_date"
            },
            "year": {
                "type": "number",
                "dsl_keyword": "year"
            }
        },
        "permissions": ["admin", "analyst", "viewer"],
        "is_read_only": True
    },
    "add_rider": {
        "dsl_syntax": "add_rider",
        "required": ["name", "first_name", "last_name", "country"],
        "optional": ["birth_date", "team_id", "rank", "points", "documented"],
        "param_types": {
            "name": {
                "type": "string"
            },
            "first_name": {
                "type": "string",
                "dsl_keyword": "first_name"
            },
            "last_name": {
                "type": "string",
                "dsl_keyword": "last_name"
            },
            "country": {
                "type": "string",
                "dsl_keyword": "country"
            },
            "birth_date": {
                "type": "string",
                "dsl_keyword": "birth_date"
            },
            "team_id": {
                "type": "number",
                "dsl_keyword": "team_id"
            },
            "rank": {
                "type": "number",
                "dsl_keyword": "rank"
            },
            "points": {
                "type": "number",
                "dsl_keyword": "points"
            },
            "documented": {
                "type": "boolean",
                "dsl_keyword": "documented"
            }
        },
        "permissions": ["admin", "editor"]
    },
    "modify_rider": {
        "dsl_syntax": "modify_rider",
        "required": ["rider_id"],
        "optional": ["first_name", "last_name", "country", "birth_date", "team_id", "rank", "points"],
        "param_types": {
            "rider_id": {
                "type": "number"
            },
            "first_name": {
                "type": "string",
                "dsl_keyword": "first_name"
            },
            "last_name": {
                "type": "string",
                "dsl_keyword": "last_name"
            },
            "country": {
                "type": "string",
                "dsl_keyword": "country"
            },
            "birth_date": {
                "type": "string",
                "dsl_keyword": "birth_date"
            },
            "team_id": {
                "type": "number",
                "dsl_keyword": "team_id"
            },
            "rank": {
                "type": "number",
                "dsl_keyword": "rank"
            },
            "points": {
                "type": "number",
                "dsl_keyword": "points"
            }
        },
        "permissions": ["admin", "editor"]
    },
    "add_team": {
        "dsl_syntax": "add_team",
        "required": ["name", "country"],
        "optional": ["bike", "website"],
        "param_types": {
            "name": {
                "type": "string"
            },
            "country": {
                "type": "string",
                "dsl_keyword": "country"
            },
            "bike": {
                "type": "string",
                "dsl_keyword": "bike"
            },
            "website": {
                "type": "string",
                "dsl_keyword": "website"
            }
        },
        "permissions": ["admin"]
    },
    "modify_team": {
        "dsl_syntax": "modify_team",
        "required": ["team_id"],
        "optional": ["name", "country", "bike", "website", "add_rider", "remove_rider"],
        "param_types": {
            "team_id": {
                "type": "number"
            },
            "name": {
                "type": "string",
                "dsl_keyword": "name"
            },
            "country": {
                "type": "string",
                "dsl_keyword": "country"
            },
            "bike": {
                "type": "string",
                "dsl_keyword": "bike"
            },
            "website": {
                "type": "string",
                "dsl_keyword": "website"
            },
            "add_rider": {
                "type": "number",
                "dsl_keyword": "add_rider"
            },
            "remove_rider": {
                "type": "number",
                "dsl_keyword": "remove_rider"
            }
        },
        "permissions": ["admin", "editor"]
    },
    "add_race": {
        "dsl_syntax": "add_race",
        "required": ["name", "country", "start_date"],
        "optional": ["class", "end_date", "distance"],
        "param_types": {
            "name": {
                "type": "string"
            },
            "country": {
                "type": "string",
                "dsl_keyword": "country"
            },
            "class": {
                "type": "string",
                "dsl_keyword": "class"
            },
            "start_date": {
                "type": "string",
                "dsl_keyword": "start_date"
            },
            "end_date": {
                "type": "string",
                "dsl_keyword": "end_date"
            },
            "distance": {
                "type": "number",
                "dsl_keyword": "distance"
            }
        },
        "permissions": ["admin"]
    },
    "modify_race": {
        "dsl_syntax": "modify_race",
        "required": ["race_id"],
        "optional": ["name", "country", "class", "start_date", "end_date", "distance"],
        "param_types": {
            "race_id": {
                "type": "number"
            },
            "name": {
                "type": "string",
                "dsl_keyword": "name"
            },
            "country": {
                "type": "string",
                "dsl_keyword": "country"
            },
            "class": {
                "type": "string",
                "dsl_keyword": "class"
            },
            "start_date": {
                "type": "string",
                "dsl_keyword": "start_date"
            },
            "end_date": {
                "type": "string",
                "dsl_keyword": "end_date"
            },
            "distance": {
                "type": "number",
                "dsl_keyword": "distance"
            }
        },
        "permissions": ["admin", "editor"]
    },
    "document_entity": {
        "dsl_syntax": "document_entity",
        "required": ["description", "entity_type", "entity_id"],
        "optional": [],
        "param_types": {
            "description": {
                "type": "string"
            },
            "entity_type": {
                "type": "string",
                "dsl_keyword": "entity_type"
            },
            "entity_id": {
                "type": "number",
                "dsl_keyword": "entity_id"
            }
        },
        "permissions": ["admin", "editor"]
    },
    "link_entities": {
        "dsl_syntax": "link_entities",
        "required": [],
        "optional": ["rider_id", "team_id", "race_id"],
        "param_types": {
            "rider_id": {
                "type": "number",
                "dsl_keyword": "rider_id"
            },
            "team_id": {
                "type": "number",
                "dsl_keyword": "team_id"
            },
            "race_id": {
                "type": "number",
                "dsl_keyword": "race_id"
            }
        },
        "permissions": ["admin", "editor"]
    }
}