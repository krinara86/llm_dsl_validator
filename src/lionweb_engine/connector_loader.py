# src/lionweb_engine/connector_loader.py
"""
LionWeb Connector Loader for loading M2 languages and M1 instances.
"""

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any

# Note: For this demo, we'll work with raw JSON since the lionweb-python 
# library structure varies between versions. In production, you would
# import the appropriate classes based on your installed version.


class LionWebConnectorLoader:
    """Loads LionWeb M2 languages and M1 instances for the conversational DSL framework."""
    
    def __init__(self, project_root: Path = None):
        """Initialize the connector loader.
        
        Args:
            project_root: Path to project root. Defaults to current directory.
        """
        self.project_root = project_root or Path.cwd()
        self.languages_dir = self.project_root / "src" / "lionweb" / "languages"
        self.domains_dir = self.project_root / "src" / "domains"
        self.model_store_dir = self.project_root / "model_store"
        
        # Storage for loaded artifacts
        self.m2_languages: Dict[str, Any] = {}
        self.m1_connectors: Dict[str, Any] = {}
        self.m1_models: Dict[str, List[Dict]] = {}  # Store as dictionaries
        
        # Create necessary directories
        self.model_store_dir.mkdir(parents=True, exist_ok=True)
        
    def load_all(self, domain: str = "cycling") -> Dict[str, Any]:
        """Load all LionWeb artifacts for a domain.
        
        Args:
            domain: The domain to load (e.g., 'cycling')
            
        Returns:
            Dictionary containing loaded languages, connectors, and models.
        """
        results = {
            "m2_languages": {},
            "connector": None,
            "models": [],
            "errors": []
        }
        
        try:
            # Load M2 metamodels
            for m2_file in self.languages_dir.glob("*.json"):
                try:
                    language = self._load_m2_file(m2_file)
                    language_key = m2_file.stem
                    self.m2_languages[language_key] = language
                    results["m2_languages"][language_key] = f"Loaded {m2_file.name}"
                except Exception as e:
                    results["errors"].append(f"Error loading {m2_file.name}: {e}")
            
            # Load domain-specific NL connector
            connector_path = self.domains_dir / domain / "nl_connector_m1.json"
            if connector_path.exists():
                try:
                    connector = self._load_m1_connector(connector_path)
                    self.m1_connectors[domain] = connector
                    results["connector"] = f"Loaded connector for {domain}"
                except Exception as e:
                    results["errors"].append(f"Error loading connector: {e}")
            
            # Load existing M1 models from model store
            domain_store = self.model_store_dir / domain
            if domain_store.exists():
                for model_file in domain_store.glob("*.json"):
                    try:
                        models = self._load_m1_models(model_file)
                        self.m1_models.setdefault(domain, []).extend(models)
                        results["models"].append(f"Loaded {model_file.name}")
                    except Exception as e:
                        results["errors"].append(f"Error loading model {model_file.name}: {e}")
                        
        except Exception as e:
            results["errors"].append(f"General loading error: {e}")
            
        return results
    
    def _load_m2_file(self, file_path: Path) -> Dict[str, Any]:
        """Load an M2 metamodel file.
        
        Args:
            file_path: Path to the M2 JSON file
            
        Returns:
            Parsed M2 language data
        """
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        # Validate format version
        if data.get("serializationFormatVersion") != "2024.1":
            raise ValueError(f"Unsupported format version in {file_path}")
            
        return data
    
    def _load_m1_connector(self, file_path: Path) -> Dict[str, Any]:
        """Load an M1 connector instance.
        
        Args:
            file_path: Path to the M1 connector JSON file
            
        Returns:
            Parsed connector data with action mappings
        """
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        # Parse the connector structure
        connector = self._parse_connector_structure(data)
        return connector
    
    def _parse_connector_structure(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse connector JSON into a structured format.
        
        Args:
            data: Raw JSON data
            
        Returns:
            Structured connector dictionary
        """
        nodes_by_id = {node["id"]: node for node in data.get("nodes", [])}
        
        # Find the connector root node
        connector_node = None
        for node in data.get("nodes", []):
            if node.get("classifier", {}).get("key") == "Connector":
                connector_node = node
                break
                
        if not connector_node:
            raise ValueError("No Connector node found in file")
        
        # Extract connector properties
        connector_data = {
            "domain_name": self._get_property_value(connector_node, "Connector-domainName"),
            "target_language": self._get_property_value(connector_node, "Connector-targetLanguage"),
            "actions": {}
        }
        
        # Extract actions
        actions_containment = self._get_containment_children(connector_node, "Connector-actions")
        for action_id in actions_containment:
            action_node = nodes_by_id.get(action_id)
            if action_node:
                action_name = self._get_property_value(action_node, "ActionMapping-actionName")
                action_data = {
                    "target_concept": self._get_property_value(action_node, "ActionMapping-targetConcept"),
                    "description": self._get_property_value(action_node, "ActionMapping-description"),
                    "parameters": {}
                }
                
                # Extract parameters
                params_containment = self._get_containment_children(action_node, "ActionMapping-parameters")
                for param_id in params_containment:
                    param_node = nodes_by_id.get(param_id)
                    if param_node:
                        param_name = self._get_property_value(param_node, "ParameterMapping-parameterName")
                        param_data = {
                            "target_feature": self._get_property_value(param_node, "ParameterMapping-targetFeature"),
                            "description": self._get_property_value(param_node, "ParameterMapping-description"),
                            "clarification_prompt": self._get_property_value(param_node, "ParameterMapping-clarificationPrompt"),
                            "required": self._get_property_value(param_node, "ParameterMapping-required", False)
                        }
                        action_data["parameters"][param_name] = param_data
                
                connector_data["actions"][action_name] = action_data
        
        return connector_data
    
    def _load_m1_models(self, file_path: Path) -> List[Dict]:
        """Load M1 model instances from a file.
        
        Args:
            file_path: Path to the M1 model JSON file
            
        Returns:
            List of loaded model nodes as dictionaries
        """
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        # Return raw dictionary data
        return data.get("nodes", [])
    
    def _get_property_value(self, node: Dict, property_key: str, default=None):
        """Extract a property value from a node.
        
        Args:
            node: The node dictionary
            property_key: The property key to look for
            default: Default value if property not found
            
        Returns:
            The property value or default
        """
        for prop in node.get("properties", []):
            if prop.get("property", {}).get("key") == property_key:
                return prop.get("value", default)
        return default
    
    def _get_containment_children(self, node: Dict, containment_key: str) -> List[str]:
        """Extract children IDs from a containment.
        
        Args:
            node: The node dictionary
            containment_key: The containment key to look for
            
        Returns:
            List of child IDs
        """
        for containment in node.get("containments", []):
            if containment.get("containment", {}).get("key") == containment_key:
                return containment.get("children", [])
        return []
    
    def create_m1_instance(self, domain: str, concept: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new M1 instance for a concept.
        
        Args:
            domain: The domain (e.g., 'cycling')
            concept: The concept type (e.g., 'Rider', 'Team')
            properties: Properties for the instance
            
        Returns:
            The created M1 instance as a dictionary
        """
        instance_id = str(uuid.uuid4())
        
        instance = {
            "id": instance_id,
            "classifier": {
                "language": domain,
                "version": "1",
                "key": concept
            },
            "properties": [],
            "containments": [],
            "references": [],
            "parent": None
        }
        
        # Add properties
        for prop_name, prop_value in properties.items():
            if prop_value is not None:
                instance["properties"].append({
                    "property": {
                        "language": domain,
                        "version": "1",
                        "key": f"{concept}-{prop_name}"
                    },
                    "value": prop_value
                })
        
        # Store in memory
        if domain not in self.m1_models:
            self.m1_models[domain] = []
        self.m1_models[domain].append(instance)
        
        return instance
    
    def modify_m1_instance(self, domain: str, instance_name: str, properties: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Modify an existing M1 instance.
        
        Args:
            domain: The domain
            instance_name: Name of the instance to modify
            properties: Properties to update
            
        Returns:
            The modified instance or None if not found
        """
        instances = self.m1_models.get(domain, [])
        
        for instance in instances:
            # Find instance by name property
            name_value = self._get_instance_property(instance, "name")
            if name_value == instance_name:
                # Update properties
                for prop_name, prop_value in properties.items():
                    if prop_value is not None:
                        self._set_instance_property(instance, prop_name, prop_value)
                return instance
        
        return None
    
    def find_m1_instances(self, domain: str, concept: str = None, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Find M1 instances matching criteria.
        
        Args:
            domain: The domain
            concept: Optional concept type filter
            filters: Optional property filters
            
        Returns:
            List of matching instances
        """
        instances = self.m1_models.get(domain, [])
        results = []
        
        for instance in instances:
            # Check concept type
            if concept and instance.get("classifier", {}).get("key") != concept:
                continue
            
            # Check filters
            if filters:
                match = True
                for prop_name, expected_value in filters.items():
                    actual_value = self._get_instance_property(instance, prop_name)
                    if "pattern" in prop_name and expected_value:
                        # Pattern matching for search
                        if not actual_value or expected_value.lower() not in str(actual_value).lower():
                            match = False
                            break
                    elif actual_value != expected_value:
                        match = False
                        break
                
                if not match:
                    continue
            
            results.append(instance)
        
        return results
    
    def _get_instance_property(self, instance: Dict, prop_name: str) -> Any:
        """Get a property value from an instance.
        
        Args:
            instance: The instance dictionary
            prop_name: The property name
            
        Returns:
            The property value or None
        """
        for prop in instance.get("properties", []):
            prop_key = prop.get("property", {}).get("key", "")
            if prop_key.endswith(f"-{prop_name}"):
                return prop.get("value")
        return None
    
    def _set_instance_property(self, instance: Dict, prop_name: str, value: Any):
        """Set a property value on an instance.
        
        Args:
            instance: The instance dictionary
            prop_name: The property name
            value: The new value
        """
        concept = instance.get("classifier", {}).get("key")
        prop_key = f"{concept}-{prop_name}"
        
        # Update existing property or add new one
        for prop in instance.get("properties", []):
            if prop.get("property", {}).get("key") == prop_key:
                prop["value"] = value
                return
        
        # Property not found, add it
        instance["properties"].append({
            "property": {
                "language": instance.get("classifier", {}).get("language"),
                "version": instance.get("classifier", {}).get("version"),
                "key": prop_key
            },
            "value": value
        })
    
    def save_models(self, domain: str):
        """Save current M1 models to the model store.
        
        Args:
            domain: The domain to save
        """
        if domain not in self.m1_models:
            return
        
        domain_store = self.model_store_dir / domain
        domain_store.mkdir(parents=True, exist_ok=True)
        
        # Save as a single file for simplicity
        file_path = domain_store / "models.json"
        
        data = {
            "serializationFormatVersion": "2024.1",
            "languages": [{"key": domain, "version": "1"}],
            "nodes": self.m1_models[domain]
        }
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)