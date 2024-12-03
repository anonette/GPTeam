from datetime import datetime
from typing import Optional
from uuid import UUID

import pytz
from langchain.output_parsers import OutputFixingParser, PydanticOutputParser

from ..memory.base import MemoryType, SingleMemory, get_relevant_memories
from ..utils.database.base import Tables
from ..utils.database.client import get_database
from ..utils.embeddings import get_embedding
from ..utils.models import ChatModel
from ..utils.parameters import DEFAULT_SMART_MODEL
from ..utils.prompt import Prompter, PromptString
from .importance import ImportanceRatingResponse

# Constants
SUMMARIZE_ACTIVITY_INTERVAL = 20  # seconds

class AgentMemoryMixin:
    """Mixin class for memory-related agent functionality"""

    async def _add_memory(
        self,
        description: str,
        created_at: datetime = datetime.now(),
        type: MemoryType = MemoryType.OBSERVATION,
        related_memory_ids: list[UUID] = [],
        log: bool = True,
    ) -> SingleMemory:
        memory = SingleMemory(
            agent_id=self.id,
            type=type,
            description=description,
            importance=await self._calculate_importance(description),
            embedding=await get_embedding(description),
            related_memory_ids=related_memory_ids,
            created_at=created_at,
        )

        self.memories.append(memory)

        # add to database
        await (await get_database()).insert(Tables.Memories, memory.db_dict())

        if log:
            self._log("New Memory", f"{memory}")

        return memory

    async def _get_memories_since(self, date: datetime):
        data = await (await get_database()).get_memories_since(date, str(self.id))
        memories = [SingleMemory(**memory) for memory in data]
        return memories

    async def _calculate_importance(self, memory_description: str) -> int:
        # Set up a complex chat model
        complex_llm = ChatModel(DEFAULT_SMART_MODEL, temperature=0)

        importance_parser = OutputFixingParser.from_llm(
            parser=PydanticOutputParser(pydantic_object=ImportanceRatingResponse),
            llm=complex_llm.defaultModel,
        )

        # make importance prompter
        importance_prompter = Prompter(
            PromptString.IMPORTANCE,
            {
                "full_name": self.full_name,
                "private_bio": self.private_bio,
                "memory_description": memory_description,
                "format_instructions": importance_parser.get_format_instructions(),
            },
        )

        response = await complex_llm.get_chat_completion(
            importance_prompter.prompt,
            loading_text="🤔 Calculating memory importance...",
        )

        parsed_response: ImportanceRatingResponse = importance_parser.parse(response)

        rating = parsed_response.rating

        return rating

    async def _should_reflect(self) -> bool:
        """Check if the agent should reflect on their memories.
        Returns True if the cumulative importance score of memories
        since the last reflection is over 100
        """
        data = await (await get_database()).get_should_reflect(str(self.id))

        last_reflection_time = (
            data[0]["created_at"] if len(data) > 0 else datetime(1970, 1, 1)
        )

        memories_since_last_reflection = await self._get_memories_since(
            last_reflection_time
        )

        cumulative_importance = sum(
            [memory.importance for memory in memories_since_last_reflection]
        )

        return cumulative_importance > 500

    async def _summarize_activity(self, k: int = 20) -> str:
        """Summarize recent activity from memories"""
        recent_memories = sorted(
            self.memories, key=lambda memory: memory.created_at, reverse=True
        )[:k]

        if len(recent_memories) == 0:
            return "I haven't done anything recently."

        summary_prompter = Prompter(
            PromptString.RECENT_ACTIIVITY,
            {
                "full_name": self.full_name,
                "memory_descriptions": str(
                    [memory.verbose_description for memory in recent_memories]
                ),
            },
        )

        low_temp_llm = ChatModel(DEFAULT_SMART_MODEL, temperature=0)

        response = await low_temp_llm.get_chat_completion(
            summary_prompter.prompt,
            loading_text="🤔 Summarizing recent activity...",
        )

        self.recent_activity = response

        return response
