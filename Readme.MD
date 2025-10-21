# Conversational DSL Framework

## Reliable Natural Language Interfaces for Domain-Specific Languages

This framework provides a systematic approach to building natural language interfaces for Domain-Specific Languages (DSLs) while maintaining formal verification and rule enforcement. By separating natural language understanding from domain logic execution, the system achieves both accessibility and reliability.

## Table of Contents

1. [Motivation](#motivation)
2. [System Architecture](#system-architecture)
3. [Installation](#installation)
4. [Quick Start](#quick-start)
5. [Reference Implementations](#reference-implementations)
6. [Building LionWeb Connectors](#building-lionweb-connectors)
7. [Extending the Framework](#extending-the-framework)
8. [API Reference](#api-reference)
9. [Contributing](#contributing)

## Motivation

### The Problem

Domain-Specific Languages provide powerful abstractions for modeling complex domains with precision, ensuring type safety, and enforcing business rules. However, they suffer from significant accessibility barriers:

- **Steep learning curves** requiring understanding of formal syntax and semantics
- **Limited to technical users** who can work with specialized tooling
- **Context switching overhead** between natural thinking and formal notation
- **Documentation gaps** that compound the training burden

Large Language Models (LLMs) offer natural language interfaces that are immediately accessible to non-technical users. However, they present critical reliability issues for production systems:

- **Hallucinations** producing plausible but incorrect outputs
- **Non-deterministic behavior** making verification impossible
- **No formal guarantees** about constraint satisfaction
- **Rule violations** due to lack of domain understanding

### The Semantic Firewall Approach

This framework implements a **semantic firewall** pattern that leverages the strengths of both technologies while mitigating their weaknesses:

- **LLMs serve as the translation layer**, converting natural language to structured intent
- **DSLs act as the verification and execution engine**, enforcing all domain rules
- **Connectors bridge the gap**, providing domain context to the LLM without giving it execution control
- **Review forms create a trust boundary**, allowing users to verify and correct extracted information before execution

The DSL interpreter validates not just syntax but the semantic implications of requests against a trusted domain model. For example, while an LLM might correctly parse "schedule a 30-person meeting in Room A," the interpreter knows Room A has a capacity of 20 and will reject the semantically invalid request.

## System Architecture

The framework employs a three-layer architecture with clean separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface Layer                     │
│                  (Natural Language Input)                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Conversation Layer (Domain-Agnostic)           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │ Orchestrator │──│ TaskExtractor│──│ ClarificationGen │ │
│  └──────────────┘  └──────────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
┌──────────────────────────┐  ┌──────────────────────────────┐
│   Domain Configuration    │  │     Execution Layer          │
│  ┌──────────────────────┐ │  │  ┌────────────────────────┐ │
│  │ Connector Definition │ │  │  │ DSL Parser/Interpreter │ │
│  │ (YAML or LionWeb M1) │ │  │  │    or LionWeb Loader   │ │
│  └──────────────────────┘ │  │  └────────────────────────┘ │
│  ┌──────────────────────┐ │  │  ┌────────────────────────┐ │
│  │   Domain Schema      │ │  │  │    State Management    │ │
│  └──────────────────────┘ │  │  └────────────────────────┘ │
└──────────────────────────┘  └──────────────────────────────┘
```

### Key Components

- **Conversation Orchestrator**: Manages the multi-turn conversation flow, maintaining state across interactions
- **Task Extractor**: Uses LLM to parse natural language into structured task representations
- **Clarification Generator**: Creates type-aware forms for missing or ambiguous parameters
- **Connector**: Provides domain-specific mappings between natural language and formal concepts
- **Execution Engine**: Either DSL interpreter (Lark) or model manipulation (LionWeb)

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Git for cloning the repository

### Basic Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/conversational-dsl-framework.git
cd conversational-dsl-framework

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### LLM Backend Configuration

The framework supports multiple LLM providers. Configure at least one:

#### Option 1: Ollama Local

For running models locally on your machine:

```bash
# Install Ollama from https://ollama.com
# Pull a model (recommended for starting)
ollama pull llama3.2:3b

# Verify installation
ollama list
```

The system will automatically detect the local Ollama instance on `http://localhost:11434`.

#### Option 2: Ollama Cloud

For using Ollama's cloud infrastructure:

1. Sign up at [Ollama Cloud](https://ollama.com/cloud)
2. Create a `.env` file in the project root:
```bash
OLLAMA_CLOUD_API_KEY=your_api_key_here
OLLAMA_CLOUD_URL=https://api.ollama.com
```

#### Option 3: HuggingFace

For using models from HuggingFace:

1. Get an API token from [HuggingFace](https://huggingface.co/settings/tokens)
2. Add to `.env` file:
```bash
HUGGINGFACE_API_KEY=your_token_here
```

### LionWeb Setup (Optional)

For the model-driven implementation:

```bash
pip install lionweb-python>=0.3.0
```

## Quick Start

### Running the Event Management Example (Lark-based)

```bash
# Start Jupyter notebook
jupyter notebook

# Open and run: notebooks/event_chatbot_simplified.ipynb
```

Example interaction:
```
User: Create a conference room called Aspen with 50 seats
System: [Shows review form with extracted parameters]
User: [Confirms]
System: ✅ Successfully created venue 'Aspen'
```

### Running the Cycling Management Example (LionWeb-based)

```bash
# Open and run: notebooks/cycling_chatbot.ipynb
```

## Reference Implementations

### 1. Lark-based Implementation (Event Management Domain)

Located in `src/domains/event/`, this implementation demonstrates:

- **Grammar-based parsing** using Lark parser
- **File-based state persistence** via JSON
- **Role-based access control** (admin vs scheduler)
- **Business rule enforcement** (capacity limits, double-booking prevention)

Key files:
- `connector.yml`: Natural language mappings
- `schema.py`: Domain structure and permissions
- `grammar.dsl`: Formal grammar specification
- `interpreter.py`: Rule enforcement logic

### 2. LionWeb-based Implementation (Cycling Management Domain)

Located in `src/lionweb_app/`, this implementation showcases:

- **Model-driven architecture** with M1/M2 separation
- **Type-safe operations** through metamodel validation
- **Dynamic schema generation** from language definitions
- **Programmatic connector generation**

Key components:
- `language_generators.py`: M2 language definitions
- `m1_connector_generator.py`: Connector instance creation
- `connector_loader.py`: Runtime model management

## Building LionWeb Connectors

### Understanding the Connector Metamodel

The connector acts as a bridge between natural language and your domain metamodel. It conforms to the `NLMappings` language (M2) and consists of:

```python
Connector
├── domainName: String
├── targetLanguage: String
└── actions: ActionMapping[]
    ├── actionName: String
    ├── targetConcept: String
    ├── description: String
    └── parameters: ParameterMapping[]
        ├── parameterName: String
        ├── targetFeature: String
        ├── description: String
        ├── clarificationPrompt: String
        └── required: Boolean
```

### Programmatic Connector Generation

Create a connector programmatically using the LionWeb API:

```python
from lionweb.model import DynamicNode
from lionweb_app.engine.m1_connector_generator import generate_and_save_connector_m1

def create_connector_for_domain(domain_name, concepts):
    connector = DynamicNode(id=f"{domain_name}-connector", 
                          concept=concepts["Connector"])
    
    connector.set_property_value(
        connector.concept.get_feature_by_name("domainName"),
        domain_name
    )
    
    # Add action mappings
    action = DynamicNode(id=f"create-entity", 
                        concept=concepts["ActionMapping"])
    action.set_property_value(
        action.concept.get_feature_by_name("actionName"),
        "create_entity"
    )
    action.set_property_value(
        action.concept.get_feature_by_name("targetConcept"),
        "YourConcept"
    )
    
    # Add parameter mappings
    param = DynamicNode(id=f"param-name",
                       concept=concepts["ParameterMapping"])
    param.set_property_value(
        param.concept.get_feature_by_name("parameterName"),
        "name"
    )
    param.set_property_value(
        param.concept.get_feature_by_name("clarificationPrompt"),
        "What should we call it?"
    )
    
    action.add_child(
        action.concept.get_feature_by_name("parameters"),
        param
    )
    connector.add_child(
        connector.concept.get_feature_by_name("actions"),
        action
    )
    
    return connector
```

### Linking to Domain Concepts

The connector references your domain language concepts through the `targetConcept` and `targetFeature` properties:

```python
# Your domain M2 defines:
Concept: Person
  Properties:
    - name: String
    - age: Integer

# Your connector maps:
ActionMapping:
  actionName: "register_person"
  targetConcept: "Person"  # Links to M2 concept
  parameters:
    - parameterName: "full_name"
      targetFeature: "name"  # Links to M2 property
      clarificationPrompt: "What is the person's name?"
```

## Extending the Framework

### Adding a New Domain

To add support for a new domain, follow these steps:

#### 1. Define the Connector

Create `src/domains/yourdomain/connector.yml`:

```yaml
domain_name: "Your Domain"
actions:
  your_action:
    description: "Performs domain-specific action"
    parameters:
      param1:
        description: "First parameter"
        clarification_prompt: "Please specify param1"
```

#### 2. Define the Schema

Create `src/domains/yourdomain/schema.py`:

```python
DOMAIN_SCHEMA = {
    "your_action": {
        "permissions": ["user", "admin"],
        "required": ["param1"],
        "optional": ["param2"],
        "param_types": {
            "param1": {"type": "string"},
            "param2": {"type": "number"}
        }
    }
}
```

#### 3. Implement Domain Logic

For Lark-based domains, create an interpreter:

```python
from framework.base_interpreter import BaseInterpreter

class YourDomainInterpreter(BaseInterpreter):
    def your_action(self, tree):
        # Validation and execution logic
        params = self.extract_params(tree)
        if self.validate_business_rules(params):
            self.state["entities"].append(params)
            return {"status": "success"}
        raise ValidationError("Business rule violated")
```

For LionWeb-based domains, extend the task executor to handle your actions through model operations.

## API Reference

### Core Classes

#### ConversationOrchestrator

Manages the conversation flow and state.

```python
orchestrator = ConversationOrchestrator(
    connector=connector_dict,
    schema=schema_dict,
    state_manager=state_manager,
    selection_provider=selection_provider
)

response = orchestrator.process_request(
    query="Create a new entity",
    role="admin",
    model_name="llama3.2:3b",
    conversation_state=state
)
```

#### TaskExtractor

Extracts structured information from natural language.

```python
extractor = TaskExtractor()
task_details = extractor.extract_task_details(
    query="Register John from Denmark",
    model_name="llama3.2:3b",
    connector=connector_dict
)
```

#### SelectionProvider

Provides dynamic options for form fields.

```python
class CustomSelectionProvider(SelectionProvider):
    def get_options(self, selection_type: str, context: Dict) -> List[str]:
        if selection_type == "entity_selection":
            return self.fetch_available_entities()
        return []
```

### Extension Points

- **Custom Interpreters**: Extend `BaseInterpreter` for new DSL execution logic
- **Selection Providers**: Implement `SelectionProvider` for dynamic form options
- **State Managers**: Override `StateManager` for custom persistence
- **LLM Clients**: Extend `LLMClient` for additional model providers

## Contributing

We welcome contributions to improve and extend the framework. Please follow these guidelines:

1. Fork the repository and create a feature branch
2. Write tests for new functionality
3. Follow PEP 8 style guidelines
4. Document new features and API changes
5. Submit a pull request with a clear description

For major changes, please open an issue first to discuss the proposed changes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

This work builds upon research in natural language interfaces for formal systems and leverages:
- [LionWeb](https://lionweb.io/) for model-driven language engineering
- [Lark](https://github.com/lark-parser/lark) for grammar-based parsing
- Various LLM providers for natural language understanding

## Citation

If you use this framework in your research, please cite:

```bibtex
@software{conversational_dsl_framework,
  title = {Conversational DSL Framework: Reliable Natural Language Interfaces for Domain-Specific Languages},
  author = {[Author Names]},
  year = {2025},
  url = {https://github.com/yourusername/conversational-dsl-framework}
}
```