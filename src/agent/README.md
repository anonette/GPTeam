# Agent Module

This module provides a modular implementation of AI agents with various capabilities including memory management, planning, reflection, and movement.

## Architecture

The agent system is built using a mixin-based architecture where different functionalities are separated into distinct components:

### Core Components

- `agent_base.py`: Core Agent class that combines all functionalities
- `agent_memory.py`: Memory management and importance calculation
- `agent_movement.py`: Location management and movement capabilities
- `agent_planning.py`: Planning, action execution, and reactions
- `agent_reflection.py`: Memory reflection and insight generation
- `agent_db.py`: Database operations and persistence

### Supporting Components

- `importance.py`: Memory importance rating functionality
- `executor.py`: Plan execution logic
- `message.py`: Message handling and communication
- `plans.py`: Plan representation and status tracking
- `react.py`: Reaction system for responding to events
- `reflection.py`: Reflection system for generating insights

## Usage

Basic usage of the Agent class:

```python
from src.agent import Agent
from src.world.context import WorldContext
from src.location.base import Location

# Create an agent
agent = Agent(
    full_name="Agent Name",
    private_bio="Agent's private biography",
    public_bio="Agent's public biography",
    context=WorldContext(...),
    location=Location(...),
    directives=["Directive 1", "Directive 2"]
)

# Run the agent for one step
await agent.run_for_one_step()
```

## Key Features

### Memory Management
- Memory creation and storage
- Importance calculation
- Memory retrieval and filtering

### Planning
- Plan generation based on context and directives
- Plan execution with tool usage
- Reaction system for adapting to events

### Movement
- Location tracking
- Movement between locations
- Location-based event generation

### Reflection
- Periodic reflection on memories
- Insight generation
- Memory-based learning

### Database Operations
- Persistent storage of agent state
- Plan tracking
- Memory archival

## Extension

The system can be extended by:

1. Creating new mixins for additional functionality
2. Modifying existing mixins to alter behavior
3. Adding new tools for agent interaction
4. Implementing new plan types

## Best Practices

1. Keep functionality separated in appropriate mixins
2. Use type hints for better code clarity
3. Document new methods and classes
4. Add tests for new functionality
5. Update this README when adding new features

## Dependencies

- Pydantic: For data validation
- Langchain: For LLM interaction
- PyTZ: For timezone handling
- SQLite/Supabase: For database operations
