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

# Global variables for process management
world_process = None
server_process = None
should_exit = False

async def cleanup():
    """Cleanup function to close connections and pending tasks"""
    try:
        # Close database connection
        print("Closing database connection...")
        db = await get_database()
        await db.close()
        
        # Cancel all pending tasks
        print("Canceling pending tasks...")
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        
    except Exception as e:
        print(f"Error during cleanup: {str(e)}")
        print(traceback.format_exc())

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
    except asyncio.CancelledError:
        print("World simulation cancelled")
    except Exception as e:
        print(f"Error in world simulation: {str(e)}")
        print(traceback.format_exc())
    finally:
        await cleanup()

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
    except KeyboardInterrupt:
        print("\nReceived keyboard interrupt, cleaning up...")
        loop.run_until_complete(cleanup())
    except Exception as e:
        print(f"Error in event loop: {str(e)}")
        print(traceback.format_exc())
    finally:
        try:
            # Cancel all pending tasks
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            # Allow cancelled tasks to complete
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            # Close the event loop
            loop.close()
        except Exception as e:
            print(f"Error during loop cleanup: {str(e)}")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global should_exit
    if not should_exit:
        should_exit = True
        print("\nShutting down gracefully...")
        # Terminate child processes
        if world_process and world_process.is_alive():
            world_process.terminate()
        if server_process and server_process.is_alive():
            server_process.terminate()
        sys.exit(0)

def run():
    global world_process, server_process
    
    # Use spawn method for process creation
    set_start_method('spawn', force=True)
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    port = get_open_port()
    print(f"Active port found: {port}")

    world_process = Process(target=run_world)
    server_process = Process(target=run_server, args=(port,))

    try:
        print("Starting processes...")
        world_process.start()
        server_process.start()

        sleep(3)

        print(f"Opening browser on port {port}...")
        webbrowser.open(f"http://127.0.0.1:{port}")

        # Wait for processes to complete or interrupt
        while not should_exit:
            if not world_process.is_alive() or not server_process.is_alive():
                break
            sleep(1)

    except KeyboardInterrupt:
        print("\nReceived keyboard interrupt...")
    except Exception as e:
        print(f"Error in main process: {str(e)}")
        print(traceback.format_exc())
    finally:
        # Clean up processes
        if world_process and world_process.is_alive():
            print("Terminating world process...")
            world_process.terminate()
            world_process.join(timeout=5)
            if world_process.is_alive():
                world_process.kill()
        
        if server_process and server_process.is_alive():
            print("Terminating server process...")
            server_process.terminate()
            server_process.join(timeout=5)
            if server_process.is_alive():
                server_process.kill()
        
        print("Shutdown complete")

def main():
    try:
        run()
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        print(traceback.format_exc())
