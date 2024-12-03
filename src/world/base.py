import asyncio
import json
import os
import random
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID

import pytz

from ..agent.agent_base import Agent
from ..event.base import Event, EventsManager
from ..location.base import Location
from ..utils.colors import LogColor
from ..utils.database.base import Tables
from ..utils.database.client import get_database
from ..utils.parameters import DEFAULT_WORLD_ID
from .context import WorldContext, WorldData

class World:
    """A world containing agents, locations, and events"""

    def __init__(
        self,
        id: UUID = DEFAULT_WORLD_ID,
        name: str = "GPTeam World",
        agents: Optional[List[Agent]] = None,
        locations: Optional[List[Location]] = None,
        events_manager: Optional[EventsManager] = None,
        context: Optional[WorldContext] = None,
    ):
        self.id = id
        self.name = name
        self.agents = agents or []
        self.locations = locations or []
        self.events_manager = events_manager
        self.context = context

    @classmethod
    async def from_id(cls, id: UUID = DEFAULT_WORLD_ID):
        """Create a world from the database using its ID"""
        database = await get_database()

        # Get world data
        worlds_data = await database.get_by_id(Tables.Worlds, str(id))
        if not worlds_data:
            raise ValueError(f"No world found with id {id}")
        world_data = worlds_data[0]  # Get first result
        
        # Get locations
        locations_data = await database.get_by_field(Tables.Locations, "world_id", str(id))
        locations = [Location(**location) for location in locations_data]

        # Create events manager
        events_manager = await EventsManager.from_world_id(str(id))

        # Create WorldData
        world = WorldData(
            id=str(id),
            name=world_data.get("name", "GPTeam World")
        )

        # Create context
        context = WorldContext(
            world=world,
            agents=[],
            locations=[loc.__dict__ for loc in locations],
            events_manager=events_manager,
        )

        # Get agents
        agents_data = await database.get_by_field(Tables.Agents, "world_id", str(id))
        agents = []
        for agent_data in agents_data:
            agent = await Agent.from_db_dict(agent_data, locations, context)
            agents.append(agent)

        # Update context with agents
        context.agents = [agent._db_dict() for agent in agents]

        return cls(
            id=id,
            name=world_data.get("name", "GPTeam World"),
            agents=agents,
            locations=locations,
            events_manager=events_manager,
            context=context,
        )

    # Alias for from_id to maintain compatibility
    from_db = from_id

    def get_agent_color(self, agent_id: UUID) -> LogColor:
        """Get the color for an agent"""
        agent_index = next(
            (i for i, agent in enumerate(self.agents) if agent.id == agent_id),
            0,
        )
        return list(LogColor)[agent_index % len(LogColor)]

    async def run(self):
        """Run the world simulation"""
        tasks = []
        for agent in self.agents:
            tasks.append(self.run_agent_loop(agent))

        await asyncio.gather(*tasks)

    async def run_agent_loop(self, agent: Agent):
        """Run an agent's loop"""
        while True:
            await agent.run_for_one_step()
            await asyncio.sleep(random.random() * 3)

    async def run_next_agent(self):
        """Run the next agent in the list"""
        if len(self.agents) == 0:
            return

        agent = self.agents[0]
        await agent.run_for_one_step()
        self.agents = self.agents[1:] + [agent]
