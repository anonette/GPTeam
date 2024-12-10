import os
from datetime import datetime
from uuid import UUID
import json

import pytz
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from src.agent.message import AgentMessage
from src.tools.context import ToolContext

from ..event.base import Event, EventType, MessageEventSubtype
from ..utils.discord import send_message as send_discord_message
from ..utils.discord import send_message_async as send_discord_message_async
from ..utils.parameters import DISCORD_ENABLED

load_dotenv()


class SpeakToolInput(BaseModel):
    """Input for the document tool."""
    recipient: str = Field(..., description="recipient of message")
    message: str = Field(..., description="content of message")


def format_message_input(recipient: str, message: str) -> dict:
    """Format raw recipient and message into proper input format."""
    return {
        "recipient": recipient.strip(),
        "message": message.strip()
    }


async def send_message_async(recipient: str, message: str, tool_context: ToolContext):
    """Emits a message event to the Events table
    And triggers discord to send a message to the appropriate channel
    
    Args:
        recipient: The recipient of the message
        message: The message content
        tool_context: The tool context
    """
    # Format the input
    formatted_input = format_message_input(recipient, message)

    # Make an AgentMessage object
    try:
        # Format input as "recipient; message" for AgentMessage
        agent_input = f"{formatted_input['recipient']}; {formatted_input['message']}"
        agent_message = AgentMessage.from_agent_input(
            agent_input,
            tool_context.agent_id, 
            tool_context.context,
            type=MessageEventSubtype.AGENT_TO_AGENT
        )
    except Exception as e:
        if "Could not find agent" in str(e):
            return "Could not find agent with that name. Try checking the directory."
        else:
            raise e

    if DISCORD_ENABLED:
        discord_token = tool_context.context.get_discord_token(agent_message.sender_id)

        # Send message to discord
        discord_message = await send_discord_message_async(
            discord_token,
            tool_context.context.get_channel_id(agent_message.location.id),
            formatted_input['message'],
        )

        # Add discord id to agent message
        agent_message.discord_id = str(discord_message.id)

    # Convert the AgentMessage to an event
    event: Event = agent_message.to_event()

    # Add to events manager
    event = await tool_context.context.add_event(event)

    return event.description


def send_message_sync(recipient: str, message: str, tool_context: ToolContext):
    """Emits a message event to the Events table
    And triggers discord to send a message to the appropriate channel
    
    Args:
        recipient: The recipient of the message
        message: The message content
        tool_context: The tool context
    """
    # Format the input
    formatted_input = format_message_input(recipient, message)

    # Make an AgentMessage object
    # Format input as "recipient; message" for AgentMessage
    agent_input = f"{formatted_input['recipient']}; {formatted_input['message']}"
    agent_message = AgentMessage.from_agent_input(
        agent_input,
        tool_context.agent_id, 
        tool_context.context,
        type=MessageEventSubtype.AGENT_TO_AGENT
    )

    if DISCORD_ENABLED:
        # Get discord token
        discord_token = tool_context.context.get_discord_token(agent_message.sender_id)

        # Send message to discord
        discord_message = send_discord_message(
            discord_token,
            tool_context.context.get_channel_id(agent_message.location.id),
            agent_message.get_event_message(),
        )

        # Add discord id to agent message
        agent_message.discord_id = str(discord_message.id)

    # Convert the AgentMessage to an event
    event = agent_message.to_event()

    # Add to events manager
    tool_context.context.add_event(event)

    return event.description
