from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field
from .plans import LLMSinglePlan


class Reaction(Enum):
    CONTINUE = "continue"
    ESCALATE = "escalate"
    TRANSFORM = "transform"

class LLMReactionResponse(BaseModel):
    reaction: Reaction = Field(
        description="The reaction to the message. Must be one of: 'continue' (push harder on current approach), 'escalate' (break their comfortable assumptions), or 'transform' (turn conflict into breakthrough). No delays allowed."
    )
    thought_process: str = Field(
        description="A summary of what has happened recently and why this reaction will drive more confrontation. Format: 'I must continue/escalate/transform because...'"
    )
    new_plan: Optional[LLMSinglePlan] = Field(
        None,
        description="If the reaction is 'escalate' or 'transform', specify how to push the confrontation further."
    )
