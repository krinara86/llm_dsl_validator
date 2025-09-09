# src/execution/executor.py
from typing import Dict
from ..core.config import AppConfig
from ..core.state_manager import StateManager
from ..core.dsl_builder import DSLBuilder
from ..framework.base_interpreter import execute_dsl
from ..domains.event.interpreter import EventInterpreter

class TaskExecutor:
    """Executes confirmed tasks using the DSL interpreter."""
    
    def __init__(self):
        self.state_manager = StateManager(AppConfig.STATE_FILE)
        self.dsl_builder = DSLBuilder()
    
    def execute(self, role: str, conversation_state: Dict) -> Dict:
        """Execute a confirmed task."""
        dsl_code = ""
        try:
            # Build DSL code
            dsl_code = self.dsl_builder.build(
                conversation_state["task_details"], 
                role
            )
            
            state = self.state_manager.load()
            interpreter = EventInterpreter(state, role)
            
            result = execute_dsl(
                dsl_code,
                AppConfig.get_grammar_path('event'),
                interpreter
            )
            
            # Check if this was a read-only operation
            if result.get('operation_type') == 'read_only':
                return self._handle_search_results(result, dsl_code)
            
            # State-changing operation
            self.state_manager.save(result['new_state'])
            
            action = conversation_state["task_details"].get("action", "").replace('_', ' ').title()
            name = conversation_state["task_details"].get("parameters", {}).get("name", "")
            success_msg = f"✅ Successfully completed: {action}"
            if name:
                success_msg += f" '{name}'"
            
            return {
                "status": "success",
                "message": success_msg,
                "dsl_code": dsl_code
            }
            
        except ValueError as e:
            return self._handle_validation_error(str(e), dsl_code)
        except Exception as e:
            return {
                "status": "error",
                "message": f"❌ Unexpected Error: {e}",
                "dsl_code": dsl_code
            }
    
    def _handle_search_results(self, result: Dict, dsl_code: str) -> Dict:
        """Format search results for display."""
        search_results = result.get('results', {})
        items = search_results.get('items', [])
        search_type = search_results.get('type', 'unknown')
        criteria = search_results.get('criteria', {})
        
        # Build result message
        if search_type == 'venues':
            message = self._format_venue_results(items, criteria)
        elif search_type == 'sessions':
            message = self._format_session_results(items, criteria)
        else:
            message = "Search completed but no results to display."
        
        return {
            "status": "search_results",
            "message": message,
            "dsl_code": dsl_code,
            "results": search_results
        }
    
    def _format_venue_results(self, venues: list, criteria: Dict) -> str:
        """Format venue search results as HTML table."""
        if not venues:
            return "🔍 <b>No venues found matching your criteria.</b>"
        
        # Build criteria summary
        criteria_text = []
        if 'min_capacity' in criteria:
            criteria_text.append(f"capacity ≥ {criteria['min_capacity']}")
        if 'has_av_system' in criteria:
            criteria_text.append(f"A/V: {'Yes' if criteria['has_av_system'] else 'No'}")
        if 'is_available' in criteria:
            criteria_text.append(f"{'Available only' if criteria['is_available'] else 'Including booked'}")
        if 'name_contains' in criteria:
            criteria_text.append(f"name contains '{criteria['name_contains']}'")
        
        criteria_summary = " | ".join(criteria_text) if criteria_text else "all venues"
        
        html = f"<div style='margin: 10px 0;'>"
        html += f"<b>🔍 Found {len(venues)} venue(s)</b>"
        if criteria_text:
            html += f" matching: <i>{criteria_summary}</i>"
        html += "</div>"
        
        html += "<table border='1' style='width:100%; margin-top:10px;'>"
        html += "<tr><th>Name</th><th>Capacity</th><th>A/V</th><th>Status</th></tr>"
        
        for venue in venues:
            av = "✅" if venue['has_av_system'] else "❌"
            status = "Available" if venue['is_available'] else f"Booked ({venue.get('booked_by', 'N/A')})"
            status_color = "green" if venue['is_available'] else "red"
            html += f"<tr>"
            html += f"<td>{venue['name']}</td>"
            html += f"<td>{venue['capacity']}</td>"
            html += f"<td>{av}</td>"
            html += f"<td style='color:{status_color};'>{status}</td>"
            html += f"</tr>"
        
        html += "</table>"
        return html
    
    def _format_session_results(self, sessions: list, criteria: Dict) -> str:
        """Format session search results as HTML table."""
        if not sessions:
            return "🔍 <b>No sessions found matching your criteria.</b>"
        
        # Build criteria summary
        criteria_text = []
        if 'name_contains' in criteria:
            criteria_text.append(f"name contains '{criteria['name_contains']}'")
        if 'hosted_by' in criteria:
            criteria_text.append(f"hosted by '{criteria['hosted_by']}'")
        if 'in_venue' in criteria:
            criteria_text.append(f"in venue '{criteria['in_venue']}'")
        if 'min_attendees' in criteria:
            criteria_text.append(f"attendees ≥ {criteria['min_attendees']}")
        if 'requires_av' in criteria:
            criteria_text.append(f"A/V: {'Required' if criteria['requires_av'] else 'Not required'}")
        
        criteria_summary = " | ".join(criteria_text) if criteria_text else "all sessions"
        
        html = f"<div style='margin: 10px 0;'>"
        html += f"<b>🔍 Found {len(sessions)} session(s)</b>"
        if criteria_text:
            html += f" matching: <i>{criteria_summary}</i>"
        html += "</div>"
        
        html += "<table border='1' style='width:100%; margin-top:10px;'>"
        html += "<tr><th>Title</th><th>Venue</th><th>Host</th><th>Attendees</th><th>A/V</th></tr>"
        
        for session in sessions:
            av = "✅" if session.get('requires_av', False) else "❌"
            html += f"<tr>"
            html += f"<td>{session.get('name', 'N/A')}</td>"
            html += f"<td>{session.get('in_venue', 'N/A')}</td>"
            html += f"<td>{session.get('hosted_by', 'N/A')}</td>"
            html += f"<td>{session.get('expected_attendees', 'N/A')}</td>"
            html += f"<td>{av}</td>"
            html += f"</tr>"
        
        html += "</table>"
        return html
    
    def _handle_validation_error(self, error_msg: str, dsl_code: str) -> Dict:
        """Handle validation errors from the interpreter."""
        if "RoleMismatchError" in error_msg:
            return {
                "status": "error",
                "message": f"❌ Permission Error: {error_msg.split(':', 1)[1] if ':' in error_msg else error_msg}",
                "dsl_code": dsl_code
            }
        elif "ValidationError" in error_msg:
            return {
                "status": "error",
                "message": f"❌ Validation Failed: {error_msg.split(':', 1)[1] if ':' in error_msg else error_msg}",
                "dsl_code": dsl_code
            }
        else:
            return {
                "status": "error",
                "message": f"❌ Error: {error_msg}",
                "dsl_code": dsl_code
            }