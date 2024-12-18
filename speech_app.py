import streamlit as st
import os
from pathlib import Path
from speech_generator import generate_debate_audio
import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

st.set_page_config(
    page_title="Debate Speech Generator",
    page_icon="🎙️",
    layout="wide"
)

# Create output directory if it doesn't exist
output_dir = Path("output")
output_dir.mkdir(exist_ok=True)

def list_generated_files():
    """List all MP3 files in the output directory with their creation time."""
    files = []
    for file in output_dir.glob("*.mp3"):
        creation_time = datetime.datetime.fromtimestamp(file.stat().st_ctime)
        files.append({
            'name': file.name,
            'path': str(file),
            'created': creation_time,
            'size': file.stat().st_size / (1024 * 1024)  # Size in MB
        })
    return sorted(files, key=lambda x: x['created'], reverse=True)

st.title("🎙️ Debate Speech Generator")

# Get API key from environment variable
api_key = os.getenv("ELEVENLABS_API_KEY")

if api_key:
    if st.button("Generate New Speech File"):
        with st.spinner("Generating speech from debate messages..."):
            try:
                output_file = generate_debate_audio(api_key)
                if output_file:
                    st.success(f"Speech generated successfully! File saved as: {output_file}")
                else:
                    st.error("No messages found to generate speech from.")
            except Exception as e:
                st.error(f"Error generating speech: {str(e)}")

    # Display generated files
    st.header("Generated Speech Files")
    files = list_generated_files()
    
    if not files:
        st.info("No generated speech files found. Click 'Generate New Speech File' to create one.")
    else:
        for file in files:
            with st.expander(f"📁 {file['name']} - {file['created'].strftime('%Y-%m-%d %H:%M:%S')}"):
                col1, col2 = st.columns([3, 1])
                
                # Audio player
                with col1:
                    st.audio(file['path'])
                
                # File info
                with col2:
                    st.markdown(f"""
                        **File Info:**
                        - Size: {file['size']:.2f} MB
                        - Created: {file['created'].strftime('%Y-%m-%d %H:%M:%S')}
                    """)
else:
    st.error("ElevenLabs API key not found in .env file. Please add ELEVENLABS_API_KEY to your .env file.")

# Add some usage instructions
st.sidebar.header("Instructions")
st.sidebar.markdown("""
1. The app uses the ElevenLabs API key from your .env file
2. Click 'Generate New Speech File' to create a new audio file
3. Generated files will appear below with playback controls
4. Each agent has a distinct voice:
   - Tata: Male, AI-like voice (Adam)
   - Gaia: Female, warm voice (Bella)
   - Sara: Female, professional voice (Rachel)
""")
