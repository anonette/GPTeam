import asyncio
import json
import os
import re
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from quart import Quart, abort, make_response, send_file, websocket
from ..utils.model_name import ChatModelName
from ..utils.parameters import DEFAULT_FAST_MODEL, DEFAULT_SMART_MODEL

from src.utils.database.base import Tables
from src.utils.database.client import get_database

load_dotenv()

window_request_queue = asyncio.Queue()
window_response_queue = asyncio.Queue()

# Track active websocket connections
active_connections = set()

@asynccontextmanager
async def track_connection(ws):
    """Track active websocket connections for cleanup"""
    try:
        active_connections.add(ws)
        yield
    finally:
        active_connections.remove(ws)

async def close_connections():
    """Close all active websocket connections"""
    for ws in active_connections.copy():
        try:
            await ws.close(1000)  # Normal closure
        except Exception as e:
            print(f"Error closing websocket: {str(e)}")

def get_server():
    app = Quart(__name__)

    app.config["ENV"] = "development"
    app.config["DEBUG"] = True

    @app.before_serving
    async def startup():
        app.active_connections = set()

    @app.after_serving
    async def shutdown():
        await close_connections()

    @app.route("/")
    async def index():
        file_path = os.path.join(os.path.dirname(__file__), "templates/logs.html")
        return await send_file(file_path)

    @app.websocket("/logs")
    async def logs_websocket():
        async with track_connection(websocket._get_current_object()):
            file_path = os.path.join(os.path.dirname(__file__), "logs/agent.txt")
            position = 0
            try:
                while True:
                    try:
                        await asyncio.sleep(0.25)
                        with open(file_path, "r") as log_file:
                            log_file.seek(position)
                            line = log_file.readline()
                            if line:
                                position = log_file.tell()
                                matches = re.match(r"\[(.*?)\] \[(.*?)\] \[(.*?)\] (.*)$", line)
                                if matches:
                                    agentName = matches.group(1).strip()
                                    color = matches.group(2).strip().split(".")[1]
                                    title = matches.group(3).strip()
                                    description = matches.group(4).strip()

                                    data = {
                                        "agentName": agentName,
                                        "color": color,
                                        "title": title,
                                        "description": description,
                                    }
                                    await websocket.send_json(data)
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        print(f"Error in logs websocket: {str(e)}")
                        break
            finally:
                print("Logs websocket connection closed")

    @app.websocket("/world")
    async def world_websocket():
        async with track_connection(websocket._get_current_object()):
            try:
                while True:
                    try:
                        await asyncio.sleep(0.25)
                        database = await get_database()
                        worlds = await database.get_all(Tables.Worlds)

                        if not worlds:
                            abort(404, "No worlds found")

                        id = worlds[0]["id"]

                        # get all locations
                        locations = await database.get_by_field(
                            Tables.Locations, "world_id", str(id)
                        )

                        # get all agents
                        agents = await database.get_by_field(Tables.Agents, "world_id", str(id))

                        location_mapping = {
                            location["id"]: location["name"] for location in locations
                        }

                        agents_state = [
                            {
                                "full_name": agent["full_name"],
                                "location": location_mapping.get(
                                    agent["location_id"], "Unknown Location"
                                ),
                            }
                            for agent in agents
                        ]

                        sorted_agents = sorted(agents_state, key=lambda k: k["full_name"])

                        await websocket.send_json(
                            {"agents": sorted_agents, "name": worlds[0]["name"]}
                        )
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        print(f"Error in world websocket: {str(e)}")
                        break
            finally:
                print("World websocket connection closed")

    @app.websocket("/window")
    async def window_websocket():
        if (
            DEFAULT_SMART_MODEL != ChatModelName.WINDOW
            and DEFAULT_FAST_MODEL != ChatModelName.WINDOW
        ):
            return

        async with track_connection(websocket._get_current_object()):
            try:
                while True:
                    try:
                        await asyncio.sleep(0.25)
                        request = await window_request_queue.get()
                        await websocket.send(request)
                        response = await websocket.receive()
                        await window_response_queue.put(response)
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        print(f"Error in window websocket: {str(e)}")
                        break
            finally:
                print("Window websocket connection closed")

    @app.websocket("/windowmodel")
    async def window_model_websocket():
        if (
            DEFAULT_SMART_MODEL != ChatModelName.WINDOW
            and DEFAULT_FAST_MODEL != ChatModelName.WINDOW
        ):
            return

        async with track_connection(websocket._get_current_object()):
            try:
                while True:
                    try:
                        await asyncio.sleep(0.25)
                        request = await websocket.receive()
                        await window_request_queue.put(request)
                        response = await window_response_queue.get()
                        await websocket.send(response)
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        print(f"Error in window model websocket: {str(e)}")
                        break
            finally:
                print("Window model websocket connection closed")

    return app
