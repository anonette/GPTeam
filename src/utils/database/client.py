import os
import asyncio
import random
from typing import Optional

import dotenv

from src.utils.database.sqlite import SqliteDatabase
from src.utils.database.base import Tables
from src.utils.config import load_config
from src.utils.general import seed_uuid
from src.utils.parameters import DISCORD_ENABLED

dotenv.load_dotenv()

database_provider = os.getenv("DATABASE_PROVIDER", "sqlite")

database_class = SqliteDatabase

if database_provider == "supabase":
    from src.utils.database.supabase import SupabaseDatabase
    database_class = SupabaseDatabase

database = None
_lock = asyncio.Lock()

async def seed_database(database):
    """Seed the database with initial data."""
    config = load_config()

    worlds = [
        {
            "id": config.world_id,
            "name": config.world_name,
        }
    ]

    locations = [
        {
            "id": location.id,
            "world_id": config.world_id,
            "name": location.name,
            "description": location.description,
            "channel_id": os.environ.get(
                f"{location.name.upper().replace(' ','_')}_CHANNEL_ID", None
            )
            if DISCORD_ENABLED
            else None,
            "allowed_agent_ids": [],
            "available_tools": [],
        }
        for location in config.locations
    ]

    agents = [
        {
            "id": agent.id,
            "full_name": agent.first_name,
            "private_bio": agent.private_bio,
            "public_bio": agent.public_bio,
            "directives": agent.directives,
            "authorized_tools": [],
            "ordered_plan_ids": [seed_uuid(f"agent-{agent.id}-initial-plan")],
            "world_id": config.world_id,
            "location_id": random.choice(locations)["id"],
            "discord_bot_token": os.environ.get(
                f"{agent.first_name.upper()}_DISCORD_TOKEN", None
            ),
        }
        for agent in config.agents
    ]

    if DISCORD_ENABLED:
        for agent in agents:
            if agent["discord_bot_token"] is None:
                raise ValueError(
                    f"Could not find discord bot token for agent {agent['full_name']}"
                )

    # For now, allow all agents in all locations
    for location in locations:
        location["allowed_agent_ids"] = [agent["id"] for agent in agents]

    def get_agent_initial_plan(agent):
        location_name = agent.initial_plan["location"]
        location = next(
            (location for location in config.locations if location.name == location_name),
            None,
        )

        if location is None:
            raise ValueError(
                f"Could not find location with name {location_name} for agent {agent.first_name}"
            )

        return {
            "id": seed_uuid(f"agent-{agent.id}-initial-plan"),
            "agent_id": agent.id,
            "description": agent.initial_plan["description"],
            "max_duration_hrs": 1,
            "stop_condition": agent.initial_plan["stop_condition"],
            "location_id": location.id,
        }

    initial_plans = [get_agent_initial_plan(agent) for agent in config.agents]

    await database.insert(Tables.Worlds, worlds, upsert=True)
    await database.insert(Tables.Locations, locations, upsert=True)
    await database.insert(Tables.Agents, agents, upsert=True)
    await database.insert(Tables.Plans, initial_plans, upsert=True)

async def initialize_database():
    """Initialize the database connection and seed with initial data."""
    global database
    # Clean up any existing database files
    try:
        if os.path.exists("database.db"):
            os.remove("database.db")
        if os.path.exists("database.db-shm"):
            os.remove("database.db-shm")
        if os.path.exists("database.db-wal"):
            os.remove("database.db-wal")
    except Exception as e:
        print(f"Warning: Could not remove existing database files: {e}")
    
    # Create new database connection
    database = await database_class.create()
    
    # Seed the database with initial data
    await seed_database(database)
    
    return database

async def get_database():
    """Get a database connection, creating it if necessary."""
    global database
    async with _lock:
        if database is None:
            database = await initialize_database()
        return database

async def close_database():
    """Close the database connection if it exists."""
    global database
    async with _lock:
        if database is not None:
            await database.close()
            database = None
