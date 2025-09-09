# src/domains/event/grammar.dsl

?start: event_command

event_command: role_statement "{" (create_venue | modify_venue | schedule_session | find_venues | find_sessions)* "}"

role_statement: "role" ESCAPED_STRING

// State-changing operations
create_venue: "create_venue" ESCAPED_STRING "{" venue_properties "}"
modify_venue: "modify_venue" ESCAPED_STRING "{" venue_properties "}"
schedule_session: "schedule_session" ESCAPED_STRING "{" session_properties "}"

// Read-only operations
find_venues: "find_venues" "{" find_venue_criteria "}"
find_sessions: "find_sessions" "{" find_session_criteria "}"

// Properties for state-changing operations
venue_properties: venue_capacity? venue_has_av?
venue_capacity: "capacity:" NUMBER
venue_has_av: "has_av_system:" CNAME

session_properties: session_venue session_attendees session_requires_av session_speaker
session_venue: "in_venue:" ESCAPED_STRING
session_attendees: "expected_attendees:" NUMBER
session_requires_av: "requires_av:" CNAME
session_speaker: "hosted_by:" ESCAPED_STRING

// Criteria for find operations
find_venue_criteria: find_venue_min_capacity? find_venue_has_av? find_venue_available? find_venue_name_contains?
find_venue_min_capacity: "min_capacity:" NUMBER
find_venue_has_av: "has_av_system:" CNAME
find_venue_available: "is_available:" CNAME
find_venue_name_contains: "name_contains:" ESCAPED_STRING

find_session_criteria: find_session_name_contains? find_session_hosted_by? find_session_in_venue? find_session_min_attendees? find_session_requires_av?
find_session_name_contains: "name_contains:" ESCAPED_STRING
find_session_hosted_by: "hosted_by:" ESCAPED_STRING
find_session_in_venue: "in_venue:" ESCAPED_STRING
find_session_min_attendees: "min_attendees:" NUMBER
find_session_requires_av: "requires_av:" CNAME

// Terminals
%import common.ESCAPED_STRING
%import common.CNAME
%import common.NUMBER
%import common.WS
%ignore WS