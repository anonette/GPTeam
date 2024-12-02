from typing import Dict, Optional, Set
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

class ConversationThread(BaseModel):
    """Tracks the state of a single conversation thread"""
    participants: Set[UUID]  # The agents involved in this conversation
    last_speaker: Optional[UUID] = None  # The agent who spoke last
    last_message_time: Optional[datetime] = None
    waiting_for_response: bool = False
    
    def can_speak(self, agent_id: UUID) -> bool:
        """Check if an agent can speak in this conversation"""
        # Can't speak if waiting for a response and you were the last speaker
        if self.waiting_for_response and agent_id == self.last_speaker:
            return False
        return True
    
    def record_message(self, speaker_id: UUID):
        """Record that an agent has spoken"""
        self.last_speaker = speaker_id
        self.last_message_time = datetime.now()
        self.waiting_for_response = True
    
    def record_response(self, responder_id: UUID):
        """Record that someone has responded"""
        if responder_id != self.last_speaker:
            self.waiting_for_response = False
            self.last_speaker = responder_id
            self.last_message_time = datetime.now()

class ConversationState:
    """Tracks the state of all conversations"""
    def __init__(self):
        self.threads: Dict[str, ConversationThread] = {}
    
    def _get_thread_key(self, agent_id: UUID, recipient_id: Optional[UUID] = None) -> str:
        """Get a unique key for a conversation thread"""
        if recipient_id is None:
            return "broadcast"
        return "-".join(sorted([str(agent_id), str(recipient_id)]))
    
    def can_speak(self, agent_id: UUID, recipient_id: Optional[UUID] = None) -> bool:
        """Check if an agent can speak to a recipient"""
        thread_key = self._get_thread_key(agent_id, recipient_id)
        
        # If thread doesn't exist, agent can speak
        if thread_key not in self.threads:
            return True
            
        return self.threads[thread_key].can_speak(agent_id)
    
    def record_message(self, speaker_id: UUID, recipient_id: Optional[UUID] = None):
        """Record that an agent has sent a message"""
        thread_key = self._get_thread_key(speaker_id, recipient_id)
        
        # Create new thread if it doesn't exist
        if thread_key not in self.threads:
            participants = {speaker_id}
            if recipient_id:
                participants.add(recipient_id)
            self.threads[thread_key] = ConversationThread(participants=participants)
            
        self.threads[thread_key].record_message(speaker_id)
    
    def record_response(self, responder_id: UUID, original_speaker_id: UUID):
        """Record that an agent has responded to another agent"""
        thread_key = self._get_thread_key(responder_id, original_speaker_id)
        
        if thread_key in self.threads:
            self.threads[thread_key].record_response(responder_id)

# Global conversation state tracker
conversation_state = ConversationState()
