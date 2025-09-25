# src/lionweb_engine/connector_loader_lionweb.py
"""
LionWeb Connector Loader using the actual lionweb-python library for serialization.
"""

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any

# Correct imports based on the debug output
from lionweb.language import Language, Concept, Property, Containment, Reference
from lionweb.language.lioncore_builtins import LionCoreBuiltins
from lionweb.model import DynamicNode
from lionweb.serialization import create_standard_json_serialization
from lionweb.utils import root


class LionWebConnectorLoader:
    """Loads LionWeb M2 languages and M1 instances using the lionweb-python library."""
    
    def __init__(self, project_root: Path = None):
        """Initialize the connector loader.
        
        Args:
            project_root: Path to project root. Defaults to current directory.
        """
        self.project_root = project_root or Path.cwd()
        self.domains_dir = self.project_root / "src" / "domains"
        self.model_store_dir = self.project_root / "model_store"
        
        # Storage for loaded artifacts
        self.languages: Dict[str, Language] = {}
        self.concepts: Dict[str, Concept] = {}
        self.m1_connectors: Dict[str, Any] = {}
        self.m1_models: Dict[str, List[DynamicNode]] = {}
        
        # Serialization handler
        self.serialization = create_standard_json_serialization()
        self.serialization.enable_dynamic_nodes()
        
        # Create necessary directories
        self.model_store_dir.mkdir(parents=True, exist_ok=True)
        
        # Load the cycling language from file, creating it if it doesn't exist.
        self._init_cycling_language_from_file()
    
    def _init_cycling_language_from_file(self):
        """
        Ensures the cycling M2 language JSON exists, and then loads it.
        If the file doesn't exist, it's generated and saved first.
        """
        domain_path = self.domains_dir / "cycling"
        domain_path.mkdir(exist_ok=True) # Ensure the domain directory exists
        language_file_path = domain_path / "cycling_m2.json"

        if not language_file_path.exists():
            self._generate_and_save_cycling_m2(language_file_path)

        with open(language_file_path, 'r', encoding='utf-8') as f:
            json_str = f.read()

        # Deserialize the language definition
        nodes = self.serialization.deserialize_string_to_nodes(json_str)
        language_node = next((n for n in nodes if isinstance(n, Language)), None)
        
        if not language_node:
            raise ValueError("Could not find a Language node in cycling_m2.json")
        
        # Store the language and its concepts for runtime use
        self.languages["cycling"] = language_node
        for element in language_node.elements:
            if isinstance(element, Concept):
                self.concepts[element.name] = element
    
    def _generate_and_save_cycling_m2(self, path: Path):
        """
        Creates the cycling language programmatically and serializes it to a file.
        This is based on the logic from the previous _create_cycling_language method.
        """
        # Create the language
        cycling_lang = Language(
            name="Cycling", key="cycling", id="cycling-lang", version="1.0"
        )
        
        # Create Rider concept
        rider_concept = Concept(
            name="Rider", key="Rider", id="cycling-Rider", abstract=False, partition=False
        )
        rider_name = Property(name="name", key="Rider-name", id="Rider-name-id", type=LionCoreBuiltins.get_string())
        rider_name.optional = False
        rider_age = Property(name="age", key="Rider-age", id="Rider-age-id", type=LionCoreBuiltins.get_integer())
        rider_age.optional = True
        rider_country = Property(name="country", key="Rider-country", id="Rider-country-id", type=LionCoreBuiltins.get_string())
        rider_country.optional = True
        rider_concept.add_feature(rider_name)
        rider_concept.add_feature(rider_age)
        rider_concept.add_feature(rider_country)
        
        # Create Team concept
        team_concept = Concept(
            name="Team", key="Team", id="cycling-Team", abstract=False, partition=False
        )
        team_name = Property(name="name", key="Team-name", id="Team-name-id", type=LionCoreBuiltins.get_string())
        team_name.optional = False
        team_country = Property(name="country", key="Team-country", id="Team-country-id", type=LionCoreBuiltins.get_string())
        team_country.optional = True
        team_budget = Property(name="budget", key="Team-budget", id="Team-budget-id", type=LionCoreBuiltins.get_integer())
        team_budget.optional = True
        team_founded = Property(name="founded", key="Team-founded", id="Team-founded-id", type=LionCoreBuiltins.get_integer())
        team_founded.optional = True
        team_concept.add_feature(team_name)
        team_concept.add_feature(team_country)
        team_concept.add_feature(team_budget)
        team_concept.add_feature(team_founded)
        
        # Create Model concept (root container)
        model_concept = Concept(
            name="Model", key="Model", id="cycling-Model", abstract=False, partition=True
        )
        riders_containment = Containment(name="riders", key="Model-riders", id="Model-riders-id", type=rider_concept, multiple=True, optional=True)
        teams_containment = Containment(name="teams", key="Model-teams", id="Model-teams-id", type=team_concept, multiple=True, optional=True)
        model_concept.add_feature(riders_containment)
        model_concept.add_feature(teams_containment)
        
        # Add concepts to language
        cycling_lang.add_element(model_concept)
        cycling_lang.add_element(rider_concept)
        cycling_lang.add_element(team_concept)
        
        # Serialize the language to a JSON string
        json_str = self.serialization.serialize_tree_to_json_string(cycling_lang)
        
        # Save to the specified file path
        with open(path, 'w', encoding='utf-8') as f:
            f.write(json_str)

    def load_all(self, domain: str = "cycling") -> Dict[str, Any]:
        """Load all LionWeb artifacts for a domain.
        
        Args:
            domain: The domain to load (e.g., 'cycling')
            
        Returns:
            Dictionary containing loaded languages, connectors, and models.
        """
        results = {
            "language": f"Loaded '{domain}' language from domains/{domain}/{domain}_m2.json",
            "connector": None,
            "models": [],
            "errors": []
        }
        
        try:
            # Load domain-specific NL connector (still JSON, not using LionWeb for this)
            connector_path = self.domains_dir / domain / "nl_connector_m1.json"
            if connector_path.exists():
                try:
                    connector = self._load_m1_connector(connector_path)
                    self.m1_connectors[domain] = connector
                    results["connector"] = f"Loaded connector for {domain}"
                except Exception as e:
                    results["errors"].append(f"Error loading connector: {e}")
            
            # Load existing M1 models from model store using LionWeb deserialization
            domain_store = self.model_store_dir / domain
            if domain_store.exists():
                model_file = domain_store / "models.json"
                if model_file.exists():
                    try:
                        self._load_m1_models_lionweb(model_file, domain)
                        results["models"].append(f"Loaded {len(self.m1_models.get(domain, []))} instances")
                    except Exception as e:
                        # Fallback to manual loading if LionWeb deserialization fails
                        results["errors"].append(f"LionWeb deserialization warning: {e}")
                        self._load_m1_models_fallback(model_file, domain)
                        results["models"].append(f"Loaded {len(self.m1_models.get(domain, []))} instances (fallback)")
                        
        except Exception as e:
            results["errors"].append(f"General loading error: {e}")
            
        return results
    
    def create_m1_instance(self, domain: str, concept_name: str, properties: Dict[str, Any]) -> DynamicNode:
        """Create a new M1 instance using LionWeb DynamicNode.
        
        Args:
            domain: The domain (e.g., 'cycling')
            concept_name: The concept type (e.g., 'Rider', 'Team')
            properties: Properties for the instance
            
        Returns:
            The created DynamicNode instance
        """
        concept = self.concepts.get(concept_name)
        if not concept:
            raise ValueError(f"Unknown concept: {concept_name}")
        
        # Create a DynamicNode instance
        instance = DynamicNode(str(uuid.uuid4()), concept)
        
        # Set properties
        for prop_name, prop_value in properties.items():
            if prop_value is not None:
                # Find the property in the concept
                for feature in concept.features:
                    if isinstance(feature, Property) and feature.name == prop_name:
                        instance.set_property_value(feature, prop_value)
                        break
        
        # Store in memory
        if domain not in self.m1_models:
            self.m1_models[domain] = []
        self.m1_models[domain].append(instance)
        
        return instance
    
    def modify_m1_instance(self, domain: str, instance_name: str, properties: Dict[str, Any]) -> Optional[DynamicNode]:
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
            if isinstance(instance, DynamicNode):
                # Get classifier using method (not attribute)
                classifier = instance.get_classifier()
                # Get name property
                for feature in classifier.features:
                    if isinstance(feature, Property) and feature.name == "name":
                        if instance.get_property_value(feature) == instance_name:
                            # Update properties
                            for prop_name, prop_value in properties.items():
                                if prop_value is not None:
                                    for f in classifier.features:
                                        if isinstance(f, Property) and f.name == prop_name:
                                            instance.set_property_value(f, prop_value)
                                            break
                            return instance
        
        return None
    
    def find_m1_instances(self, domain: str, concept_name: str = None, filters: Dict[str, Any] = None) -> List[DynamicNode]:
        """Find M1 instances matching criteria.
        
        Args:
            domain: The domain
            concept_name: Optional concept type filter
            filters: Optional property filters
            
        Returns:
            List of matching instances
        """
        instances = self.m1_models.get(domain, [])
        results = []
        
        for instance in instances:
            if isinstance(instance, DynamicNode):
                # Check concept type using get_classifier()
                if concept_name and instance.get_classifier().name != concept_name:
                    continue
                
                # Check filters
                if filters:
                    match = True
                    for prop_name, expected_value in filters.items():
                        actual_value = self._get_property_from_instance(instance, prop_name)
                        
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
    
    def save_models(self, domain: str):
        """Save current M1 models using LionWeb serialization.
        
        Args:
            domain: The domain to save
        """
        if domain not in self.m1_models:
            return
        
        domain_store = self.model_store_dir / domain
        domain_store.mkdir(parents=True, exist_ok=True)
        
        # Create a Model instance to contain all nodes
        model_concept = self.concepts.get("Model")
        if model_concept:
            model = DynamicNode(str(uuid.uuid4()), model_concept)
            
            # Add riders and teams to the model
            for instance in self.m1_models[domain]:
                if isinstance(instance, DynamicNode):
                    classifier = instance.get_classifier()
                    if classifier.name == "Rider":
                        # Add to riders containment
                        for feature in model_concept.features:
                            if isinstance(feature, Containment) and feature.name == "riders":
                                model.add_child(feature, instance)
                                break
                    elif classifier.name == "Team":
                        # Add to teams containment
                        for feature in model_concept.features:
                            if isinstance(feature, Containment) and feature.name == "teams":
                                model.add_child(feature, instance)
                                break
            
            # Serialize to JSON using LionWeb serialization
            json_str = self.serialization.serialize_tree_to_json_string(model)
            
            # Save to file
            file_path = domain_store / "models.json"
            with open(file_path, 'w') as f:
                f.write(json_str)
    
    # Helper methods
    
    def _get_property_from_instance(self, instance: DynamicNode, prop_name: str) -> Any:
        """Get a property value from a DynamicNode instance."""
        classifier = instance.get_classifier()
        for feature in classifier.features:
            if isinstance(feature, Property) and feature.name == prop_name:
                return instance.get_property_value(feature)
        return None
    
    def _load_m1_connector(self, file_path: Path) -> Dict[str, Any]:
        """Load an M1 connector instance (still using JSON parsing, not LionWeb)."""
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Parse the connector structure manually (this is metadata, not domain instances)
        return self._parse_connector_structure(data)
    
    def _parse_connector_structure(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse connector JSON into a structured format."""
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
        
        # Extract actions and parameters
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
    
    def _load_m1_models_lionweb(self, file_path: Path, domain: str):
        """Load M1 model instances using LionWeb deserialization."""
        with open(file_path, 'r') as f:
            json_str = f.read()
        
        # Deserialize using LionWeb
        nodes = self.serialization.deserialize_string_to_nodes(json_str)
        
        if domain not in self.m1_models:
            self.m1_models[domain] = []
        
        # If we got a model container, extract its children
        if nodes:
            root_node = root(nodes)
            if root_node and isinstance(root_node, DynamicNode):
                classifier = root_node.get_classifier()
                if classifier.name == "Model":
                    # Extract riders and teams from the model
                    for feature in classifier.features:
                        if isinstance(feature, Containment):
                            children = root_node.get_children(feature)
                            self.m1_models[domain].extend(children)
                else:
                    # Not a model container, add directly
                    self.m1_models[domain].extend(nodes)
    
    def _load_m1_models_fallback(self, file_path: Path, domain: str):
        """Fallback: Create DynamicNodes from JSON manually."""
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        if domain not in self.m1_models:
            self.m1_models[domain] = []
        
        # Convert JSON nodes to DynamicNodes
        for node_data in data.get("nodes", []):
            concept_key = node_data.get("classifier", {}).get("key")
            concept = self.concepts.get(concept_key)
            
            if concept:
                instance = DynamicNode(node_data.get("id", str(uuid.uuid4())), concept)
                
                # Set properties
                for prop_data in node_data.get("properties", []):
                    prop_key = prop_data.get("property", {}).get("key", "")
                    value = prop_data.get("value")
                    
                    # Find matching property
                    for feature in concept.features:
                        if isinstance(feature, Property) and f"{concept_key}-{feature.name}" == prop_key:
                            instance.set_property_value(feature, value)
                            break
                
                self.m1_models[domain].append(instance)
    
    def _get_property_value(self, node: Dict, property_key: str, default=None):
        """Extract a property value from a JSON node."""
        for prop in node.get("properties", []):
            if prop.get("property", {}).get("key") == property_key:
                return prop.get("value", default)
        return default
    
    def _get_containment_children(self, node: Dict, containment_key: str) -> List[str]:
        """Extract children IDs from a containment."""
        for containment in node.get("containments", []):
            if containment.get("containment", {}).get("key") == containment_key:
                return containment.get("children", [])
        return []