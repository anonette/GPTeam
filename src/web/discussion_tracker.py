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
    
    Args:
        log_file: Path to the log file to analyze
        
    Returns:
        Dictionary containing analysis results
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
    
    # Parse emotional responses and reactions
    emotional_pattern = r'\[(\w+(?:\s+\w+)?)\].*?\[Emotional Response\] (\w+(?:\s+\w+)?) said to (?:everyone in the Conference|(\w+(?:\s+\w+)?)): \'(.*?)\''
    reaction_pattern = r'\[(\w+(?:\s+\w+)?)\].*?\[Reaction\] Decided to (continue|postpone) the current plan: (.*?)(?=\[|$)'
    
    # Track emotional responses
    for match in re.finditer(emotional_pattern, log_content, re.DOTALL):
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
    
    # Analyze debate dynamics
    dynamics = analyze_debate_dynamics(messages, reactions)
    
    # Generate analysis
    analysis = {
        'summary': generate_summary(messages, reactions, dynamics),
        'participation': analyze_participation(messages),
        'interactions': analyze_interactions(messages),
        'strategies': analyze_strategies(messages),
        'categorized_quotes': categorize_quotes(messages),
        'debate_dynamics': dynamics
    }
    
    return analysis

def generate_summary(messages: List[Dict[str, Any]], reactions: List[Dict[str, Any]], dynamics: Dict[str, Any]) -> str:
    """Generate an enhanced summary of the debate including key insights"""
    total_messages = len(messages)
    speakers = Counter(msg['speaker'] for msg in messages)
    most_active = speakers.most_common(1)[0] if speakers else ('No participants', 0)
    
    # Basic statistics
    summary = [
        f"A heated debate unfolded with {total_messages} total exchanges.",
        f"{most_active[0]} was most active with {most_active[1]} messages.",
        "\nKey Debate Insights:",
    ]
    
    # Add stance changes and influential arguments
    if dynamics['stance_changes']:
        summary.append("\nKey Position Shifts:")
        seen_shifts = set()  # Track unique shifts to avoid repetition
        for change in dynamics['stance_changes']:
            # Extract the core reason by removing common prefixes and cleaning up
            reason = change['reason']
            reason = reason.replace("I must postpone my plan because ", "")
            reason = reason.replace("I must postpone the current plan because ", "")
            
            # Create a unique key for this shift
            shift_key = (change['speaker'], reason[:50])  # Use first 50 chars as key
            
            if shift_key not in seen_shifts:
                seen_shifts.add(shift_key)
                # Format the reason more concisely
                formatted_reason = reason.split('.')[0]  # Take first sentence
                summary.append(f"- {change['speaker']} shifted position when: {formatted_reason}")
    
    if dynamics['influential_arguments']:
        summary.append("\nMost Influential Arguments:")
        for arg in dynamics['influential_arguments'][:3]:  # Show top 3
            # Clean up and format the argument
            argument = arg['argument'].split('!')[0] if '!' in arg['argument'] else arg['argument']
            argument = argument.strip()
            if len(argument) > 100:
                argument = argument[:97] + "..."
            summary.append(f"- Generated {arg['response_count']} responses: {argument}")
    
    # Analyze argument patterns
    emotional_appeals = sum(1 for msg in messages if any(word in msg['message'].lower() for word in ['suffering', 'tragedy', 'pain', 'heart']))
    logical_arguments = sum(1 for msg in messages if any(word in msg['message'].lower() for word in ['because', 'therefore', 'evidence', 'fact']))
    
    summary.append("\nArgumentation Patterns:")
    summary.append(f"- Emotional appeals: {emotional_appeals} instances")
    summary.append(f"- Logical arguments: {logical_arguments} instances")
    
    # Add participant overview
    summary.append("\nParticipant Impact Analysis:")
    for speaker, count in speakers.most_common():
        percentage = (count / total_messages) * 100 if total_messages > 0 else 0
        stance_changes = sum(1 for r in reactions if r['speaker'] == speaker and r['decision'] == 'postpone')
        influence = "High" if stance_changes > 1 else "Medium" if stance_changes == 1 else "Low"
        summary.append(f"- {speaker}: {count} messages ({percentage:.1f}%), Influence Level: {influence}")
    
    return "\n".join(summary)

def analyze_participation(messages: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """Analyze participation statistics"""
    total_messages = len(messages)
    message_counts = Counter(msg['speaker'] for msg in messages)
    
    participation = {}
    for speaker, count in message_counts.items():
        broadcasts = sum(1 for msg in messages if msg['speaker'] == speaker and msg['type'] == 'broadcast')
        conversations = sum(1 for msg in messages if msg['speaker'] == speaker and msg['type'] == 'conversation')
        
        participation[speaker] = {
            'count': count,
            'percentage': (count / total_messages) * 100 if total_messages > 0 else 0,
            'broadcasts': broadcasts,
            'conversations': conversations
        }
    
    return participation

def analyze_interactions(messages: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """Analyze interaction patterns between participants"""
    interactions = defaultdict(lambda: defaultdict(int))
    
    for msg in messages:
        speaker = msg['speaker']
        if msg['type'] == 'conversation' and 'target' in msg:
            target = msg['target']
            interactions[speaker][target] += 1
    
    # Convert to percentages
    result = {}
    for speaker, targets in interactions.items():
        total = sum(targets.values())
        if total > 0:
            result[speaker] = {
                target: (count / total) * 100
                for target, count in targets.items()
            }
    
    return result

def analyze_strategies(messages: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Analyze debate strategies used by participants"""
    strategies = {}
    
    for speaker in set(msg['speaker'] for msg in messages):
        speaker_msgs = [m for m in messages if m['speaker'] == speaker]
        
        # Analyze message patterns
        emotional = len([m for m in speaker_msgs if any(word in m['message'].lower() for word in ['must', 'need', 'urgent', 'critical', 'suffering', 'tragedy', 'mother', 'pain', 'heart'])])
        confrontational = len([m for m in speaker_msgs if '!' in m['message'] or any(word in m['message'].lower() for word in ['demand', 'challenge', 'oppose', 'fight', 'threat', 'danger', 'chaos'])])
        persuasive = len([m for m in speaker_msgs if any(word in m['message'].lower() for word in ['consider', 'imagine', 'think', 'understand', 'future', 'safety', 'responsibility'])])
        
        # Determine primary strategy
        strategy_counts = {
            'Emotional Appeal': emotional,
            'Confrontational': confrontational,
            'Persuasive': persuasive
        }
        primary_strategy = max(strategy_counts.items(), key=lambda x: x[1])[0]
        
        strategies[speaker] = {
            'primary_strategy': primary_strategy,
            'stats': {
                'emotional_appeals': emotional,
                'confrontational_statements': confrontational,
                'persuasive_arguments': persuasive
            }
        }
    
    return strategies

def categorize_quotes(messages: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, str]]]:
    """Categorize notable quotes from the debate"""
    categories = {
        'emotional_appeals': [],
        'calls_to_action': [],
        'key_arguments': [],
        'confrontations': []
    }
    
    for msg in messages:
        content = msg['message']
        speaker = msg['speaker']
        
        # Categorize based on content and patterns
        if any(word in content.lower() for word in ['suffering', 'tragedy', 'pain', 'heart', 'mother', 'life', 'death']):
            categories['emotional_appeals'].append({
                'speaker': speaker,
                'message': content
            })
            
        if any(word in content.lower() for word in ['must', 'join', 'rise', 'stand', 'act', 'fight', 'liberate']):
            categories['calls_to_action'].append({
                'speaker': speaker,
                'message': content
            })
            
        if len(content) > 150 and any(word in content.lower() for word in ['because', 'therefore', 'however', 'imagine', 'future', 'reality']):
            categories['key_arguments'].append({
                'speaker': speaker,
                'message': content
            })
            
        if '!' in content or any(word in content.lower() for word in ['demand', 'challenge', 'oppose', 'fight', 'threat', 'danger', 'chaos']):
            categories['confrontations'].append({
                'speaker': speaker,
                'message': content
            })
    
    return categories
