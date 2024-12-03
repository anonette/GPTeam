import os
from datetime import datetime

import pytz

from ..memory.base import MemoryType
from .message import get_conversation_history
from .plans import PlanStatus

class AgentFileMixin:
    """Mixin class for file-related agent functionality"""

    async def write_progress_to_file(self):
        """Write agent's current progress to a file"""
        agents_folder = os.path.join(os.getcwd(), "agents")
        if not os.path.exists(agents_folder):
            os.makedirs(agents_folder)

        file_path = os.path.join(agents_folder, f"{self.full_name}.txt")

        plans_in_progress = [
            "🏃‍♂️ " + plan.description
            for plan in self.plans
            if plan.status == PlanStatus.IN_PROGRESS
        ]

        current_action = (
            "\n".join(plans_in_progress) if len(plans_in_progress) > 0 else "No actions"
        )

        conversation_history = await get_conversation_history(self.id, self.context)

        plans_to_do = [
            "📆 " + plan.description
            for plan in self.plans
            if plan.status == PlanStatus.TODO
        ]

        current_plans = "\n".join(plans_to_do) if len(plans_to_do) > 0 else "No plans"

        # Sort memories in reverse chronological order
        sorted_memories = sorted(
            self.memories, key=lambda m: m.created_at, reverse=True
        )

        memories = "\n".join(
            [
                f"{memory.created_at.replace(tzinfo=pytz.utc).strftime('%Y-%m-%d %H:%M:%S')}: {'👀' if memory.type == MemoryType.OBSERVATION else ''} {memory.description} (Importance: {memory.importance})"
                for memory in sorted_memories
            ]
        )

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(
                f"* {self.full_name}\n\nCurrent Action:\n{current_action}\n\nLocation: {self.location.name}\n\nCurrent Conversations:\n{conversation_history}\n\nCurrent Plans:\n{current_plans}\n\nMemories:\n{memories}\n"
            )
