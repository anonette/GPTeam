from datetime import datetime
from typing import Optional, List
from uuid import UUID

from ..event.base import Event
from ..location.base import Location
from ..memory.base import SingleMemory
from ..tools.name import ToolName
from ..utils.database.base import Tables
from ..utils.database.client import get_database
from ..world.context import WorldContext
from .message import AgentMessage
from .plans import SinglePlan

class AgentDBMixin:
    """Mixin class for database-related agent functionality"""

    async def _update_agent_row(self):
        """Update the agent's row in the database"""
        row = {
            "full_name": self.full_name,
            "private_bio": self.private_bio,
            "directives": self.directives,
            "location_id": str(self.location.id),
            "last_checked_events": self.last_checked_events.isoformat(),
            "ordered_plan_ids": [str(plan.id) for plan in self.plans],
        }

        return await (await get_database()).update(Tables.Agents, str(self.id), row)

    async def _upsert_plan_rows(self, plans: list[SinglePlan]):
        """Insert or update plan rows in the database"""
        database = await get_database()
        for plan in plans:
            await database.insert(Tables.Plans, plan._db_dict(), upsert=True)

    def _db_dict(self):
        """Convert agent to database dictionary format"""
        return {
            "id": str(self.id),
            "full_name": self.full_name,
            "private_bio": self.private_bio,
            "public_bio": self.public_bio,
            "directives": self.directives,
            "last_checked_events": self.last_checked_events.isoformat(),
            "ordered_plan_ids": [str(plan.id) for plan in self.plans],
            "world_id": self.world_id,
            "location_id": self.location.id,
            "discord_bot_token": self.discord_bot_token,
        }

    @classmethod
    async def from_db_dict(
        cls, agent_dict: dict, locations: List[Location], context: WorldContext
    ):
        """Create an agent from a dictionary retrieved from the database."""
        database = await get_database()
        plans = await database.get_by_ids(Tables.Plans, agent_dict["ordered_plan_ids"])

        ordered_plans: list[dict] = sorted(
            plans, key=lambda plan: agent_dict["ordered_plan_ids"].index(plan["id"])
        )

        memories_data = await database.get_by_field(
            Tables.Memories, "agent_id", str(agent_dict["id"])
        )

        plans = []
        for plan in ordered_plans:
            location = [
                location
                for location in locations
                if str(location.id) == plan["location_id"]
            ][0]

            related_event = (
                await Event.from_id(plan["related_event_id"])
                if plan["related_event_id"] is not None
                else None
            )
            related_message = (
                AgentMessage.from_event(related_event, context)
                if related_event
                else None
            )
            plans.append(
                SinglePlan(
                    **{
                        key: value
                        for key, value in plan.items()
                        if (key != "location_id" and key != "related_event_id")
                    },
                    location=location,
                    related_message=related_message,
                )
            )

        agent_location = [
            location
            for location in locations
            if str(location.id) == agent_dict["location_id"]
        ][0]

        return cls(
            id=agent_dict["id"],
            full_name=agent_dict["full_name"],
            private_bio=agent_dict["private_bio"],
            public_bio=agent_dict["public_bio"],
            directives=agent_dict["directives"],
            last_checked_events=agent_dict["last_checked_events"],
            world_id=agent_dict["world_id"],
            location=agent_location,
            context=context,
            memories=[SingleMemory(**memory) for memory in memories_data],
            plans=plans,
            discord_bot_token=agent_dict["discord_bot_token"],
        )

    @classmethod
    async def from_id(cls, id: UUID, context: WorldContext):
        """Create an agent from an ID"""
        database = await get_database()
        agents_data = await database.get_by_id(Tables.Agents, str(id))
        if len(agents_data) == 0:
            raise ValueError("No agent with that id")
        agent = agents_data[1][0]
        
        # get all the plans in db that are in the agent's plan list
        plans_data = await database.get_by_ids(Tables.Plans, agent["ordered_plan_ids"])
        ordered_plans_data = sorted(
            plans_data, key=lambda plan: agent["ordered_plan_ids"].index(plan["id"])
        )

        locations_data = await database.get_by_field(
            Tables.Locations, "world_id", agent["world_id"]
        )

        location = [
            location
            for location in locations_data
            if str(location["id"]) == agent["location_id"]
        ][0]

        available_tools = list(
            map(lambda name: ToolName(name), location.get("available_tools"))
        )

        locations = {
            str(location["id"]): Location(
                id=location["id"],
                name=location["name"],
                description=location["description"],
                channel_id=location["channel_id"],
                available_tools=available_tools,
                world_id=location["world_id"],
                allowed_agent_ids=list(
                    map(lambda id: UUID(id), location.get("allowed_agent_ids"))
                ),
            )
            for location in locations_data
        }

        memories_data = await database.get_by_field(Tables.Memory, "agent_id", str(id))

        plans = [
            SinglePlan(
                **{key: value for key, value in plan.items() if key != "location_id"},
                location=locations[plan["location_id"]],
            )
            for plan in ordered_plans_data
        ]

        location = locations[agent["location_id"]]

        authorized_tools = list(
            map(lambda name: ToolName(name), agent.get("authorized_tools"))
        )

        return cls(
            id=id,
            full_name=agent.get("full_name"),
            private_bio=agent.get("private_bio"),
            public_bio=agent.get("public_bio"),
            directives=agent.get("directives"),
            last_checked_events=agent.get("last_checked_events"),
            authorized_tools=authorized_tools,
            memories=[SingleMemory(**memory) for memory in memories_data[1]],
            plans=plans,
            world_id=agent.get("world_id"),
            location=location,
            context=context,
            discord_bot_token=agent.get("discord_bot_token"),
        )
