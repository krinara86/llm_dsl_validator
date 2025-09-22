# src/domains/cycling/state_manager.py
import json
import os
from typing import Dict, List, Any, Optional, Generator
from pathlib import Path
from collections import defaultdict
import time

class CyclingStateManager:
    """Manages large cycling JSON files with efficient memory usage."""
    
    def __init__(self, data_file: Path):
        self.data_file = data_file
        self.indices = {
            'documentedRiders': {},
            'documentedTeams': {},
            'documentedRaces': {},
            'undocumentedRiders': {},
            'undocumentedTeams': {},
            'undocumentedRaces': {}
        }
        self.next_ids = {
            'rider': 200000,
            'team': 40000,
            'race': 10000
        }
        self._ensure_data_file()
        self._build_indices()
    
    def _ensure_data_file(self):
        """Ensure the data file exists with minimal structure."""
        if not self.data_file.exists():
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            default_data = {
                "documentedRiders": [],
                "documentedTeams": [],
                "documentedRaces": [],
                "undocumentedRiders": [],
                "undocumentedTeams": [],
                "undocumentedRaces": []
            }
            with open(self.data_file, 'w') as f:
                json.dump(default_data, f, indent=2)
    
    def _build_indices(self):
        """Build lightweight indices for quick lookups."""
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                
            # Build indices for each entity type
            for i, rider in enumerate(data.get('documentedRiders', [])):
                self.indices['documentedRiders'][rider['id']] = i
                # Track highest ID for new entities
                if rider['id'] >= self.next_ids['rider']:
                    self.next_ids['rider'] = rider['id'] + 1
                    
            for i, team in enumerate(data.get('documentedTeams', [])):
                self.indices['documentedTeams'][team['id']] = i
                if team['id'] >= self.next_ids['team']:
                    self.next_ids['team'] = team['id'] + 1
                    
            for i, race in enumerate(data.get('documentedRaces', [])):
                race_id = race.get('raceId', race.get('id', 0))
                self.indices['documentedRaces'][race_id] = i
                if race_id >= self.next_ids['race']:
                    self.next_ids['race'] = race_id + 1
                    
            # Same for undocumented
            for i, rider in enumerate(data.get('undocumentedRiders', [])):
                self.indices['undocumentedRiders'][rider['id']] = i
                
            for i, team in enumerate(data.get('undocumentedTeams', [])):
                team_id = int(team.get('id', 0))  # Handle string IDs
                self.indices['undocumentedTeams'][team_id] = i
                
            for i, race in enumerate(data.get('undocumentedRaces', [])):
                race_id = race.get('raceId', race.get('id', 0))
                self.indices['undocumentedRaces'][race_id] = i
                
        except Exception as e:
            print(f"Warning: Error building indices: {e}")
    
    def get_next_id(self, entity_type: str) -> int:
        """Get the next available ID for an entity type."""
        return self.next_ids.get(entity_type, 100000)
    
    def increment_id(self, entity_type: str):
        """Increment the ID counter after using it."""
        if entity_type in self.next_ids:
            self.next_ids[entity_type] += 1
    
    def search_riders(self, criteria: Dict[str, Any], chunk_size: int = 100) -> List[Dict]:
        """Search riders with chunked processing."""
        results = []
        
        with open(self.data_file, 'r') as f:
            data = json.load(f)
        
        # Determine which list to search
        if 'documented' in criteria:
            search_lists = ['documentedRiders'] if criteria['documented'] else ['undocumentedRiders']
        else:
            search_lists = ['documentedRiders', 'undocumentedRiders']
        
        for list_name in search_lists:
            riders = data.get(list_name, [])
            
            # Process in chunks for memory efficiency
            for i in range(0, len(riders), chunk_size):
                chunk = riders[i:i + chunk_size]
                
                for rider in chunk:
                    if self._match_rider(rider, criteria):
                        # Add source info
                        rider['_source'] = list_name
                        results.append(rider)
        
        return results
    
    def _match_rider(self, rider: Dict, criteria: Dict) -> bool:
        """Check if a rider matches search criteria."""
        if 'name_pattern' in criteria:
            pattern = criteria['name_pattern'].lower()
            first_name = rider.get('firstName', '').lower()
            last_name = rider.get('lastName', '').lower()
            if pattern not in first_name and pattern not in last_name:
                return False
        
        if 'country' in criteria and rider.get('country') != criteria['country']:
            return False
        
        if 'team_id' in criteria and rider.get('team') != criteria['team_id']:
            return False
        
        # Ranking checks (only for documented riders with ranking)
        if 'ranking' in rider:
            rank = rider['ranking'].get('rank', float('inf'))
            if 'min_rank' in criteria and rank < criteria['min_rank']:
                return False
            if 'max_rank' in criteria and rank > criteria['max_rank']:
                return False
            
            points = rider['ranking'].get('points', 0)
            if 'min_points' in criteria and points < criteria['min_points']:
                return False
            if 'max_points' in criteria and points > criteria['max_points']:
                return False
        
        return True
    
    def search_teams(self, criteria: Dict[str, Any]) -> List[Dict]:
        """Search teams."""
        results = []
        
        with open(self.data_file, 'r') as f:
            data = json.load(f)
        
        for team in data.get('documentedTeams', []):
            if self._match_team(team, criteria):
                team['_source'] = 'documentedTeams'
                results.append(team)
        
        for team in data.get('undocumentedTeams', []):
            if self._match_team(team, criteria):
                team['_source'] = 'undocumentedTeams'
                results.append(team)
        
        return results
    
    def _match_team(self, team: Dict, criteria: Dict) -> bool:
        """Check if a team matches search criteria."""
        if 'name_pattern' in criteria:
            pattern = criteria['name_pattern'].lower()
            name = team.get('name', '').lower()
            if pattern not in name:
                return False
        
        if 'country' in criteria and team.get('country') != criteria['country']:
            return False
        
        if 'bike' in criteria:
            bike_pattern = criteria['bike'].lower()
            bike = team.get('bike', '').lower()
            if bike_pattern not in bike:
                return False
        
        if 'has_rider' in criteria:
            riders = team.get('riders', [])
            if criteria['has_rider'] not in riders:
                return False
        
        return True
    
    def search_races(self, criteria: Dict[str, Any]) -> List[Dict]:
        """Search races."""
        results = []
        
        with open(self.data_file, 'r') as f:
            data = json.load(f)
        
        for race in data.get('documentedRaces', []):
            if self._match_race(race, criteria):
                race['_source'] = 'documentedRaces'
                results.append(race)
        
        for race in data.get('undocumentedRaces', []):
            if self._match_race(race, criteria):
                race['_source'] = 'undocumentedRaces'
                results.append(race)
        
        return results
    
    def _match_race(self, race: Dict, criteria: Dict) -> bool:
        """Check if a race matches search criteria."""
        if 'name_pattern' in criteria:
            pattern = criteria['name_pattern'].lower()
            name = race.get('name', '').lower()
            if pattern not in name:
                return False
        
        if 'country' in criteria and race.get('country') != criteria['country']:
            return False
        
        if 'class' in criteria and race.get('class') != criteria['class']:
            return False
        
        # Date filtering
        if 'year' in criteria:
            start_date = race.get('startDate', '')
            if not start_date.startswith(str(criteria['year'])):
                return False
        
        return True
    
    def add_entity(self, entity_type: str, entity_data: Dict, documented: bool = True) -> Dict:
        """Add a new entity to the data file."""
        with open(self.data_file, 'r') as f:
            data = json.load(f)
        
        # Determine the list to add to
        if entity_type == 'rider':
            list_key = 'documentedRiders' if documented else 'undocumentedRiders'
            entity_data['id'] = self.get_next_id('rider')
            self.increment_id('rider')
        elif entity_type == 'team':
            list_key = 'documentedTeams' if documented else 'undocumentedTeams'
            entity_data['id'] = self.get_next_id('team')
            self.increment_id('team')
        elif entity_type == 'race':
            list_key = 'documentedRaces' if documented else 'undocumentedRaces'
            entity_data['raceId'] = self.get_next_id('race')
            self.increment_id('race')
        else:
            raise ValueError(f"Unknown entity type: {entity_type}")
        
        # Add to the appropriate list
        if list_key not in data:
            data[list_key] = []
        data[list_key].append(entity_data)
        
        # Update indices
        self.indices[list_key][entity_data.get('id', entity_data.get('raceId'))] = len(data[list_key]) - 1
        
        # Save back
        with open(self.data_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        return entity_data
    
    def modify_entity(self, entity_type: str, entity_id: int, updates: Dict) -> bool:
        """Modify an existing entity."""
        with open(self.data_file, 'r') as f:
            data = json.load(f)
        
        # Find the entity
        found = False
        if entity_type == 'rider':
            for list_key in ['documentedRiders', 'undocumentedRiders']:
                if entity_id in self.indices.get(list_key, {}):
                    idx = self.indices[list_key][entity_id]
                    data[list_key][idx].update(updates)
                    found = True
                    break
        elif entity_type == 'team':
            for list_key in ['documentedTeams', 'undocumentedTeams']:
                if entity_id in self.indices.get(list_key, {}):
                    idx = self.indices[list_key][entity_id]
                    
                    # Handle special operations
                    if 'add_rider' in updates:
                        if 'riders' not in data[list_key][idx]:
                            data[list_key][idx]['riders'] = []
                        rider_id = updates.pop('add_rider')
                        if rider_id not in data[list_key][idx]['riders']:
                            data[list_key][idx]['riders'].append(rider_id)
                    
                    if 'remove_rider' in updates:
                        rider_id = updates.pop('remove_rider')
                        if 'riders' in data[list_key][idx]:
                            data[list_key][idx]['riders'] = [
                                r for r in data[list_key][idx]['riders'] if r != rider_id
                            ]
                    
                    data[list_key][idx].update(updates)
                    found = True
                    break
        elif entity_type == 'race':
            for list_key in ['documentedRaces', 'undocumentedRaces']:
                if entity_id in self.indices.get(list_key, {}):
                    idx = self.indices[list_key][entity_id]
                    data[list_key][idx].update(updates)
                    found = True
                    break
        
        if found:
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
        
        return found
    
    def document_entity(self, entity_type: str, entity_id: int) -> bool:
        """Move an entity from undocumented to documented."""
        with open(self.data_file, 'r') as f:
            data = json.load(f)
        
        # Determine source and destination lists
        if entity_type == 'rider':
            source = 'undocumentedRiders'
            dest = 'documentedRiders'
        elif entity_type == 'team':
            source = 'undocumentedTeams'
            dest = 'documentedTeams'
        elif entity_type == 'race':
            source = 'undocumentedRaces'
            dest = 'documentedRaces'
        else:
            return False
        
        # Find and move the entity
        if entity_id in self.indices.get(source, {}):
            idx = self.indices[source][entity_id]
            entity = data[source].pop(idx)
            
            if dest not in data:
                data[dest] = []
            data[dest].append(entity)
            
            # Save and rebuild indices
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            self._build_indices()
            return True
        
        return False