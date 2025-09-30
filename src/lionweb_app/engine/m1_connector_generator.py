"""
Contains a function to programmatically generate the M1 connector instance.
"""
from pathlib import Path
from lionweb.model import DynamicNode

def generate_and_save_connector_m1(file_path: Path, serialization, concepts):
    """Generates the full nl_connector_m1.json file programmatically."""
    connector_concept = concepts["Connector"]
    action_map_concept = concepts["ActionMapping"]
    param_map_concept = concepts["ParameterMapping"]

    # Create Root Connector Node
    connector = DynamicNode(id="cycling-connector", concept=connector_concept)
    connector.set_property_value(connector_concept.get_feature_by_name("domainName"), "Cycling Management")
    connector.set_property_value(connector_concept.get_feature_by_name("targetLanguage"), "cycling")

    # Define all actions and their parameters
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

    json_str = serialization.serialize_tree_to_json_string(connector)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(json_str)