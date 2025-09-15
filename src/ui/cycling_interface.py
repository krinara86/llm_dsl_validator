# src/ui/cycling_interface.py
"""Cycling-specific UI interface."""

import ipywidgets as widgets
from IPython.display import display, HTML
from typing import Optional, List, Dict, Any

class CyclingChatInterface:
    """Chat interface for the cycling system."""
    
    def __init__(self, cycling_system):
        self.system = cycling_system
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
            "<h1>🚴 Cycling Data Assistant</h1>"
            "<p>Manage riders, teams, and races using natural language.</p>"
        )
        
        # Model selector
        available_models = self.system.get_available_models()
        self.model_selector = widgets.Dropdown(
            options=available_models,
            value=available_models[0] if available_models else None,
            description='Model:',
            layout={'width': '300px'}
        )
        
        # Role selector
        self.role_selector = widgets.RadioButtons(
            options=['admin', 'editor', 'analyst', 'viewer'],
            value='admin',
            description='Role:',
            layout={'width': '150px'}
        )
        
        # Stats display
        self.stats_display = widgets.HTML()
        
        # Chat area
        self.chat_history = widgets.VBox([], layout={'max_height': '400px', 'overflow_y': 'auto'})
        
        # Input area
        self.user_input = widgets.Textarea(
            placeholder='Try: "Find all French riders in the top 100" or "Add Jonas Vingegaard to team 32814"',
            layout={'width': '95%', 'height': '80px'}
        )
        
        # Buttons
        self.send_button = widgets.Button(
            description='Send', button_style='success', icon='paper-plane'
        )
        self.clear_button = widgets.Button(
            description='Clear', button_style='warning', icon='trash'
        )
        self.confirm_button = widgets.Button(
            description='✅ Confirm', button_style='success', 
            layout={'visibility': 'hidden'}
        )
        self.cancel_button = widgets.Button(
            description='❌ Cancel', button_style='danger',
            layout={'visibility': 'hidden'}
        )
        
        # Example queries
        self.examples_label = widgets.HTML("<b>Example queries:</b>")
        self.example_buttons = widgets.VBox([
            widgets.Button(description="Find French riders", layout={'width': '200px'}),
            widgets.Button(description="Search teams with Van Rysel bikes", layout={'width': '200px'}),
            widgets.Button(description="Add a new rider", layout={'width': '200px'}),
            widgets.Button(description="Find races in July 2023", layout={'width': '200px'})
        ])
    
    def _setup_handlers(self):
        """Setup event handlers."""
        self.send_button.on_click(self._on_send)
        self.clear_button.on_click(self._on_clear)
        self.confirm_button.on_click(self._on_confirm)
        self.cancel_button.on_click(self._on_cancel)
        
        # Example button handlers
        for i, btn in enumerate(self.example_buttons.children):
            btn.on_click(lambda b, idx=i: self._on_example(idx))
    
    def _on_example(self, idx):
        """Handle example button clicks."""
        examples = [
            "Find all riders from France",
            "Find teams that use Van Rysel bikes",
            "Add a new rider named John Doe from USA",
            "Find races in France during July 2023"
        ]
        if idx < len(examples):
            self.user_input.value = examples[idx]
    
    def _on_send(self, b):
        """Handle send button click."""
        query = self.user_input.value.strip()
        if not query:
            return
        
        # Check if it's a document (long text)
        if len(query) > 300 and not self.conversation_state:
            self._process_document(query)
        else:
            self._process_query(query)
    
    def _process_query(self, query: str, pre_filled_details: dict = None):
        """Process a single query."""
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
        
        if result['status'] == 'clarification_needed':
            # Build and display form
            self._build_clarification_form(result)
            
        elif result['status'] == 'confirmation_needed':
            self._add_message(result.get('understanding', ''))
            self._add_message(result['message'], 'assistant')
            self._show_confirmation_buttons(True)
        
        elif result['status'] == 'direct_execute':
            self._add_message(result['message'], 'system')
            self._on_confirm(None)
        
        else:
            self._add_message(f"<b>Assistant:</b><br>{result['message']}", 'assistant')
            self._reset_conversation()

    def _build_clarification_form(self, result: Dict):
        """Build a form for collecting missing parameters."""
        self._clear_clarification_form()
        self.active_clarification_widgets = {}
        
        message = result.get("message", "Please provide more information:")
        fields = result.get("form_fields", [])
        
        form_elements = [widgets.HTML(f"<div class='assistant-bubble'>{message}</div>")]
        
        for field in fields:
            label = widgets.Label(f"{field['label']}:")
            
            # Create appropriate widget based on type
            if field["type"] == "boolean":
                widget = widgets.Checkbox(value=False, indent=False)
            elif field["type"] == "number":
                widget = widgets.IntText(value=0, placeholder=field.get('placeholder', ''))
            else:  # string
                widget = widgets.Text(value="", placeholder=field.get('placeholder', ''))
            
            self.active_clarification_widgets[field["name"]] = widget
            
            # Add help text if available
            help_text = widgets.HTML(f"<i style='font-size: smaller; color: #666;'>{field['prompt']}</i>")
            form_elements.append(widgets.VBox([label, widget, help_text]))
        
        submit_button = widgets.Button(
            description="Submit", 
            button_style='success', 
            icon='check'
        )
        submit_button.on_click(self._on_submit_clarification)
        
        cancel_button = widgets.Button(
            description="Cancel",
            button_style='danger',
            icon='times'
        )
        cancel_button.on_click(self._on_cancel_clarification)
        
        form_elements.append(widgets.HBox([submit_button, cancel_button]))
        
        # Display the form
        self.clarification_form_area = widgets.VBox(form_elements)
        self.chat_history.children = list(self.chat_history.children) + [self.clarification_form_area]
        self._toggle_main_input(False)

    def _on_submit_clarification(self, b):
        """Handle form submission."""
        lines = []
        for name, widget in self.active_clarification_widgets.items():
            value = widget.value
            lines.append(f"{name}: {value}")
        
        query = "\n".join(lines)
        
        # Clear the form
        self._clear_clarification_form()
        self._toggle_main_input(True)
        
        # Process the response
        self._process_query(query)

    def _on_cancel_clarification(self, b):
        """Cancel the clarification form."""
        self._clear_clarification_form()
        self._toggle_main_input(True)
        self._add_message("Operation cancelled.", 'system')
        self._reset_conversation()

    def _clear_clarification_form(self):
        """Clear the clarification form."""
        if hasattr(self, 'clarification_form_area'):
            # Remove form from chat history
            children = list(self.chat_history.children)
            if self.clarification_form_area in children:
                children.remove(self.clarification_form_area)
                self.chat_history.children = children
        self.active_clarification_widgets = {}

    def _toggle_main_input(self, enabled: bool):
        """Enable/disable main input area."""
        self.user_input.disabled = not enabled
        self.send_button.disabled = not enabled

    def _process_document(self, document: str):
        """Process a document with multiple tasks."""
        self._add_message(f"<b>You:</b> [Document with {len(document)} characters]", 'user')
        self.user_input.value = ''
        
        result = self.system.process_document(
            document, 
            self.role_selector.value, 
            self.model_selector.value
        )
        
        self._add_message(f"<b>Assistant:</b> {result['message']}", 'assistant')
        
        if result['status'] == 'tasks_extracted' and result['tasks']:
            self.task_queue = result['tasks']
            self.total_tasks = len(self.task_queue)
            self._process_next_task()
    
    def _process_next_task(self):
        """Process the next task in the queue."""
        if not self.task_queue:
            if self.total_tasks > 1:
                self._add_message(
                    f"✅ Completed all {self.total_tasks} tasks!", 
                    'system'
                )
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
        
        self._add_message(
            f"<b>Processing Task {self.current_task_index}/{self.total_tasks}:</b> {task_description}",
            'system'
        )
        
        self._process_query(task_description, details_for_orchestrator)
    
    def _on_confirm(self, b):
        """Handle confirmation."""
        self._show_confirmation_buttons(False)
        self._add_message("<i>Executing...</i>", 'system')
        
        result = self.system.execute_task(
            self.role_selector.value, 
            self.conversation_state
        )
        
        # Remove the "Executing..." message
        self.chat_history.children = self.chat_history.children[:-1]
        
        if result['status'] == 'success':
            self._add_message(f"<b>Assistant:</b> {result['message']}", 'system')
            
            if result.get('action_type') == 'query':
                self._display_query_results(
                    result.get('results', []),
                    self.conversation_state.get("task_details", {}).get("action")
                )
            
            if 'dsl_code' in result and result['dsl_code']:
                self._show_dsl_code(result['dsl_code'])
        else:
            self._add_message(f"<b>Assistant:</b> {result['message']}", 'error')
        
        self._reset_conversation()
        self._process_next_task()
        self._update_stats()
    
    def _on_cancel(self, b):
        """Handle cancellation."""
        self._show_confirmation_buttons(False)
        self._add_message("<b>Assistant:</b> Task cancelled.", 'system')
        self._reset_conversation()
        self._process_next_task()
    
    def _on_clear(self, b):
        """Clear the chat history."""
        self._reset_conversation()
        self.task_queue = []
        self.total_tasks = 0
        self.current_task_index = 0
        
        welcome_msg = (
            "<b>Assistant:</b><br>Hello! I can help you manage cycling data. "
            "You can search for riders, teams, and races, or add and modify them. "
            "What would you like to do?"
        )
        self.chat_history.children = [
            widgets.HTML(f"<div class='chat-bubble assistant-bubble'>{welcome_msg}</div>")
        ]
        self._show_confirmation_buttons(False)
        self._update_stats()
    
    def _add_message(self, content: str, msg_type: str = 'assistant'):
        """Add a message to the chat history."""
        bubble_class = {
            'user': 'user-bubble',
            'assistant': 'assistant-bubble',
            'system': 'system-bubble',
            'error': 'error-bubble'
        }.get(msg_type, 'assistant-bubble')
        
        html = f"<div class='chat-bubble {bubble_class}'>{content}</div>"
        self.chat_history.children = list(self.chat_history.children) + [widgets.HTML(html)]
    
    def _display_query_results(self, results: List[Dict], action: str):
        """Display query results in a formatted way."""
        if not results:
            return
        
        html = "<div style='background-color: #f0f0f0; padding: 10px; border-radius: 5px;'>"
        
        if action == "find_rider":
            html += f"<h4>Found {len(results)} rider(s)</h4>"
            html += "<table style='width:100%; border-collapse: collapse;'>"
            html += "<tr style='background: #333; color: white;'>"
            html += "<th>ID</th><th>Name</th><th>Country</th><th>Team</th><th>Rank</th><th>Points</th><th>Source</th>"
            html += "</tr>"
            
            for i, rider in enumerate(results[:20]):  # Limit to 20 for display
                bg = '#fff' if i % 2 == 0 else '#f9f9f9'
                html += f"<tr style='background: {bg};'>"
                html += f"<td>{rider.get('id', 'N/A')}</td>"
                html += f"<td>{rider.get('firstName', '')} {rider.get('lastName', '')}</td>"
                html += f"<td>{rider.get('country', 'N/A')}</td>"
                html += f"<td>{rider.get('team', 'N/A')}</td>"
                
                if 'ranking' in rider:
                    html += f"<td>{rider['ranking'].get('rank', 'N/A')}</td>"
                    html += f"<td>{rider['ranking'].get('points', 'N/A')}</td>"
                else:
                    html += "<td>N/A</td><td>N/A</td>"
                
                source = rider.get('_source', '').replace('documented', 'Doc').replace('undocumented', 'Undoc')
                html += f"<td>{source}</td>"
                html += "</tr>"
            
            if len(results) > 20:
                html += f"<tr><td colspan='7'><i>... and {len(results) - 20} more</i></td></tr>"
            
        elif action == "find_team":
            html += f"<h4>Found {len(results)} team(s)</h4>"
            html += "<table style='width:100%; border-collapse: collapse;'>"
            html += "<tr style='background: #333; color: white;'>"
            html += "<th>ID</th><th>Name</th><th>Country</th><th>Bike</th><th>Riders</th>"
            html += "</tr>"
            
            for i, team in enumerate(results[:20]):
                bg = '#fff' if i % 2 == 0 else '#f9f9f9'
                html += f"<tr style='background: {bg};'>"
                html += f"<td>{team.get('id', 'N/A')}</td>"
                html += f"<td>{team.get('name', 'N/A')}</td>"
                html += f"<td>{team.get('country', 'N/A')}</td>"
                html += f"<td>{team.get('bike', 'N/A')}</td>"
                html += f"<td>{len(team.get('riders', []))}</td>"
                html += "</tr>"
            
        elif action == "find_race":
            html += f"<h4>Found {len(results)} race(s)</h4>"
            html += "<table style='width:100%; border-collapse: collapse;'>"
            html += "<tr style='background: #333; color: white;'>"
            html += "<th>ID</th><th>Name</th><th>Country</th><th>Class</th><th>Start Date</th>"
            html += "</tr>"
            
            for i, race in enumerate(results[:20]):
                bg = '#fff' if i % 2 == 0 else '#f9f9f9'
                html += f"<tr style='background: {bg};'>"
                html += f"<td>{race.get('raceId', race.get('id', 'N/A'))}</td>"
                html += f"<td>{race.get('name', 'N/A')}</td>"
                html += f"<td>{race.get('country', 'N/A')}</td>"
                html += f"<td>{race.get('class', 'N/A')}</td>"
                html += f"<td>{race.get('startDate', 'N/A')[:10]}</td>"
                html += "</tr>"
        
        html += "</table></div>"
        self._add_message(html, 'assistant')
    
    def _show_dsl_code(self, dsl_code: str):
        """Show the generated DSL code."""
        dsl_html = f"<pre style='background-color:#f5f5f5; padding:10px; font-size:11px;'>{dsl_code}</pre>"
        dsl_accordion = widgets.Accordion(
            children=[widgets.HTML(dsl_html)],
            titles=('🔍 Generated DSL Code',)
        )
        dsl_accordion.selected_index = None
        self.chat_history.children = list(self.chat_history.children) + [dsl_accordion]
    
    def _show_confirmation_buttons(self, show: bool):
        """Show or hide confirmation buttons."""
        visibility = 'visible' if show else 'hidden'
        self.confirm_button.layout.visibility = visibility
        self.cancel_button.layout.visibility = visibility
        self.user_input.disabled = show
        self.send_button.disabled = show
    
    def _reset_conversation(self):
        """Reset the conversation state."""
        self.conversation_state = {}
        self.user_input.disabled = False
        self.send_button.disabled = False
    
    def _update_stats(self):
        """Update statistics display."""
        try:
            # This is a simplified version - you could add actual stats from the data file
            self.stats_display.value = (
                "<div style='background: #f8f9fa; padding: 10px; border-radius: 5px;'>"
                "<b>Database Stats:</b> Connected to cycling_data.json"
                "</div>"
            )
        except Exception as e:
            self.stats_display.value = f"<p style='color:red;'>Error loading stats: {e}</p>"
    
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
        .error-bubble {
            background-color: #FFEBEE;
            margin-right: 20%;
            border: 1px solid #EF5350;
        }
        table th {
            padding: 5px;
            text-align: left;
        }
        table td {
            padding: 5px;
            border-bottom: 1px solid #ddd;
        }
        </style>
        """)
    
    def display(self):
        """Display the complete interface."""
        display(self.styles)
        
        # Layout
        controls = widgets.HBox([self.model_selector, self.role_selector])
        input_area = widgets.HBox([self.user_input, self.send_button, self.clear_button])
        confirm_area = widgets.HBox([self.confirm_button, self.cancel_button])
        
        examples_section = widgets.VBox([self.examples_label, self.example_buttons])
        
        layout = widgets.VBox([
            self.header,
            controls,
            widgets.HTML("<hr>"),
            self.stats_display,
            self.chat_history,
            input_area,
            confirm_area,
            widgets.HTML("<hr>"),
            examples_section
        ])
        
        display(layout)
        self._on_clear(None)
        self._update_stats()