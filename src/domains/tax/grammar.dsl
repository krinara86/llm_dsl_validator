
start: bill

bill: "bill" "{" items "}"

items: item+

item: CNAME ":" NUMBER "*" NUMBER -> line_item_with_quantity
    | CNAME ":" NUMBER           -> line_item_simple

%import common.CNAME
%import common.NUMBER
%import common.WS
%ignore WS