import os
from pathlib import Path
import requests
from debate_visualizer import get_all_messages
from pydub import AudioSegment
from pydub.effects import normalize
import io
import datetime

# Voice IDs from ElevenLabs
VOICE_CONFIG = {
    'Tata': {
        'voice_id': 'pNInz6obpgDQGcFmaJgB',  # Adam - Male, AI-like, confident
        'style': 1.0,
        'stability': 0.5,
        'target_dBFS': -20  # Target volume level
    },
    'Gaia': {
        'voice_id': 'EXAVITQu4vr4xnSDxMaL',  # Bella - Female, warm, nature-focused
        'style': 1.0,
        'stability': 0.7,
        'target_dBFS': -20  # Target volume level
    },
    'Sara': {
        'voice_id': '21m00Tcm4TlvDq8ikWAM',  # Rachel - Female, professional, human rights advocate
        'style': 1.0,
        'stability': 0.6,
        'target_dBFS': -20  # Target volume level
    }
}

def generate_speech_with_elevenlabs(text, voice_id, api_key, style=1.0, stability=0.5):
    """Generate speech using ElevenLabs API."""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }
    
    data = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": stability,
            "similarity_boost": style
        }
    }
    
    response = requests.post(url, json=data, headers=headers)
    
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"Error generating speech: {response.text}")

def normalize_audio(audio_segment, target_dBFS):
    """Normalize audio to target dBFS level."""
    change_in_dBFS = target_dBFS - audio_segment.dBFS
    return audio_segment.apply_gain(change_in_dBFS)

def generate_debate_audio(api_key, max_duration_seconds=180):
    """Generate a combined audio file from agent messages using ElevenLabs voices."""
    # Create temp directory for audio files if it doesn't exist
    temp_dir = Path("temp_audio")
    temp_dir.mkdir(exist_ok=True)
    
    # Get all messages
    messages = get_all_messages()
    
    # Generate individual audio files
    audio_segments = []
    total_duration_ms = 0
    
    for idx, message in enumerate(messages):
        speaker = message['speaker']
        voice_config = VOICE_CONFIG[speaker]
        
        # Format the text for speech
        speech_text = message['message']
        
        try:
            # Generate audio using ElevenLabs
            audio_content = generate_speech_with_elevenlabs(
                speech_text,
                voice_config['voice_id'],
                api_key,
                voice_config['style'],
                voice_config['stability']
            )
            
            # Save temporary file
            temp_file = temp_dir / f"message_{idx}.mp3"
            with open(temp_file, 'wb') as f:
                f.write(audio_content)
            
            # Load audio segment and normalize volume
            audio = AudioSegment.from_mp3(str(temp_file))
            audio = normalize_audio(audio, voice_config['target_dBFS'])
            
            # Add 0.5 second pause between messages
            if audio_segments:
                pause = AudioSegment.silent(duration=500)  # 0.5 second
                audio_segments.append(pause)
                total_duration_ms += 500
            
            # Check if adding this segment would exceed max duration
            if total_duration_ms + len(audio) > max_duration_seconds * 1000:
                break
            
            audio_segments.append(audio)
            total_duration_ms += len(audio)
            
            print(f"Processed {speaker}'s message {idx + 1} - Duration: {len(audio)/1000:.2f}s, Volume: {audio.dBFS:.1f} dBFS")
            
        except Exception as e:
            print(f"Error processing message {idx}: {str(e)}")
            continue
    
    # Combine all audio segments
    if audio_segments:
        combined = sum(audio_segments)
        
        # Final normalization pass on the combined audio
        combined = normalize_audio(combined, -20)
        
        # Create output directory if it doesn't exist
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        # Generate timestamp for unique filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"debate_speech_{timestamp}.mp3"
        
        # Export final audio
        combined.export(str(output_file), format="mp3")
        
        # Cleanup temp files
        for file in temp_dir.glob("*.mp3"):
            file.unlink()
        temp_dir.rmdir()
        
        print(f"Generated {len(audio_segments)} speech segments")
        print(f"Total duration: {total_duration_ms/1000:.2f} seconds")
        print(f"Final audio level: {combined.dBFS:.1f} dBFS")
        
        return str(output_file)
    
    return None

if __name__ == "__main__":
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print("Please set ELEVENLABS_API_KEY environment variable")
        exit(1)
        
    print("Generating speech from debate messages...")
    output_file = generate_debate_audio(api_key)
    if output_file:
        print(f"Speech generated successfully! File saved to: {output_file}")
    else:
        print("No messages found to generate speech from.")
