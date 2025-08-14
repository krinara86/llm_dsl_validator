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

        if name in self.state["venues"]:
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

        if name not in self.state["venues"]:
            raise ValueError(f"ValidationError: Cannot modify venue '{name}' because it does not exist.")
            
        properties = dict(props)
        self.state["venues"][name].update(properties)
        self.actions_performed.append(f"Modified venue '{name}'")

    def schedule_session(self, children):
        if self.role not in ['admin', 'scheduler']:
            raise ValueError(f"RoleMismatchError: Role '{self.role}' is not authorized to schedule sessions.")

        session_name = children[0]
        properties = dict(children[1:])
        venue_name = properties.get('in_venue')
        
        # --- VALIDATION LOGIC ---
        if venue_name not in self.state['venues']:
            raise ValueError(f"ValidationError in session '{session_name}': Venue '{venue_name}' does not exist.")

        if venue_name in self.state['venue_bookings']:
            conflicting_session = self.state['venue_bookings'][venue_name]
            raise ValueError(f"ValidationError in session '{session_name}': Venue '{venue_name}' is already booked by session '{conflicting_session}'.")

        venue = self.state['venues'][venue_name]
        
        attendees = properties.get('expected_attendees', 0)
        venue_capacity = venue.get('capacity', 0)
        if attendees > venue_capacity:
            raise ValueError(f"ValidationError in session '{session_name}': Expected attendees ({attendees}) exceeds venue capacity ({venue_capacity}).")

        session_reqs_av = properties.get('requires_av', False)
        venue_has_av = venue.get('has_av_system', False)
        if session_reqs_av and not venue_has_av:
            raise ValueError(f"ValidationError in session '{session_name}': Session requires A/V, but venue '{venue_name}' does not have an A/V system.")

        self.state['venue_bookings'][venue_name] = session_name
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