start: event_command

event_command: "role" ESCAPED_STRING "{" command* "}"

command: create_venue | modify_venue | schedule_session | find_venue | find_session

// Venue actions
create_venue: "create_venue" ESCAPED_STRING "{" venue_prop* "}"
modify_venue: "modify_venue" ESCAPED_STRING "{" venue_prop* "}"

venue_prop: "capacity" ":" NUMBER -> venue_capacity
          | "has_av_system" ":" CNAME -> venue_has_av // true or false

// Session actions
schedule_session: "schedule_session" ESCAPED_STRING "{" session_prop* "}"

session_prop: "hosted_by" ":" ESCAPED_STRING -> session_speaker
            | "in_venue" ":" ESCAPED_STRING -> session_venue
            | "expected_attendees" ":" NUMBER -> session_attendees
            | "requires_av" ":" CNAME -> session_requires_av


find_venue: "find_venue" "{" venue_search_criteria* "}"
find_session: "find_session" "{" session_search_criteria* "}"


venue_search_criteria: "name_pattern" ":" ESCAPED_STRING -> venue_name_pattern
                     | "min_capacity" ":" NUMBER -> venue_min_capacity
                     | "max_capacity" ":" NUMBER -> venue_max_capacity
                     | "has_av" ":" CNAME -> venue_has_av_filter


session_search_criteria: "name_pattern" ":" ESCAPED_STRING -> session_name_pattern
                       | "hosted_by_pattern" ":" ESCAPED_STRING -> session_hosted_by_pattern
                       | "in_venue" ":" ESCAPED_STRING -> session_in_venue
                       | "min_attendees" ":" NUMBER -> session_min_attendees
                       | "max_attendees" ":" NUMBER -> session_max_attendees
                       | "requires_av" ":" CNAME -> session_requires_av_filter

%import common.CNAME
%import common.NUMBER
%import common.ESCAPED_STRING
%import common.WS
%ignore WS