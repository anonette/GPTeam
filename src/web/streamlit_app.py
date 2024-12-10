import streamlit as st
import re
from datetime import datetime
import pytz

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
            'main': '#4CAF50',      # Green
            'light': '#E8F5E9'
        },
        'Sara': {
            'main': '#2196F3',      # Blue
            'light': '#E3F2FD'
        },
        'Tata': {
            'main': '#9C27B0',      # Purple
            'light': '#F3E5F5'
        },
        'default': {
            'main': '#757575',      # Grey
            'light': '#F5F5F5'
        }
    }
    return color_map.get(agent_name, color_map['default'])

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

def display_chat(messages):
    st.markdown("""
        <h1 style='text-align: center; color: #1a237e; margin-bottom: 2rem;'>
            💬 Agent Dialogue Visualization
        </h1>
    """, unsafe_allow_html=True)
    
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
