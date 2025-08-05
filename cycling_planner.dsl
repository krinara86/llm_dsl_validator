// Grammar for Cycling Ride Planner DSL
start: ride
ride: "ride" "{" properties "}"
properties: property+
// The value can now be a CNAME (unquoted word) or a NUMBER
property: CNAME ":" (CNAME | NUMBER) -> prop_line

// --- Terminal Definitions ---
%import common.CNAME
%import common.NUMBER
%import common.WS
%ignore WS