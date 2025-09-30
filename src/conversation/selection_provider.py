# src/conversation/selection_provider.py
"""Selection providers for different backend systems."""

from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod


class SelectionProvider(ABC):
    """Abstract base class for providing selection options for clarification forms."""
    
    @abstractmethod
    def get_options(self, selection_type: str, context: Dict[str, Any]) -> List[str]:
        """
        Get available options for a selection field.
        
        Args:
            selection_type: Type of selection (e.g., 'venue_selection', 'team_selection')
            context: Additional context like task_details, current parameters
            
        Returns:
            List of string options for the dropdown
        """
        pass


class StateBasedSelectionProvider(SelectionProvider):
    """Selection provider for systems using StateManager (Event/Lark)."""
    
    def __init__(self, state_manager):
        """
        Initialize with a state manager.
        
        Args:
            state_manager: StateManager instance for loading domain state
        """
        self.state_manager = state_manager
    
    def get_options(self, selection_type: str, context: Dict[str, Any]) -> List[str]:
        """Get options based on state.json data."""
        print(f"[DEBUG] get_options called with selection_type: {selection_type}")
        print(f"[DEBUG] Context: {context}")
        
        if not self.state_manager:
            print("[DEBUG] No state_manager!")
            return ["No options available"]
            
        state = self.state_manager.load()
        print(f"[DEBUG] State has {len(state.get('venues', {}))} venues")
        
        task_details = context.get("task_details", {})
        print(f"[DEBUG] Task details: {task_details}")
        
        if selection_type == "venue_selection":
            result = self._get_suitable_venues(task_details, state)
            print(f"[DEBUG] _get_suitable_venues returned: {result[:3] if len(result) > 3 else result}")
            return result
        else:
            return ["No options available"]

    def _get_suitable_venues(self, task_details: Dict, state: Dict) -> List[str]:
        """Get venues that meet the requirements."""
        params = task_details.get("parameters", {})
        attendees_req = params.get("expected_attendees", 0)
        av_req = params.get("requires_av", False)
        
        print(f"[DEBUG] Looking for venues with capacity >= {attendees_req}, AV required: {av_req}")
        
        suitable_venues = []
        venues = state.get("venues", {})
        bookings = state.get("venue_bookings", {})
        
        for name, props in venues.items():
            # Venue must be available (not booked)
            if name not in bookings:
                capacity = props.get("capacity", 0)
                has_av = props.get("has_av_system", False)
                # Check if venue meets requirements
                if capacity >= attendees_req and (not av_req or has_av):
                    suitable_venues.append(name)
        
        print(f"[DEBUG] Found {len(suitable_venues)} suitable venues out of {len(venues)} total")
        
        return suitable_venues if suitable_venues else ["No suitable venues available"]


class LionWebSelectionProvider(SelectionProvider):
    """Selection provider for LionWeb-based systems."""
    
    def __init__(self, loader, domain: str):
        """
        Initialize with a LionWeb loader and domain.
        
        Args:
            loader: LionWebConnectorLoader instance
            domain: Domain name (e.g., 'cycling')
        """
        self.loader = loader
        self.domain = domain
    
    def get_options(self, selection_type: str, context: Dict[str, Any]) -> List[str]:
        """Get options from LionWeb M1 instances."""
        # Map selection type to concept name
        # e.g., "team_selection" -> "Team"
        if selection_type == "team_selection":
            concept_name = "Team"
        elif selection_type == "rider_selection":
            concept_name = "Rider"
        else:
            # Try to infer from selection type
            concept_name = selection_type.replace("_selection", "").title()
        
        try:
            # Find all instances of this concept
            instances = self.loader.find_m1_instances(self.domain, concept_name)
            
            # Extract names from instances
            names = []
            for instance in instances:
                # Get the name property
                name_feature = instance.get_classifier().get_feature_by_name("name")
                if name_feature:
                    name_value = instance.get_property_value(name_feature)
                    if name_value:
                        names.append(str(name_value))
            
            return names if names else [f"No {concept_name.lower()}s available"]
            
        except Exception as e:
            # If something goes wrong, return a safe default
            return [f"Error loading {selection_type}: {str(e)}"]


class NullSelectionProvider(SelectionProvider):
    """Fallback provider that returns empty options."""
    
    def get_options(self, selection_type: str, context: Dict[str, Any]) -> List[str]:
        """Always returns a message indicating no options."""
        return ["Options not available"]