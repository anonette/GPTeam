"""
Core Agent class that combines functionality from various mixins.
"""

import asyncio
import random
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

import pytz
from pydantic import BaseModel

from ..event.base import Event
from ..location.base import Location
from ..memory.base import MemoryType, SingleMemory
from ..tools.name import ToolName
from ..utils.colors import LogColor
from ..utils.logging import agent_logger
from ..utils.formatting import print_to_console
from ..utils.parameters import DEFAULT_WORLD_ID
from ..world.context import WorldContext
from .agent_db import AgentDBMixin
from .agent_file import AgentFileMixin
from .agent_memory import AgentMemoryMixin
from .agent_movement import AgentMovementMixin
from .agent_planning import AgentPlanningMixin
from .agent_reflection import AgentReflectionMixin
from .executor import PlanExecutor
from .plans import SinglePlan
from .react import LLMReactionResponse, Reaction

class Agent(
    AgentDBMixin,
    AgentMemoryMixin,
    AgentMovementMixin,
    AgentPlanningMixin,
    AgentReflectionMixin,
    AgentFileMixin,
    BaseModel
):
    """
    Main Agent class that combines functionality from various mixins.
    Each mixin handles a specific aspect of the agent's functionality:
    - AgentDBMixin: Database operations
    - AgentMemoryMixin: Memory management
    - AgentMovementMixin: Location and movement
    - AgentPlanningMixin: Planning and action execution
    - AgentReflectionMixin: Reflection and insights
    - AgentFileMixin: File operations and progress tracking
    """
    
    id: UUID
    full_name: str
    private_bio: str
    public_bio: str
    directives: Optional[list[str]]
    last_checked_events: datetime
    last_summarized_activity: datetime
    memories: list[SingleMemory]
    plans: list[SinglePlan]
    authorized_tools: list[ToolName]
    world_id: UUID
    notes: list[str] = []
    plan_executor: Optional[PlanExecutor] = None
    context: WorldContext
    location: Location
    discord_bot_token: Optional[str] = None
    react_response: Optional[LLMReactionResponse] = None
    recent_activity: str = ""

    class Config:
        allow_underscore_names = True
        arbitrary_types_allowed = True

    def __init__(
        self,
        full_name: str,
        private_bio: str,
        public_bio: str,
        context: WorldContext,
        location: Location,
        directives: list[str] = None,
        last_checked_events: datetime = None,
        last_summarized_activity: datetime = None,
        memories: list[SingleMemory] = [],
        plans: list[SinglePlan] = [],
        authorized_tools: list[ToolName] = [],
        id: Optional[str | UUID] = None,
        world_id: Optional[UUID] = DEFAULT_WORLD_ID,
        discord_bot_token: str = None,
        recent_activity: str = "",
    ):
        if id is None:
            id = uuid4()
        elif isinstance(id, str):
            id = UUID(id)
        if last_checked_events is None:
            last_checked_events = datetime.fromtimestamp(0, tz=pytz.utc)
        if last_summarized_activity is None:
            last_summarized_activity = datetime.fromtimestamp(0, tz=pytz.utc)

        # initialize the base model
        super().__init__(
            id=id,
            full_name=full_name,
            private_bio=private_bio,
            public_bio=public_bio,
            directives=directives,
            last_checked_events=last_checked_events,
            last_summarized_activity=last_summarized_activity,
            authorized_tools=authorized_tools,
            memories=memories,
            plans=plans,
            world_id=world_id,
            location=location,
            context=context,
            discord_bot_token=discord_bot_token,
            recent_activity=recent_activity,
        )

        print("\n\nAGENT INITIALIZED --------------------------\n")
        print(self)

    def __str__(self) -> str:
        private_bio = (
            self.private_bio[:100] + "..."
            if len(self.private_bio) > 100
            else self.private_bio
        )
        memories = " " + "\n ".join(
            [
                str(memory)[:100] + "..." if len(str(memory)) > 100 else str(memory)
                for memory in self.memories[-5:]
            ]
        )
        plans = " " + "\n ".join([str(plan) for plan in self.plans])

        return f"{self.full_name} - {self.location.name}\nprivate_bio: {private_bio}\nDirectives: {self.directives}\n\nRecent Memories: \n{memories}\n\nPlans: \n{plans}\n"

    @property
    def color(self) -> LogColor:
        return self.context.get_agent_color(self.id)

    def _log(self, title: str, description: str = ""):
        agent_logger.info(f"[{self.full_name}] [{self.color}] [{title}] {description}")
        print_to_console(f"[{self.full_name}] {title}", self.color, description)

    async def observe(self) -> list[Event]:
        """Take in new events and add them to memory. Return the events"""
        # Get new events witnessed by this agent
        last_checked_events = self.last_checked_events
        self.last_checked_events = datetime.now(pytz.utc)

        (events, _) = await self.context.events_manager.get_events(
            after=last_checked_events, witness_ids=[self.id], force_refresh=True
        )

        self._log(
            "Observe",
            f"Observed {len(events)} new events since {last_checked_events.strftime('%H:%M:%S')}",
        )

        if len(events) > 0:
            # Make new memories based on the events
            new_memories = [
                await self._add_memory(
                    event.description,
                    created_at=event.timestamp,
                    type=MemoryType.OBSERVATION,
                    log=False,
                )
                for event in events
            ]

        return events

    async def run_for_one_step(self):
        """Main loop for the agent's behavior"""
        await asyncio.sleep(random.random() * 3)

        events = await self.observe()

        # if there's no current plan, make some
        if len(self.plans) == 0:
            print(f"{self.full_name} has no plans, making some...")
            await self._plan()

        # Decide how to react to these events
        self.react_response = await self._react(events)

        # If the reaction calls to cancel the current plan, remove the first one
        if self.react_response.reaction == Reaction.CANCEL:
            self.plans = self.plans[1:]

        # If the reaction calls to postpone the current plan, insert the new plan at the top
        elif self.react_response.reaction == Reaction.POSTPONE:
            # create a new plan from the LLMSinglePlan
            new_plan = await SinglePlan.from_llm_single_plan(self.id, self.react_response.new_plan)
            self.plans.insert(0, new_plan)

        # Work through the plans
        await self._do_first_plan()

        # Reflect, if we should
        if await self._should_reflect():
            await self._reflect()

        await self.write_progress_to_file()
