// Grammar for our Tax Calculation DSL

start: bill

bill: "bill" "{" items "}"

items: item+

// A line item can now have two forms
item: CNAME ":" NUMBER "*" NUMBER -> line_item_with_quantity
    | CNAME ":" NUMBER           -> line_item_simple

// --- Terminal Definitions ---
%import common.CNAME
%import common.NUMBER
%import common.WS
%ignore WS