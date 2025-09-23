# src/lionweb_engine/connector_loader.py

from pathlib import Path
from lionwebpython.serialization.json_serialization import JsonSerialization

class LionWebConnectorLoader:
    """
    Loads and interprets the LionWeb M2 languages and M1 connector model
    for a given domain.
    """
    def __init__(self, domain: str):
        self.domain = domain
        self.project_root = Path(__file__).parent.parent.parent
        self.languages_dir = self.project_root / "src" / "lionweb" / "languages"
        self.connector_path = self.project_root / "src" / "domains" / domain / "nl_connector.json"

    def load(self):
        """
        Parses all necessary LionWeb files and transforms the M1 connector
        into a simple dictionary for the orchestrator.
        """
        serializer = JsonSerialization()

        # First, the serializer needs to learn the definitions of all languages (M2s).
        for lang_file in ["shapes.2025.1.json", "nl_mappings.json", "findings.json"]:
            path = self.languages_dir / lang_file
            with open(path, "r", encoding="utf-8") as f:
                serializer.deserialize_languages(f.read())
        
        # Now that the serializer knows the languages, it can parse the M1 model.
        with open(self.connector_path, "r", encoding="utf-8") as f:
            model_nodes = serializer.deserialize_to_nodes(f.read())
        
        return self._transform_model_to_dict(model_nodes)

    def _transform_model_to_dict(self, model_nodes):
        """
        Extracts intents and parameters from the M1 connector model.
        """
        connector_dict = {"actions": {}}
        mapping_model_node = model_nodes[0]
        concept_mappings_key = "key-conceptMappings"
        
        for concept_map in mapping_model_node.get_children_by_key(concept_mappings_key):
            phrases_key = "key-nlActionPhrases"
            target_concept_key = "key-targetConcept"
            
            action_phrases = concept_map.get_property_value_by_key(phrases_key)
            target_concept_ref = concept_map.get_reference_values_by_key(target_concept_key)[0].resolve()
            
            action_name = action_phrases.split(',')[0].strip().replace(" ", "_")
            
            action_details = {
                "description": f"Handles operations for the {target_concept_ref.get_name()} concept.",
                "parameters": {},
                "_lionweb_meta": {
                    "phrases": action_phrases,
                    "target_concept": target_concept_ref
                }
            }
            
            prop_mappings_key = "key-propertyMappings"
            for prop_map in concept_map.get_children_by_key(prop_mappings_key):
                prompt_key = "key-nlClarificationPrompt"
                target_prop_key = "key-targetProperty"
                
                clarification_prompt = prop_map.get_property_value_by_key(prompt_key)
                target_prop_ref = prop_map.get_reference_values_by_key(target_prop_key)[0].resolve()
                param_name = target_prop_ref.get_name()
                
                action_details["parameters"][param_name] = {
                    "description": clarification_prompt,
                    "_lionweb_meta": {
                        "target_property": target_prop_ref
                    }
                }
            
            connector_dict["actions"][action_name] = action_details
            
        return connector_dict