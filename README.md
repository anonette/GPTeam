# GPTeam - AI Debate and Team Interaction Platform

A comprehensive platform for AI agent debates, team interactions, and speech generation. This project combines multi-agent conversations, natural language processing, and voice synthesis to create dynamic, interactive debates between AI agents.

GitHub Repository: [GPTeam](https://github.com/anonette/GPTeam/tree/dknewversion)

## Project Overview

GPTeam is an innovative platform that enables AI agents to engage in meaningful debates and team interactions. The project features:

- **Multi-Agent System**: Multiple AI agents with distinct personalities and roles interact in structured debates
- **Dynamic Conversations**: Agents can discuss topics, share perspectives, and respond to each other's arguments
- **Voice Generation**: Using ElevenLabs API to give each agent a unique voice, making debates more engaging
- **Debate Visualization**: A Streamlit interface to visualize and analyze agent interactions
- **Memory and Context**: Agents maintain context and can reference previous points in the conversation
- **Extensible Architecture**: Modular design allowing for new agents, tools, and features to be added

## Core Components

- **Agents**: Located in `src/agent/`, defines different AI personalities and their interaction logic
- **Tools**: Various utilities in `src/tools/` for agent interactions, context management, and more
- **Memory System**: Handles conversation history and context (`src/memory/`)
- **World Context**: Manages the environment and state of conversations (`src/world/`)
- **Database Integration**: Supports both SQLite and Supabase for data persistence
- **Web Interface**: Streamlit-based visualization of debates and interactions

## Features

- **Debate Visualization**:
  - Real-time display of agent conversations
  - Filter debates by speaker
  - Visualize conversation flow and interaction patterns
  - Play audio versions of debates with distinct voices

- **Agent System**:
  - Multiple AI personalities (Tata, Gaia, Sara, etc.)
  - Customizable agent profiles
  - Dynamic response generation
  - Context-aware interactions

- **Speech Generation**:
  - Text-to-speech conversion using ElevenLabs
  - Unique voices for each agent
  - Audio playback of debates
  - Speech file management

## Deployment on Streamlit Cloud

1. Fork this repository to your GitHub account
2. Visit [Streamlit Cloud](https://share.streamlit.io)
3. Click "New app"
4. Select your forked repository
5. Set the main file path to `debate_visualizer.py`
6. Add the following secrets in Streamlit Cloud settings:
   - ELEVENLABS_API_KEY
   - OPENAI_API_KEY

## Environment Setup

The application requires specific Python version and dependencies:

- Python version: >=3.9,<3.12 (recommended: 3.11.7)
- Dependencies are listed in requirements.txt

## Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a .env file with your API keys:
```
ELEVENLABS_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
```

3. Run the application:
```bash
streamlit run debate_visualizer.py
```

## Project Structure

- `debate_visualizer.py`: Main Streamlit application for visualizing debates
- `speech_generator.py`: Speech generation using ElevenLabs API
- `src/`: Core project source code
  - `agent/`: AI agent implementations and profiles
  - `tools/`: Utility tools for agent interactions
  - `memory/`: Conversation history and context management
  - `world/`: Environment and state management
  - `utils/`: Helper functions and utilities
  - `web/`: Web interface components
- `agents/`: Contains agent conversation files
- `output/`: Generated speech files
- `.streamlit/`: Streamlit configuration
- `supabase/`: Database migrations and configuration
- `tests/`: Project test files

## Technical Details

- **Database**: Supports both SQLite (local) and Supabase (cloud) for data persistence
- **API Integration**: Uses OpenAI for language processing and ElevenLabs for voice synthesis
- **Web Framework**: Built with Streamlit for easy deployment and visualization
- **Testing**: Includes test suite for core functionality
- **Configuration**: Flexible configuration system with environment variables and config files

## Notes

- The application uses ElevenLabs for text-to-speech with distinct voices for each agent
- Sample debate audio is available at the top of the interface
- Messages can be filtered by speaker using the toggle filters
- The system is designed to be extensible, allowing for new agents and features to be added
- Database migrations are managed through the Supabase configuration
