# src/domains/event/interpreter.py
from ...framework.base_interpreter import BaseInterpreter, v_args

class EventInterpreter(BaseInterpreter):
    def __init__(self):
        # The interpreter is now the "source of truth" for venue data.
        self.venues = {
            "Grand Ballroom": {"capacity": 500, "has_av_system": True},
            "Workshop Room A": {"capacity": 40, "has_av_system": False},
            "Workshop Room B": {"capacity": 40, "has_av_system": True},
            "Lecture Hall C": {"capacity": 100, "has_av_system": True}
        }
        self.speakers = set()
        self.sessions = []
        self.plan_name = ""
        # New property to track venue bookings for validation.
        self.venue_bookings = {}

    def _parse_boolean(self, cname):
        return str(cname).lower() == 'true'

    @v_args(inline=True)
    def conference_plan(self, name, *items):
        self.plan_name = name
        return {
            "plan_name": self.plan_name,
            "venue_count": len(self.venues),
            "speaker_count": len(self.speakers),
            "session_count": len(self.sessions),
            "sessions": self.sessions
        }

    @v_args(inline=True)
    def speaker_def(self, name):
        self.speakers.add(name)

    def session(self, children):
        session_name = children[0]
        properties = dict(children[1:])
        
        venue_name = properties.get('in_venue')
        
        # --- NEW VALIDATION LOGIC ---
        
        if venue_name not in self.venues:
            raise ValueError(f"Validation Error in session '{session_name}': Venue '{venue_name}' does not exist.")

        if venue_name in self.venue_bookings:
            conflicting_session = self.venue_bookings[venue_name]
            raise ValueError(f"Validation Error in session '{session_name}': Venue '{venue_name}' is already booked by session '{conflicting_session}'.")

        venue = self.venues[venue_name]
        
        attendees = properties.get('expected_attendees', 0)
        venue_capacity = venue.get('capacity', 0)
        if attendees > venue_capacity:
            raise ValueError(f"Validation Error in session '{session_name}': Expected attendees ({attendees}) exceeds venue capacity ({venue_capacity}).")

        session_reqs_av = properties.get('requires_av', False)
        venue_has_av = venue.get('has_av_system', False)
        if session_reqs_av and not venue_has_av:
            raise ValueError(f"Validation Error in session '{session_name}': Session requires A/V, but venue '{venue_name}' does not have an A/V system.")

        self.venue_bookings[venue_name] = session_name
        self.sessions.append({"name": session_name, **properties})

    @v_args(inline=True)
    def session_speaker(self, name): return ("hosted_by", name)
    
    @v_args(inline=True)
    def session_venue(self, name): return ("in_venue", name)
    
    @v_args(inline=True)
    def session_attendees(self, num): return ("expected_attendees", num)
    
    @v_args(inline=True)
    def session_requires_av(self, req_av): return ("requires_av", self._parse_boolean(req_av))