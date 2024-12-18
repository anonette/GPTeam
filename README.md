# Debate Visualizer and Speech Generator

A Streamlit application that visualizes AI agent debates and generates speech using ElevenLabs voices.

## Features

- Visualize debates between AI agents (Tata, Gaia, Sara)
- Generate speech with distinct voices for each agent
- Play sample debate audio
- Filter conversations by speaker

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
- `agents/`: Contains agent conversation files
- `output/`: Generated speech files
- `.streamlit/`: Streamlit configuration
- `requirements.txt`: Project dependencies
- `runtime.txt`: Python version specification

## Notes

- The application uses ElevenLabs for text-to-speech with distinct voices for each agent
- Sample debate audio is available at the top of the interface
- Messages can be filtered by speaker using the toggle filters
