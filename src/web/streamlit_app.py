import streamlit as st
import re
from datetime import datetime
import pytz
from elevenlabs import generate, voices, set_api_key
import os
import tempfile
from dotenv import load_dotenv
import wave
import io
import json
from pathlib import Path

# Load environment variables
load_dotenv()

# Set Eleven Labs API key from environment
ELEVEN_LABS_API_KEY = os.getenv('ELEVEN_LABS_API_KEY')
if ELEVEN_LABS_API_KEY:
    set_api_key(ELEVEN_LABS_API_KEY)

# Create directory for storing audio files if it doesn't exist
AUDIO_DIR = Path('src/web/audio')
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# Create logs directory if it doesn't exist
Path('src/web/logs').mkdir(parents=True, exist_ok=True)

# Load agent configuration
with open('config.json', 'r') as f:
    config = json.load(f)

# Create agent gender mapping from config
AGENT_GENDERS = {}
for agent in config['agents']:
    name = agent['first_name']
    # Determine gender from private_bio using pronouns and context
    bio = agent['private_bio'].lower()
    if 'she' in bio or 'her' in bio:
        AGENT_GENDERS[name] = 'female'
    else:
        AGENT_GENDERS[name] = 'male'

# Define voice mapping for agents based on gender
AGENT_VOICES = {
    # Female voices - warm and empathetic for environmental and human rights themes
    'female': {
        'Gaia': 'Rachel',     # Warm, nurturing voice for the environmental activist
        'Sara Marddini': 'Bella',  # Strong, passionate voice for the human rights activist
        'default': 'Elli'     # Backup female voice
    },
    # Male voices - authoritative and technical for AI/tech themes
    'male': {
        'Tata': 'Antoni',     # Professional, technical voice for the AI expert
        'default': 'Josh'     # Backup male voice
    }
}

# Store agent-voice mappings persistently
VOICE_MAPPING_FILE = AUDIO_DIR / 'voice_mapping.json'
if VOICE_MAPPING_FILE.exists():
    with open(VOICE_MAPPING_FILE, 'r') as f:
        AGENT_TO_VOICE = json.load(f)
else:
    AGENT_TO_VOICE = {}

def get_agent_gender(agent_name):
    """Get agent's gender from config-based mapping"""
    return AGENT_GENDERS.get(agent_name, 'male')  # Default to male if not found

def assign_voice(agent_name):
    """Assign a voice to an agent based on their gender and role"""
    if agent_name in AGENT_TO_VOICE:
        return AGENT_TO_VOICE[agent_name]
    
    gender = get_agent_gender(agent_name)
    # Get the specific voice for this agent, or use the default for their gender
    voice = AGENT_VOICES[gender].get(agent_name, AGENT_VOICES[gender]['default'])
    
    AGENT_TO_VOICE[agent_name] = voice
    
    # Save updated mapping
    with open(VOICE_MAPPING_FILE, 'w') as f:
        json.dump(AGENT_TO_VOICE, f)
    
    return voice

def parse_log_line(line):
    # Parse log line format: [AgentName] [Color] [Action] Message
    pattern = r"\[(.*?)\] \[LogColor\.(.*?)\] \[(.*?)\] (.*)"
    match = re.match(pattern, line)
    if match:
        agent_name, color, action, message = match.groups()
        # Extract timestamp if present in message
        time_pattern = r"since (\d{2}:\d{2}:\d{2})"
        time_match = re.search(time_pattern, message)
        timestamp = time_match.group(1) if time_match else None
        return {
            'agent': agent_name.strip(),
            'color': color.strip(),
            'action': action.strip(),
            'message': message.strip(),
            'timestamp': timestamp
        }
    return None

def get_dialogue_messages(log_file_path):
    messages = []
    try:
        with open(log_file_path, 'r') as file:
            for line in file:
                parsed = parse_log_line(line)
                if parsed and parsed['action'] in ['speak', 'Action Response']:
                    # Only include actual dialogue messages
                    if 'said to' in parsed['message']:
                        # Extract recipient and content
                        parts = parsed['message'].split("said to")
                        if len(parts) == 2:
                            # Get full recipient text before the colon
                            recipient_content = parts[1].split(":", 1)
                            recipient = recipient_content[0].strip()
                            content = recipient_content[1].strip().strip("'") if len(recipient_content) > 1 else ""
                            messages.append({
                                'agent': parsed['agent'],
                                'recipient': recipient,
                                'content': content,
                                'timestamp': parsed['timestamp'],
                                'color': parsed['color']
                            })
    except FileNotFoundError:
        st.warning("No dialogue log file found. Please generate some dialogue first.")
    return messages

def get_agent_color(agent_name):
    # Define a color palette for agents
    color_map = {
        'Gaia': {
            'main': '#4CAF50',      # Green for environmental focus
            'light': '#E8F5E9'
        },
        'Sara Marddini': {
            'main': '#2196F3',      # Blue for human rights
            'light': '#E3F2FD'
        },
        'Tata': {
            'main': '#9C27B0',      # Purple for technology/AI
            'light': '#F3E5F5'
        },
        'default': {
            'main': '#757575',      # Grey
            'light': '#F5F5F5'
        }
    }
    return color_map.get(agent_name, color_map['default'])

def generate_dialogue_audio(messages):
    """Generate audio from dialogue messages using Eleven Labs"""
    if not ELEVEN_LABS_API_KEY:
        st.error("Eleven Labs API key not found in environment variables.")
        return None
    
    # Create a unique identifier for this dialogue
    dialogue_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_path = AUDIO_DIR / f'dialogue_{dialogue_id}.mp3'
    
    # Check if this dialogue was already generated
    if audio_path.exists():
        return str(audio_path)
    
    # Prepare dialogue segments (limit to roughly 3 minutes worth of content)
    word_count = 0
    word_limit = 450  # Assuming average speaking rate of 150 words per minute
    audio_segments = []
    
    for msg in messages:
        # Get word count for this message
        words_in_message = len(msg['content'].split())
        
        if word_count + words_in_message > word_limit:
            break
            
        try:
            # Get or assign a voice for this agent
            voice = assign_voice(msg['agent'])
            
            # Generate audio for this message
            audio = generate(
                text=msg['content'],
                voice=voice,
                model="eleven_monolingual_v1"
            )
            audio_segments.append(audio)
            word_count += words_in_message
            
            # Add a short pause between messages
            pause_duration = 0.5  # seconds
            pause = bytes([128] * int(44100 * pause_duration))  # Generate silence
            audio_segments.append(pause)
            
        except Exception as e:
            st.error(f"Error generating audio for {msg['agent']}: {str(e)}")
            continue
    
    if not audio_segments:
        return None
        
    # Combine all audio segments and save to file
    try:
        with open(audio_path, 'wb') as f:
            for segment in audio_segments:
                f.write(segment)
        return str(audio_path)
            
    except Exception as e:
        st.error(f"Error saving audio file: {str(e)}")
        return None

def display_message(msg):
    # Determine message alignment and styling
    is_broadcast = 'everyone' in msg['recipient'].lower()
    agent_colors = get_agent_color(msg['agent'])
    
    # Create columns with better proportions
    cols = st.columns([1, 4])
    
    # Display agent name and timestamp
    with cols[0]:
        st.markdown(
            f"""
            <div style="
                text-align: right;
                padding: 10px;
                margin-right: 15px;
            ">
                <div style="
                    font-weight: bold;
                    color: {agent_colors['main']};
                    font-size: 1.1em;
                ">{msg['agent']}</div>
                {f'<div style="font-size: 0.8em; color: #666; margin-top: 4px;">at {msg["timestamp"]}</div>' if msg['timestamp'] else ''}
            </div>
            """,
            unsafe_allow_html=True
        )
    
    # Display message content
    with cols[1]:
        st.markdown(
            f"""
            <div style="
                background-color: {'white' if is_broadcast else agent_colors['light']};
                border-left: 4px solid {agent_colors['main']};
                padding: 15px;
                border-radius: 4px;
                margin: 5px 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                animation: fadeIn 0.5s ease-in;
            ">
                <div style="
                    color: #212121;
                    font-size: 1em;
                    line-height: 1.5;
                ">
                    {'📢 ' if is_broadcast else ''}{msg['content']}
                </div>
                <div style="
                    color: #666;
                    font-size: 0.8em;
                    margin-top: 8px;
                    font-style: italic;
                ">
                    To: {msg['recipient']}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    # Add spacing between messages
    st.markdown("<div style='margin: 10px 0;'></div>", unsafe_allow_html=True)

def list_saved_dialogues():
    """List all previously generated dialogue audio files"""
    audio_files = sorted(AUDIO_DIR.glob('dialogue_*.mp3'), reverse=True)
    return [f for f in audio_files if f.is_file()]

def format_timestamp(filename):
    """Format the timestamp from filename"""
    try:
        # Extract timestamp from filename (e.g., dialogue_20241210_123456.mp3)
        timestamp = filename.stem.split('_', 1)[1]  # Get everything after first underscore
        dt = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (IndexError, ValueError):
        return "Unknown time"

def display_chat(messages):
    st.markdown("""
        <h1 style='text-align: center; color: #1a237e; margin-bottom: 2rem;'>
            💬 Agent Dialogue Visualization
        </h1>
    """, unsafe_allow_html=True)
    
    # Add Generate Audio button and saved dialogues at the top
    with st.expander("🎧 Dialogue Audio"):
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Generate New 3-Minute Audio"):
                with st.spinner("Generating audio..."):
                    audio_file = generate_dialogue_audio(messages)
                    if audio_file:
                        st.audio(audio_file)
        
        with col2:
            st.write("Previously Generated Dialogues:")
            saved_dialogues = list_saved_dialogues()
            for audio_file in saved_dialogues:
                formatted_time = format_timestamp(audio_file)
                st.audio(str(audio_file), format='audio/mp3')
                st.caption(f"Generated at: {formatted_time}")
    
    # Initialize session state for message counter if not exists
    if 'message_index' not in st.session_state:
        st.session_state.message_index = 0
    
    # Create chat container
    chat_container = st.container()
    
    with chat_container:
        # Display messages up to current index
        for i in range(st.session_state.message_index + 1):
            if i < len(messages):
                display_message(messages[i])
    
    # Add Next Message button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.session_state.message_index < len(messages) - 1:
            if st.button("Next Message ➡️", key="next"):
                st.session_state.message_index += 1
                st.rerun()
        elif len(messages) > 0:
            st.button("End of Dialogue", disabled=True)
    
    # Add Reset button
    with col3:
        if st.session_state.message_index > 0:
            if st.button("Reset 🔄"):
                st.session_state.message_index = 0
                st.rerun()

def main():
    st.set_page_config(
        page_title="Agent Dialogue Visualization",
        layout="wide"
    )
    
    # Add custom CSS
    st.markdown("""
        <style>
        .stApp {
            max-width: 1000px;
            margin: 0 auto;
            background-color: #fafafa;
        }
        .stMarkdown {
            padding: 0;
        }
        div[data-testid="stHorizontalBlock"] {
            align-items: center;
            justify-content: center;
            gap: 0;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Read and display messages
    messages = get_dialogue_messages('src/web/logs/agent.txt')
    display_chat(messages)

if __name__ == "__main__":
    main()
