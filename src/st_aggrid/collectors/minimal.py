"""
Minimal collector for lightweight AgGrid responses
"""

from typing import Any

from .base import BaseCollector


class MinimalResponse:
    """
    Minimal response object for the MINIMAL DataReturnMode.
    Provides only essential data with minimal processing overhead.
    """
    
    def __init__(self, component_value: Any = None, original_data: Any = None):
        """
        Initialize minimal response with raw component value

        Parameters
        ----------
        component_value : Any
            Raw response from the AgGrid component
        original_data : Any
            The frame that was handed to the grid. It is what ``.data`` reports
            until the frontend sends something back, which is how every other
            data_return_mode behaves on a first render.
        """
        self._component_value = component_value
        self._original_data = original_data

    @property
    def raw_data(self) -> Any:
        """Access to the raw component data"""
        return self._component_value

    @property
    def data(self):
        """Rows from the grid, or the input frame before the first response.

        The frontend has not reported anything on a first render (and never
        does until an update_on event fires, which under update_mode=MANUAL
        means until the toolbar button is clicked). Returning None there made
        MINIMAL the only mode whose ``.data`` was empty on load; the input
        frame is what AS_INPUT, FILTERED and FILTERED_AND_SORTED all return.
        """
        if self._component_value and isinstance(self._component_value, dict):
            return self._component_value.get('data')
        return self._original_data

    @property
    def selected_rows(self):
        """Basic selected rows access"""
        if self._component_value and isinstance(self._component_value, dict):
            return self._component_value.get('selectedRows', [])
        return []
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Safe access to component data properties
        
        Parameters
        ----------
        key : str
            Key to access in component data
        default : Any
            Default value if key not found
            
        Returns
        -------
        Any
            Value for key or default
        """
        if self._component_value and isinstance(self._component_value, dict):
            return self._component_value.get(key, default)
        return default
    
    def __getitem__(self, key: str) -> Any:
        """Dictionary-style access to component data"""
        if self._component_value and isinstance(self._component_value, dict):
            return self._component_value[key]
        raise KeyError(f"Key '{key}' not found in component data")
    
    def __contains__(self, key: str) -> bool:
        """Check if key exists in component data"""
        if self._component_value and isinstance(self._component_value, dict):
            return key in self._component_value
        return False


class MinimalCollector(BaseCollector):
    """
    Collector for MINIMAL DataReturnMode that provides lightweight responses
    with minimal processing overhead.
    """
    
    def __init__(self):
        """Initialize the minimal collector"""
    
    def create_initial_response(self, original_data: Any, grid_options: dict, **kwargs) -> MinimalResponse:
        """
        Create an initial MinimalResponse object that can be safely referenced by callbacks
        """
        return MinimalResponse(original_data=original_data)

    def update_response(self, response: MinimalResponse, component_value: Any) -> MinimalResponse:
        """
        Update the MinimalResponse object with component data
        """
        if component_value:
            response._component_value = component_value
        return response
    
    def process_response(self, component_value: Any, original_data: Any, grid_options: dict) -> MinimalResponse:
        """
        Process response with minimal overhead - just wrap the raw component value
        """
        return MinimalResponse(component_value, original_data=original_data)
    
    def get_return_type(self) -> str:
        """Return type description for minimal collector"""
        return "MinimalResponse"
    
    def validate_response(self, response: Any) -> bool:
        """Validate that response is a MinimalResponse object"""
        return isinstance(response, MinimalResponse)