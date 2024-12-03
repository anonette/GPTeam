from datetime import datetime
from typing import Optional

import pytz
from langchain.output_parsers import OutputFixingParser, PydanticOutputParser

from ..event.base import Event, EventType, MessageEventSubtype
from ..memory.base import MemoryType, get_relevant_memories
from ..utils.models import ChatModel
from ..utils.parameters import DEFAULT_SMART_MODEL, REFLECTION_MEMORY_COUNT
from ..utils.prompt import Prompter, PromptString
from .reflection import ReflectionQuestions, ReflectionResponse

class AgentReflectionMixin:
    """Mixin class for reflection-related agent functionality"""

    async def _reflect(self):
        """Reflect on recent memories and generate insights"""
        recent_memories = sorted(
            self.memories,
            key=lambda memory: memory.last_accessed or memory.created_at,
            reverse=True,
        )[:REFLECTION_MEMORY_COUNT]

        self._log("Reflection", "Beginning reflection... 🤔")

        # Set up a complex chat model
        chat_llm = ChatModel(DEFAULT_SMART_MODEL, temperature=0)

        # Set up the parser
        question_parser = OutputFixingParser.from_llm(
            parser=PydanticOutputParser(pydantic_object=ReflectionQuestions),
            llm=chat_llm.defaultModel,
        )

        # Create questions Prompter
        questions_prompter = Prompter(
            PromptString.REFLECTION_QUESTIONS,
            {
                "memory_descriptions": str(
                    [memory.verbose_description for memory in recent_memories]
                ),
                "format_instructions": question_parser.get_format_instructions(),
            },
        )

        # Get the reflection questions
        response = await chat_llm.get_chat_completion(
            questions_prompter.prompt,
            loading_text="🤔 Thinking about what to reflect on...",
        )

        # Parse the response into an object
        parsed_questions_response: ReflectionQuestions = question_parser.parse(response)

        # For each question in the parsed questions...
        for question in parsed_questions_response.questions:
            # Get the related memories
            related_memories = await get_relevant_memories(question, self.memories, 20)

            # Format them into a string
            memory_strings = [
                f"{index}. {related_memory.description}"
                for index, related_memory in enumerate(related_memories, start=1)
            ]

            # Make the reflection parser
            reflection_parser = OutputFixingParser.from_llm(
                parser=PydanticOutputParser(pydantic_object=ReflectionResponse),
                llm=chat_llm.defaultModel,
            )

            self._log("Reflecting on Question", f"{question}")

            # Make the reflection prompter
            reflection_prompter = Prompter(
                PromptString.REFLECTION_INSIGHTS,
                {
                    "full_name": self.full_name,
                    "memory_strings": str(memory_strings),
                    "format_instructions": reflection_parser.get_format_instructions(),
                },
            )

            # Get the reflection insights
            response = await chat_llm.get_chat_completion(
                reflection_prompter.prompt,
                loading_text="🤔 Reflecting",
            )

            # Parse the response into an object
            parsed_insights_response: ReflectionResponse = reflection_parser.parse(
                response
            )

            # For each insight in the parsed insights...
            for reflection_insight in parsed_insights_response.insights:
                # Get the related memory ids
                related_memory_ids = [
                    related_memories[index - 1].id
                    for index in reflection_insight.related_statements
                ]

                # Add a new memory
                await self._add_memory(
                    description=reflection_insight.insight,
                    type=MemoryType.REFLECTION,
                    related_memory_ids=related_memory_ids,
                )

        # Gossip to other agents
        await self._share_reflections(recent_memories)

    async def _share_reflections(self, recent_memories):
        """Share reflections with other agents in the same location"""
        # Get other agents at the location
        agents_at_location = self.context.get_agents_at_location(
            location_id=self.location.id
        )

        other_agents = [a for a in agents_at_location if str(a["id"]) != str(self.id)]

        # names of other agents at location
        other_agent_names = ", ".join([a["full_name"] for a in other_agents])

        # Make the reaction prompter
        gossip_prompter = Prompter(
            PromptString.GOSSIP,
            {
                "full_name": self.full_name,
                "memory_descriptions": str(
                    [memory.description for memory in recent_memories]
                ),
                "other_agent_names": other_agent_names,
            },
        )

        chat_llm = ChatModel(DEFAULT_SMART_MODEL, temperature=0)
        response = await chat_llm.get_chat_completion(
            gossip_prompter.prompt,
            loading_text="🤔 Creating gossip...",
        )

        self._log(
            "Gossip",
            f"{response}",
        )

        event = Event(
            agent_id=self.id,
            type=EventType.MESSAGE,
            subtype=MessageEventSubtype.AGENT_TO_AGENT,
            description=f"{self.full_name} said to everyone in the {self.location.name}: '{response}'",
            location_id=self.location.id,
        )

        await self.context.add_event(event)
