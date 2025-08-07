# src/domains/event/interpreter.py
from ...framework.base_interpreter import BaseInterpreter, v_args

class EventInterpreter(BaseInterpreter):
    def __init__(self):
        self.venues = {}
        self.speakers = set()
        self.sessions = []
        self.plan_name = ""

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

    def venue(self, children):
        venue_name = children[0]
        properties = dict(children[1:])
        self.venues[venue_name] = properties

    @v_args(inline=True)
    def venue_capacity(self, capacity): return ("capacity", capacity)

    @v_args(inline=True)
    def venue_av(self, has_av): return ("has_av_system", self._parse_boolean(has_av))

    @v_args(inline=True)
    def speaker_def(self, name):
        self.speakers.add(name)

    def session(self, children):
        session_name = children[0]
        properties = dict(children[1:])
        
        speaker = properties.get('hosted_by')
        venue_name = properties.get('in_venue')
        
        if speaker and speaker not in self.speakers:
            raise ValueError(f"Validation Error in session '{session_name}': Speaker '{speaker}' is not defined.")
        
        if venue_name not in self.venues:
            raise ValueError(f"Validation Error in session '{session_name}': Venue '{venue_name}' is not defined.")

        venue = self.venues[venue_name]
        attendees = properties.get('expected_attendees', 0)
        venue_capacity = venue.get('capacity', 0)
        if attendees > venue_capacity:
            raise ValueError(f"Validation Error in session '{session_name}': Expected attendees ({attendees}) exceeds venue capacity ({venue_capacity}).")

        session_reqs_av = properties.get('requires_av', False)
        venue_has_av = venue.get('has_av_system', False)
        if session_reqs_av and not venue_has_av:
            raise ValueError(f"Validation Error in session '{session_name}': Session requires A/V, but venue '{venue_name}' does not have an A/V system.")

        self.sessions.append({"name": session_name, **properties})

    @v_args(inline=True)
    def session_speaker(self, name): return ("hosted_by", name)
    @v_args(inline=True)
    def session_venue(self, name): return ("in_venue", name)
    @v_args(inline=True)
    def session_attendees(self, num): return ("expected_attendees", num)
    @v_args(inline=True)
    def session_requires_av(self, req_av): return ("requires_av", self._parse_boolean(req_av))