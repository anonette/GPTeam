import streamlit as st
import re
from pathlib import Path
from typing import List, Dict, Set

def extract_speech_interactions(log_text):
    interactions = []
    seen_messages = set()
    current_timestamp = "00:00:00"
    
    # Split into lines for easier processing
    lines = log_text.split('\n')
    
    # Process one line at a time
    for line in lines:
        # Update current timestamp from Observe lines
        observe_match = re.search(r'\[.*?\] \[LogColor\.AGENT_\d\] \[Observe\] Observed \d+ new events since (\d{2}:\d{2}:\d{2})', line)
        if observe_match:
            current_timestamp = observe_match.group(1)
            continue
            
        # Only look for Action Response lines with speech
        if '[Action Response]' not in line or ' said to ' not in line:
            continue
            
        try:
            # Get the speech part - match everything between the first and last single quotes
            parts = line.split("[Action Response] ")[1]
            speaker_part, message = parts.split(": '", 1)
            speaker, recipient = speaker_part.split(" said to ")
            message = message.rsplit("'", 1)[0]  # Get everything up to the last quote
            
            # Validate speaker
            if speaker not in ['Tata', 'Gaia', 'Sara']:
                continue
                
            # Skip system messages
            if 'The event I was waiting for' in message or 'waiting' in message.lower():
                continue
                
            # Skip empty or duplicate messages
            if not message.strip() or message in seen_messages:
                continue
                
            # Clean up recipient text
            if "everyone in the Conference" in recipient:
                recipient = "everyone"
                
            seen_messages.add(message)
            interactions.append({
                'timestamp': current_timestamp,
                'speaker': speaker,
                'recipient': recipient,
                'message': message.strip()
            })
            
        except Exception as e:
            continue
    
    # Sort by timestamp
    return sorted(interactions, key=lambda x: x['timestamp'])

def filter_interactions(interactions: List[Dict], selected_speakers: Set[str]) -> List[Dict]:
    if not selected_speakers:
        return interactions
        
    if len(selected_speakers) == 1:
        # Show all messages from the selected speaker
        speaker = list(selected_speakers)[0]
        return [i for i in interactions if i['speaker'] == speaker]
    else:
        # Show conversations between selected speakers
        return [i for i in interactions if 
                (i['speaker'] in selected_speakers and i['recipient'] in selected_speakers) or
                (i['speaker'] in selected_speakers and i['recipient'] == 'everyone')]

def display_debate():
    st.title("AI Apocalypse Club Debate")
    
    # Check for log file
    log_path = Path("src/web/logs/agent.txt")
    
    if log_path.exists():
        with open(log_path, 'r') as f:
            log_content = f.read()
        
        interactions = extract_speech_interactions(log_content)
        
        if not interactions:
            st.warning("No speech interactions found in the log file.")
            return
            
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
        
        # Initialize session state for selected speakers
        if 'selected_speakers' not in st.session_state:
            st.session_state.selected_speakers = set()
        
        # Show speaker selection
        st.markdown("""
            <div style='background-color: #f8f9fa; padding: 15px; border-radius: 10px; margin-bottom: 20px;'>
                <div style='font-weight: bold; margin-bottom: 10px;'>Select Participants to View:</div>
                <div style='font-size: 0.9em; color: #666; margin-bottom: 10px;'>
                    Click one speaker to see their messages, or two speakers to see their conversation.
                </div>
                <div style='display: flex; flex-wrap: wrap; gap: 10px;'>
        """, unsafe_allow_html=True)
        
        for speaker, info in colors.items():
            is_selected = speaker in st.session_state.selected_speakers
            if st.button(
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
                st.rerun()
        
        st.markdown("</div></div>", unsafe_allow_html=True)
        
        # Filter interactions based on selected speakers
        filtered_interactions = filter_interactions(interactions, st.session_state.selected_speakers)
        
        if not filtered_interactions:
            if st.session_state.selected_speakers:
                speakers_list = " and ".join(st.session_state.selected_speakers)
                st.info(f"No messages found between {speakers_list}.")
            else:
                st.info("Select one or two participants to view their messages.")
            return
        
        # Show filtered messages
        for interaction in filtered_interactions:
            speaker_info = colors[interaction['speaker']]
            recipient_info = colors.get(interaction['recipient'], {
                'bg': '#f8f9fa',
                'border': '#666666',
                'icon': '👥'
            })
            
            st.markdown(f"""
                <div style='
                    background-color: {speaker_info['bg']};
                    border: 2px solid {speaker_info['border']};
                    padding: 20px;
                    border-radius: 10px;
                    margin: 20px 0;
                '>
                    <div style='color: #666; margin-bottom: 10px;'>{interaction['timestamp']}</div>
                    <div style='
                        display: flex;
                        align-items: center;
                        background-color: rgba(255,255,255,0.7);
                        padding: 10px;
                        border-radius: 5px;
                        margin-bottom: 15px;
                        gap: 10px;
                    '>
                        <div style='
                            background-color: {speaker_info['bg']};
                            border: 2px solid {speaker_info['border']};
                            padding: 5px 15px;
                            border-radius: 20px;
                            display: inline-flex;
                            align-items: center;
                            gap: 5px;
                        '>
                            {speaker_info['icon']} <strong>{interaction['speaker']}</strong>
                        </div>
                        <div style='color: #666;'>responding to</div>
                        <div style='
                            background-color: {recipient_info['bg']};
                            border: 2px solid {recipient_info['border']};
                            padding: 5px 15px;
                            border-radius: 20px;
                            display: inline-flex;
                            align-items: center;
                            gap: 5px;
                        '>
                            {recipient_info['icon']} <strong>{interaction['recipient']}</strong>
                        </div>
                    </div>
                    <div style='
                        background-color: white;
                        padding: 15px;
                        border-radius: 5px;
                        border: 1px solid rgba(0,0,0,0.1);
                    '>
                        {interaction['message']}
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
        # Show message count
        if st.session_state.selected_speakers:
            speakers_list = " and ".join(st.session_state.selected_speakers)
            st.markdown(f"""
                <div style='
                    text-align: center;
                    margin: 20px 0;
                    padding: 10px;
                    background-color: #f0f0f0;
                    border-radius: 5px;
                '>
                    Showing {len(filtered_interactions)} messages {
                        f"from {speakers_list}" if len(st.session_state.selected_speakers) == 1
                        else f"between {speakers_list}"
                    }
                </div>
            """, unsafe_allow_html=True)
    else:
        st.error(f"Log file not found at {log_path}")

if __name__ == "__main__":
    st.set_page_config(
        page_title="AI Apocalypse Club Debate",
        page_icon="🗣️",
        layout="wide"
    )
    display_debate()
