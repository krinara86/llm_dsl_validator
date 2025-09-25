"""
Contains functions to programmatically generate M2 language definitions.
"""
import uuid
from pathlib import Path

from lionweb.language import Language, Concept, Property, Containment
from lionweb.language.lioncore_builtins import LionCoreBuiltins


def generate_and_save_cycling_m2(path: Path, serialization):
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
    
    json_str = serialization.serialize_tree_to_json_string(cycling_lang)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(json_str)

def generate_and_save_nl_mappings_m2(path: Path, serialization):
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

    json_str = serialization.serialize_tree_to_json_string(nl_lang)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(json_str)