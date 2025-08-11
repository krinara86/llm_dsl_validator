start: conference_plan

conference_plan: "conference_plan" ESCAPED_STRING "{" plan_item* "}"

plan_item: speaker | session

speaker: "speaker" ESCAPED_STRING -> speaker_def

session: "session" ESCAPED_STRING "{" session_prop* "}"
session_prop: "hosted_by" ":" ESCAPED_STRING -> session_speaker
            | "in_venue" ":" ESCAPED_STRING -> session_venue
            | "expected_attendees" ":" NUMBER -> session_attendees
            | "requires_av" ":" CNAME -> session_requires_av // CNAME will be 'true' or 'false'

%import common.CNAME
%import common.NUMBER
%import common.ESCAPED_STRING
%import common.WS
%ignore WS