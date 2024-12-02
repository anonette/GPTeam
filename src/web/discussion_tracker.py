import re
import json
from typing import Dict, List, Tuple, DefaultDict, Optional, Any
from datetime import datetime
from collections import defaultdict, Counter
from pathlib import Path

class DiscussionTracker:
    """Tracks messages during a simulation for later analysis"""
    
    def __init__(self):
        self.messages = []
        self.current_timestamp = None
    
    def add_message(self, speaker: str, message: str, message_type: str):
        """Add a message to the discussion tracker"""
        self.messages.append({
            'speaker': speaker,
            'message': message,
            'type': message_type,
            'timestamp': datetime.now()
        })
    
    def save_to_file(self, filepath: str):
        """Save the discussion to a file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"debate_log_{timestamp}.txt"
        full_path = Path(filepath) / filename
        
        with open(full_path, 'w') as f:
            for msg in self.messages:
                timestamp = msg['timestamp'].strftime("%Y-%m-%dT%H:%M:%S.%f")
                f.write(f"[{timestamp}]{msg['speaker']}: {msg['message']}\n")

def analyze_debate_dynamics(messages: List[Dict[str, Any]], reactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze the dynamics and evolution of the debate"""
    dynamics = {
        'key_turning_points': [],
        'consensus_moments': [],
        'influential_arguments': [],
        'stance_changes': []
    }
    
    # Track stance changes through reactions
    for reaction in reactions:
        if reaction['decision'] == 'postpone':
            dynamics['stance_changes'].append({
                'speaker': reaction['speaker'],
                'reason': reaction['reasoning']
            })
    
    # Identify influential arguments by tracking responses and reactions
    message_responses = defaultdict(list)
    for i, msg in enumerate(messages[:-1]):
        # Look for direct responses in the next few messages
        for response in messages[i+1:i+4]:  # Look at next 3 messages
            if response.get('target') == msg['speaker']:
                message_responses[msg['message']].append(response)
    
    # Find arguments that generated the most responses
    for message, responses in message_responses.items():
        if len(responses) >= 2:  # If message generated multiple responses
            dynamics['influential_arguments'].append({
                'argument': message,
                'response_count': len(responses)
            })
    
    # Sort influential arguments by response count
    dynamics['influential_arguments'].sort(key=lambda x: x['response_count'], reverse=True)
    
    return dynamics

def analyze_debate(log_file: str) -> Dict[str, Any]:
    """
    Analyze a debate log file and return structured analysis
    """
    with open(log_file, 'r') as f:
        log_content = f.read()
        
    # Extract messages from the log content
    messages = []
    
    # Parse timestamped messages with JSON content
    message_pattern = r'\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+)\](\w+(?:\s+\w+)?):.*?Action Input: ({.*?})'
    matches = re.finditer(message_pattern, log_content, re.DOTALL)
    
    for match in matches:
        timestamp_str, speaker, json_str = match.groups()
        try:
            message_data = json.loads(json_str)
            if 'message' in message_data:
                message_type = 'broadcast' if message_data.get('recipient') == 'everyone' else 'conversation'
                messages.append({
                    'speaker': speaker,
                    'message': message_data['message'],
                    'type': message_type,
                    'target': message_data.get('recipient'),
                    'timestamp': datetime.strptime(timestamp_str.split('.')[0], '%Y-%m-%dT%H:%M:%S')
                })
        except json.JSONDecodeError:
            continue
    
    # Updated patterns to handle all emotional response formats
    emotional_patterns = [
        # Pattern for direct speech
        r'\[(\w+(?:\s+\w+)?)\].*?\[Emotional Response\] (\w+(?:\s+\w+)?) said to (?:everyone in the Conference|(\w+(?:\s+\w+)?)): \'(.*?)\'',
        # Pattern for emotional observations
        r'\[(\w+(?:\s+\w+)?)\].*?\[Emotional Response\] (.*?)(?=\[|$)',
        # Pattern for emotional thoughts
        r'\[(\w+(?:\s+\w+)?)\].*?\[Thought\] (.*?)(?=\[|$)'
    ]
    
    reaction_pattern = r'\[(\w+(?:\s+\w+)?)\].*?\[Reaction\] Decided to (continue|postpone) the current plan: (.*?)(?=\[|$)'
    
    # Track emotional responses using multiple patterns
    for pattern in emotional_patterns:
        for match in re.finditer(pattern, log_content, re.DOTALL):
            if len(match.groups()) == 4:  # Direct speech pattern
                speaker, confirmed_speaker, target, content = match.groups()
                if speaker == confirmed_speaker:
                    messages.append({
                        'speaker': speaker,
                        'message': content,
                        'type': 'broadcast' if target is None else 'conversation',
                        'target': 'everyone' if target is None else target,
                        'timestamp': datetime.now(),
                        'category': 'emotional_response'
                    })
            else:  # Observation or thought pattern
                speaker, content = match.groups()
                # Skip formatting markers
                if not any(marker in content for marker in ['##', '```', '{', '}', 'Action:', 'Action Input:', 'Observation:']):
                    messages.append({
                        'speaker': speaker,
                        'message': content.strip(),
                        'type': 'emotional',
                        'timestamp': datetime.now(),
                        'category': 'emotional_response'
                    })
    
    # Track reactions and stance changes
    reactions = []
    for match in re.finditer(reaction_pattern, log_content, re.DOTALL):
        speaker, decision, reasoning = match.groups()
        reactions.append({
            'speaker': speaker,
            'decision': decision,
            'reasoning': reasoning.strip()
        })
    
    # Sort messages by timestamp
    messages.sort(key=lambda x: x['timestamp'])
    
    # Generate analysis
    analysis = {
        'summary': generate_summary(messages, reactions, dynamics),
        'participation': analyze_participation(messages),
        'interactions': analyze_interactions(messages),
        'strategies': analyze_strategies(messages),
        'categorized_quotes': categorize_quotes(messages),
        'debate_dynamics': analyze_debate_dynamics(messages, reactions)
    }
    
    return analysis

# Rest of the file remains unchanged...
