import asyncio
import os
import subprocess
import traceback
import webbrowser
from multiprocessing import Process
from time import sleep

from openai import OpenAI
import toml
from dotenv import load_dotenv

from src.utils.database.client import get_database
from src.utils.discord import discord_listener
from src.world.base import World

from .utils.colors import LogColor
from .utils.database.base import Tables
from .utils.formatting import print_to_console
from .utils.logging import init_logging
from .utils.parameters import DISCORD_ENABLED
from .web import get_server
from .utils.general import get_open_port

load_dotenv()

init_logging()

# Read pyproject.toml
with open("pyproject.toml", "r") as f:
    pyproject = toml.load(f)

# Get OpenAI base URL from pyproject.toml
openai_base_url = pyproject.get("tool", {}).get("openai", {}).get("base_url", "https://api.openai.com/v1")

async def run_world_async():
    api_key = os.getenv("OPENAI_API_KEY")
    # api_key = os.getenv("OPENROUTER_API_KEY")
    client = OpenAI(api_key=api_key, base_url=openai_base_url)
    print(f"Using OpenAI base URL: {client.base_url}")
    print(f"API Key: {api_key[:5]}...{api_key[-5:]}")
    try:
        database = await get_database()

        worlds = await database.get_all(Tables.Worlds)

        if len(worlds) == 0:
            raise ValueError("No worlds found!")

        world = await World.from_id(worlds[-1]["id"])

        print_to_console(
            f"Welcome to {world.name}!",
            LogColor.ANNOUNCEMENT,
            "\n",
        )

        await world.run()
    except Exception:
        print(traceback.format_exc())
    finally:
        await (await get_database()).close()


def run_world():
    run_in_new_loop(run_world_async())


def run_server():
    app = get_server()
    port = get_open_port()
    run_in_new_loop(app.run_task(port=port))


def run_in_new_loop(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(coro)
    finally:
        loop.close()


def is_wsl():
    return 'microsoft-standard' in os.uname().release


def run():
    port = get_open_port()

    process_discord = Process(target=discord_listener)
    process_world = Process(target=run_world)
    process_server = Process(target=run_server)

    process_discord.start()
    process_world.start()
    process_server.start()

    sleep(3)

    print(f"Server running on port {port}...")
    if not is_wsl():
        print("Opening browser...")
        webbrowser.open(f"http://127.0.0.1:{port}")
    else:
        print(f"Running in WSL. Please open a browser and navigate to http://127.0.0.1:{port}")

    process_discord.join()
    process_world.join()
    process_server.join()


def main():
    run()
