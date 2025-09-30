#
# Changes to: src/domains/event/interpreter.py
#
import re
from ...framework.base_interpreter import BaseInterpreter, v_args
from copy import deepcopy

class EventInterpreter(BaseInterpreter):
    def __init__(self, state, role):
        self.state = deepcopy(state) 
        self.role = role
        self.actions_performed = []
        # --- NEW: To store query results ---
        self.query_results = None

    def _parse_boolean(self, cname):
        return str(cname).lower() == 'true'

    def event_command(self, children):
        # --- MODIFIED: Handle query results ---
        if self.query_results is not None:
            return {
                "message": f"Found {len(self.query_results)} result(s).",
                "results": self.query_results,
                "new_state": self.state # Unchanged state
            }
        
        return {
            "message": "Execution successful. " + ", ".join(self.actions_performed),
            "new_state": self.state
        }

    @v_args(inline=True)
    def create_venue(self, name, *props):
        # ... (no changes to this method)
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
        # ... (no changes to this method)
        if self.role != 'admin':
            raise ValueError(f"RoleMismatchError: Role '{self.role}' is not authorized to modify venues. Requires 'admin'.")
        key_to_modify = next((v for v in self.state["venues"] if v.lower() == name.lower()), None)
        if not key_to_modify:
            raise ValueError(f"ValidationError: Cannot modify venue '{name}' because it does not exist.")
        properties = dict(props)
        self.state["venues"][key_to_modify].update(properties)
        self.actions_performed.append(f"Modified venue '{key_to_modify}'")

    def schedule_session(self, children):
        # ... (no changes to this method)
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

    def find_venue(self, children):
        criteria = dict(children)
        results = []
        for name, props in self.state.get("venues", {}).items():
            match = True
            if 'name_pattern' in criteria and not re.search(criteria['name_pattern'], name, re.IGNORECASE):
                match = False
            if 'min_capacity' in criteria and props.get('capacity', 0) < criteria['min_capacity']:
                match = False
            if 'max_capacity' in criteria and props.get('capacity', 0) > criteria['max_capacity']:
                match = False
            if 'has_av' in criteria and props.get('has_av_system', False) != criteria['has_av']:
                match = False
            
            if match:
                results.append({"name": name, **props})
        
        self.query_results = results

    def find_session(self, children):
        criteria = dict(children)
        results = []
        for session in self.state.get("sessions", []):
            match = True
            if 'name_pattern' in criteria and not re.search(criteria['name_pattern'], session.get('name', ''), re.IGNORECASE):
                match = False
            if 'hosted_by_pattern' in criteria and not re.search(criteria['hosted_by_pattern'], session.get('hosted_by', ''), re.IGNORECASE):
                match = False
            if 'in_venue' in criteria and session.get('in_venue', '').lower() != criteria['in_venue'].lower():
                match = False
            if 'min_attendees' in criteria and session.get('expected_attendees', 0) < criteria['min_attendees']:
                match = False
            if 'max_attendees' in criteria and session.get('expected_attendees', 0) > criteria['max_attendees']:
                match = False
            if 'requires_av' in criteria and session.get('requires_av', False) != criteria['requires_av']:
                match = False

            if match:
                results.append(session)
        
        self.query_results = results

    # --- Property Helpers ---
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
    @v_args(inline=True)
    def venue_name_pattern(self, pattern): return ("name_pattern", pattern)
    @v_args(inline=True)
    def venue_min_capacity(self, num): return ("min_capacity", num)
    @v_args(inline=True)
    def venue_max_capacity(self, num): return ("max_capacity", num)
    @v_args(inline=True)
    def venue_has_av_filter(self, req_av): return ("has_av", self._parse_boolean(req_av))
    @v_args(inline=True)
    def session_name_pattern(self, pattern): return ("name_pattern", pattern)
    @v_args(inline=True)
    def session_hosted_by_pattern(self, pattern): return ("hosted_by_pattern", pattern)
    @v_args(inline=True)
    def session_in_venue(self, name): return ("in_venue", name)
    @v_args(inline=True)
    def session_min_attendees(self, num): return ("min_attendees", num)
    @v_args(inline=True)
    def session_max_attendees(self, num): return ("max_attendees", num)
    @v_args(inline=True)
    def session_requires_av_filter(self, req_av): return ("requires_av", self._parse_boolean(req_av))