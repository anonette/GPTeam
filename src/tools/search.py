from colorama import Fore
from langchain.agents import Tool
from langchain.utilities import SerpAPIWrapper


class SearchTool(Tool):
    def __init__(self):
        search = SerpAPIWrapper()
        super().__init__(
            name="Current Search",
            func=search.run,
            description="useful for when you need feedback. the input to this should be a single search term.",
        )
