import re
from datetime import datetime
from enum import Enum
from typing import Optional, Tuple
from uuid import UUID

from pydantic import BaseModel, Field, validator

from ..event.base import Event, EventType, MessageEventSubtype
from ..location.base import Location
from ..utils.general import deduplicate_list
from ..world.context import WorldContext


class MessageParsingError(Exception):
    """Custom exception for message parsing errors"""
    pass


class LLMMessageResponse(BaseModel):
    """Response model for LLM message processing"""
    content: str
    recipient_name: Optional[str] = None
    thought_process: str = Field(description="The reasoning behind the message content")


class MessageFormat(BaseModel):
    """Standard format for message content"""
    recipient: str
    message: str

    @validator('recipient')
    def validate_recipient(cls, v):
        if not isinstance(v, str):
            raise ValueError("Recipient must be a string")
        # Remove any special characters and extra whitespace
        v = re.sub(r'[^\w\s]', '', v)
        return v.strip()

    @validator('message')
    def validate_message(cls, v):
        if not isinstance(v, str):
            raise ValueError("Message must be a string")
        # Remove any nested JSON-like structures
        v = re.sub(r'\{.*?\}', '', v)
        # Clean up any remaining special characters
        v = re.sub(r'[^\w\s:,.!?\'"-]', '', v)
        return v.strip()

    @classmethod
    def parse_raw(cls, raw_input: str) -> 'MessageFormat':
        """Parse raw input string into MessageFormat, handling missing commas"""
        try:
            # First try parsing as-is
            import json
            try:
                data = json.loads(raw_input)
            except json.JSONDecodeError:
                # If parsing fails, try fixing common formatting issues
                # Add missing comma between fields
                fixed_input = re.sub(r'"\s+"', '", "', raw_input)
                data = json.loads(fixed_input)
            
            return cls(
                recipient=data.get('recipient', ''),
                message=data.get('message', '')
            )
        except Exception as e:
            raise MessageParsingError(f"Failed to parse message format: {str(e)}")


class AgentMessage(BaseModel):
    content: str
    sender_id: Optional[UUID] = None
    sender_name: str
    type: MessageEventSubtype = MessageEventSubtype.AGENT_TO_AGENT
    recipient_id: Optional[UUID] = None
    recipient_name: Optional[str] = None
    location: Location
    timestamp: datetime
    context: WorldContext
    event_id: UUID = None
    discord_id: Optional[str] = None

    @validator('content')
    def sanitize_content(cls, v):
        """Sanitize message content to prevent format issues"""
        if not isinstance(v, str):
            raise ValueError("Content must be a string")
        # Remove any nested JSON-like structures
        v = re.sub(r'\{.*?\}', '', v)
        # Clean up any remaining special characters
        v = re.sub(r'[^\w\s:,.!?\'"-]', '', v)
        return v.strip()

    def get_event_message(self) -> str:
        """Generate a standardized event message format"""
        try:
            if self.type == MessageEventSubtype.AGENT_TO_HUMAN:
                return f"{self.sender_name} asked the humans: '{self.content}'"
            elif self.recipient_id is None:
                return f"{self.sender_name} said to everyone in the {self.location.name}: '{self.content}'"
            else:
                return f"{self.sender_name} said to {self.recipient_name}: '{self.content}'"
        except Exception as e:
            raise MessageParsingError(f"Failed to generate event message: {str(e)}")

    @classmethod
    def from_agent_input(
        cls,
        agent_input: str,
        agent_id: UUID,
        context: WorldContext,
        type: MessageEventSubtype = MessageEventSubtype.AGENT_TO_AGENT,
    ):
        """Create message from agent input with improved validation"""
        try:
            # Get agent details
            agent_name = context.get_agent_full_name(agent_id)
            agent_location_id = context.get_agent_location_id(agent_id)

            # Validate location
            location = next(
                (Location(**loc) for loc in context.locations 
                 if str(loc["id"]) == str(agent_location_id)),
                None
            )
            if not location:
                raise MessageParsingError(f"Invalid location ID: {agent_location_id}")

            if type == MessageEventSubtype.AGENT_TO_AGENT:
                # Parse recipient and content using strict format
                try:
                    # Remove any JSON-like structures first
                    clean_input = re.sub(r'\{.*?\}', '', agent_input)
                    
                    # Split on first semicolon only
                    parts = clean_input.split(";", 1)
                    
                    if len(parts) == 2:
                        recipient_name = parts[0].strip()
                        content = parts[1].strip().strip("'\"")
                    else:
                        recipient_name = "everyone"
                        content = parts[0].strip().strip("'\"")

                    # Validate content is not empty
                    if not content:
                        raise MessageParsingError("Message content cannot be empty")

                    # Handle recipient
                    if recipient_name.lower() == "everyone":
                        recipient_name = None
                        recipient_id = None
                    else:
                        try:
                            recipient_id = context.get_agent_id_from_name(recipient_name)
                        except Exception as e:
                            raise MessageParsingError(f"Invalid recipient: {str(e)}")

                except Exception as e:
                    raise MessageParsingError(f"Failed to parse message format: {str(e)}")

                return cls(
                    content=content,
                    sender_id=agent_id,
                    recipient_id=recipient_id,
                    recipient_name=recipient_name,
                    location=location,
                    context=context,
                    type=type,
                    timestamp=datetime.now(),
                    sender_name=agent_name,
                )

            return cls(
                content=agent_input,
                sender_id=agent_id,
                location=location,
                context=context,
                type=type,
                timestamp=datetime.now(),
                sender_name=agent_name,
            )
        except Exception as e:
            raise MessageParsingError(f"Failed to create message from agent input: {str(e)}")

    @classmethod
    def from_event(cls, event: Event, context: WorldContext):
        """Create message from event with improved error handling and format validation"""
        try:
            if event.type != EventType.MESSAGE:
                raise MessageParsingError("Event must be of type message")

            # Validate and get location
            location = next(
                (Location(**loc) for loc in context.locations 
                 if str(loc["id"]) == str(event.location_id)),
                None
            )
            if not location:
                raise MessageParsingError(f"Invalid location ID: {event.location_id}")

            # Extract discord ID if present
            discord_id = event.metadata.get("discord_id") if event.metadata else None

            if event.subtype == MessageEventSubtype.AGENT_TO_AGENT:
                # Use more precise regex patterns with named groups
                direct_pattern = r"^(?P<sender>[\w\s]+)\s*said\s*to\s*(?P<recipient>[\w\s]+)\s*:\s*'(?P<content>(?:[^']|'')*)'$"
                broadcast_pattern = r"^(?P<sender>[\w\s]+)\s*said\s*to\s*everyone\s*in\s*the\s*[\w\s]+\s*:\s*'(?P<content>(?:[^']|'')*)'$"
                
                # Try direct message pattern first
                direct_match = re.match(direct_pattern, event.description)
                if direct_match:
                    groups = direct_match.groupdict()
                    sender_name = groups['sender'].strip()
                    recipient = groups['recipient'].strip()
                    content = groups['content'].strip()
                    
                    # Handle recipient
                    if recipient.lower() == "everyone":
                        recipient_name = None
                        recipient_id = None
                    else:
                        recipient_name = recipient
                        try:
                            recipient_id = context.get_agent_id_from_name(recipient_name)
                        except Exception as e:
                            raise MessageParsingError(f"Invalid recipient: {str(e)}")
                else:
                    # Try broadcast pattern
                    broadcast_match = re.match(broadcast_pattern, event.description)
                    if broadcast_match:
                        groups = broadcast_match.groupdict()
                        sender_name = groups['sender'].strip()
                        content = groups['content'].strip()
                        recipient_name = None
                        recipient_id = None
                    else:
                        raise MessageParsingError(
                            f"Could not parse message format. Expected format: '[sender] said to [recipient]: '[content]'' "
                            f"or '[sender] said to everyone in [location]: '[content]''. Got: {event.description}"
                        )

                # Validate content is not empty
                if not content:
                    raise MessageParsingError("Message content cannot be empty")

                return cls(
                    content=content,
                    sender_id=event.agent_id,
                    sender_name=sender_name,
                    location=location,
                    recipient_id=recipient_id,
                    recipient_name=recipient_name,
                    context=context,
                    timestamp=event.timestamp,
                    event_id=event.id,
                    type=event.subtype,
                    discord_id=discord_id,
                )

            elif event.subtype == MessageEventSubtype.HUMAN_AGENT_REPLY:
                # Parse human reply with improved format handling
                pattern = r"^(?:Human:)?\s*(?P<content>.+)$"
                match = re.match(pattern, event.description)
                if not match:
                    raise MessageParsingError(f"Invalid human reply format: {event.description}")
                
                content = match.group('content').strip()

                # Get recipient details
                recipient_id = event.metadata.get("referenced_agent_id")
                if not recipient_id:
                    raise MessageParsingError("Missing referenced_agent_id in human reply")
                recipient_name = context.get_agent_full_name(recipient_id)

                return cls(
                    content=content,
                    sender_name="Human",
                    sender_id=None,
                    location=location,
                    recipient_id=recipient_id,
                    recipient_name=recipient_name,
                    context=context,
                    timestamp=event.timestamp,
                    event_id=event.id,
                    type=event.subtype,
                    discord_id=discord_id,
                )

            elif event.subtype == MessageEventSubtype.AGENT_TO_HUMAN:
                # Parse agent to human message with improved pattern
                pattern = r"^(?P<sender>[\w\s]+)\s*asked\s*the\s*humans:\s*'(?P<content>(?:[^']|'')*)'$"
                match = re.match(pattern, event.description)
                
                if not match:
                    raise MessageParsingError(
                        f"Invalid agent to human message format. Expected format: '[sender] asked the humans: '[content]''. "
                        f"Got: {event.description}"
                    )
                    
                sender_name = match.group('sender').strip()
                content = match.group('content').strip()

                # Validate content is not empty
                if not content:
                    raise MessageParsingError("Message content cannot be empty")

                return cls(
                    content=content,
                    sender_id=event.agent_id,
                    sender_name=sender_name,
                    location=location,
                    context=context,
                    timestamp=event.timestamp,
                    event_id=event.id,
                    type=event.subtype,
                    discord_id=discord_id,
                )

            # Default case
            sender_name = context.get_agent_full_name(event.agent_id)
            return cls(
                content=event.description,
                sender_id=event.agent_id,
                sender_name=sender_name,
                location=location,
                context=context,
                timestamp=event.timestamp,
                event_id=event.id,
                type=event.subtype,
                discord_id=discord_id,
            )

        except Exception as e:
            raise MessageParsingError(f"Failed to create message from event: {str(e)}")

    def to_event(self) -> Event:
        """Convert message to event with validation"""
        try:
            # Validate required fields
            if not self.sender_name:
                raise MessageParsingError("sender_name is required")
            if not self.content:
                raise MessageParsingError("content is required")
            if not self.location:
                raise MessageParsingError("location is required")
            
            event_message = self.get_event_message()
            
            metadata = {"discord_id": self.discord_id} if self.discord_id else None
            
            event = Event(
                agent_id=self.sender_id,
                type=EventType.MESSAGE,
                subtype=self.type,
                description=event_message,
                location_id=self.location.id,
                metadata=metadata,
            )

            self.event_id = event.id
            return event
            
        except Exception as e:
            raise MessageParsingError(f"Failed to convert message to event: {str(e)}")

    def __str__(self):
        """String representation with error handling"""
        try:
            if self.recipient_name is None:
                return f"[{self.location.name}] {self.sender_name}: {self.content}"
            else:
                return f"[{self.location.name}] {self.sender_name} to {self.recipient_name}: {self.content}"
        except Exception as e:
            return f"<Invalid message format: {str(e)}>"


def get_latest_messages(messages: list[AgentMessage]) -> list[AgentMessage]:
    """Get latest messages with validation"""
    if not isinstance(messages, list):
        raise ValueError("Expected list of messages")
    
    messages.sort(key=lambda x: x.timestamp, reverse=True)
    return deduplicate_list(messages, key=lambda x: str(x.sender_id))


async def get_conversation_history(
    agent_id: UUID | str,
    context: WorldContext,
) -> str:
    """Get conversation history with improved error handling"""
    try:
        if isinstance(agent_id, str):
            agent_id = UUID(agent_id)

        # Get message events
        message_events, _ = await context.events_manager.get_events(
            type=EventType.MESSAGE,
            witness_ids=[agent_id],
        )

        # Parse messages with validation
        messages = []
        for event in message_events:
            try:
                message = AgentMessage.from_event(event, context)
                messages.append(message)
            except MessageParsingError as e:
                print(f"Warning: Skipped invalid message: {str(e)}")
                continue

        # Sort and limit messages
        messages.sort(key=lambda x: x.timestamp)
        messages = messages[-20:]

        # Group messages by conversation thread
        conversation_threads = {}
        for msg in messages:
            thread_key = (
                tuple(sorted([str(msg.sender_id), str(msg.recipient_id)]))
                if msg.recipient_id
                else ('everyone', str(msg.sender_id))
            )
            
            if thread_key not in conversation_threads:
                conversation_threads[thread_key] = []
            conversation_threads[thread_key].append(msg)

        # Format messages
        formatted_messages = []
        for thread_key, thread_messages in conversation_threads.items():
            thread_messages.sort(key=lambda x: x.timestamp)
            
            # Add thread separator
            if thread_messages[0].recipient_id:
                formatted_messages.append(
                    f"\nConversation between {thread_messages[0].sender_name} "
                    f"and {thread_messages[0].recipient_name}:"
                )
            else:
                formatted_messages.append(
                    f"\nBroadcast messages from {thread_messages[0].sender_name}:"
                )
            
            # Add messages with timestamps
            for m in thread_messages:
                formatted_messages.append(
                    f"{m.sender_name}: {m.content} @ {m.timestamp}"
                )

        return "\n".join(formatted_messages)
        
    except Exception as e:
        raise MessageParsingError(f"Failed to get conversation history: {str(e)}")
