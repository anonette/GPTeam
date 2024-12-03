import json
import os
import re
import time
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union
from uuid import UUID

from dotenv import load_dotenv
from langchain import LLMChain
from langchain.agents import AgentOutputParser, LLMSingleActionAgent
from langchain.llms import OpenAI
from langchain.output_parsers import OutputFixingParser
from langchain.prompts import BaseChatPromptTemplate
from langchain.schema import (
    AgentAction,
    AgentFinish,
    HumanMessage,
    OutputParserException,
    SystemMessage,
)
from langchain.tools import BaseTool
from pydantic import BaseModel, validator
from typing_extensions import override

from src.utils.logging import agent_logger
from src.world.context import WorldContext
from src.web.discussion_tracker import DiscussionTracker

from ..memory.base import SingleMemory, get_relevant_memories
from ..tools.base import CustomTool, get_tools
from ..tools.context import ToolContext
from ..tools.name import ToolName
from ..utils.colors import LogColor
from ..utils.formatting import print_to_console
from ..utils.models import ChatModel
from ..utils.parameters import DEFAULT_FAST_MODEL, DEFAULT_SMART_MODEL
from ..utils.prompt import PromptString
from .message import AgentMessage, MessageParsingError, get_conversation_history
from .plans import SinglePlan, PlanStatus

load_dotenv()

# Initialize the discussion tracker
discussion_tracker = DiscussionTracker()

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
    def fix_json_format(cls, input_str: str) -> str:
        """Fix common JSON formatting issues"""
        # Remove any whitespace between fields
        fixed = re.sub(r'"\s+"', '", "', input_str)
        # Add missing commas between fields
        fixed = re.sub(r'"([^"]+)"\s*"([^"]+)"', r'"\1", "\2"', fixed)
        return fixed

class CustomPromptTemplate(BaseChatPromptTemplate):
    template: str
    tools: List[BaseTool]

    @override
    def format_messages(self, **kwargs) -> List[HumanMessage]:
        intermediate_steps = kwargs.pop("intermediate_steps", [])
        thoughts = ""
        for action, observation in intermediate_steps:
            thoughts += action.log
            thoughts += f"\nObservation: {observation}\nThought: "
        kwargs["agent_scratchpad"] = thoughts

        kwargs["tools"] = "\n".join(
            [f"{tool.name}: {tool.description}" for tool in self.tools]
        )
        kwargs["tool_names"] = ", ".join([tool.name for tool in self.tools])

        formatted = self.template.format(**kwargs)

        return [HumanMessage(content=formatted)]

class CustomOutputParser(AgentOutputParser):
    tools: List[BaseTool]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tools = kwargs.pop("tools")

    def parse(self, llm_output: str) -> Union[AgentAction, AgentFinish]:
        if "Final Response:" in llm_output:
            return AgentFinish(
                return_values={
                    "output": llm_output.split("Final Response:")[-1].strip()
                },
                log=llm_output,
            )
        regex = r"Action\s*\d*\s*:(.*?)\nAction\s*\d*\s*Input\s*\d*\s*:[\s]*(.*)"
        match = re.search(regex, llm_output, re.DOTALL)
        if not match:
            llm = ChatModel(DEFAULT_FAST_MODEL, temperature=0.8)
            formatting_correction = f"Could not parse the LLM output: `{llm_output}`\n\n Reformat the output to correspond to the following format: {self.get_format_instructions()} so that the result can be extracted using the regex: `{regex}`"
            retry = llm.get_chat_completion_sync(
                [SystemMessage(content=formatting_correction)]
            )
            match = re.search(regex, retry, re.DOTALL)
            if not match:
                raise OutputParserException(
                    f"Could not parse LLM output after retrying: \n`{retry}`. \nFirst attempt: \n`{retry}`"
                )

        action = match.group(1).strip()
        action_input = match.group(2)
        
        try:
            # Special handling for speak tool to ensure proper message format
            if action.lower().strip() == "speak":
                try:
                    # Parse and validate message format
                    if isinstance(action_input, str):
                        # Fix JSON format and try to parse
                        fixed_input = MessageFormat.fix_json_format(action_input)
                        try:
                            data = json.loads(fixed_input)
                        except json.JSONDecodeError:
                            # If still fails, try to extract fields using regex
                            pattern = r'"recipient"\s*:\s*"([^"]+)"\s*,?\s*"message"\s*:\s*"([^"]+)"'
                            match = re.search(pattern, action_input)
                            if match:
                                data = {
                                    "recipient": match.group(1),
                                    "message": match.group(2)
                                }
                            else:
                                raise MessageParsingError("Could not parse message format")
                            
                        # Extract recipient and message
                        recipient = data.get('recipient', '').strip()
                        message = data.get('message', '').strip()
                        
                        # Validate required fields
                        if not recipient or not message:
                            raise MessageParsingError("Missing required fields: recipient and message")
                        
                        # Remove recipient prefix from message if present
                        message = re.sub(f"^{recipient}[:,]\\s*", "", message)
                        
                        # Format as string for send_message_impl
                        action_input = json.dumps({
                            "recipient": recipient,
                            "message": message
                        })
                except Exception as e:
                    raise MessageParsingError(f"Error parsing message format: {str(e)}")

            # Find the tool by name
            tool = next((t for t in self.tools if t.name.lower() == action.lower().strip()), None)
            if tool is None:
                raise OutputParserException(f"Unknown tool: {action}")

            return AgentAction(tool=action, tool_input=action_input, log=llm_output)
        except Exception as e:
            raise OutputParserException(f"Error parsing tool input: {str(e)}")

    @override
    def get_format_instructions(self) -> str:
        return """To use a tool, please use the following format:

Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action

For example:
Action: speak
Action Input: {{"recipient": "John", "message": "Hello there!"}}

When you want to respond to the human, use the format:
Final Response: your response here"""

class PlanExecutorResponse(BaseModel):
    """Response from plan execution"""
    status: PlanStatus
    output: Optional[str] = None
    error: Optional[str] = None
    scratchpad: Optional[str] = None
    tool: Optional[CustomTool] = None
    tool_input: Optional[str] = None

class PlanExecutor:
    """Executes plans using available tools"""

    def __init__(self, context: ToolContext):
        self.context = context
        # Get available tools from location
        location_id = context.context.get_agent_location_id(context.agent_id)
        location_tools = context.context.get_location_from_location_id(location_id).get("available_tools", [])
        
        self.tools = get_tools(
            tools=location_tools,
            context=context.context,
            agent_id=context.agent_id,
            include_worldwide=True
        )
        
        # Initialize LLM and chain
        llm = ChatModel(DEFAULT_SMART_MODEL)
        self.prompt = CustomPromptTemplate(
            template=str(PromptString.EXECUTE_PLAN.value),
            tools=self.tools,
            input_variables=[
                "input",
                "intermediate_steps",
                "tools",
                "tool_names",
                "your_name",
                "your_private_bio",
                "relevant_memories",
                "conversation_history"
            ],
        )
        self.output_parser = CustomOutputParser(tools=self.tools)
        self.llm_chain = LLMChain(
            llm=llm.defaultModel,  # Use the underlying OpenAI model
            prompt=self.prompt
        )
        self.agent = LLMSingleActionAgent(
            llm_chain=self.llm_chain,
            output_parser=self.output_parser,
            stop=["\nObservation:"],
            allowed_tools=[tool.name for tool in self.tools],
        )

    async def start_or_continue_plan(
        self, 
        plan: SinglePlan,
        tools: List[CustomTool]
    ) -> PlanExecutorResponse:
        """Start or continue executing a plan"""
        try:
            # Get agent info from context
            agent_name = self.context.context.get_agent_full_name(self.context.agent_id)
            agent_bio = self.context.context.get_agent_private_bio(self.context.agent_id)
            agent_dict = self.context.context.get_agent_dict_from_id(self.context.agent_id)
            
            # Get memories from agent dict
            memories = [SingleMemory(**m) for m in agent_dict.get("memories", [])]
            
            # Get relevant memories
            relevant_memories = await get_relevant_memories(
                plan.description,
                memories=memories,
                k=5
            )
            
            # Get conversation history
            conversation_history = await get_conversation_history(
                self.context.agent_id,
                self.context.context
            )
            
            # Format input for the agent including tools
            agent_input = {
                "input": plan.description,
                "your_name": agent_name,
                "your_private_bio": agent_bio,
                "relevant_memories": "\n".join([m.description for m in relevant_memories]),
                "conversation_history": conversation_history,
                "tools": "\n".join([f"{tool.name}: {tool.description}" for tool in tools]),
                "tool_names": ", ".join([tool.name for tool in tools]),
                "intermediate_steps": []  # Initialize empty intermediate steps
            }
            return await self.execute(tools, agent_input)
        except Exception as e:
            return PlanExecutorResponse(
                status=PlanStatus.FAILED,
                error=f"Error executing plan: {str(e)}"
            )

    async def execute(
        self,
        tools: List[CustomTool],
        agent_input: Dict[str, Any],
        max_iterations: int = 10
    ) -> PlanExecutorResponse:
        """Execute the agent's plan"""
        try:
            # Execute steps
            intermediate_steps = []
            scratchpad = ""
            last_tool = None
            last_tool_input = None
            
            for _ in range(max_iterations):
                # Update intermediate steps in agent input
                current_input = {**agent_input, "intermediate_steps": intermediate_steps}
                
                # Run the LLM chain directly
                output = await self.llm_chain.apredict(**current_input)
                action = self.output_parser.parse(output)
                scratchpad += str(output)
                
                if isinstance(action, AgentFinish):
                    return PlanExecutorResponse(
                        status=PlanStatus.DONE,
                        output=action.return_values["output"],
                        scratchpad=scratchpad,
                        tool=last_tool,
                        tool_input=last_tool_input
                    )
                
                try:
                    tool = next(t for t in tools if t.name.lower() == action.tool.lower())
                    last_tool = tool
                    last_tool_input = action.tool_input
                    observation = await tool.run(action.tool_input, self.context)
                    intermediate_steps.append((action, observation))
                    scratchpad += f"\nObservation: {observation}\n"
                except StopIteration:
                    return PlanExecutorResponse(
                        status=PlanStatus.FAILED,
                        error=f"Tool not found: {action.tool}",
                        scratchpad=scratchpad
                    )
                except Exception as tool_error:
                    return PlanExecutorResponse(
                        status=PlanStatus.FAILED,
                        error=f"Tool execution error: {str(tool_error)}",
                        scratchpad=scratchpad
                    )

            return PlanExecutorResponse(
                status=PlanStatus.IN_PROGRESS,
                output="Reached maximum number of iterations",
                scratchpad=scratchpad,
                tool=last_tool,
                tool_input=last_tool_input
            )

        except Exception as e:
            return PlanExecutorResponse(
                status=PlanStatus.FAILED,
                error=f"Error during execution: {str(e)}",
                scratchpad=scratchpad if 'scratchpad' in locals() else None,
                tool=last_tool if 'last_tool' in locals() else None,
                tool_input=last_tool_input if 'last_tool_input' in locals() else None
            )
