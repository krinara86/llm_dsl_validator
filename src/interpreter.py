from lark import Lark, Transformer, v_args

class BillInterpreter(Transformer):
    def __init__(self):
        self.net_food_cost = 0
        self.net_drink_cost = 0

    def _classify_and_add(self, item_name, total_value):
        item_name_str = str(item_name).lower()
        if item_name_str in ["schnitzel", "salad", "food"]:
            self.net_food_cost += total_value
        elif item_name_str in ["beer", "water", "wine", "drink"]:
            self.net_drink_cost += total_value

    @v_args(inline=True)
    def line_item_with_quantity(self, item_name, quantity, price):
        total_value = float(quantity) * float(price)
        self._classify_and_add(item_name, total_value)

    @v_args(inline=True)
    def line_item_simple(self, item_name, value):
        total_value = float(value)
        self._classify_and_add(item_name, total_value)

    def bill(self, items):
        food_tax = self.net_food_cost * 0.07
        drink_tax = self.net_drink_cost * 0.19
        total_bill = self.net_food_cost + self.net_drink_cost + food_tax + drink_tax

        return {
            "net_food_cost": self.net_food_cost,
            "net_drink_cost": self.net_drink_cost,
            "total_tax": food_tax + drink_tax,
            "final_bill": total_bill
        }

    def CNAME(self, cname):
        return cname.value

    def NUMBER(self, num):
        return float(num.value)


def calculate_bill_from_dsl(dsl_text: str, grammar_path: str) -> dict:
    with open(grammar_path, 'r') as f:
        grammar = f.read()

    parser = Lark(grammar)
    tree = parser.parse(dsl_text)

    interpreter = BillInterpreter()
    # The result of the transform is the first (and only) child of the tree.
    result = interpreter.transform(tree)
    return result