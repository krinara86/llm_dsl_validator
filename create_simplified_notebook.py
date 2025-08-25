# Script to create the simplified notebook
import json

notebook_content = {
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# Event Management Chatbot\n",
                "\n",
                "This notebook provides a conversational interface for managing events using natural language."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Setup and imports\n",
                "import sys\n",
                "sys.path.append('..')  # Add src to path\n",
                "\n",
                "import ipywidgets as widgets\n",
                "from IPython.display import display, HTML\n",
                "from src.event_system import EventSystem\n",
                "from src.ui.interface import ChatInterface\n",
                "\n",
                "# Initialize system\n",
                "system = EventSystem()\n",
                "interface = ChatInterface(system)\n",
                "\n",
                "# Display the interface\n",
                "interface.display()"
            ]
        }
    ],
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "name": "python",
            "version": "3.8.0"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 4
}

with open('notebooks/event_chatbot_simplified.ipynb', 'w') as f:
    json.dump(notebook_content, f, indent=2)

print("Created simplified notebook: notebooks/event_chatbot_simplified.ipynb")