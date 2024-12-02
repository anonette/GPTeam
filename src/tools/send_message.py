import os
from datetime import datetime
from typing import Optional, Union
from uuid import UUID

import pytz
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from src.agent.message import AgentMessage
from src.tools.context import ToolContext
from src.agent.conversation_state import conversation_state

from ..event.base import Event, EventType
from ..utils.discord import send_message as send_discord_message
from ..utils.discord import send_message_async as send_discord_message_async
from ..utils.parameters import DISCORD_ENABLED

load_dotenv()


class SpeakToolInput(BaseModel):
    """Input for the document tool."""

    recipient: str = Field(..., description="recipient of message")
    message: str = Field(..., description="content of message")


async def send_message_async(recipient: str, message: str, tool_context: ToolContext) -> str:
    """Emits a message event to the Events table and triggers discord to send a message.
    
    Args:
        recipient: The name of the recipient agent
        message: The content of the message to send
        tool_context: The tool context containing agent and environment info
        
    Returns:
        str: Description of the event or error message
        
    Raises:
        Exception: If there is an error creating the agent message or sending to discord
    """
    return await _send_message_impl(recipient, message, tool_context, is_async=True)


def send_message_sync(recipient: str, message: str, tool_context: ToolContext) -> str:
    """Synchronous version of send_message_async."""
    return _send_message_impl(recipient, message, tool_context, is_async=False)


async def _send_message_impl(
    recipient: str, 
    message: str, 
    tool_context: ToolContext,
    is_async: bool = True
) -> str:
    """Implementation of message sending logic shared between sync/async versions."""

    # Make an AgentMessage object
    agent_message = None
    try:
        agent_message = AgentMessage.from_agent_input(
            f"{recipient}; {message}", tool_context.agent_id, tool_context.context
        )
    except Exception as e:
        if "Could not find agent" in str(e):
            return "Could not find agent with that name. Try checking the directory."
        else:
            raise e

    # Check if agent can speak based on conversation state
    if not conversation_state.can_speak(tool_context.agent_id, agent_message.recipient_id):
        return f"Cannot send message - waiting for response from previous message"

    # Send to Discord if enabled
    if DISCORD_ENABLED:
        discord_token = tool_context.context.get_discord_token(agent_message.sender_id)
        channel_id = tool_context.context.get_channel_id(agent_message.location.id)
        
        try:
            if is_async:
                discord_message = await send_discord_message_async(
                    discord_token,
                    channel_id,
                    message,
                )
            else:
                discord_message = send_discord_message(
                    discord_token,
                    channel_id,
                    message,
                )
            agent_message.discord_id = str(discord_message.id)
        except Exception as e:
            return f"Failed to send message to Discord: {str(e)}"

    # Convert the AgentMessage to an event
    event: Event = agent_message.to_event()

    # Add it to the events manager
    if is_async:
        event = await tool_context.context.add_event(event)
    else:
        event = tool_context.context.add_event(event)

    # Record the message in conversation state
    conversation_state.record_message(
        tool_context.agent_id,
        agent_message.recipient_id
    )

    return event.description
