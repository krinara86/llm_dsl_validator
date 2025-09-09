# src/ui/interface.py
"""Simplified UI interface for the chatbot with improved input widgets."""

import re
import ipywidgets as widgets
from IPython.display import display, HTML
from typing import Optional, Dict, List
from ..domains.event.schema import DOMAIN_SCHEMA

class ChatInterface:
    """Main chat interface for the event system."""
    
    def __init__(self, event_system):
        self.system = event_system
        self.conversation_state = {}
        self.task_queue = []
        self.current_task_index = 0
        self.total_tasks = 0
        self.clarification_widgets = []  # Store widgets for parameter input
        
        # Initialize UI components
        self._create_widgets()
        self._setup_handlers()
        self._apply_styles()
    
    def _create_widgets(self):
        """Create all UI widgets."""
        # Header
        self.header = widgets.HTML(
            "<h1>Event Management Assistant 🎯</h1>"
            "<p>Manage venues and schedule sessions using natural language.</p>"
        )
        
        # Model and role selection
        available_models = self.system.get_available_models()
        self.model_selector = widgets.Dropdown(
            options=available_models,
            value=available_models[0] if available_models else None,
            description='Model:'
        )
        
        self.role_selector = widgets.RadioButtons(
            options=['admin', 'scheduler', 'viewer'],
            value='admin',
            description='Role:'
        )
        
        # State display
        self.state_display = widgets.HTML()
        self.state_accordion = widgets.Accordion(
            children=[self.state_display],
            titles=('📊 Current State',)
        )
        self.state_accordion.selected_index = None
        
        # Progress indicator
        self.progress_label = widgets.HTML()
        
        # Chat area
        self.chat_history = widgets.VBox([])
        self.user_input = widgets.Textarea(
            placeholder='Type your request or paste a document...',
            layout={'width': '95%', 'height': '80px'}
        )
        
        # Clarification input area (initially hidden)
        self.clarification_area = widgets.VBox([])
        
        # Buttons
        self.send_button = widgets.Button(
            description='Send',
            button_style='success',
            icon='paper-plane'
        )
        
        self.clear_button = widgets.Button(
            description='Clear',
            button_style='warning',
            icon='trash'
        )
        
        self.confirm_button = widgets.Button(
            description='✅ Confirm',
            button_style='success',
            layout={'visibility': 'hidden'}
        )
        
        self.cancel_button = widgets.Button(
            description='❌ Cancel',
            button_style='danger',
            layout={'visibility': 'hidden'}
        )
        
        self.submit_params_button = widgets.Button(
            description='Submit Parameters',
            button_style='primary',
            icon='check',
            layout={'visibility': 'hidden'}
        )
    
    def _setup_handlers(self):
        """Setup event handlers for buttons."""
        self.send_button.on_click(self._on_send)
        self.clear_button.on_click(self._on_clear)
        self.confirm_button.on_click(self._on_confirm)
        self.cancel_button.on_click(self._on_cancel)
        self.submit_params_button.on_click(self._on_submit_params)
    
    def _apply_styles(self):
        """Apply CSS styles."""
        self.styles = HTML("""
        <style>
        .chat-bubble {
            max-width: 80%;
            padding: 12px;
            border-radius: 10px;
            margin: 8px 0;
            line-height: 1.5;
        }
        .user-bubble {
            background-color: #E3F2FD;
            margin-left: 20%;
            border: 1px solid #90CAF9;
        }
        .assistant-bubble {
            background-color: #F3E5F5;
            margin-right: 20%;
            border: 1px solid #CE93D8;
        }
        .system-bubble {
            background-color: #E8F5E9;
            margin: 0 auto;
            width: 60%;
            text-align: center;
            border: 1px solid #A5D6A7;
        }
        .param-input-area {
            background-color: #f0f7ff;
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
            border: 1px solid #90CAF9;
        }
        </style>
        """)
    
    def display(self):
        """Display the complete interface."""
        display(self.styles)
        
        # Build layout
        controls = widgets.HBox([self.model_selector, self.role_selector])
        input_area = widgets.HBox([self.user_input, self.send_button, self.clear_button])
        confirm_area = widgets.HBox([self.confirm_button, self.cancel_button])
        
        layout = widgets.VBox([
            self.header,
            controls,
            widgets.HTML("<hr>"),
            self.state_accordion,
            self.progress_label,
            self.chat_history,
            self.clarification_area,  # Add clarification area
            input_area,
            confirm_area,
            self.submit_params_button  # Add submit params button
        ])
        
        display(layout)
        
        # Initialize
        self._on_clear(None)
        self._update_state_display()
    
    def _add_message(self, content: str, msg_type: str = 'assistant'):
        """Add a message to the chat history."""
        bubble_class = {
            'user': 'user-bubble',
            'assistant': 'assistant-bubble',
            'system': 'system-bubble'
        }.get(msg_type, 'assistant-bubble')
        
        html = f"<div class='chat-bubble {bubble_class}'>{content}</div>"
        self.chat_history.children = list(self.chat_history.children) + [widgets.HTML(html)]
    
    def _create_input_widgets_for_params(self, missing_params: List[str], task_details: Dict) -> Dict[str, widgets.Widget]:
        """Create appropriate input widgets for missing parameters."""
        param_widgets = {}
        action = task_details.get("action", "")
        
        if action not in DOMAIN_SCHEMA:
            return param_widgets
        
        param_types = DOMAIN_SCHEMA[action].get("param_types", {})
        state = self.system.get_current_state()
        
        for param in missing_params:
            param_info = param_types.get(param, {})
            param_type = param_info.get("type", "string")
            param_label = param.replace('_', ' ').title()
            
            if param_type == "boolean":
                # Create radio buttons for boolean
                widget = widgets.RadioButtons(
                    options=['Yes', 'No'],
                    description=f'{param_label}:',
                    style={'description_width': 'initial'}
                )
                param_widgets[param] = widget
                
            elif param_type == "number":
                # Create number input
                widget = widgets.IntText(
                    description=f'{param_label}:',
                    style={'description_width': 'initial'}
                )
                param_widgets[param] = widget
                
            elif param_type == "venue_selection":
                # Create dropdown for venue selection
                venues = list(state.get('venues', {}).keys())
                if venues:
                    widget = widgets.Dropdown(
                        options=[''] + venues,  # Add empty option
                        description=f'{param_label}:',
                        style={'description_width': 'initial'}
                    )
                else:
                    widget = widgets.Text(
                        description=f'{param_label}:',
                        placeholder='No venues available',
                        style={'description_width': 'initial'}
                    )
                param_widgets[param] = widget
                
            else:
                # Default to text input
                widget = widgets.Text(
                    description=f'{param_label}:',
                    placeholder=f'Enter {param_label.lower()}',
                    style={'description_width': 'initial'}
                )
                param_widgets[param] = widget
        
        return param_widgets
    
    def _on_send(self, b):
        """Handle send button click."""
        query = self.user_input.value.strip()
        if not query:
            return
        
        # Clear any existing clarification widgets
        self.clarification_area.children = []
        self.clarification_widgets = []
        self.submit_params_button.layout.visibility = 'hidden'
        
        if len(query) > 300 and not self.conversation_state:
            self._process_document(query)
        else:
            self._process_query(query)
    
    def _process_query(self, query: str, pre_filled_details: dict = None):
        """Process a single query, potentially with pre-filled details."""
        if not pre_filled_details:
             self._add_message(f"<b>You:</b> {query}", 'user')
        self.user_input.value = ''
        
        result = self.system.process_query(
            query,
            self.role_selector.value,
            self.model_selector.value,
            self.conversation_state,
            pre_filled_details
        )
        
        self.conversation_state = result.get('new_state', self.conversation_state)
        
        # Handle response
        if result['status'] == 'clarification_needed':
            if 'understanding_html' in result:
                self._add_message(result['understanding_html'])
            
            # Create input widgets for missing parameters
            self._show_parameter_inputs(result)
            
        elif result['status'] == 'confirmation_needed':
            if 'understanding_html' in result:
                self._add_message(result['understanding_html'])
            self._add_message(result['message'])
            self._show_confirmation_buttons(True)
            
        elif result['status'] == 'execute_immediately':
            # For read-only operations, execute immediately
            if 'understanding_html' in result:
                self._add_message(result['understanding_html'])
            self._execute_task_immediate()
            
        else:  # Error
            self._add_message(f"<b>Assistant:</b><br>{result['message']}")
            self._reset_conversation()
    
    def _show_parameter_inputs(self, result: Dict):
        """Show input widgets for missing parameters."""
        missing_params = self.conversation_state.get('missing_params', [])
        task_details = self.conversation_state.get('task_details', {})
        
        if not missing_params:
            return
        
        # Create header
        header = widgets.HTML(
            "<div class='param-input-area'>"
            "<b>Please provide the following information:</b>"
            "</div>"
        )
        
        # Create input widgets
        self.clarification_widgets = self._create_input_widgets_for_params(missing_params, task_details)
        
        # Arrange widgets in a nice layout
        widget_list = [header]
        for param_name, widget in self.clarification_widgets.items():
            widget_list.append(widget)
        
        # Add widgets to clarification area
        self.clarification_area.children = widget_list
        
        # Show submit button
        self.submit_params_button.layout.visibility = 'visible'
        self.user_input.disabled = True
        self.send_button.disabled = True
    
    def _on_submit_params(self, b):
        """Handle parameter submission from widgets."""
        # Collect values from widgets
        collected_values = []
        
        for param_name, widget in self.clarification_widgets.items():
            if isinstance(widget, widgets.RadioButtons):
                value = 'yes' if widget.value == 'Yes' else 'no'
            elif isinstance(widget, widgets.IntText):
                value = str(widget.value)
            elif isinstance(widget, widgets.Dropdown):
                value = widget.value
            elif isinstance(widget, widgets.Text):
                value = widget.value
            else:
                value = str(widget.value)
            
            if value and value != '':
                collected_values.append(f"{param_name}: {value}")
        
        # Build response string
        response = '\n'.join(collected_values)
        
        # Clear clarification area
        self.clarification_area.children = []
        self.clarification_widgets = []
        self.submit_params_button.layout.visibility = 'hidden'
        self.user_input.disabled = False
        self.send_button.disabled = False
        
        # Process the response
        if response:
            self._add_message(f"<b>You:</b><br>{response.replace(chr(10), '<br>')}", 'user')
            self._process_query(response)
    
    def _execute_task_immediate(self):
        """Execute a task immediately (for read-only operations)."""
        self._add_message("<i>Searching...</i>")
        
        result = self.system.execute_task(
            self.role_selector.value,
            self.conversation_state
        )
        
        # Remove searching message
        self.chat_history.children = self.chat_history.children[:-1]
        
        if result['status'] in ['success', 'search_results']:
            self._add_message(f"<b>Results:</b><br>{result['message']}")
            
            # Show DSL code if available and not a search
            if result['status'] == 'success' and 'dsl_code' in result and result['dsl_code']:
                self._show_dsl_code(result['dsl_code'])
        else:
            self._add_message(f"<b>Assistant:</b> {result['message']}")
        
        self._reset_conversation()
        self._process_next_task()
    
    def _process_document(self, document: str):
        """Process a document with multiple tasks."""
        self._add_message(f"<b>You:</b> [Document with {len(document)} characters]", 'user')
        self.user_input.value = ''
        
        result = self.system.process_document(
            document,
            self.role_selector.value,
            self.model_selector.value
        )
        
        self._add_message(f"<b>Assistant:</b> {result['message']}")
        
        if result['status'] == 'tasks_extracted' and result['tasks']:
            self.task_queue = result['tasks']
            self.total_tasks = len(self.task_queue)
            self._process_next_task()
    
    def _process_next_task(self):
        """Process the next task in the queue."""
        if not self.task_queue:
            if self.total_tasks > 1:
                self._add_message(f"✅ Completed all {self.total_tasks} tasks!", 'system')
            self.total_tasks = 0
            self.current_task_index = 0
            return
        
        self.current_task_index = self.total_tasks - len(self.task_queue) + 1
        task_object = self.task_queue.pop(0)
        
        task_description = task_object.get("task_description", "Unnamed Task")
        
        details_for_orchestrator = {
            "action": task_object.get("action", "unknown"),
            "parameters": task_object.get("details", {})
        }
        
        self._add_message(f"<b>Processing Task {self.current_task_index}/{self.total_tasks}:</b> {task_description}", 'system')
        self._process_query(task_description, details_for_orchestrator)
    
    def _on_confirm(self, b):
        """Handle confirmation button click."""
        self._show_confirmation_buttons(False)
        self._add_message("<i>Executing task...</i>")
        
        result = self.system.execute_task(
            self.role_selector.value,
            self.conversation_state
        )
        
        # Remove executing message
        self.chat_history.children = self.chat_history.children[:-1]
        
        if result['status'] == 'success':
            self._add_message(f"<b>Assistant:</b> {result['message']}", 'system')
            
            # Show DSL code if available
            if 'dsl_code' in result and result['dsl_code']:
                self._show_dsl_code(result['dsl_code'])
            
            self._update_state_display()
        else:
            self._add_message(f"<b>Assistant:</b> {result['message']}")
        
        self._reset_conversation()
        self._process_next_task()
    
    def _on_cancel(self, b):
        """Handle cancel button click."""
        self._show_confirmation_buttons(False)
        self._add_message("<b>Assistant:</b> Task cancelled.", 'system')
        self._reset_conversation()
        self._process_next_task()
    
    def _on_clear(self, b):
        """Handle clear button click."""
        self._reset_conversation()
        self.task_queue = []
        self.total_tasks = 0
        self.current_task_index = 0
        self.clarification_area.children = []
        self.clarification_widgets = []
        self.submit_params_button.layout.visibility = 'hidden'
        
        welcome_msg = (
            "<b>Assistant:</b><br>"
            "Hello! I can help you manage event venues and sessions. "
            "You can create venues, schedule sessions, or search for information. "
            "What would you like to do?"
        )
        self.chat_history.children = [widgets.HTML(f"<div class='chat-bubble assistant-bubble'>{welcome_msg}</div>")]
        self._show_confirmation_buttons(False)
    
    def _show_confirmation_buttons(self, show: bool):
        """Show or hide confirmation buttons."""
        visibility = 'visible' if show else 'hidden'
        self.confirm_button.layout.visibility = visibility
        self.cancel_button.layout.visibility = visibility
        self.user_input.disabled = show
        self.send_button.disabled = show
    
    def _show_dsl_code(self, dsl_code: str):
        """Display DSL code in an accordion."""
        dsl_html = f"<pre style='background-color:#f5f5f5; padding:10px;'>{dsl_code}</pre>"
        dsl_accordion = widgets.Accordion(
            children=[widgets.HTML(dsl_html)],
            titles=('🔍 Generated DSL Code',)
        )
        dsl_accordion.selected_index = None
        self.chat_history.children = list(self.chat_history.children) + [dsl_accordion]
    
    def _reset_conversation(self):
        """Reset the conversation state."""
        self.conversation_state = {}
        self.user_input.disabled = False
        self.send_button.disabled = False
    
    def _update_state_display(self):
        """Update the state display."""
        try:
            state = self.system.get_current_state()
            venues = state.get('venues', {})
            sessions = state.get('sessions', [])
            bookings = state.get('venue_bookings', {})
            
            # Venues table
            html = "<h4>Venues</h4><table border='1' style='width:100%;'>"
            html += "<tr><th>Name</th><th>Capacity</th><th>A/V</th><th>Status</th></tr>"
            
            for name, props in venues.items():
                status = "Booked" if name in bookings else "Available"
                av = "✅" if props.get('has_av_system') else "❌"
                html += f"<tr><td>{name}</td><td>{props.get('capacity')}</td><td>{av}</td><td>{status}</td></tr>"
            
            if not venues:
                html += "<tr><td colspan='4'><i>No venues yet</i></td></tr>"
            html += "</table>"
            
            # Sessions table
            html += "<h4 style='margin-top:15px;'>Scheduled Sessions</h4>"
            html += "<table border='1' style='width:100%;'>"
            html += "<tr><th>Name</th><th>Venue</th><th>Host</th><th>Attendees</th><th>A/V</th></tr>"
            
            for session in sessions:
                av = "✅" if session.get('requires_av') else "❌"
                html += (f"<tr><td>{session.get('name', 'N/A')}</td>"
                        f"<td>{session.get('in_venue', 'N/A')}</td>"
                        f"<td>{session.get('hosted_by', 'N/A')}</td>"
                        f"<td>{session.get('expected_attendees', 'N/A')}</td>"
                        f"<td>{av}</td></tr>")
            
            if not sessions:
                html += "<tr><td colspan='5'><i>No sessions scheduled yet</i></td></tr>"
            html += "</table>"
            
            self.state_display.value = html
            
        except Exception as e:
            self.state_display.value = f"<p style='color:red;'>Error: {e}</p>"