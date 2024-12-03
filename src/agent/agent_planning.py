from datetime import datetime
from typing import Optional, List

import pytz
from langchain.output_parsers import OutputFixingParser, PydanticOutputParser
from langchain.schema import AIMessage, HumanMessage

from ..event.base import Event, EventType
from ..memory.base import get_relevant_memories
from ..tools.base import CustomTool, get_tools
from ..tools.context import ToolContext
from ..tools.name import ToolName
from ..utils.models import ChatModel
from ..utils.parameters import DEFAULT_SMART_MODEL, PLAN_LENGTH
from ..utils.prompt import Prompter, PromptString
from .executor import PlanExecutor, PlanExecutorResponse
from .message import get_conversation_history
from .plans import LLMPlanResponse, LLMSinglePlan, PlanStatus, SinglePlan
from .react import LLMReactionResponse, Reaction

class AgentPlanningMixin:
    """Mixin class for planning-related agent functionality"""

    def _get_current_tools(self) -> List[CustomTool]:
        """Get the tools currently available to the agent"""
        location_tools = self.location.available_tools

        all_tools = get_tools(
            tools=location_tools,
            context=self.context,
            agent_id=self.id,
            include_worldwide=True,
        )

        authorized_tools = [
            tool
            for tool in all_tools
            if (tool.name in self.authorized_tools or not tool.requires_authorization)
        ]

        return authorized_tools

    def update_plan(self, new_plan: SinglePlan):
        """Update a plan in the agent's plan list"""
        old_plan = [
            p
            for p in self.plans
            if (p.id == new_plan.id or p.description == new_plan.description)
        ][0]
        self.plans = [
            plan if plan.id is not old_plan.id else new_plan for plan in self.plans
        ]

    async def _act(
        self,
        plan: SinglePlan,
    ) -> PlanStatus:
        """Act on a plan"""

        self._log("Act", "Starting to act on plan.")

        # If we are not in the right location, move to the new location
        if (hasattr(plan, 'location') and plan.location and self.location.id != plan.location.id):
            await self._move_to_location(plan.location)

        # Observe and react to new events
        await self.observe()

        # Get available tools
        current_tools = self._get_current_tools()

        # Create a tool context that includes the context
        tool_context = ToolContext(
            context=self.context,
            agent_id=self.id
        )

        # Initialize PlanExecutor with the tool context
        self.plan_executor = PlanExecutor(context=tool_context)

        # Execute the plan with all required variables
        resp: PlanExecutorResponse = await self.plan_executor.start_or_continue_plan(
            plan,
            tools=current_tools
        )

        # IF the plan failed
        if resp.status == PlanStatus.FAILED:
            self._log(
                "Action Failed",
                f"{plan.description} Error: {resp.output or resp.error}",
            )

            # update the plan in the local agent object
            plan.scratchpad = resp.scratchpad
            plan.status = resp.status
            self.update_plan(plan)

            # update the plan in the db
            await self._upsert_plan_rows([plan])

            # remove all plans with the same description
            self.plans = [p for p in self.plans if p.description != plan.description]

            event = Event(
                agent_id=self.id,
                timestamp=datetime.now(pytz.utc),
                type=EventType.NON_MESSAGE,
                description=f"{self.full_name} has failed to complete the following: {plan.description} at the location: {plan.location.name}. {self.full_name} had the following problem: {resp.output or resp.error}.",
                location_id=self.location.id,
            )

            event = await self.context.add_event(event)

        # If the plan is in progress
        elif resp.status == PlanStatus.IN_PROGRESS:
            self._log("Action In Progress", f"{plan.description}")

            # update the plan in the local agent object
            plan.scratchpad = resp.scratchpad
            plan.status = resp.status
            self.update_plan(plan)

            # update the plan in the db
            await self._upsert_plan_rows([plan])

            # IF the tool use was successful, summarize it
            if resp.tool and resp.tool_input:
                tool_usage_summary = await resp.tool.summarize_usage(
                    plan_description=plan.description,
                    tool_input=resp.tool_input,
                    tool_result=resp.output,
                    agent_full_name=self.full_name,
                )

        # If the plan is done, remove it from the list of plans
        elif resp.status == PlanStatus.DONE:
            self._log("Action Completed", f"{plan.description}")

            # update the plan in the local agent object
            plan.completed_at = datetime.now(pytz.utc)
            plan.scratchpad = resp.scratchpad
            plan.status = resp.status
            self.update_plan(plan)

            # update the plan in the db
            await self._upsert_plan_rows([plan])

            # remove all plans with the same description
            self.plans = [p for p in self.plans if p.description != plan.description]

        return resp.status

    async def _plan(self, thought_process: str = "") -> list[SinglePlan]:
        """Trigger the agent's planning process"""

        self._log("Starting to Plan", "📝")

        low_temp_llm = ChatModel(DEFAULT_SMART_MODEL, temperature=0, streaming=True)

        # Make the plan parser
        plan_parser = OutputFixingParser.from_llm(
            parser=PydanticOutputParser(
                pydantic_object=LLMPlanResponse,
            ),
            llm=low_temp_llm.defaultModel,
        )

        # Get a summary of the recent activity
        if (
            datetime.now(pytz.utc) - self.last_summarized_activity
        ).total_seconds() > 20:  # SUMMARIZE_ACTIVITY_INTERVAL
            recent_activity = await self._summarize_activity()
        else:
            recent_activity = self.recent_activity

        self._log("Recent Activity Summary", recent_activity)

        # Make the Plan prompter
        plan_prompter = Prompter(
            PromptString.MAKE_PLANS,
            {
                "time_window": PLAN_LENGTH,
                "allowed_location_descriptions": [
                    f"'uuid: {location.id}, name: {location.name}, description: {location.description}\n"
                    for location in await self.allowed_locations
                ],
                "full_name": self.full_name,
                "private_bio": self.private_bio,
                "directives": str(self.directives),
                "recent_activity": recent_activity,
                "current_plans": [
                    f"{index}. {plan.description}"
                    for index, plan in enumerate(self.plans)
                ],
                "format_instructions": plan_parser.get_format_instructions(),
                "location_context": self.context.location_context_string(self.id),
                "thought_process": thought_process,
            },
        )

        chat_llm = ChatModel(temperature=0, streaming=True, request_timeout=600)

        # Get the plans
        response = await chat_llm.get_chat_completion(
            plan_prompter.prompt,
            loading_text="🤔 Making plans...",
        )

        # Parse the response into an object
        parsed_plans_response: LLMPlanResponse = plan_parser.parse(response)

        invalid_locations = [
            plan.location_name
            for plan in parsed_plans_response.plans
            if plan.location_name
            not in [location.name for location in await self.allowed_locations]
        ]

        if invalid_locations:
            self._log(
                "Invalid Locations in Plan",
                f"The following locations are invalid: {invalid_locations}",
            )

            # Get the plans
            response = await chat_llm.get_chat_completion(
                plan_prompter.prompt
                + [
                    AIMessage(content=response),
                    HumanMessage(
                        content=f"Your response included the following invalid location_ids: {invalid_locations}. Please try again."
                    ),
                ],
                loading_text="🤔 Correcting plans...",
            )

            # Parse the response into an object
            parsed_plans_response: LLMPlanResponse = plan_parser.parse(response)

        # Delete existing plans
        self.plans = []

        # Make a bunch of new plan objects, put em into a list
        new_plans: list[SinglePlan] = []

        for plan in parsed_plans_response.plans:
            new_plan = SinglePlan(
                description=plan.description,
                location=next(
                    (
                        location
                        for location in await self.allowed_locations
                        if str(location.name) == str(plan.location_name)
                    ),
                    None,
                ),
                max_duration_hrs=plan.max_duration_hrs,
                agent_id=self.id,
                stop_condition=plan.stop_condition,
            )
            new_plans.append(new_plan)

        # update the local agent object
        self.plans = new_plans

        # update the db agent row
        await self._update_agent_row()

        # add the plans to the plan table
        await self._upsert_plan_rows(new_plans)

        # Loop through each plan and print it to the console
        for index, plan in enumerate(new_plans):
            self._log(
                "New Plan",
                f"#{index}: {plan.description} @ {plan.location.name} (<{plan.max_duration_hrs} hrs) [Stop Condition: {plan.stop_condition}]",
            )

        return new_plans

    async def _react(self, events: list[Event]) -> LLMReactionResponse:
        """Get the recent activity and decide whether to replan to carry on"""

        self._log("React", "Deciding how to react to recent events...")

        # Make the reaction parser
        reaction_parser = OutputFixingParser.from_llm(
            parser=PydanticOutputParser(pydantic_object=LLMReactionResponse),
            llm=ChatModel(temperature=0).defaultModel,
        )

        # Get a summary of the recent activity
        if (
            datetime.now(pytz.utc) - self.last_summarized_activity
        ).total_seconds() > 20:  # SUMMARIZE_ACTIVITY_INTERVAL
            recent_activity = await self._summarize_activity()
        else:
            recent_activity = self.recent_activity

        # Make the reaction prompter
        reaction_prompter = Prompter(
            PromptString.REACT,
            {
                "format_instructions": reaction_parser.get_format_instructions(),
                "full_name": self.full_name,
                "private_bio": self.private_bio,
                "directives": str(self.directives),
                "recent_activity": recent_activity,
                "current_plan": self.plans[0].description,
                "location_context": self.context.location_context_string(self.id),
                "event_descriptions": [
                    f"{index}. {event.description}"
                    for index, event in enumerate(events)
                ],
                "conversation_history": await get_conversation_history(
                    self.id, self.context
                ),
            },
        )

        # Get the reaction
        llm = ChatModel(DEFAULT_SMART_MODEL, temperature=0)
        response = await llm.get_chat_completion(
            reaction_prompter.prompt,
            loading_text="🤔 Deciding how to react...",
        )

        # parse the reaction response
        parsed_reaction_response: LLMReactionResponse = reaction_parser.parse(response)

        self._log(
            "Reaction",
            f"Decided to {parsed_reaction_response.reaction.value} the current plan: {parsed_reaction_response.thought_process}",
        )

        self.context.update_agent(self._db_dict())
        await self._update_agent_row()

        return parsed_reaction_response

    async def _do_first_plan(self) -> None:
        """Do the first plan in the list"""

        current_plan = None

        # If we do not have a plan state, consult the plans or plan something new
        # If we have no plans, make some
        if len(self.plans) == 0:
            print(f"{self.full_name} has no plans, making some...")
            await self._plan()

        current_plan = self.plans[0]

        await self._act(current_plan)
