from datetime import datetime
from langchain.output_parsers import OutputFixingParser, PydanticOutputParser
from pydantic import BaseModel, Field, validator

from src.tools.context import ToolContext
from src.utils.database.base import Tables
from src.utils.database.client import get_database
from src.utils.prompt import Prompter, PromptString

from ..utils.models import ChatModel
from ..utils.parameters import DEFAULT_FAST_MODEL, DEFAULT_SMART_MODEL


class HasHappenedLLMResponse(BaseModel):
    has_happened: bool = Field(description="Whether the event has happened or not")
    date_occured: str = Field(
        description="The date and time the event occured, in this format: %Y-%m-%d %H:%M:%S"
    )


async def wait_async(agent_input: str, tool_context: ToolContext) -> str:
    """Wait for a specified event to occur."""
    
    # Get only memories that occurred after the last memory
    if tool_context.memories:
        last_memory_time = max(m.created_at for m in tool_context.memories)
        recent_memories = [
            f"{m.description} @ {m.created_at}" 
            for m in tool_context.memories 
            if m.created_at >= last_memory_time
        ]
    else:
        recent_memories = []

    # If no recent memories, return waiting message
    if not recent_memories:
        return "Waiting for new events..."

    # Set up the LLM, Parser, and Prompter
    llm = ChatModel(temperature=0.8)
    parser = OutputFixingParser.from_llm(
        parser=PydanticOutputParser(pydantic_object=HasHappenedLLMResponse),
        llm=llm.defaultModel,
    )

    prompter = Prompter(
        PromptString.HAS_HAPPENED,
        {
            "memory_descriptions": "-" + "\n-".join(recent_memories),
            "event_description": agent_input,
            "format_instructions": parser.get_format_instructions(),
        },
    )

    # Get the response
    response = await llm.get_chat_completion(
        prompter.prompt,
        loading_text="Checking if event has happened...",
    )

    # Parse the response
    parsed_response: HasHappenedLLMResponse = parser.parse(response)

    if parsed_response.has_happened:
        return f"The event I was waiting for occurred at {parsed_response.date_occured}. Moving forward with the conversation."
    else:
        return "Still waiting for a response..."


def wait_sync(agent_input: str, tool_context: ToolContext) -> str:
    """Wait for a specified event to occur."""
    raise NotImplementedError("This tool is not implemented in sync mode")
