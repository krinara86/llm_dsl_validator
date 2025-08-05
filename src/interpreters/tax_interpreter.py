# src/interpreters/tax_interpreter.py
from .base_interpreter import BaseInterpreter, v_args

class BillInterpreter(BaseInterpreter):
    def __init__(self):
        self.net_food_cost = 0
        self.net_drink_cost = 0

    def _classify_and_add(self, item_name, total_value):
        item_name_str = str(item_name).lower()
        if item_name_str in ["burger", "fries", "food"]:
            self.net_food_cost += total_value
        elif item_name_str in ["soda", "shake", "drink"]:
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