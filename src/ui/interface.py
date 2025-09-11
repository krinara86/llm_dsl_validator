# src/ui/interface.py
"""Simplified UI interface for the chatbot."""

import ipywidgets as widgets
from IPython.display import display, HTML
from typing import Optional, List, Dict

class ChatInterface:
    """Main chat interface for the event system."""
    
    def __init__(self, event_system):
        self.system = event_system
        self.conversation_state = {}
        self.task_queue = []
        self.current_task_index = 0
        self.total_tasks = 0
        self.active_clarification_widgets = {}
        
        self._create_widgets()
        self._setup_handlers()
        self._apply_styles()
    
    def _create_widgets(self):
        """Create all UI widgets."""
        self.header = widgets.HTML(
            "<h1>Event Management Assistant 🎯</h1>"
            "<p>Manage venues and schedule sessions using natural language.</p>"
        )
        available_models = self.system.get_available_models()
        self.model_selector = widgets.Dropdown(
            options=available_models,
            value=available_models[0] if available_models else None,
            description='Model:'
        )
        self.role_selector = widgets.RadioButtons(
            options=['admin', 'scheduler'],
            value='admin',
            description='Role:'
        )
        self.state_display = widgets.HTML()
        self.state_accordion = widgets.Accordion(
            children=[self.state_display],
            titles=('📊 Current State',)
        )
        self.state_accordion.selected_index = None
        self.progress_label = widgets.HTML()
        self.chat_history = widgets.VBox([])
        self.user_input = widgets.Textarea(
            placeholder='Type your request or paste a document...',
            layout={'width': '95%', 'height': '80px'}
        )
        self.send_button = widgets.Button(
            description='Send', button_style='success', icon='paper-plane'
        )
        self.clear_button = widgets.Button(
            description='Clear', button_style='warning', icon='trash'
        )
        self.confirm_button = widgets.Button(
            description='✅ Confirm', button_style='success', layout={'visibility': 'hidden'}
        )
        self.cancel_button = widgets.Button(
            description='❌ Cancel', button_style='danger', layout={'visibility': 'hidden'}
        )
        self.clarification_form_area = widgets.VBox([])

    def _setup_handlers(self):
        """Setup event handlers for buttons."""
        self.send_button.on_click(self._on_send)
        self.clear_button.on_click(self._on_clear)
        self.confirm_button.on_click(self._on_confirm)
        self.cancel_button.on_click(self._on_cancel)

    def _on_send(self, b):
        """Handle send button click."""
        query = self.user_input.value.strip()
        if not query:
            return
        
        if len(query) > 300 and not self.conversation_state:
            self._process_document(query)
        else:
            self._process_query(query)

    def _process_query(self, query: str, pre_filled_details: dict = None):
        if not pre_filled_details:
             self._add_message(f"<b>You:</b> {query}", 'user')
        self.user_input.value = ''
        
        result = self.system.process_query(
            query, self.role_selector.value, self.model_selector.value,
            self.conversation_state, pre_filled_details
        )
        
        self.conversation_state = result.get('new_state', self.conversation_state)
        
        if result['status'] == 'clarification_needed':
            if 'understanding_html' in result: self._add_message(result['understanding_html'])
            # --- MODIFIED: Build and display the form ---
            self._build_clarification_form(result.get('clarification_data', {}))
            
        elif result['status'] == 'confirmation_needed':
            if 'understanding_html' in result: self._add_message(result['understanding_html'])
            self._add_message(result['message'])
            self._show_confirmation_buttons(True)
        
        elif result['status'] == 'direct_execute':
            if 'understanding_html' in result: self._add_message(result['understanding_html'])
            self._on_confirm(None)

        else:
            self._add_message(f"<b>Assistant:</b><br>{result['message']}")
            self._reset_conversation()

    def _build_clarification_form(self, clarification_data: Dict):
        self._clear_clarification_form()
        self.active_clarification_widgets = {}
        
        message = clarification_data.get("message", "Please provide more information.")
        fields = clarification_data.get("form_fields", [])
        
        form_elements = [widgets.HTML(f"<div class='assistant-bubble'>{message}</div>")]

        for field in fields:
            label = widgets.Label(f"{field['label']}:")
            prompt = widgets.HTML(f"<i style='font-size: smaller;'>{field['prompt']}</i>")
            
            widget = None
            if field["type"] == "boolean":
                widget = widgets.Checkbox(value=False, indent=False)
            elif field["type"] == "number":
                widget = widgets.IntText(value=0)
            elif field["type"] == "venue_selection":
                widget = widgets.Dropdown(options=field.get("options", []))
            else: # string
                widget = widgets.Text(value="")
            
            self.active_clarification_widgets[field["name"]] = widget
            form_elements.append(widgets.VBox([label, prompt, widget]))

        submit_button = widgets.Button(description="Submit Details", button_style='info', icon='check')
        submit_button.on_click(self._on_submit_clarification)
        
        form_elements.append(submit_button)
        self.clarification_form_area.children = form_elements
        self._toggle_main_input(False)

    def _on_submit_clarification(self, b):
        lines = []
        for name, widget in self.active_clarification_widgets.items():
            value = widget.value
            lines.append(f"{name}: {value}")
        
        query = "\n".join(lines)
        
        self._add_message(f"<b>You (form submission):</b><br><pre>{query}</pre>", 'user')
        self._clear_clarification_form()
        self._toggle_main_input(True) 
        
        self._process_query(query)

    def _clear_clarification_form(self):
        self.clarification_form_area.children = []
        self.active_clarification_widgets = {}

    def _toggle_main_input(self, enabled: bool):
        self.user_input.disabled = not enabled
        self.send_button.disabled = not enabled

    def _on_clear(self, b):
        """Handle clear button click."""
        self._reset_conversation()
        self.task_queue = []
        self.total_tasks = 0
        self.current_task_index = 0
        self._clear_clarification_form()
        self._toggle_main_input(True)
        
        welcome_msg = "<b>Assistant:</b><br>Hello! I can help you manage event venues and sessions. What would you like to do?"
        self.chat_history.children = [widgets.HTML(f"<div class='chat-bubble assistant-bubble'>{welcome_msg}</div>")]
        self._show_confirmation_buttons(False)

    def _on_cancel(self, b):
        """Handle cancel button click."""
        self._show_confirmation_buttons(False)
        self._add_message("<b>Assistant:</b> Task cancelled.", 'system')
        self._reset_conversation()
        self._process_next_task()

    def display(self):
        """Display the complete interface."""
        display(self.styles)
        
        controls = widgets.HBox([self.model_selector, self.role_selector])
        input_area = widgets.HBox([self.user_input, self.send_button, self.clear_button])
        confirm_area = widgets.HBox([self.confirm_button, self.cancel_button])
        
        layout = widgets.VBox([
            self.header, controls, widgets.HTML("<hr>"),
            self.state_accordion, self.progress_label,
            self.chat_history, 
            self.clarification_form_area, 
            input_area, confirm_area
        ])
        
        display(layout)
        self._on_clear(None)
        self._update_state_display()
        
    def _add_message(self, content: str, msg_type: str = 'assistant'):
        bubble_class = {'user': 'user-bubble', 'assistant': 'assistant-bubble', 'system': 'system-bubble'}.get(msg_type, 'assistant-bubble')
        html = f"<div class='chat-bubble {bubble_class}'>{content}</div>"
        self.chat_history.children = list(self.chat_history.children) + [widgets.HTML(html)]
    def _process_document(self, document: str):
        self._add_message(f"<b>You:</b> [Document with {len(document)} characters]", 'user')
        self.user_input.value = ''
        result = self.system.process_document(document, self.role_selector.value, self.model_selector.value)
        self._add_message(f"<b>Assistant:</b> {result['message']}")
        if result['status'] == 'tasks_extracted' and result['tasks']:
            self.task_queue = result['tasks']
            self.total_tasks = len(self.task_queue)
            self._process_next_task()
    def _process_next_task(self):
        if not self.task_queue:
            if self.total_tasks > 1: self._add_message(f"✅ Completed all {self.total_tasks} tasks!", 'system')
            self.total_tasks = 0
            self.current_task_index = 0
            return
        self.current_task_index = self.total_tasks - len(self.task_queue) + 1
        task_object = self.task_queue.pop(0)
        task_description = task_object.get("task_description", "Unnamed Task")
        details_for_orchestrator = {"action": task_object.get("action", "unknown"), "parameters": task_object.get("details", {})}
        self._add_message(f"<b>Processing Task {self.current_task_index}/{self.total_tasks}:</b> {task_description}", 'system')
        self._process_query(task_description, details_for_orchestrator)
    def _on_confirm(self, b):
        self._show_confirmation_buttons(False)
        self._add_message("<i>Executing...</i>", 'system')
        result = self.system.execute_task(self.role_selector.value, self.conversation_state)
        self.chat_history.children = self.chat_history.children[:-1]
        if result['status'] == 'success':
            self._add_message(f"<b>Assistant:</b> {result['message']}", 'system')
            if result.get('action_type') == 'query':
                self._display_query_results(result.get('results', []), self.conversation_state.get("task_details", {}).get("action"))
            else:
                self._update_state_display()
            if 'dsl_code' in result and result['dsl_code']:
                self._show_dsl_code(result['dsl_code'])
        else:
            self._add_message(f"<b>Assistant:</b> {result['message']}")
        self._reset_conversation()
        self._process_next_task()
    def _show_confirmation_buttons(self, show: bool):
        visibility = 'visible' if show else 'hidden'
        self.confirm_button.layout.visibility = visibility
        self.cancel_button.layout.visibility = visibility
        self._toggle_main_input(not show)
    def _show_dsl_code(self, dsl_code: str):
        dsl_html = f"<pre style='background-color:#f5f5f5; padding:10px;'>{dsl_code}</pre>"
        dsl_accordion = widgets.Accordion(children=[widgets.HTML(dsl_html)], titles=('📝 Generated DSL Code',))
        dsl_accordion.selected_index = None
        self.chat_history.children = list(self.chat_history.children) + [dsl_accordion]
    def _reset_conversation(self):
        self.conversation_state = {}
        self._toggle_main_input(True)
    def _update_state_display(self):
        try:
            state = self.system.get_current_state()
            venues = state.get('venues', {})
            sessions = state.get('sessions', [])
            bookings = state.get('venue_bookings', {})
            html = "<h4>Venues</h4><table border='1' style='width:100%;'><tr><th>Name</th><th>Capacity</th><th>A/V</th><th>Status</th></tr>"
            for name, props in venues.items():
                status = "Booked" if name in bookings else "Available"
                av = "✅" if props.get('has_av_system') else "❌"
                html += f"<tr><td>{name}</td><td>{props.get('capacity')}</td><td>{av}</td><td>{status}</td></tr>"
            if not venues: html += "<tr><td colspan='4'><i>No venues yet</i></td></tr>"
            html += "</table>"
            html += "<h4 style='margin-top:15px;'>Scheduled Sessions</h4><table border='1' style='width:100%;'><tr><th>Name</th><th>Venue</th><th>Host</th><th>Attendees</th><th>A/V</th></tr>"
            for session in sessions:
                av = "✅" if session.get('requires_av') else "❌"
                html += (f"<tr><td>{session.get('name', 'N/A')}</td><td>{session.get('in_venue', 'N/A')}</td><td>{session.get('hosted_by', 'N_A')}</td><td>{session.get('expected_attendees', 'N_A')}</td><td>{av}</td></tr>")
            if not sessions: html += "<tr><td colspan='5'><i>No sessions scheduled yet</i></td></tr>"
            html += "</table>"
            self.state_display.value = html
        except Exception as e:
            self.state_display.value = f"<p style='color:red;'>Error: {e}</p>"
    def _display_query_results(self, results: List[Dict], action: str):
        if not results: return
        html = ""
        if action == "find_venue":
            html += "<h4>Venue Search Results</h4><table border='1' style='width:100%;'><tr><th>Name</th><th>Capacity</th><th>A/V</th></tr>"
            for venue in results:
                av = "✅" if venue.get('has_av_system') else "❌"
                html += f"<tr><td>{venue.get('name')}</td><td>{venue.get('capacity')}</td><td>{av}</td></tr>"
        elif action == "find_session":
            html += "<h4 style='margin-top:15px;'>Session Search Results</h4><table border='1' style='width:100%;'><tr><th>Name</th><th>Venue</th><th>Host</th><th>Attendees</th><th>A/V</th></tr>"
            for session in results:
                av = "✅" if session.get('requires_av') else "❌"
                html += (f"<tr><td>{session.get('name', 'N/A')}</td><td>{session.get('in_venue', 'N/A')}</td><td>{session.get('hosted_by', 'N/A')}</td><td>{session.get('expected_attendees', 'N/A')}</td><td>{av}</td></tr>")
        html += "</table>"
        self._add_message(html, 'assistant')
    def _apply_styles(self):
        self.styles = HTML("<style>.chat-bubble{max-width:80%;padding:12px;border-radius:10px;margin:8px 0;line-height:1.5;}.user-bubble{background-color:#E3F2FD;margin-left:20%;border:1px solid #90CAF9;}.assistant-bubble{background-color:#F3E5F5;margin-right:20%;border:1px solid #CE93D8;}.system-bubble{background-color:#E8F5E9;margin:0 auto;width:60%;text-align:center;border:1px solid #A5D6A7;}</style>")