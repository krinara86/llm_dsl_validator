# src/interpreters/turtle_interpreter.py
import turtle
from .base_interpreter import BaseInterpreter, v_args

class TurtleInterpreter(BaseInterpreter):
    """
    This interpreter executes turtle graphics commands.
    It now collects all commands first, then executes them in a controlled
    turtle screen that closes properly.
    """
    def __init__(self):
        # We don't initialize turtle here anymore to prevent premature window pop-ups.
        pass

    def value(self, children):
        return children[0]

    # This method now returns a tuple representing a command, e.g., ('forward', 100)
    def line(self, children):
        command_func = children[0]
        value = children[1] if len(children) > 1 else None
        return (command_func, value)

    # This method now just collects the list of command tuples.
    def program(self, lines):
        return lines

    # The draw method now handles the entire turtle lifecycle.
    def draw(self, children):
        command_list = children[0]
        
        try:
            # 1. Setup the screen
            screen = turtle.Screen()
            screen.clearscreen()
            
            # 2. Create the turtle and execute commands
            t = turtle.Turtle()
            t.speed("fast")

            for command_func, value in command_list:
                if value is not None:
                    command_func(t, value)
                else:
                    command_func(t)
            
            # 3. Keep the window open until it's clicked.
            message = "Drawing complete. Click the window to close."
            screen.exitonclick()

        except turtle.Terminator:
            # This error is expected when the window is closed, so we can pass.
            message = "Turtle window closed by user."
        except Exception as e:
            return {"status": "error", "message": f"An error occurred during drawing: {e}"}
            
        return {"status": "success", "message": message}

    # --- Command Rules ---
    # These methods now return a *function* that takes the turtle instance `t` as an argument.
    def color(self, _): return lambda t, val: t.color(val)
    def forward(self, _): return lambda t, val: t.forward(val)
    def backward(self, _): return lambda t, val: t.backward(val)
    def right(self, _): return lambda t, val: t.right(val)
    def left(self, _): return lambda t, val: t.left(val)
    def penup(self, _): return lambda t: t.penup()
    def pendown(self, _): return lambda t: t.pendown()
