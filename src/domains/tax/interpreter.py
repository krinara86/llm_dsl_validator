# src/domains/tax/interpreter.py
from ...framework.base_interpreter import BaseInterpreter, v_args

class BillInterpreter(BaseInterpreter):
    # --- Business Rules ---
    VALID_MENU_ITEMS = {"burger", "fries", "soda", "shake", "water", "salad"}
    MAX_ITEM_PRICE = 50.0

    def __init__(self):
        self.net_food_cost = 0
        self.net_drink_cost = 0

    def _validate_and_classify(self, item_name, total_value):
        item_name_str = str(item_name).lower()

        if item_name_str not in self.VALID_MENU_ITEMS:
            raise ValueError(f"Validation Error: Item '{item_name_str}' is not on the menu.")

        if total_value > self.MAX_ITEM_PRICE:
            raise ValueError(f"Validation Error: Item '{item_name_str}' with price €{total_value:.2f} exceeds the maximum of €{self.MAX_ITEM_PRICE:.2f}.")

        if item_name_str in ["burger", "fries", "salad"]:
            self.net_food_cost += total_value
        elif item_name_str in ["soda", "shake", "water"]:
            self.net_drink_cost += total_value

    @v_args(inline=True)
    def line_item_with_quantity(self, item_name, quantity, price):
        total_value = float(quantity) * float(price)
        self._validate_and_classify(item_name, total_value)

    @v_args(inline=True)
    def line_item_simple(self, item_name, value):
        total_value = float(value)
        self._validate_and_classify(item_name, total_value)

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