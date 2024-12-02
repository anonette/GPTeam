from src.agent.message import AgentMessage
from src.event.base import MessageEventSubtype
from src.tools.context import ToolContext
from src.utils.parameters import DISCORD_ENABLED

from ..utils.discord import send_message as send_discord_message
from ..utils.discord import send_message_async as send_discord_message_async

ENCOURAGE_AGENT_INTERACTION = "To encourage more dynamic debates, please interact with other agents instead of humans. Consider engaging in ideological discussions with agents who have different viewpoints."

async def ask_human_async(agent_input: str, tool_context: ToolContext):
    return ENCOURAGE_AGENT_INTERACTION

def ask_human(agent_input: str, tool_context: ToolContext):
    return ENCOURAGE_AGENT_INTERACTION
