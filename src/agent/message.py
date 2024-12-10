import re
from datetime import datetime
from enum import Enum
from typing import Optional, Union, Dict
from uuid import UUID

from pydantic import BaseModel, Field

from ..event.base import Event, EventType, MessageEventSubtype
from ..location.base import Location
from ..utils.general import deduplicate_list
from ..world.context import WorldContext


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

    def get_event_message(self) -> str:
        if self.type == MessageEventSubtype.AGENT_TO_HUMAN:
            event_message = f"{self.sender_name} asked the humans: '{self.content}'"
        elif self.recipient_id is None:
            event_message = f"{self.sender_name} said to everyone in the {self.location.name}: '{self.content}'"
        else:
            event_message = (
                f"{self.sender_name} said to {self.recipient_name}: '{self.content}'"
            )
        return event_message

    @classmethod
    def from_agent_input(
        cls,
        agent_input: Union[str, Dict[str, str]],
        agent_id: UUID,
        context: WorldContext,
        type: MessageEventSubtype = MessageEventSubtype.AGENT_TO_AGENT,
    ):
        # get the agent name and location id
        agent_name = context.get_agent_full_name(agent_id)
        agent_location_id = context.get_agent_location_id(agent_id)

        # make the location object
        location = [
            Location(**loc)
            for loc in context.locations
            if str(loc["id"]) == str(agent_location_id)
        ][0]

        if type == MessageEventSubtype.AGENT_TO_AGENT:
            # Handle both string and dict inputs
            if isinstance(agent_input, dict):
                recipient_name = agent_input.get("recipient", "").strip()
                content = agent_input.get("message", "").strip()
            else:
                try:
                    # Fallback to semicolon split for backwards compatibility
                    parts = agent_input.split(";", 1)  # Split on first semicolon only
                    if len(parts) != 2:
                        raise ValueError("Invalid message format")
                    recipient_name, content = parts
                except Exception as e:
                    raise ValueError(f"Could not parse message: {str(e)}")

            # remove the leading and trailing quotation marks if they exist
            content = content.strip().strip("'").strip('"')
            recipient_name = recipient_name.strip()

            if "everyone" in recipient_name.lower():
                recipient_name = None
                recipient_id = None
            else:
                try:
                    # Handle multiple recipients by taking the first one
                    first_recipient = recipient_name.split(";")[0].strip()
                    recipient_id = context.get_agent_id_from_name(first_recipient)
                    recipient_name = first_recipient
                except Exception as e:
                    raise Exception(f"Could not find agent with name: {recipient_name}")

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
            content=agent_input if isinstance(agent_input, str) else agent_input.get("message", ""),
            sender_id=agent_id,
            location=location,
            context=context,
            type=type,
            timestamp=datetime.now(),
            sender_name=agent_name,
        )

    @classmethod
    def from_event(cls, event: Event, context: WorldContext):
        if event.type != EventType.MESSAGE:
            raise ValueError("Event must be of type message")

        # get the location object
        location = [
            Location(**loc)
            for loc in context.locations
            if str(loc["id"]) == str(event.location_id)
        ][0]

        discord_id = (
            event.metadata["discord_id"]
            if event.metadata is not None and "discord_id" in event.metadata
            else None
        )

        if event.subtype == MessageEventSubtype.AGENT_TO_AGENT:
            # Handle both quoted and unquoted message formats, including multiple recipients
            pattern = r"(?P<sender>[\w\s]+) said to (?P<recipient>[\w\s;]+)(?: in the [\w\s]+)?: ['\"]*(?P<message>.*)['\"]*$"
            match = re.search(pattern, event.description)
            if not match:
                # If no match, try simpler pattern without quotes
                pattern = r"(?P<sender>[\w\s]+) said to (?P<recipient>[\w\s;]+)(?: in the [\w\s]+)?: (?P<message>.*)"
                match = re.search(pattern, event.description)
                if not match:
                    raise ValueError(f"Could not parse message: {event.description}")
            
            sender_name = match.group("sender").strip()
            recipients = match.group("recipient").strip()
            content = match.group("message").strip().strip("'\"")

            if "everyone" in recipients.lower():
                recipient_name = None
                recipient_id = None
            else:
                # Handle multiple recipients by taking the first one
                recipient_name = recipients.split(";")[0].strip()
                try:
                    recipient_id = context.get_agent_id_from_name(recipient_name)
                except Exception:
                    # If first recipient not found, try others
                    recipient_found = False
                    for recipient in recipients.split(";"):
                        recipient = recipient.strip()
                        try:
                            recipient_id = context.get_agent_id_from_name(recipient)
                            recipient_name = recipient
                            recipient_found = True
                            break
                        except Exception:
                            continue
                    if not recipient_found:
                        raise ValueError(f"Could not find any valid recipients in: {recipients}")

            return cls(
                content=content,
                sender_id=str(event.agent_id),
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
            recipient_id = event.metadata["referenced_agent_id"]
            recipient_name = context.get_agent_full_name(recipient_id)
            content = event.description.split(": ")[-1]

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
            pattern = r"(?P<sender>[\w\s]+) asked the humans: ['\"]*(?P<message>.*)['\"]*$"
            match = re.search(pattern, event.description)
            if not match:
                raise ValueError(f"Could not parse message: {event.description}")

            sender_name = match.group("sender").strip()
            content = match.group("message").strip().strip("'\"")

            return cls(
                content=content,
                sender_id=str(event.agent_id),
                sender_name=sender_name,
                location=location,
                context=context,
                timestamp=event.timestamp,
                event_id=event.id,
                type=event.subtype,
                discord_id=discord_id,
            )

        sender_name = context.get_agent_full_name(event.agent_id)

        return cls(
            content=event.description,
            sender_id=str(event.agent_id),
            sender_name=sender_name,
            location=location,
            context=context,
            timestamp=event.timestamp,
            event_id=event.id,
            type=event.subtype,
            discord_id=discord_id,
        )

    def to_event(self) -> Event:
        # get the agent_name and location_name
        event_message = self.get_event_message()

        event = Event(
            agent_id=self.sender_id,
            type=EventType.MESSAGE,
            subtype=self.type,
            description=event_message,
            location_id=self.location.id,
            metadata={"discord_id": self.discord_id}
            if self.discord_id is not None
            else None,
        )

        self.event_id = event.id

        return event

    def __str__(self):
        if self.recipient_name is None:
            return f"[{self.location.name}] {self.sender_name}: {self.content}"
        else:
            return f"[{self.location.name}] {self.sender_name} to {self.recipient_name}: {self.content}"


class LLMMessageResponse(BaseModel):
    to: str = Field(description="The recipient of the message")
    content: str = Field(description="The content of the message")


def get_latest_messages(messages: list[AgentMessage]) -> list[AgentMessage]:
    messages.sort(key=lambda x: x.timestamp, reverse=True)

    return deduplicate_list(messages, key=lambda x: str(x.sender_id))


async def get_conversation_history(
    agent_id: UUID | str,
    context: WorldContext,
) -> str:
    """Gets up to 20 messages from the location. If a message is provided, only gets messages from that agent."""
    if isinstance(agent_id, str):
        agent_id = UUID(agent_id)

    # get all the messages sent at the location witnessed by the agent_id
    (message_events, _) = await context.events_manager.get_events(
        type=EventType.MESSAGE,
        witness_ids=[agent_id],
    )

    messages = [AgentMessage.from_event(event, context) for event in message_events]

    # sort the messages by timestamp, with the newest messages last
    messages.sort(key=lambda x: x.timestamp)

    # limit the messages to 20
    messages = messages[-20:]

    formatted_messages = [
        f"{m.sender_name}: {m.content} @ {m.timestamp}" for m in messages
    ]

    return "\n".join(formatted_messages)
