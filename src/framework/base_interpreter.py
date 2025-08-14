# src/framework/base_interpreter.py
from lark import Lark, Transformer, v_args

class BaseInterpreter(Transformer):
    def CNAME(self, cname):
        return cname.value

    def NUMBER(self, num):
        return float(num.value)

    def ESCAPED_STRING(self, s):
        return s[1:-1].replace('\\"', '"').replace('\\\\', '\\')

def execute_dsl(dsl_text: str, grammar_path: str, interpreter_instance) -> dict:
    """
    Executes DSL text using a pre-configured interpreter instance.
    
    Args:
        dsl_text: The string containing the DSL code.
        grammar_path: The file path to the Lark grammar.
        interpreter_instance: An already created instance of an interpreter class.
    """
    with open(grammar_path, 'r') as f:
        grammar = f.read()

    parser = Lark(grammar)
    tree = parser.parse(dsl_text)

    # The key change: Use the provided INSTANCE directly. Do not create a new one.
    transformed_tree = interpreter_instance.transform(tree)
    
    if hasattr(transformed_tree, 'children') and transformed_tree.children:
        # This handles grammars that might produce a list of results
        return transformed_tree.children[0]
    return transformed_tree