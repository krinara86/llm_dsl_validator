
start: ride
ride: "ride" "{" properties "}"
properties: property+
property: CNAME ":" (CNAME | NUMBER) -> prop_line


%import common.CNAME
%import common.NUMBER
%import common.WS
%ignore WS