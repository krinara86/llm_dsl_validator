// Grammar for our Tax Calculation DSL

start: bill

bill: "bill" "{" items "}"

items: item+

item: CNAME ":" NUMBER -> line_item

// --- Terminal Definitions ---
// These define the basic building blocks (tokens) of our language.
%import common.CNAME
%import common.NUMBER
%import common.WS
%ignore WS // Tell Lark to ignore whitespace between tokens