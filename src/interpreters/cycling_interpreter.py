# src/interpreters/cycling_interpreter.py
from .base_interpreter import BaseInterpreter, v_args



class RideInterpreter(BaseInterpreter):
    TERRAIN_SPEEDS = {
        "flat": 25.0,
        "hilly": 18.0,
        "mountainous": 12.0
    }

    @v_args(inline=True)
    def prop_line(self, key, value):
        return (str(key), value)

    def properties(self, items):
        return items

    def ride(self, children):
        props_list = children[0]
        props_dict = dict(props_list)

        distance = props_dict.get('distance_km', 0)
        terrain = str(props_dict.get('terrain', 'flat')).lower()
        
        speed = self.TERRAIN_SPEEDS.get(terrain, self.TERRAIN_SPEEDS["flat"])
        
        estimated_hours = distance / speed if speed > 0 else 0

        return {
            "input_properties": props_dict,
            "estimated_duration_hours": estimated_hours
        }