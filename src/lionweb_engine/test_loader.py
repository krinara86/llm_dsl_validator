# src/lionweb_engine/connector_loader.py

from pathlib import Path
from lionweb.serialization import Deserializer

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
        lang_deserializer = Deserializer()
        all_languages = []

        for lang_file in ["shapes.2025.1.json", "nl_mappings.json", "findings.json"]:
            path = self.languages_dir / lang_file
            with open(path, "r", encoding="utf-8") as f:
                language_nodes = lang_deserializer.deserialize(f.read())
                all_languages.append(language_nodes[0])

        model_deserializer = Deserializer(all_languages)

        with open(self.connector_path, "r", encoding="utf-8") as f:
            model_nodes = model_deserializer.deserialize(f.read())
        
        return self._transform_model_to_dict(model_nodes)

    def _transform_model_to_dict(self, model_nodes):
        """
        Extracts intents and parameters from the M1 connector model.
        """
        connector_dict = {"actions": {}}
        mapping_model_node = model_nodes[0]
        concept_mappings_key = "key-conceptMappings"
        
        for concept_map in mapping_model_node.get_containment_values(concept_mappings_key):
            phrases_key = "key-nlActionPhrases"
            target_concept_key = "key-targetConcept"
            
            action_phrases = concept_map.get_property_value(phrases_key)
            target_concept_ref = concept_map.get_reference_values(target_concept_key)[0].resolve()
            
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
            for prop_map in concept_map.get_containment_values(prop_mappings_key):
                prompt_key = "key-nlClarificationPrompt"
                target_prop_key = "key-targetProperty"
                
                clarification_prompt = prop_map.get_property_value(prompt_key)
                target_prop_ref = prop_map.get_reference_values(target_prop_key)[0].resolve()
                param_name = target_prop_ref.get_name()
                
                action_details["parameters"][param_name] = {
                    "description": clarification_prompt,
                    "_lionweb_meta": {
                        "target_property": target_prop_ref
                    }
                }
            
            connector_dict["actions"][action_name] = action_details
            
        return connector_dict