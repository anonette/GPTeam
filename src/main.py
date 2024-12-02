import asyncio
import os
import subprocess
import signal
import sys
import traceback
import webbrowser
from multiprocessing import Process, set_start_method
from time import sleep

import openai
from dotenv import load_dotenv

from src.utils.database.client import get_database
from src.world.base import World

from .utils.colors import LogColor
from .utils.database.base import Tables
from .utils.formatting import print_to_console
from .utils.logging import init_logging
from .web import get_server
from .utils.general import get_open_port

load_dotenv()

init_logging()


async def run_world_async():
    openai.api_key = os.getenv("OPENAI_API_KEY")
    try:
        print("Connecting to database...")
        database = await get_database()

        print("Getting worlds...")
        worlds = await database.get_all(Tables.Worlds)

        if len(worlds) == 0:
            raise ValueError("No worlds found!")

        print(f"Loading world {worlds[-1]['id']}...")
        world = await World.from_id(worlds[-1]["id"])

        print_to_console(
            f"Welcome to {world.name}!",
            LogColor.ANNOUNCEMENT,
            "\n",
        )

        print("Starting world simulation...")
        await world.run()
    except Exception as e:
        print(f"Error in world simulation: {str(e)}")
        print(traceback.format_exc())
    finally:
        print("Closing database connection...")
        await (await get_database()).close()


def run_world():
    try:
        # Detach from terminal
        os.setpgrp()
        print("Starting world process...")
        run_in_new_loop(run_world_async())
    except Exception as e:
        print(f"Error in world process: {str(e)}")
        print(traceback.format_exc())


def run_server(port):
    try:
        # Detach from terminal
        os.setpgrp()
        print(f"Starting server on port {port}...")
        app = get_server()
        run_in_new_loop(app.run_task(port=port))
    except Exception as e:
        print(f"Error in server process: {str(e)}")
        print(traceback.format_exc())


def run_in_new_loop(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(coro)
    except Exception as e:
        print(f"Error in event loop: {str(e)}")
        print(traceback.format_exc())
    finally:
        loop.close()


def signal_handler(signum, frame):
    print("\nShutting down gracefully...")
    sys.exit(0)


def run():
    # Use spawn method for process creation
    set_start_method('spawn', force=True)
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    port = get_open_port()
    print(f"Active port found: {port}")

    process_world = Process(target=run_world)
    process_server = Process(target=run_server, args=(port,))

    try:
        print("Starting processes...")
        process_world.start()
        process_server.start()

        sleep(3)

        print(f"Opening browser on port {port}...")
        webbrowser.open(f"http://127.0.0.1:{port}")

        # Wait for processes to complete or interrupt
        process_world.join()
        process_server.join()

    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    except Exception as e:
        print(f"Error in main process: {str(e)}")
        print(traceback.format_exc())
    finally:
        # Clean up processes
        if process_world.is_alive():
            process_world.terminate()
            process_world.join()
        if process_server.is_alive():
            process_server.terminate()
            process_server.join()
        print("Shutdown complete")


def main():
    try:
        run()
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        print(traceback.format_exc())
