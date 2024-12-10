from src.agent.message import AgentMessage
from src.event.base import MessageEventSubtype
from src.tools.context import ToolContext
from src.utils.parameters import DISCORD_ENABLED

from ..utils.discord import send_message as send_discord_message
from ..utils.discord import send_message_async as send_discord_message_async


def _print_func(text: str) -> None:
    print("\n")
    print(text)


async def ask_human_async(question: str, tool_context: ToolContext):
    """Ask a human for input.
    
    Args:
        question: The question to ask
        tool_context: The tool context
    """
    if DISCORD_ENABLED:
        # Make an AgentMessage object
        agent_message = AgentMessage.from_agent_input(
            question,
            tool_context.agent_id,
            tool_context.context,
            type=MessageEventSubtype.AGENT_TO_HUMAN,
        )

        # get the appropriate discord token
        discord_token = tool_context.context.get_discord_token(
            agent_message.sender_id
        )

        # Send message to discord
        discord_message = await send_discord_message_async(
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
    
    _print_func(question)
    return input()


def ask_human(question: str, tool_context: ToolContext):
    """Ask a human for input.
    
    Args:
        question: The question to ask
        tool_context: The tool context
    """
    if DISCORD_ENABLED:
        # Make an AgentMessage object
        agent_message = AgentMessage.from_agent_input(
            question,
            tool_context.agent_id,
            tool_context.context,
            type=MessageEventSubtype.AGENT_TO_HUMAN,
        )

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
    
    _print_func(question)
    return input()
