# src/interpreters/base_interpreter.py
from lark import Lark, Transformer, v_args

class BaseInterpreter(Transformer):
    def CNAME(self, cname):
        return cname.value

    def NUMBER(self, num):
        return float(num.value)

    def STRING(self, s):
        return s[1:-1] # Removes the surrounding quotes

def execute_dsl(dsl_text: str, grammar_path: str, interpreter_class) -> dict:
    with open(grammar_path, 'r') as f:
        grammar = f.read()

    parser = Lark(grammar)
    tree = parser.parse(dsl_text)

    interpreter = interpreter_class()
    transformed_tree = interpreter.transform(tree)
    return transformed_tree.children[0]