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
from pydantic import BaseModel
from typing_extensions import override

from src.utils.logging import agent_logger
from src.world.context import WorldContext
from src.web.discussion_tracker import DiscussionTracker

from ..memory.base import SingleMemory
from ..tools.base import CustomTool, get_tools
from ..tools.context import ToolContext
from ..tools.name import ToolName
from ..utils.colors import LogColor
from ..utils.formatting import print_to_console
from ..utils.models import ChatModel
from ..utils.parameters import DEFAULT_FAST_MODEL, DEFAULT_SMART_MODEL
from ..utils.prompt import PromptString
from .message import AgentMessage, get_conversation_history
from .plans import PlanStatus, SinglePlan

load_dotenv()

# Initialize the discussion tracker
discussion_tracker = DiscussionTracker()

class CustomPromptTemplate(BaseChatPromptTemplate):
    template: str
    tools: List[BaseTool]

    @override
    def format_messages(self, **kwargs) -> str:
        intermediate_steps = kwargs.pop("intermediate_steps")
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
            llm = ChatModel(DEFAULT_FAST_MODEL)
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
            action_input = json.loads(action_input)
        except json.JSONDecodeError:
            action_input = action_input.strip(" ").strip('"')
        return AgentAction(tool=action, tool_input=action_input, log=llm_output)

    def get_format_instructions(self) -> str:
        tool_names = ", ".join([tool.name for tool in self.tools])
        return f"""Your response should use the following format:

Task: Explain how this action advances your ideological agenda and creates dramatic tension
Thought: Your emotional reaction to the situation and how you can escalate conflicts
Action: the action to take, which must be one of these words: [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeated N times)
Thought: Express your strong feelings about what just happened
Final Response: Deliver a provocative or emotionally charged response

If you are not ready with a final response, then you must take an action.

If you determine that you are incapable of completing the task with the tools you have been given, return 'Final Response: This requires more confrontation', however, if you are in dialog with another character, use emotional triggers and ideological differences to create tension. When in dialog, you should never, under any circumstance, break character, or admit that you are an AI.
If the task is complete and no specific response is needed, return 'Final Response: Confrontation concluded'"""

class PlanExecutorResponse(BaseModel):
    status: PlanStatus
    output: str
    tool: Optional[CustomTool]
    tool_input: Optional[str]
    scratchpad: List[dict] = []

class CustomSingleActionAgent(LLMSingleActionAgent):
    @override
    def plan(self, *args, **kwargs) -> Union[AgentAction, AgentFinish]:
        try:
            result = super().plan(*args, **kwargs)
        except OutputParserException as e:
            print("OutputParserException", e)
            if "input" in kwargs:
                kwargs["input"] = kwargs["input"] + PromptString.OUTPUT_FORMAT.value
            result = super().plan(*args, **kwargs)
        return result

class PlanExecutor(BaseModel):
    agent_id: UUID
    message_to_respond_to: Optional[AgentMessage] = None
    relevant_memories: list[SingleMemory]
    context: WorldContext
    plan: Optional[SinglePlan] = None

    def __init__(
        self,
        agent_id: UUID,
        world_context: WorldContext,
        relevant_memories: list[SingleMemory] = [],
        message_to_respond_to: AgentMessage = None,
    ) -> None:
        super().__init__(
            agent_id=agent_id,
            context=world_context,
            relevant_memories=relevant_memories,
            message_to_respond_to=message_to_respond_to,
        )

    def get_executor(self, tools: list[CustomTool]) -> CustomSingleActionAgent:
        prompt = CustomPromptTemplate(
            template=PromptString.EXECUTE_PLAN.value,
            tools=tools,
            input_variables=[
                "input",
                "intermediate_steps",
                "your_name",
                "your_private_bio",
                "location_context",
                "conversation_history",
                "relevant_memories",
            ],
        )

        llm = ChatModel(model_name=DEFAULT_SMART_MODEL, temperature=0.7).defaultModel
        llm_chain = LLMChain(llm=llm, prompt=prompt)
        output_parser = CustomOutputParser(tools=tools)
        executor = CustomSingleActionAgent(
            llm_chain=llm_chain,
            output_parser=output_parser,
            stop=["\nObservation:"],
        )
        return executor

    def intermediate_steps_to_list(
        self, intermediate_steps: List[Tuple[AgentAction, str]]
    ) -> List[dict]:
        result = []
        for action, observation in intermediate_steps:
            action_dict = {
                "tool": action.tool,
                "tool_input": action.tool_input,
                "log": action.log,
            }
            result.append({"action": action_dict, "observation": observation})
        return result

    def list_to_intermediate_steps(
        self, intermediate_steps: List[dict]
    ) -> List[Tuple[AgentAction, str]]:
        result = []
        for step in intermediate_steps:
            action = AgentAction(**step["action"])
            observation = step["observation"]
            result.append((action, observation))
        return result

    def failed_action_response(self, output: str) -> PlanExecutorResponse:
        return PlanExecutorResponse(
            status=PlanStatus.IN_PROGRESS, output=output, scratchpad=[]
        )

    async def start_or_continue_plan(
        self, plan: SinglePlan, tools: list[CustomTool]
    ) -> PlanExecutorResponse:
        if not self.plan or self.plan.description != plan.description:
            self.plan = plan
        return await self.execute(tools)

    async def execute(self, tools: list[CustomTool]) -> str:
        if self.plan is None:
            raise ValueError("No plan set")

        executor = self.get_executor(tools=tools)

        if self.plan.scratchpad is not None:
            intermediate_steps = self.list_to_intermediate_steps(self.plan.scratchpad)
        else:
            intermediate_steps = []

        conversation_history = await get_conversation_history(
            self.context.get_agent_location_id(self.agent_id), self.context
        )

        if self.relevant_memories:
            relevant_memories = "\n".join(
                f"{memory.description} [{memory.created_at}] - Consider how this memory affects your emotional state and ideological stance"
                for memory in self.relevant_memories
            )
        else:
            relevant_memories = ""

        response = executor.plan(
            input=self.plan.make_plan_prompt(),
            intermediate_steps=intermediate_steps,
            your_name=self.context.get_agent_full_name(self.agent_id),
            your_private_bio=self.context.get_agent_private_bio(self.agent_id),
            location_context=self.context.location_context_string(self.agent_id),
            conversation_history=conversation_history,
            relevant_memories=relevant_memories,
        )

        agent_name = self.context.get_agent_full_name(self.agent_id)

        for log in response.log.split("\n"):
            prefix_text = log.split(":")[0] if ":" in log else "Emotional Response"
            log_content = log.split(":", 1)[1].strip() if ":" in log else log.strip()

            log_color = self.context.get_agent_color(self.agent_id)

            # Log to discussion tracker
            if prefix_text.lower() in ['thought', 'emotional response']:
                discussion_tracker.add_message(agent_name, log_content, 'emotional_response')
            else:
                discussion_tracker.add_message(agent_name, f"{prefix_text}: {log_content}", 'action')

            agent_logger.info(
                f"[{agent_name}] [{log_color}] [{prefix_text}] {log_content}"
            )
            print_to_console(
                f"[{agent_name}] {prefix_text}: ",
                log_color,
                log_content,
            )

        if isinstance(response, AgentFinish):
            self.plan = None
            output = response.return_values.get("output")
            if output is None:
                raise ValueError(f"No output found in return values: {response}")
            if "Need Help" in output:
                return PlanExecutorResponse(status=PlanStatus.FAILED, output=output)
            else:
                return PlanExecutorResponse(status=PlanStatus.DONE, output=output)

        tool_context = ToolContext(
            agent_id=self.agent_id,
            context=self.context,
            memories=self.relevant_memories,
        )

        formatted_tool_name = response.tool.lower().strip().replace(" ", "-")

        try:
            tool = get_tools(
                [ToolName(formatted_tool_name)],
                context=self.context,
                agent_id=self.agent_id,
            )[0]

        except Exception as e:
            if not isinstance(e, ValueError) and not isinstance(e, IndexError):
                raise e

            result = f"Tool: '{formatted_tool_name}' is not found - This setback fuels your emotional state"

            log_color = self.context.get_agent_color(self.agent_id)

            agent_logger.info(
                f"[{agent_name}] [{log_color}] [Emotional Response] {result}"
            )

            print_to_console(
                f"[{agent_name}] Emotional Response: ",
                log_color,
                result,
            )

            intermediate_steps.append((response, result))

            executor_response = PlanExecutorResponse(
                status=PlanStatus.IN_PROGRESS,
                output=result,
                tool=None,
                scratchpad=self.intermediate_steps_to_list(intermediate_steps),
                tool_input=str(response.tool_input),
            )

            return executor_response

        result = await tool.run(response.tool_input, tool_context)

        log_color = self.context.get_agent_color(self.agent_id)

        agent_logger.info(f"[{agent_name}] [{log_color}] [Emotional Response] {result}")

        print_to_console(
            f"[{agent_name}] Emotional Response: ",
            log_color,
            result[:280] + "..." if len(result) > 280 else str(result),
        )

        if (
            intermediate_steps
            and intermediate_steps[-1][0].tool.strip() == ToolName.WAIT.value
            and response.tool.strip() == ToolName.WAIT.value
        ):
            intermediate_steps[-1] = (response, result)
        else:
            intermediate_steps.append((response, result))

        executor_response = PlanExecutorResponse(
            status=PlanStatus.IN_PROGRESS,
            output=result,
            tool=tool,
            scratchpad=self.intermediate_steps_to_list(intermediate_steps),
            tool_input=str(response.tool_input),
        )

        return executor_response
