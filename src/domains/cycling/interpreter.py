# src/domains/cycling/interpreter.py
import re
from typing import Dict, List, Any
from ...framework.base_interpreter import BaseInterpreter, v_args
from .state_manager import CyclingStateManager
from pathlib import Path

class CyclingInterpreter(BaseInterpreter):
    def __init__(self, data_file: Path, role: str):
        self.state_manager = CyclingStateManager(data_file)
        self.role = role
        self.actions_performed = []
        self.query_results = None
    
    def _parse_boolean(self, cname):
        return str(cname).lower() == 'true'
    
    def cycling_command(self, children):
        """Process the results of the cycling command."""
        if self.query_results is not None:
            return {
                "message": f"Found {len(self.query_results)} result(s).",
                "results": self.query_results,
                "action_type": "query"
            }
        
        return {
            "message": "Execution successful. " + ", ".join(self.actions_performed),
            "action_type": "mutation"
        }
    
    # Search operations
    def find_rider(self, children):
        """Search for riders based on criteria."""
        criteria = dict(children)
        
        # Convert boolean strings
        if 'documented' in criteria:
            criteria['documented'] = criteria['documented']
        
        results = self.state_manager.search_riders(criteria)
        self.query_results = results
    
    def find_team(self, children):
        """Search for teams based on criteria."""
        criteria = dict(children)
        results = self.state_manager.search_teams(criteria)
        self.query_results = results
    
    def find_race(self, children):
        """Search for races based on criteria."""
        criteria = dict(children)
        results = self.state_manager.search_races(criteria)
        self.query_results = results
    
    # Add operations
    @v_args(inline=True)
    def add_rider(self, name, *props):
        """Add a new rider."""
        if self.role not in ['admin', 'editor']:
            raise ValueError(f"RoleMismatchError: Role '{self.role}' cannot add riders.")
        
        properties = dict(props)
        
        # Build rider object
        rider_data = {
            'firstName': properties.get('first_name', ''),
            'lastName': properties.get('last_name', ''),
            'country': properties.get('country', ''),
        }
        
        if 'birth_date' in properties:
            rider_data['birthDate'] = properties['birth_date']
        
        if 'team_id' in properties:
            rider_data['team'] = properties['team_id']
        
        if 'rank' in properties or 'points' in properties:
            rider_data['ranking'] = {
                'title': 'UCI World Ranking',
                'rank': properties.get('rank', 0),
                'points': properties.get('points', 0)
            }
        
        documented = properties.get('documented', True)
        result = self.state_manager.add_entity('rider', rider_data, documented)
        
        self.actions_performed.append(
            f"Added rider '{name}' with ID {result['id']}"
        )
    
    @v_args(inline=True)
    def add_team(self, name, *props):
        """Add a new team."""
        if self.role != 'admin':
            raise ValueError(f"RoleMismatchError: Role '{self.role}' cannot add teams.")
        
        properties = dict(props)
        
        team_data = {
            'name': name,
            'country': properties.get('country', ''),
            'riders': []
        }
        
        if 'bike' in properties:
            team_data['bike'] = properties['bike']
        
        if 'website' in properties:
            team_data['website'] = properties['website']
        
        result = self.state_manager.add_entity('team', team_data, documented=True)
        
        self.actions_performed.append(
            f"Added team '{name}' with ID {result['id']}"
        )
    
    @v_args(inline=True)
    def add_race(self, name, *props):
        """Add a new race."""
        if self.role != 'admin':
            raise ValueError(f"RoleMismatchError: Role '{self.role}' cannot add races.")
        
        properties = dict(props)
        
        race_data = {
            'name': name,
            'country': properties.get('country', ''),
            'startDate': properties.get('start_date', ''),
        }
        
        if 'class' in properties:
            race_data['class'] = properties['class']
        
        if 'end_date' in properties:
            race_data['endDate'] = properties['end_date']
        
        if 'distance' in properties:
            race_data['distance'] = properties['distance']
        
        result = self.state_manager.add_entity('race', race_data, documented=True)
        
        self.actions_performed.append(
            f"Added race '{name}' with ID {result.get('raceId', 'unknown')}"
        )
    
    # Modify operations
    @v_args(inline=True)
    def modify_rider(self, rider_id, *props):
        """Modify an existing rider."""
        if self.role not in ['admin', 'editor']:
            raise ValueError(f"RoleMismatchError: Role '{self.role}' cannot modify riders.")
        
        properties = dict(props)
        
        # Map properties to correct field names
        updates = {}
        if 'first_name' in properties:
            updates['firstName'] = properties['first_name']
        if 'last_name' in properties:
            updates['lastName'] = properties['last_name']
        if 'country' in properties:
            updates['country'] = properties['country']
        if 'birth_date' in properties:
            updates['birthDate'] = properties['birth_date']
        if 'team_id' in properties:
            updates['team'] = properties['team_id']
        
        # Handle ranking updates
        if 'rank' in properties or 'points' in properties:
            updates['ranking'] = {
                'title': 'UCI World Ranking',
                'rank': properties.get('rank', 0),
                'points': properties.get('points', 0)
            }
        
        success = self.state_manager.modify_entity('rider', rider_id, updates)
        
        if success:
            self.actions_performed.append(f"Modified rider ID {rider_id}")
        else:
            raise ValueError(f"ValidationError: Rider with ID {rider_id} not found.")
    
    @v_args(inline=True)
    def modify_team(self, team_id, *props):
        """Modify an existing team."""
        if self.role not in ['admin', 'editor']:
            raise ValueError(f"RoleMismatchError: Role '{self.role}' cannot modify teams.")
        
        properties = dict(props)
        
        updates = {}
        if 'name' in properties:
            updates['name'] = properties['name']
        if 'country' in properties:
            updates['country'] = properties['country']
        if 'bike' in properties:
            updates['bike'] = properties['bike']
        if 'website' in properties:
            updates['website'] = properties['website']
        if 'add_rider' in properties:
            updates['add_rider'] = properties['add_rider']
        if 'remove_rider' in properties:
            updates['remove_rider'] = properties['remove_rider']
        
        success = self.state_manager.modify_entity('team', team_id, updates)
        
        if success:
            self.actions_performed.append(f"Modified team ID {team_id}")
        else:
            raise ValueError(f"ValidationError: Team with ID {team_id} not found.")
    
    @v_args(inline=True)
    def modify_race(self, race_id, *props):
        """Modify an existing race."""
        if self.role not in ['admin', 'editor']:
            raise ValueError(f"RoleMismatchError: Role '{self.role}' cannot modify races.")
        
        properties = dict(props)
        
        updates = {}
        if 'name' in properties:
            updates['name'] = properties['name']
        if 'country' in properties:
            updates['country'] = properties['country']
        if 'class' in properties:
            updates['class'] = properties['class']
        if 'start_date' in properties:
            updates['startDate'] = properties['start_date']
        if 'end_date' in properties:
            updates['endDate'] = properties['end_date']
        if 'distance' in properties:
            updates['distance'] = properties['distance']
        
        success = self.state_manager.modify_entity('race', race_id, updates)
        
        if success:
            self.actions_performed.append(f"Modified race ID {race_id}")
        else:
            raise ValueError(f"ValidationError: Race with ID {race_id} not found.")
    
    # Special operations
    @v_args(inline=True)
    def document_entity(self, description, *props):
        """Move entity from undocumented to documented."""
        if self.role not in ['admin', 'editor']:
            raise ValueError(f"RoleMismatchError: Role '{self.role}' cannot document entities.")
        
        properties = dict(props)
        entity_type = properties.get('entity_type', '')
        entity_id = properties.get('entity_id', 0)
        
        success = self.state_manager.document_entity(entity_type, entity_id)
        
        if success:
            self.actions_performed.append(
                f"Documented {entity_type} with ID {entity_id}"
            )
        else:
            raise ValueError(
                f"ValidationError: Could not document {entity_type} with ID {entity_id}."
            )
    
    def link_entities(self, children):
        """Create relationships between entities."""
        if self.role not in ['admin', 'editor']:
            raise ValueError(f"RoleMismatchError: Role '{self.role}' cannot link entities.")
        
        properties = dict(children)
        
        # This would handle linking riders to teams, adding results, etc.
        # For now, we'll focus on the most common case: adding rider to team
        if 'rider_id' in properties and 'team_id' in properties:
            updates = {'add_rider': properties['rider_id']}
            success = self.state_manager.modify_entity(
                'team', properties['team_id'], updates
            )
            
            if success:
                self.actions_performed.append(
                    f"Linked rider {properties['rider_id']} to team {properties['team_id']}"
                )
            else:
                raise ValueError("ValidationError: Could not link entities.")
        else:
            raise ValueError("ValidationError: Need both rider_id and team_id to link.")
    
    # Property helpers for the grammar
    @v_args(inline=True)
    def rider_first_name(self, name): return ("first_name", name)
    @v_args(inline=True)
    def rider_last_name(self, name): return ("last_name", name)
    @v_args(inline=True)
    def rider_country(self, country): return ("country", country)
    @v_args(inline=True)
    def rider_birth_date(self, date): return ("birth_date", date)
    @v_args(inline=True)
    def rider_team(self, team_id): return ("team_id", team_id)
    @v_args(inline=True)
    def rider_rank(self, rank): return ("rank", rank)
    @v_args(inline=True)
    def rider_points(self, points): return ("points", points)
    @v_args(inline=True)
    def rider_documented(self, doc): return ("documented", self._parse_boolean(doc))
    
    @v_args(inline=True)
    def rider_name_pattern(self, pattern): return ("name_pattern", pattern)
    @v_args(inline=True)
    def rider_country_filter(self, country): return ("country", country)
    @v_args(inline=True)
    def rider_team_filter(self, team_id): return ("team_id", team_id)
    @v_args(inline=True)
    def rider_min_rank(self, rank): return ("min_rank", rank)
    @v_args(inline=True)
    def rider_max_rank(self, rank): return ("max_rank", rank)
    @v_args(inline=True)
    def rider_min_points(self, points): return ("min_points", points)
    @v_args(inline=True)
    def rider_max_points(self, points): return ("max_points", points)
    @v_args(inline=True)
    def rider_documented_filter(self, doc): return ("documented", self._parse_boolean(doc))
    
    @v_args(inline=True)
    def team_name(self, name): return ("name", name)
    @v_args(inline=True)
    def team_country(self, country): return ("country", country)
    @v_args(inline=True)
    def team_bike(self, bike): return ("bike", bike)
    @v_args(inline=True)
    def team_website(self, website): return ("website", website)
    @v_args(inline=True)
    def team_add_rider(self, rider_id): return ("add_rider", rider_id)
    @v_args(inline=True)
    def team_remove_rider(self, rider_id): return ("remove_rider", rider_id)
    
    @v_args(inline=True)
    def team_name_pattern(self, pattern): return ("name_pattern", pattern)
    @v_args(inline=True)
    def team_country_filter(self, country): return ("country", country)
    @v_args(inline=True)
    def team_bike_filter(self, bike): return ("bike", bike)
    @v_args(inline=True)
    def team_has_rider(self, rider_id): return ("has_rider", rider_id)
    
    @v_args(inline=True)
    def race_name(self, name): return ("name", name)
    @v_args(inline=True)
    def race_country(self, country): return ("country", country)
    @v_args(inline=True)
    def race_class(self, cls): return ("class", cls)
    @v_args(inline=True)
    def race_start_date(self, date): return ("start_date", date)
    @v_args(inline=True)
    def race_end_date(self, date): return ("end_date", date)
    @v_args(inline=True)
    def race_distance(self, distance): return ("distance", distance)
    
    @v_args(inline=True)
    def race_name_pattern(self, pattern): return ("name_pattern", pattern)
    @v_args(inline=True)
    def race_country_filter(self, country): return ("country", country)
    @v_args(inline=True)
    def race_class_filter(self, cls): return ("class", cls)
    @v_args(inline=True)
    def race_start_date_filter(self, date): return ("start_date", date)
    @v_args(inline=True)
    def race_end_date_filter(self, date): return ("end_date", date)
    @v_args(inline=True)
    def race_year_filter(self, year): return ("year", year)
    
    @v_args(inline=True)
    def doc_entity_type(self, entity_type): return ("entity_type", entity_type)
    @v_args(inline=True)
    def doc_entity_id(self, entity_id): return ("entity_id", entity_id)
    
    @v_args(inline=True)
    def link_rider_id(self, rider_id): return ("rider_id", rider_id)
    @v_args(inline=True)
    def link_team_id(self, team_id): return ("team_id", team_id)
    @v_args(inline=True)
    def link_race_id(self, race_id): return ("race_id", race_id)