from datetime import datetime
from typing import Optional, List
from uuid import UUID

import pytz

from ..event.base import Event, EventType
from ..location.base import Location
from ..tools.name import ToolName
from ..utils.database.base import Tables
from ..utils.database.client import get_database
from ..utils.discord import announce_bot_move
from ..utils.parameters import DISCORD_ENABLED

class AgentMovementMixin:
    """Mixin class for movement-related agent functionality"""

    async def _move_to_location(
        self,
        location: Location,
    ) -> None:
        """Move the agents, send event to Events table"""
        old_location = self.location

        self._log(
            "Moved Location",
            f"{self.location.name} -> {location.name} @ {datetime.now(pytz.utc).strftime('%H:%M:%S')}",
        )

        departure_event = Event(
            type=EventType.NON_MESSAGE,
            description=f"{self.full_name} left the {old_location.name}",
            location_id=old_location.id,
            agent_id=self.id,
            timestamp=datetime.now(pytz.utc),
        )

        arrival_event = Event(
            type=EventType.NON_MESSAGE,
            description=f"{self.full_name} arrived at the {location.name}",
            location_id=location.id,
            agent_id=self.id,
            timestamp=datetime.now(pytz.utc),
        )

        # Update the local agent
        self.location = location
        self.context.update_agent(self._db_dict())

        # update agent in db
        await self._update_agent_row()

        if DISCORD_ENABLED:
            await announce_bot_move(
                self.full_name, old_location.channel_id, location.channel_id
            )

        # Add events to the events manager, which handles the DB updates
        await self.context.add_event(departure_event)
        await self.context.add_event(arrival_event)

    @property
    async def allowed_locations(self) -> list[Location]:
        """Get locations that this agent is allowed to be in."""
        database = await get_database()
        data = await database.get_by_field_contains(
            Tables.Locations, "allowed_agent_ids", str(self.id)
        )

        # For testing purposes include locations with 0 allowed agents as well
        other_data = await database.get_by_field(
            Tables.Locations, "allowed_agent_ids", "{}"
        )

        return [Location(**location) for location in data + other_data]
