# src/domains/event/interpreter.py
from ...framework.base_interpreter import BaseInterpreter, v_args
from copy import deepcopy

class EventInterpreter(BaseInterpreter):
    def __init__(self, state, role):
        # The interpreter is initialized with the current state and the user's role.
        self.state = deepcopy(state) # Work on a copy to avoid partial updates on error
        self.role = role
        self.actions_performed = []

    def _parse_boolean(self, cname):
        return str(cname).lower() == 'true'

    def event_command(self, children):
        # This is the final step. If all commands within were successful,
        # return the new state and a summary of actions.
        return {
            "message": "Execution successful. " + ", ".join(self.actions_performed),
            "new_state": self.state
        }

    @v_args(inline=True)
    def create_venue(self, name, *props):
        if self.role != 'admin':
            raise ValueError(f"RoleMismatchError: Role '{self.role}' is not authorized to create venues. Requires 'admin'.")

        # This check is now case-insensitive to prevent duplicates like 'Room A' and 'room a'.
        if name.lower() in [v.lower() for v in self.state["venues"]]:
            raise ValueError(f"ValidationError: Venue '{name}' already exists.")
        
        properties = dict(props)
        # Store with the name as provided (after quote stripping in core.py) to preserve capitalization.
        self.state["venues"][name] = {
            "capacity": properties.get("capacity", 0),
            "has_av_system": properties.get("has_av_system", False)
        }
        self.actions_performed.append(f"Created venue '{name}'")

    @v_args(inline=True)
    def modify_venue(self, name, *props):
        if self.role != 'admin':
            raise ValueError(f"RoleMismatchError: Role '{self.role}' is not authorized to modify venues. Requires 'admin'.")

        # Find the actual venue key in a case-insensitive way.
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
        
        # --- VALIDATION LOGIC (Now case-insensitive) ---

        # Find the actual venue key case-insensitively.
        venue_key_actual = next((v for v in self.state['venues'] if v.lower() == venue_name.lower()), None)
        if not venue_key_actual:
            raise ValueError(f"ValidationError in session '{session_name}': Venue '{venue_name}' does not exist.")

        # Check for bookings using the actual key, but also check case-insensitively for safety.
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

        # Use the actual, original-cased key for booking to maintain data consistency.
        self.state['venue_bookings'][venue_key_actual] = session_name
        self.state['sessions'].append({"name": session_name, **properties})
        self.actions_performed.append(f"Scheduled session '{session_name}'")

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