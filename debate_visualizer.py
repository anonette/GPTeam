import streamlit as st
import re
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set, Tuple
import requests

def get_base_locations() -> Tuple[str, str]:
    """Get the base path and url depending on environment (local or Streamlit Cloud)."""
    base_path = os.getcwd()
    base_url = "https://teamfiles.zrok.yair.cc"
    return base_path, base_url

def get_agent_log_url(agent_name: str) -> str:
    """Get the URL for an agent's raw log file."""
    base_path, base_url = get_base_locations()
    if st.runtime.exists():
        return f"{base_url}/agents/{agent_name}.txt"
    else:
        return os.path.join(base_path, "agents", f"{agent_name}.txt")

def read_file_content(filepath: str, is_remote: bool = False) -> str:
    """Read file content from local path or remote URL."""
    try:
        if is_remote:
            response = requests.get(filepath)
            response.raise_for_status()
            return response.text
        else:
            with open(filepath, 'r') as f:
                return f.read()
    except Exception as e:
        st.error(f"Error reading file {filepath}: {str(e)}")
        return ""

def parse_agent_file(filepath: str, is_remote: bool = False) -> List[Dict]:
    """Parse an agent file and extract messages."""
    try:
        content = read_file_content(filepath, is_remote)
        if not content:
            return []
            
        # Find all messages in the Current Conversations section
        conversation_match = re.search(r'Current Conversations:\n(.*?)\n\nCurrent Plans:', content, re.DOTALL)
        if not conversation_match:
            return []
            
        conversation_text = conversation_match.group(1)
        messages = []
        
        # Process each line
        for line in conversation_text.split('\n'):
            if not line.strip():
                continue
                
            try:
                # First split on @ to get message and timestamp
                parts = line.split(' @ ')
                if len(parts) != 2:
                    continue
                    
                message_part = parts[0].strip()
                timestamp = parts[1].strip()
                
                # Get speaker from start of line
                speaker_match = re.match(r'^(Tata|Gaia|Sara):', message_part)
                if not speaker_match:
                    continue
                    
                speaker = speaker_match.group(1)
                
                # Get the rest of the message
                message_text = message_part[len(speaker) + 1:].strip()
                
                # Extract recipient and message
                if message_text.startswith("Ladies and Gentlemen"):
                    recipient = "everyone"
                    message = message_text
                else:
                    # Check first part before period/question mark for multiple names
                    first_part = re.split(r'[.?]', message_text)[0]
                    # Split on commas and 'and'
                    name_parts = [p.strip() for p in first_part.replace(' and ', ', ').split(',')]
                    # Get all valid names
                    valid_names = [name.strip() for name in name_parts if name.strip() in ['Tata', 'Gaia', 'Sara']]
                    
                    if len(valid_names) > 1:
                        recipient = "everyone"
                        message = message_text
                    elif len(valid_names) == 1:
                        recipient = valid_names[0]
                        # Keep the full message including recipient name
                        message = message_text
                    else:
                        continue
                
                messages.append({
                    'timestamp': timestamp,
                    'speaker': speaker,
                    'recipient': recipient,
                    'message': message
                })
                
            except Exception as e:
                continue
        
        return messages
        
    except Exception as e:
        st.error(f"Error reading file {filepath}: {str(e)}")
        return []

def get_all_messages() -> List[Dict]:
    """Get messages from all agent files and combine them."""
    all_messages = []
    seen_messages = set()  # Track unique messages across all files
    
    # Get base locations
    base_path, base_url = get_base_locations()
    is_remote = st.runtime.exists()
    
    # Set up file paths based on environment
    if is_remote:
        agent_files = [
            f"{base_url}/agents/Tata.txt",
            f"{base_url}/agents/Gaia.txt",
            f"{base_url}/agents/Sara.txt"
        ]
    else:
        agents_path = os.path.join(base_path, "agents")
        agent_files = [
            os.path.join(agents_path, "Tata.txt"),
            os.path.join(agents_path, "Gaia.txt"),
            os.path.join(agents_path, "Sara.txt")
        ]
    
    # First collect all messages
    for filepath in agent_files:
        all_messages.extend(parse_agent_file(filepath, is_remote))
    
    # Sort by timestamp first
    all_messages.sort(key=lambda x: x['timestamp'])
    
    # Then deduplicate while preserving order
    unique_messages = []
    for msg in all_messages:
        # Create a key that uniquely identifies the message content
        message_key = f"{msg['speaker']}:{msg['recipient']}:{msg['message']}"
        if message_key not in seen_messages:
            seen_messages.add(message_key)
            unique_messages.append(msg)
    
    return unique_messages

def filter_messages(messages: List[Dict], selected_speakers: Set[str]) -> List[Dict]:
    """Filter messages based on selected speakers."""
    if not selected_speakers:
        return messages
        
    if len(selected_speakers) == 1:
        # Show all messages from the selected speaker
        speaker = list(selected_speakers)[0]
        return [m for m in messages if m['speaker'] == speaker]
    else:
        # Show conversations between selected speakers
        return [m for m in messages if 
                (m['speaker'] in selected_speakers and m['recipient'] in selected_speakers) or
                (m['speaker'] in selected_speakers and m['recipient'] == 'everyone')]

def display_debate():
    st.title("AI Apocalypse Club Debate")
    
    # Add raw logs section at the top
    st.header("📄 Raw Agent Logs")
    st.markdown("""
        <div style='background-color: #f8f9fa; padding: 15px; border-radius: 10px; margin-bottom: 20px;'>
            Access the raw conversation logs for each agent:
        </div>
    """, unsafe_allow_html=True)
    
    # Create columns for agent log links
    log_cols = st.columns(3)
    agents = ['Tata', 'Gaia', 'Sara']
    
    for idx, agent in enumerate(agents):
        with log_cols[idx]:
            log_url = get_agent_log_url(agent)
            st.markdown(f"""
                <div style='text-align: center;'>
                    <a href="{log_url}" target="_blank" style='
                        display: inline-block;
                        padding: 10px 20px;
                        background-color: #f0f0f0;
                        border-radius: 5px;
                        text-decoration: none;
                        color: #333;
                        border: 1px solid #ddd;
                    '>
                        📝 {agent}'s Log
                    </a>
                </div>
            """, unsafe_allow_html=True)
    
    # Add audio player section
    st.header("🎧 Listen to Sample Debate")
    st.markdown("""
        <div style='background-color: #f0f8ff; padding: 15px; border-radius: 10px; margin-bottom: 20px;'>
            Listen to a sample of the debate with distinct voices for each agent:
            <ul>
                <li>Tata: Male, AI-like voice</li>
                <li>Gaia: Female, warm voice</li>
                <li>Sara: Female, professional voice</li>
            </ul>
        </div>
    """, unsafe_allow_html=True)
    
    # Get base locations
    base_path, base_url = get_base_locations()
    
    # Set audio path based on environment
    if st.runtime.exists():
        # When deployed on Streamlit Cloud, use base_url
        audio_url = f"{base_url}/sound/debate_speech_20241218_134139.mp3"
    else:
        # When running locally, use base_path
        audio_url = os.path.join(base_path, "output", "debate_speech.mp3")
    
    st.audio(audio_url, format='audio/mp3')
    
    # Color coding for different speakers
    colors = {
        'Tata': {
            'bg': '#FFE6E6',
            'border': '#FF6666',
            'icon': '🤖',
            'role': 'AI Safety'
        },
        'Gaia': {
            'bg': '#E6FFE6',
            'border': '#66FF66',
            'icon': '🌍',
            'role': 'Environment'
        },
        'Sara': {
            'bg': '#E6E6FF',
            'border': '#6666FF',
            'icon': '👥',
            'role': 'Human Rights'
        }
    }
    
    # Initialize session states
    if 'message_index' not in st.session_state:
        st.session_state.message_index = 0
    if 'selected_speakers' not in st.session_state:
        st.session_state.selected_speakers = set()
    if 'show_filters' not in st.session_state:
        st.session_state.show_filters = False
    
    # Get all messages
    all_messages = get_all_messages()
    
    # Toggle filters button
    if st.button("Toggle Speaker Filters" if not st.session_state.show_filters else "Hide Filters"):
        st.session_state.show_filters = not st.session_state.show_filters
        st.session_state.selected_speakers = set()  # Clear selections when toggling
        st.session_state.message_index = 0  # Reset index when toggling filters
        st.rerun()
    
    # Show speaker selection if filters are enabled
    if st.session_state.show_filters:
        st.markdown("""
            <div style='background-color: #f8f9fa; padding: 15px; border-radius: 10px; margin: 20px 0;'>
                <div style='font-weight: bold; margin-bottom: 10px;'>Select Participants to View:</div>
                <div style='font-size: 0.9em; color: #666; margin-bottom: 10px;'>
                    Click one speaker to see their messages, or two speakers to see their conversation.
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        cols = st.columns(3)
        for i, (speaker, info) in enumerate(colors.items()):
            is_selected = speaker in st.session_state.selected_speakers
            if cols[i].button(
                f"{info['icon']} {speaker}",
                key=f"btn_{speaker}",
                type="primary" if is_selected else "secondary",
            ):
                if speaker in st.session_state.selected_speakers:
                    st.session_state.selected_speakers.remove(speaker)
                else:
                    if len(st.session_state.selected_speakers) < 2:
                        st.session_state.selected_speakers.add(speaker)
                    else:
                        # If two speakers are already selected, remove the first one
                        st.session_state.selected_speakers = {list(st.session_state.selected_speakers)[1], speaker}
                st.session_state.message_index = 0  # Reset index when changing selection
                st.rerun()
    
    # Filter messages if speakers are selected
    messages = filter_messages(all_messages, st.session_state.selected_speakers)
    
    if not messages:
        if st.session_state.selected_speakers:
            speakers_list = " and ".join(st.session_state.selected_speakers)
            st.info(f"No messages found between {speakers_list}.")
        else:
            st.info("No messages found. Please check the agent files.")
        return
    
    # Ensure message_index is valid for filtered messages
    st.session_state.message_index = min(st.session_state.message_index, len(messages) - 1)
    
    # Container for messages with max width
    st.markdown("""
        <style>
            .message-container {
                max-width: 800px;
                margin: 0 auto;
            }
            .message-header {
                display: flex;
                align-items: center;
                gap: 10px;
                margin-bottom: 10px;
            }
            .message-timestamp {
                color: #666;
                font-size: 0.9em;
            }
            .message-content {
                line-height: 1.6;
                font-size: 1.1em;
            }
            .message-badge {
                display: inline-flex;
                align-items: center;
                gap: 5px;
                padding: 5px 15px;
                border-radius: 20px;
                font-size: 0.9em;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Show messages up to current index
    for i in range(st.session_state.message_index + 1):
        message = messages[i]
        speaker_info = colors[message['speaker']]
        recipient_info = colors.get(message['recipient'], {
            'bg': '#f8f9fa',
            'border': '#666666',
            'icon': '👥'
        })
        
        st.markdown(f"""
            <div class='message-container'>
                <div style='
                    background-color: {speaker_info['bg']};
                    border: 2px solid {speaker_info['border']};
                    padding: 15px;
                    border-radius: 10px;
                    margin: 15px 0;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                '>
                    <div class='message-header'>
                        <div class='message-badge' style='
                            background-color: {speaker_info['bg']};
                            border: 2px solid {speaker_info['border']};
                        '>
                            {speaker_info['icon']} <strong>{message['speaker']}</strong>
                        </div>
                        <span style='color: #666;'>→</span>
                        <div class='message-badge' style='
                            background-color: {recipient_info['bg']};
                            border: 2px solid {recipient_info['border']};
                        '>
                            {recipient_info['icon']} <strong>{message['recipient']}</strong>
                        </div>
                        <span class='message-timestamp'>{message['timestamp']}</span>
                    </div>
                    <div class='message-content' style='
                        background-color: white;
                        padding: 15px;
                        border-radius: 5px;
                        border: 1px solid rgba(0,0,0,0.1);
                    '>
                        {message['message']}
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    # Show progress and navigation
    st.markdown(f"""
        <div style='
            text-align: center;
            margin: 20px auto;
            padding: 10px;
            background-color: #f0f0f0;
            border-radius: 5px;
            max-width: 800px;
        '>
            Showing messages 1-{st.session_state.message_index + 1} of {len(messages)}
            {f" between {' and '.join(st.session_state.selected_speakers)}" if st.session_state.selected_speakers else ""}
        </div>
    """, unsafe_allow_html=True)
    
    # Navigation buttons in container
    st.markdown("""
        <div style='max-width: 800px; margin: 0 auto;'>
            <div style='display: flex; justify-content: space-between;'>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    # Previous button
    if st.session_state.message_index > 0:
        if col1.button("← Show Less"):
            st.session_state.message_index -= 1
            st.rerun()
    
    # Next button
    if st.session_state.message_index < len(messages) - 1:
        if col2.button("Show More →"):
            st.session_state.message_index += 1
            st.rerun()
            
    st.markdown("</div></div>", unsafe_allow_html=True)

if __name__ == "__main__":
    st.set_page_config(
        page_title="AI Apocalypse Club Debate",
        page_icon="🗣️",
        layout="wide"
    )
    display_debate()
