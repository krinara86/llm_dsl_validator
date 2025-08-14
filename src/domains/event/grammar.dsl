start: event_command

event_command: "role" ESCAPED_STRING "{" command* "}"

command: create_venue | modify_venue | schedule_session

// Admin actions
create_venue: "create_venue" ESCAPED_STRING "{" venue_prop* "}"
modify_venue: "modify_venue" ESCAPED_STRING "{" venue_prop* "}"

venue_prop: "capacity" ":" NUMBER -> venue_capacity
          | "has_av_system" ":" CNAME -> venue_has_av // true or false

// Scheduler/Admin action
schedule_session: "schedule_session" ESCAPED_STRING "{" session_prop* "}"

session_prop: "hosted_by" ":" ESCAPED_STRING -> session_speaker
            | "in_venue" ":" ESCAPED_STRING -> session_venue
            | "expected_attendees" ":" NUMBER -> session_attendees
            | "requires_av" ":" CNAME -> session_requires_av

%import common.CNAME
%import common.NUMBER
%import common.ESCAPED_STRING
%import common.WS
%ignore WS