# src/core/connector_loader.py
import yaml
from pathlib import Path
from typing import Dict, Any

# --- NEW ---
# Simple in-memory cache to avoid re-reading the YAML file on every request.
_connector_cache: Dict[str, Dict[str, Any]] = {}

def load_connector(domain: str) -> Dict[str, Any]:
    """
    Loads, parses, and caches the connector.yml for a given domain.

    Args:
        domain: The name of the domain (e.g., 'event').

    Returns:
        A dictionary containing the parsed YAML content.

    Raises:
        FileNotFoundError: If the connector.yml for the domain does not exist.
        ValueError: If the YAML file is malformed.
    """
    if domain in _connector_cache:
        return _connector_cache[domain]

    try:
        # Assuming a standard project structure.
        project_root = Path(__file__).parent.parent.parent
        connector_path = project_root / "src" / "domains" / domain / "connector.yml"

        if not connector_path.exists():
            raise FileNotFoundError(f"Connector file not found for domain '{domain}' at {connector_path}")

        with open(connector_path, 'r') as f:
            connector_data = yaml.safe_load(f)
            if not connector_data:
                raise ValueError(f"Connector file for domain '{domain}' is empty or malformed.")
            
            _connector_cache[domain] = connector_data
            return connector_data

    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing YAML for domain '{domain}': {e}")
    except Exception as e:
        # Re-raise other exceptions with more context.
        raise type(e)(f"Failed to load connector for domain '{domain}': {e}")