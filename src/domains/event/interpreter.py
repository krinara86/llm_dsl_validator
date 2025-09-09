# src/domains/event/interpreter.py
from ...framework.base_interpreter import BaseInterpreter, v_args
from copy import deepcopy

class EventInterpreter(BaseInterpreter):
    def __init__(self, state, role):
        self.state = deepcopy(state) 
        self.role = role
        self.actions_performed = []
        self.search_results = None  
    def _parse_boolean(self, cname):
        return str(cname).lower() == 'true'

    def event_command(self, children):
        if self.search_results is not None:
            return {
                "operation_type": "read_only",
                "results": self.search_results,
                "message": "Search completed successfully."
            }
        return {
            "operation_type": "state_changing",
            "message": "Execution successful. " + ", ".join(self.actions_performed),
            "new_state": self.state
        }

    @v_args(inline=True)
    def create_venue(self, name, *props):
        if self.role != 'admin':
            raise ValueError(f"RoleMismatchError: Role '{self.role}' is not authorized to create venues. Requires 'admin'.")

        if name.lower() in [v.lower() for v in self.state["venues"]]:
            raise ValueError(f"ValidationError: Venue '{name}' already exists.")
        
        properties = dict(props)
        self.state["venues"][name] = {
            "capacity": properties.get("capacity", 0),
            "has_av_system": properties.get("has_av_system", False)
        }
        self.actions_performed.append(f"Created venue '{name}'")

    @v_args(inline=True)
    def modify_venue(self, name, *props):
        if self.role != 'admin':
            raise ValueError(f"RoleMismatchError: Role '{self.role}' is not authorized to modify venues. Requires 'admin'.")

        key_to_modify = next((v for v in self.state["venues"] if v.lower() == name.lower()), None)

        if not key_to_modify:
            raise ValueError(f"ValidationError: Cannot modify venue '{name}' because it does not exist.")
            
        properties = dict(props)
        self.state["venues"][key_to_modify].update(properties)
        self.actions_performed.append(f"Modified venue '{key_to_modify}'")

    def schedule_session(self, children):
        if self.role not in ['admin', 'scheduler']:
            raise ValueError(f"RoleMismatchError: Role '{self.role}' is not authorized to schedule sessions.")

        session_name = children[0]
        properties = dict(children[1:])
        venue_name = properties.get('in_venue')
        
        venue_key_actual = next((v for v in self.state['venues'] if v.lower() == venue_name.lower()), None)
        if not venue_key_actual:
            raise ValueError(f"ValidationError in session '{session_name}': Venue '{venue_name}' does not exist.")

        booking_key_actual = next((v for v in self.state['venue_bookings'] if v.lower() == venue_name.lower()), None)
        if booking_key_actual:
            conflicting_session = self.state['venue_bookings'][booking_key_actual]
            raise ValueError(f"ValidationError in session '{session_name}': Venue '{booking_key_actual}' is already booked by session '{conflicting_session}'.")

        venue = self.state['venues'][venue_key_actual]
        
        attendees = properties.get('expected_attendees', 0)
        venue_capacity = venue.get('capacity', 0)
        if attendees > venue_capacity:
            raise ValueError(f"ValidationError in session '{session_name}': Expected attendees ({attendees}) exceeds venue capacity ({venue_capacity}).")

        session_reqs_av = properties.get('requires_av', False)
        venue_has_av = venue.get('has_av_system', False)
        if session_reqs_av and not venue_has_av:
            raise ValueError(f"ValidationError in session '{session_name}': Session requires A/V, but venue '{venue_key_actual}' does not have an A/V system.")

        self.state['venue_bookings'][venue_key_actual] = session_name
        self.state['sessions'].append({"name": session_name, **properties})
        self.actions_performed.append(f"Scheduled session '{session_name}'")

    def find_venues(self, children):
        """Search for venues based on criteria."""
        if self.role not in ['admin', 'scheduler', 'viewer']:
            raise ValueError(f"RoleMismatchError: Role '{self.role}' is not authorized to search venues.")
        
        criteria = dict(children)
        results = []
        
        for venue_name, venue_props in self.state.get('venues', {}).items():
            # Check each criterion
            if 'min_capacity' in criteria:
                if venue_props.get('capacity', 0) < criteria['min_capacity']:
                    continue
            
            if 'has_av_system' in criteria:
                if venue_props.get('has_av_system', False) != criteria['has_av_system']:
                    continue
            
            if 'is_available' in criteria:
                is_booked = venue_name in self.state.get('venue_bookings', {})
                is_available = not is_booked
                if is_available != criteria['is_available']:
                    continue
            
            if 'name_contains' in criteria:
                if criteria['name_contains'].lower() not in venue_name.lower():
                    continue
            
            # Add availability status to results
            is_booked = venue_name in self.state.get('venue_bookings', {})
            results.append({
                'name': venue_name,
                'capacity': venue_props.get('capacity', 0),
                'has_av_system': venue_props.get('has_av_system', False),
                'is_available': not is_booked,
                'booked_by': self.state.get('venue_bookings', {}).get(venue_name)
            })
        
        self.search_results = {
            'type': 'venues',
            'criteria': criteria,
            'items': results,
            'count': len(results)
        }

    def find_sessions(self, children):
        """Search for sessions based on criteria."""
        if self.role not in ['admin', 'scheduler', 'viewer']:
            raise ValueError(f"RoleMismatchError: Role '{self.role}' is not authorized to search sessions.")
        
        criteria = dict(children)
        results = []
        
        for session in self.state.get('sessions', []):
            # Check each criterion
            if 'name_contains' in criteria:
                if criteria['name_contains'].lower() not in session.get('name', '').lower():
                    continue
            
            if 'hosted_by' in criteria:
                if criteria['hosted_by'].lower() not in session.get('hosted_by', '').lower():
                    continue
            
            if 'in_venue' in criteria:
                if criteria['in_venue'].lower() not in session.get('in_venue', '').lower():
                    continue
            
            if 'min_attendees' in criteria:
                if session.get('expected_attendees', 0) < criteria['min_attendees']:
                    continue
            
            if 'requires_av' in criteria:
                if session.get('requires_av', False) != criteria['requires_av']:
                    continue
            
            results.append(session)
        
        self.search_results = {
            'type': 'sessions',
            'criteria': criteria,
            'items': results,
            'count': len(results)
        }

    @v_args(inline=True)
    def venue_capacity(self, num): return ("capacity", num)
    
    @v_args(inline=True)
    def venue_has_av(self, req_av): return ("has_av_system", self._parse_boolean(req_av))

    @v_args(inline=True)
    def session_speaker(self, name): return ("hosted_by", name)
    
    @v_args(inline=True)
    def session_venue(self, name): return ("in_venue", name)
    
    @v_args(inline=True)
    def session_attendees(self, num): return ("expected_attendees", num)
    
    @v_args(inline=True)
    def session_requires_av(self, req_av): return ("requires_av", self._parse_boolean(req_av))
    
    # --- Property Helpers for find operations ---
    @v_args(inline=True)
    def find_venue_min_capacity(self, num): return ("min_capacity", num)
    
    @v_args(inline=True)
    def find_venue_has_av(self, has_av): return ("has_av_system", self._parse_boolean(has_av))
    
    @v_args(inline=True)
    def find_venue_available(self, is_available): return ("is_available", self._parse_boolean(is_available))
    
    @v_args(inline=True)
    def find_venue_name_contains(self, text): return ("name_contains", text)
    
    @v_args(inline=True)
    def find_session_name_contains(self, text): return ("name_contains", text)
    
    @v_args(inline=True)
    def find_session_hosted_by(self, name): return ("hosted_by", name)
    
    @v_args(inline=True)
    def find_session_in_venue(self, venue): return ("in_venue", venue)
    
    @v_args(inline=True)
    def find_session_min_attendees(self, num): return ("min_attendees", num)
    
    @v_args(inline=True)
    def find_session_requires_av(self, req_av): return ("requires_av", self._parse_boolean(req_av))