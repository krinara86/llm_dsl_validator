# src/lionweb_app/engine/connector_loader_lionweb.py
"""
LionWeb Connector Loader using the actual lionweb-python library for serialization.
"""

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any

from lionweb.language import Language, Concept, Property, Containment
from lionweb.language.lioncore_builtins import LionCoreBuiltins
from lionweb.model import DynamicNode
from lionweb.serialization import create_standard_json_serialization
from lionweb.utils import root


class LionWebConnectorLoader:
    """Loads LionWeb M2 languages and M1 instances using the lionweb-python library."""
    
    def __init__(self, project_root: Path = None):
        """Initialize the connector loader."""
        self.project_root = project_root or Path.cwd()
        # --- CHANGE: Update path to new package name ---
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
        
        self._init_cycling_language_from_file()
        self._init_nl_mappings_language_from_file()

    def _init_cycling_language_from_file(self):
        """Initializes the cycling language."""
        self._initialize_language("cycling", self.languages_dir, self._generate_and_save_cycling_m2)

    def _init_nl_mappings_language_from_file(self):
        """Initializes the nl_mappings language."""
        self._initialize_language("nl_mappings", self.languages_dir, self._generate_and_save_nl_mappings_m2)

    def _initialize_language(self, domain: str, path: Path, generator_func):
        """Generic method to initialize a language from a file or generate it."""
        path.mkdir(exist_ok=True)
        language_file_path = path / f"{domain}_m2.json"

        if not language_file_path.exists():
            generator_func(language_file_path)

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
    
    def _generate_and_save_cycling_m2(self, path: Path):
        """Creates the cycling language programmatically using UUIDs for IDs."""
        cycling_lang = Language(name="Cycling", key="cycling", id=str(uuid.uuid4()), version="1.0")
        
        rider_concept = Concept(name="Rider", key="Rider", id=str(uuid.uuid4()), abstract=False, partition=False)
        rider_name = Property(name="name", key="Rider-name", id=str(uuid.uuid4()), type=LionCoreBuiltins.get_string())
        rider_name.optional = False
        rider_age = Property(name="age", key="Rider-age", id=str(uuid.uuid4()), type=LionCoreBuiltins.get_integer())
        rider_age.optional = True
        rider_country = Property(name="country", key="Rider-country", id=str(uuid.uuid4()), type=LionCoreBuiltins.get_string())
        rider_country.optional = True
        rider_concept.add_feature(rider_name)
        rider_concept.add_feature(rider_age)
        rider_concept.add_feature(rider_country)
        
        team_concept = Concept(name="Team", key="Team", id=str(uuid.uuid4()), abstract=False, partition=False)
        team_name = Property(name="name", key="Team-name", id=str(uuid.uuid4()), type=LionCoreBuiltins.get_string())
        team_name.optional = False
        team_country = Property(name="country", key="Team-country", id=str(uuid.uuid4()), type=LionCoreBuiltins.get_string())
        team_country.optional = True
        team_budget = Property(name="budget", key="Team-budget", id=str(uuid.uuid4()), type=LionCoreBuiltins.get_integer())
        team_budget.optional = True
        team_founded = Property(name="founded", key="Team-founded", id=str(uuid.uuid4()), type=LionCoreBuiltins.get_integer())
        team_founded.optional = True
        team_concept.add_feature(team_name)
        team_concept.add_feature(team_country)
        team_concept.add_feature(team_budget)
        team_concept.add_feature(team_founded)
        
        model_concept = Concept(name="Model", key="Model", id=str(uuid.uuid4()), abstract=False, partition=True)
        riders_containment = Containment(name="riders", key="Model-riders", id=str(uuid.uuid4()), type=rider_concept, multiple=True, optional=True)
        teams_containment = Containment(name="teams", key="Model-teams", id=str(uuid.uuid4()), type=team_concept, multiple=True, optional=True)
        model_concept.add_feature(riders_containment)
        model_concept.add_feature(teams_containment)
        
        cycling_lang.add_element(model_concept)
        cycling_lang.add_element(rider_concept)
        cycling_lang.add_element(team_concept)
        
        json_str = self.serialization.serialize_tree_to_json_string(cycling_lang)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(json_str)

    def _generate_and_save_nl_mappings_m2(self, path: Path):
        """Creates the NL Mappings language programmatically using UUIDs for IDs."""
        nl_lang = Language(name="NLMappings", key="nl_mappings", id=str(uuid.uuid4()), version="1")

        string_type = LionCoreBuiltins.get_string()
        boolean_type = LionCoreBuiltins.get_boolean()

        connector_concept = Concept(name="Connector", key="Connector", id=str(uuid.uuid4()), abstract=False, partition=True)
        action_mapping_concept = Concept(name="ActionMapping", key="ActionMapping", id=str(uuid.uuid4()), abstract=False, partition=False)
        param_mapping_concept = Concept(name="ParameterMapping", key="ParameterMapping", id=str(uuid.uuid4()), abstract=False, partition=False)

        prop_domain_name = Property(name="domainName", key="Connector-domainName", id=str(uuid.uuid4()), type=string_type)
        prop_domain_name.optional = False
        prop_target_lang = Property(name="targetLanguage", key="Connector-targetLanguage", id=str(uuid.uuid4()), type=string_type)
        prop_target_lang.optional = False
        cont_actions = Containment(name="actions", key="Connector-actions", id=str(uuid.uuid4()), type=action_mapping_concept, multiple=True, optional=True)
        connector_concept.add_feature(prop_domain_name)
        connector_concept.add_feature(prop_target_lang)
        connector_concept.add_feature(cont_actions)

        prop_action_name = Property(name="actionName", key="ActionMapping-actionName", id=str(uuid.uuid4()), type=string_type)
        prop_action_name.optional = False
        prop_target_concept = Property(name="targetConcept", key="ActionMapping-targetConcept", id=str(uuid.uuid4()), type=string_type)
        prop_target_concept.optional = False
        prop_action_desc = Property(name="description", key="ActionMapping-description", id=str(uuid.uuid4()), type=string_type)
        prop_action_desc.optional = False
        cont_params = Containment(name="parameters", key="ActionMapping-parameters", id=str(uuid.uuid4()), type=param_mapping_concept, multiple=True, optional=True)
        action_mapping_concept.add_feature(prop_action_name)
        action_mapping_concept.add_feature(prop_target_concept)
        action_mapping_concept.add_feature(prop_action_desc)
        action_mapping_concept.add_feature(cont_params)

        prop_param_name = Property(name="parameterName", key="ParameterMapping-parameterName", id=str(uuid.uuid4()), type=string_type)
        prop_param_name.optional = False
        prop_target_feature = Property(name="targetFeature", key="ParameterMapping-targetFeature", id=str(uuid.uuid4()), type=string_type)
        prop_target_feature.optional = False
        prop_param_desc = Property(name="description", key="ParameterMapping-description", id=str(uuid.uuid4()), type=string_type)
        prop_param_desc.optional = False
        prop_param_prompt = Property(name="clarificationPrompt", key="ParameterMapping-clarificationPrompt", id=str(uuid.uuid4()), type=string_type)
        prop_param_prompt.optional = False
        prop_param_req = Property(name="required", key="ParameterMapping-required", id=str(uuid.uuid4()), type=boolean_type)
        prop_param_req.optional = False
        param_mapping_concept.add_feature(prop_param_name)
        param_mapping_concept.add_feature(prop_target_feature)
        param_mapping_concept.add_feature(prop_param_desc)
        param_mapping_concept.add_feature(prop_param_prompt)
        param_mapping_concept.add_feature(prop_param_req)

        nl_lang.add_element(connector_concept)
        nl_lang.add_element(action_mapping_concept)
        nl_lang.add_element(param_mapping_concept)

        json_str = self.serialization.serialize_tree_to_json_string(nl_lang)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(json_str)

    def generate_and_save_connector_m1(self, domain: str, file_path: Path):
        """Generates the full nl_connector_m1.json file programmatically."""
        connector_concept = self.concepts["Connector"]
        action_map_concept = self.concepts["ActionMapping"]
        param_map_concept = self.concepts["ParameterMapping"]

        connector = DynamicNode(id="cycling-connector", concept=connector_concept)
        connector.set_property_value(connector_concept.get_feature_by_name("domainName"), "Cycling Management")
        connector.set_property_value(connector_concept.get_feature_by_name("targetLanguage"), "cycling")

        actions_data = {
            "create_rider": ("Rider", "Creates a new cyclist/rider", {
                "name": ("name", "The cyclist's full name", "What is the cyclist's name?", True),
                "age": ("age", "Age in years", "How old is the cyclist?", False),
                "country": ("country", "Country of origin", "Which country is the cyclist from?", False),
            }),
            "modify_rider": ("Rider", "Modifies an existing rider", {
                "name": ("name", "Name of rider to modify", "Which rider do you want to modify?", True),
                "age": ("age", "New age", "What is the new age?", False),
                "country": ("country", "New country", "What is the new country?", False),
            }),
            "create_team": ("Team", "Creates a new cycling team", {
                "name": ("name", "Team name", "What is the team's name?", True),
                "country": ("country", "Team's country", "Which country is the team from?", False),
                "budget": ("budget", "Budget in millions", "What is the team's budget (in millions)?", False),
                "founded": ("founded", "Year founded", "What year was the team founded?", False),
            }),
            "find_rider": ("Rider", "Search for riders", {
                "name_pattern": ("name", "Name pattern to search", "What name should I search for?", False),
                "country": ("country", "Country to filter by", "Which country to filter by?", False),
            }),
            "find_team": ("Team", "Search for teams", {
                "name_pattern": ("name", "Name pattern to search", "What team name should I search for?", False),
                "country": ("country", "Country to filter by", "Which country to filter by?", False),
            }),
        }

        for action_name, (target_concept, desc, params) in actions_data.items():
            action_node = DynamicNode(id=f"action-{action_name}", concept=action_map_concept)
            action_node.set_property_value(action_map_concept.get_feature_by_name("actionName"), action_name)
            action_node.set_property_value(action_map_concept.get_feature_by_name("targetConcept"), target_concept)
            action_node.set_property_value(action_map_concept.get_feature_by_name("description"), desc)

            for param_name, (target_feature, param_desc, prompt, required) in params.items():
                param_node = DynamicNode(id=f"param-{action_name}-{param_name}", concept=param_map_concept)
                param_node.set_property_value(param_map_concept.get_feature_by_name("parameterName"), param_name)
                param_node.set_property_value(param_map_concept.get_feature_by_name("targetFeature"), target_feature)
                param_node.set_property_value(param_map_concept.get_feature_by_name("description"), param_desc)
                param_node.set_property_value(param_map_concept.get_feature_by_name("clarificationPrompt"), prompt)
                param_node.set_property_value(param_map_concept.get_feature_by_name("required"), required)
                action_node.add_child(action_map_concept.get_feature_by_name("parameters"), param_node)
            
            connector.add_child(connector_concept.get_feature_by_name("actions"), action_node)

        json_str = self.serialization.serialize_tree_to_json_string(connector)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(json_str)

    def load_all(self, domain: str = "cycling") -> Dict[str, Any]:
        """Load all LionWeb artifacts for a domain."""
        results = {
            "language": f"Loaded languages: {list(self.languages.keys())}",
            "connector": None,
            "models": [],
            "errors": []
        }
        
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
                    else:
                        results["errors"].append("Error: Could not find a 'Connector' node in nl_connector_m1.json")
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