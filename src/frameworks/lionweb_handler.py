# src/frameworks/lionweb_handler.py
"""LionWeb-specific domain handler for M2/M1 based domains."""

import json
import uuid
from typing import Dict, List, Any, Optional
from pathlib import Path
from .base_handler import BaseDomainHandler

class LionWebHandler(BaseDomainHandler):
    """Handler for LionWeb-based domains using M2/M1 instances."""
    
    def __init__(self, domain: str):
        """Initialize with LionWeb M2 and NL mappings."""
        self.domain = domain
        self.m1_instances = []  # In-memory store of M1 instances
        
        # Load M2 (metamodel)
        m2_path = Path(__file__).parent.parent / "lionweb" / "languages" / f"{domain}_m2.json"
        with open(m2_path, 'r') as f:
            self.m2_model = json.load(f)
        
        # Load NL mappings (M1 of NL mapping language)
        mappings_path = Path(__file__).parent.parent / "lionweb" / "mappings" / f"{domain}_nl.json"
        with open(mappings_path, 'r') as f:
            self.nl_mappings = json.load(f)
        
        # Build concept index for quick lookup
        self._build_m2_index()
        
        # Convert NL mappings to connector-like format for compatibility
        self.connector_format = self._convert_nl_mappings_to_connector_format()
    
    def _build_m2_index(self):
        """Build indices for quick M2 lookups."""
        self.concepts_by_key = {}
        self.concepts_by_name = {}
        self.properties_by_key = {}
        
        for node in self.m2_model.get("nodes", []):
            classifier = node.get("classifier", {})
            if classifier.get("key") == "Concept":
                # Get concept key and name
                concept_key = self._get_property_value(node, "IKeyed-key")
                concept_name = self._get_property_value(node, "LionCore-builtins-INamed-name")
                
                if concept_key:
                    self.concepts_by_key[concept_key] = node
                if concept_name:
                    self.concepts_by_name[concept_name] = node
                
                # Index properties
                for feature in self._get_containment_children(node, "Classifier-features"):
                    if isinstance(feature, dict):
                        prop_key = self._get_property_value(feature, "IKeyed-key")
                        if prop_key:
                            self.properties_by_key[prop_key] = feature
    
    def _get_property_value(self, node: Dict, property_key: str) -> Optional[str]:
        """Get property value from a node."""
        for prop in node.get("properties", []):
            if property_key in str(prop.get("property", {}).get("key", "")):
                return prop.get("value")
        return None
    
    def _get_containment_children(self, node: Dict, containment_key: str) -> List:
        """Get children from a containment."""
        for cont in node.get("containments", []):
            if containment_key in str(cont.get("containment", {}).get("key", "")):
                children = cont.get("children", [])
                # Resolve children if they're IDs
                resolved = []
                for child in children:
                    if isinstance(child, str):
                        # Find the actual node
                        for n in self.m2_model.get("nodes", []):
                            if n.get("id") == child:
                                resolved.append(n)
                                break
                    else:
                        resolved.append(child)
                return resolved
        return []
    
    def _convert_nl_mappings_to_connector_format(self) -> Dict:
        """Convert NL mappings to connector.yml-like format for compatibility."""
        connector = {"domain_name": self.domain.title(), "actions": {}}
        
        for mapping_node in self.nl_mappings.get("nodes", []):
            if mapping_node.get("classifier", {}).get("key") == "ConceptMapping":
                # Get the target concept
                target_key = self._get_property_value(mapping_node, "targetConceptKey")
                nl_phrases = json.loads(self._get_property_value(mapping_node, "nlPhrases") or "[]")
                description = self._get_property_value(mapping_node, "description")
                
                # Create action for each phrase (simplified)
                for phrase in nl_phrases:
                    action_name = f"create_{phrase.replace(' ', '_').lower()}"
                    connector["actions"][action_name] = {
                        "description": description or f"Create a {phrase}",
                        "parameters": {}
                    }
                    
                    # Add property mappings
                    for prop_mapping in self._get_containment_children(mapping_node, "propertyMappings"):
                        prop_key = self._get_property_value(prop_mapping, "targetPropertyKey")
                        prop_prompt = self._get_property_value(prop_mapping, "nlPrompt")
                        prop_required = self._get_property_value(prop_mapping, "required") == "true"
                        
                        # Map to parameter name
                        param_name = self._property_key_to_param_name(prop_key)
                        connector["actions"][action_name]["parameters"][param_name] = {
                            "description": prop_prompt or f"Value for {param_name}",
                            "clarification_prompt": prop_prompt,
                            "required": prop_required
                        }
        
        # Add find actions
        connector["actions"]["find_shapes"] = {
            "description": "Search for shapes",
            "parameters": {
                "shape_type": {
                    "description": "Type of shape to find (circle, line, etc.)",
                    "clarification_prompt": "What type of shape are you looking for?"
                }
            }
        }
        
        return connector
    
    def _property_key_to_param_name(self, prop_key: str) -> str:
        """Convert property key to parameter name."""
        # Special cases
        if "INamed-name" in prop_key:
            return "name"
        if prop_key == "key-r":
            return "radius"
        if prop_key == "key-x":
            return "x"
        if prop_key == "key-y":
            return "y"
        if prop_key == "key-z":
            return "z"
        
        # Default: use last part of key
        return prop_key.replace("key-", "").replace("-", "_")
    
    def load_mappings(self) -> Dict[str, Any]:
        """Return connector-format mappings for compatibility."""
        return self.connector_format
    
    def get_schema(self) -> Dict[str, Any]:
        """Convert M2 concepts to schema format."""
        schema = {}
        
        for action_name, action_data in self.connector_format.get("actions", {}).items():
            # Simplified schema from action data
            required = [p for p, d in action_data.get("parameters", {}).items() 
                       if d.get("required", False)]
            optional = [p for p, d in action_data.get("parameters", {}).items() 
                       if not d.get("required", False)]
            
            schema[action_name] = {
                "dsl_syntax": action_name,  # Not used for LionWeb but needed for compatibility
                "required": required,
                "optional": optional,
                "param_types": {
                    p: {"type": "string"}  # Simplified - could infer from M2
                    for p in action_data.get("parameters", {})
                },
                "permissions": ["admin", "scheduler"],  # Default permissions
                "is_read_only": "find" in action_name
            }
        
        return schema
    
    def validate_params(self, action: str, params: Dict[str, Any], role: str) -> Dict[str, Any]:
        """Validate parameters against M2 schema."""
        schema = self.get_schema()
        
        if action not in schema:
            return {
                'valid': False,
                'missing': [],
                'errors': [f"Unknown action: {action}"]
            }
        
        action_schema = schema[action]
        required = action_schema.get("required", [])
        missing = [p for p in required if p not in params or params[p] in [None, "", "unknown"]]
        
        return {
            'valid': len(missing) == 0,
            'missing': missing,
            'errors': []
        }
    
    def build_artifact(self, task_details: Dict[str, Any], role: str) -> str:
        """Build LionWeb M1 instance JSON."""
        action = task_details.get("action", "")
        params = task_details.get("parameters", {})
        
        # Determine concept type from action
        if "circle" in action:
            return self._build_circle_instance(params)
        elif "line" in action:
            return self._build_line_instance(params)
        else:
            # Generic shape - for now just create a circle
            return self._build_circle_instance(params)
    
    def _build_circle_instance(self, params: Dict) -> str:
        """Build a Circle M1 instance."""
        instance_id = f"circle-{uuid.uuid4().hex[:8]}"
        coord_id = f"coord-{uuid.uuid4().hex[:8]}"
        
        instance = {
            "id": instance_id,
            "classifier": {
                "language": "Shapes",
                "version": "1",
                "key": "key-Circle"
            },
            "properties": [
                {
                    "property": {"key": "key-r"},
                    "value": params.get("radius", 10)
                },
                {
                    "property": {"key": "LionCore-builtins-INamed-name"},
                    "value": params.get("name", f"Circle_{instance_id}")
                },
                {
                    "property": {"key": "key-uuid"},
                    "value": str(uuid.uuid4())
                }
            ],
            "containments": [
                {
                    "containment": {"key": "key-center"},
                    "children": [{
                        "id": coord_id,
                        "classifier": {"key": "key-Coord"},
                        "properties": [
                            {"property": {"key": "key-x"}, "value": params.get("x", 0)},
                            {"property": {"key": "key-y"}, "value": params.get("y", 0)},
                            {"property": {"key": "key-z"}, "value": params.get("z", 0)}
                        ]
                    }]
                }
            ]
        }
        
        return json.dumps(instance, indent=2)
    
    def _build_line_instance(self, params: Dict) -> str:
        """Build a Line M1 instance."""
        instance_id = f"line-{uuid.uuid4().hex[:8]}"
        start_coord_id = f"coord-{uuid.uuid4().hex[:8]}"
        end_coord_id = f"coord-{uuid.uuid4().hex[:8]}"
        
        instance = {
            "id": instance_id,
            "classifier": {
                "language": "Shapes",
                "version": "1",
                "key": "key-Line"
            },
            "properties": [
                {
                    "property": {"key": "LionCore-builtins-INamed-name"},
                    "value": params.get("name", f"Line_{instance_id}")
                },
                {
                    "property": {"key": "key-uuid"},
                    "value": str(uuid.uuid4())
                }
            ],
            "containments": [
                {
                    "containment": {"key": "key-start"},
                    "children": [{
                        "id": start_coord_id,
                        "classifier": {"key": "key-Coord"},
                        "properties": [
                            {"property": {"key": "key-x"}, "value": params.get("start_x", 0)},
                            {"property": {"key": "key-y"}, "value": params.get("start_y", 0)},
                            {"property": {"key": "key-z"}, "value": params.get("start_z", 0)}
                        ]
                    }]
                },
                {
                    "containment": {"key": "key-end"},
                    "children": [{
                        "id": end_coord_id,
                        "classifier": {"key": "key-Coord"},
                        "properties": [
                            {"property": {"key": "key-x"}, "value": params.get("end_x", 10)},
                            {"property": {"key": "key-y"}, "value": params.get("end_y", 10)},
                            {"property": {"key": "key-z"}, "value": params.get("end_z", 0)}
                        ]
                    }]
                }
            ]
        }
        
        return json.dumps(instance, indent=2)
    
    def execute(self, artifact: str, role: str, task_details: Dict[str, Any]) -> Dict[str, Any]:
        """Execute by adding/querying M1 instances."""
        action = task_details.get("action", "")
        
        if "find" in action:
            # Query operation
            return self._execute_query(task_details)
        else:
            # Create operation
            return self._execute_create(artifact)
    
    def _execute_create(self, artifact: str) -> Dict[str, Any]:
        """Add M1 instance to in-memory store."""
        try:
            instance = json.loads(artifact)
            self.m1_instances.append(instance)
            
            shape_name = None
            for prop in instance.get("properties", []):
                if "INamed-name" in str(prop.get("property", {}).get("key", "")):
                    shape_name = prop.get("value")
                    break
            
            return {
                "status": "success",
                "message": f"Successfully created shape: {shape_name or instance.get('id')}",
                "new_state": {"shapes": self.m1_instances},
                "action_type": "mutation"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to create shape: {e}"
            }
    
    def _execute_query(self, task_details: Dict) -> Dict[str, Any]:
        """Query M1 instances."""
        params = task_details.get("parameters", {})
        shape_type = params.get("shape_type", "").lower()
        
        results = []
        for instance in self.m1_instances:
            # Check if matches shape type
            classifier_key = instance.get("classifier", {}).get("key", "")
            
            if not shape_type or shape_type in classifier_key.lower():
                # Extract display info
                shape_info = {"type": classifier_key.replace("key-", "")}
                
                for prop in instance.get("properties", []):
                    prop_key = prop.get("property", {}).get("key", "")
                    if "INamed-name" in prop_key:
                        shape_info["name"] = prop.get("value")
                    elif prop_key == "key-r":
                        shape_info["radius"] = prop.get("value")
                    elif prop_key == "key-uuid":
                        shape_info["uuid"] = prop.get("value")
                
                results.append(shape_info)
        
        return {
            "status": "success",
            "message": f"Found {len(results)} shape(s)",
            "results": results,
            "action_type": "query"
        }
    
    def get_state(self) -> Dict[str, Any]:
        """Get current state (M1 instances)."""
        return {"shapes": self.m1_instances}
    
    def save_state(self, state: Dict[str, Any]):
        """Update in-memory state."""
        self.m1_instances = state.get("shapes", [])
    
    def get_state_manager(self):
        """Return self as state manager for backward compatibility."""
        return self
    
    def load(self) -> Dict[str, Any]:
        """Load method for state manager compatibility."""
        return self.get_state()
    
    def save(self, state: Dict[str, Any]):
        """Save method for state manager compatibility."""
        self.save_state(state)