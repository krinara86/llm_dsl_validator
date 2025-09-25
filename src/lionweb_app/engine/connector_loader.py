"""
Main LionWeb runtime engine. Loads languages and models, and provides an API
for creating, modifying, and persisting model instances.
"""

import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any

from lionweb.language import Language, Concept, Property, Containment
from lionweb.model import DynamicNode
from lionweb.serialization import create_standard_json_serialization
from lionweb.utils import root

# Import the new generator functions
from .language_generators import generate_and_save_cycling_m2, generate_and_save_nl_mappings_m2
from .m1_connector_generator import generate_and_save_connector_m1


class LionWebConnectorLoader:
    """Loads LionWeb languages and models, and manages M1 instances."""
    
    def __init__(self, project_root: Path = None):
        """Initialize the connector loader."""
        self.project_root = project_root or Path.cwd()
        self.languages_dir = self.project_root / "src" / "lionweb_app" / "languages"
        self.domains_dir = self.project_root / "src" / "domains"
        self.model_store_dir = self.project_root / "model_store"
        
        self.languages: Dict[str, Language] = {}
        self.concepts: Dict[str, Concept] = {}
        self.m1_connectors: Dict[str, DynamicNode] = {}
        self.m1_models: Dict[str, List[DynamicNode]] = {}
        
        self.serialization = create_standard_json_serialization()
        self.serialization.enable_dynamic_nodes()
        
        self.model_store_dir.mkdir(parents=True, exist_ok=True)
        self.languages_dir.mkdir(parents=True, exist_ok=True)
        
        self._init_languages()

    def _init_languages(self):
        """Initializes all languages by loading them from files or generating them."""
        self._initialize_language("cycling", self.languages_dir, generate_and_save_cycling_m2)
        self._initialize_language("nl_mappings", self.languages_dir, generate_and_save_nl_mappings_m2)

    def _initialize_language(self, domain: str, path: Path, generator_func):
        """Generic method to initialize a language from a file or generate it."""
        path.mkdir(exist_ok=True)
        language_file_path = path / f"{domain}_m2.json"

        if not language_file_path.exists():
            generator_func(language_file_path, self.serialization)

        with open(language_file_path, 'r', encoding='utf-8') as f:
            json_str = f.read()

        nodes = self.serialization.deserialize_string_to_nodes(json_str)
        language_node = next((n for n in nodes if isinstance(n, Language)), None)
        
        if not language_node:
            raise ValueError(f"Could not find a Language node in {language_file_path.name}")
        
        self.serialization.register_language(language_node)
        
        self.languages[domain] = language_node
        for element in language_node.elements:
            if isinstance(element, Concept):
                self.concepts[element.name] = element

    def generate_connector_m1(self, domain: str):
        """Generates the M1 connector file for a given domain."""
        file_path = self.domains_dir / domain / "nl_connector_m1.json"
        generate_and_save_connector_m1(file_path, self.serialization, self.concepts)
        print(f"   ✅ '{file_path.name}' was generated successfully.")

    def load_all(self, domain: str = "cycling") -> Dict[str, Any]:
        """Load all LionWeb artifacts for a domain."""
        results = {"connector": None, "models": [], "errors": []}
        
        try:
            connector_path = self.domains_dir / domain / "nl_connector_m1.json"
            if connector_path.exists():
                try:
                    with open(connector_path, 'r', encoding='utf-8') as f:
                        json_str = f.read()
                    
                    nodes = self.serialization.deserialize_string_to_nodes(json_str)
                    connector_node = next((n for n in nodes if isinstance(n, DynamicNode) and n.get_classifier().name == "Connector"), None)
                    
                    if connector_node:
                        self.m1_connectors[domain] = connector_node
                        results["connector"] = f"Loaded and validated connector for {domain}"
                except Exception as e:
                    results["errors"].append(f"Error validating connector '{connector_path.name}': {e}")
            
            domain_store = self.model_store_dir / domain
            if domain_store.exists():
                model_file = domain_store / "models.json"
                if model_file.exists():
                    try:
                        self._load_m1_models_lionweb(model_file, domain)
                        results["models"].append(f"Loaded {len(self.m1_models.get(domain, []))} instances")
                    except Exception as e:
                        results["errors"].append(f"LionWeb deserialization warning: {e}")
                        
        except Exception as e:
            results["errors"].append(f"General loading error: {e}")
            
        return results
    
    def create_m1_instance(self, domain: str, concept_name: str, properties: Dict[str, Any]) -> DynamicNode:
        """Create a new M1 instance using LionWeb DynamicNode."""
        concept = self.concepts.get(concept_name)
        if not concept:
            raise ValueError(f"Unknown concept: {concept_name}")
        
        instance = DynamicNode(str(uuid.uuid4()), concept)
        
        for prop_name, prop_value in properties.items():
            if prop_value is not None:
                feature = concept.get_feature_by_name(prop_name)
                if isinstance(feature, Property):
                    instance.set_property_value(feature, prop_value)
        
        if domain not in self.m1_models:
            self.m1_models[domain] = []
        self.m1_models[domain].append(instance)
        
        return instance
    
    def modify_m1_instance(self, domain: str, instance_name: str, properties: Dict[str, Any]) -> Optional[DynamicNode]:
        """Modify an existing M1 instance."""
        for instance in self.m1_models.get(domain, []):
            if isinstance(instance, DynamicNode):
                classifier = instance.get_classifier()
                name_prop = classifier.get_feature_by_name("name")
                if name_prop and instance.get_property_value(name_prop) == instance_name:
                    for prop_name, prop_value in properties.items():
                        if prop_value is not None:
                            feature = classifier.get_feature_by_name(prop_name)
                            if isinstance(feature, Property):
                                instance.set_property_value(feature, prop_value)
                    return instance
        return None
    
    def find_m1_instances(self, domain: str, concept_name: str = None, filters: Dict[str, Any] = None) -> List[DynamicNode]:
        """Find M1 instances matching criteria."""
        instances = self.m1_models.get(domain, [])
        results = []
        
        for instance in instances:
            if not isinstance(instance, DynamicNode): continue
            
            if concept_name and instance.get_classifier().name != concept_name: continue
            
            if filters:
                match = all(
                    self._get_property_from_instance(instance, prop_name) == expected_value
                    for prop_name, expected_value in filters.items()
                )
                if not match: continue
            
            results.append(instance)
        
        return results
    
    def save_models(self, domain: str):
        """Save current M1 models using LionWeb serialization."""
        if domain not in self.m1_models: return
        
        domain_store = self.model_store_dir / domain
        domain_store.mkdir(parents=True, exist_ok=True)
        
        model_concept = self.concepts.get("Model")
        if not model_concept: return

        model = DynamicNode(str(uuid.uuid4()), model_concept)
        riders_containment = model_concept.get_feature_by_name("riders")
        teams_containment = model_concept.get_feature_by_name("teams")

        for instance in self.m1_models[domain]:
            classifier_name = instance.get_classifier().name
            if classifier_name == "Rider" and riders_containment:
                model.add_child(riders_containment, instance)
            elif classifier_name == "Team" and teams_containment:
                model.add_child(teams_containment, instance)
        
        json_str = self.serialization.serialize_tree_to_json_string(model)
        
        file_path = domain_store / "models.json"
        with open(file_path, 'w') as f:
            f.write(json_str)
    
    def _get_property_from_instance(self, instance: DynamicNode, prop_name: str) -> Any:
        """Get a property value from a DynamicNode instance."""
        feature = instance.get_classifier().get_feature_by_name(prop_name)
        if isinstance(feature, Property):
            return instance.get_property_value(feature)
        return None

    def _load_m1_models_lionweb(self, file_path: Path, domain: str):
        """Load M1 model instances using LionWeb deserialization."""
        with open(file_path, 'r') as f:
            json_str = f.read()
        
        nodes = self.serialization.deserialize_string_to_nodes(json_str)
        
        if domain not in self.m1_models:
            self.m1_models[domain] = []
        
        if nodes:
            root_node = root(nodes)
            if root_node and root_node.get_classifier().name == "Model":
                for feature in root_node.get_classifier().features:
                    if isinstance(feature, Containment):
                        self.m1_models[domain].extend(root_node.get_children(feature))