from lark import Lark, Transformer, v_args

class BillInterpreter(Transformer):
    def __init__(self):
        self.net_food_cost = 0
        self.net_drink_cost = 0

    @v_args(inline=True)
    def line_item(self, item_name, value):
        item_name_str = str(item_name).lower()
        item_value = float(value)

        if item_name_str in ["schnitzel", "salad", "food"]:
            self.net_food_cost += item_value
        elif item_name_str in ["beer", "water", "wine", "drink"]:
            self.net_drink_cost += item_value

    def bill(self, items):
        food_tax = self.net_food_cost * 0.07
        drink_tax = self.net_drink_cost * 0.19
        total_bill = self.net_food_cost + self.net_drink_cost + food_tax + drink_tax

        return {
            "net_food_cost": self.net_food_cost,
            "net_drink_cost": self.net_drink_cost,
            "food_tax": food_tax,
            "drink_tax": drink_tax,
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
    result = interpreter.transform(tree)

    return result