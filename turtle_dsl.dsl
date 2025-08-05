
start: draw

draw: "draw" "{" program "}"

program: (line)*

line: command (value)?

command: "c" -> color
        | "f" -> forward
        | "b" -> backward
        | "r" -> right
        | "l" -> left
        | "u" -> penup
        | "d" -> pendown

// Use the specific ESCAPED_STRING terminal for the color value
value: NUMBER | ESCAPED_STRING

%import common.NUMBER
%import common.ESCAPED_STRING
%import common.WS
%ignore WS