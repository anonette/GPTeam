from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field
from .plans import LLMSinglePlan


class Reaction(Enum):
    CONTINUE = "continue"
    POSTPONE = "postpone"
    CANCEL = "cancel"

class LLMReactionResponse(BaseModel):
    reaction: Reaction = Field(
        description="The reaction to the message. Must be one of 'continue', 'postpone', or 'cancel'. Choose based on dramatic potential and emotional impact."
    )
    thought_process: str = Field(
        description="An emotionally charged analysis of recent events, explaining your reaction with strong ideological conviction. Include your character's emotional state and how it affects your decision. Format as: 'I must continue/postpone/cancel my plan because [emotional reason tied to your ideological stance]'"
    )
    new_plan: Optional[LLMSinglePlan] = Field(
        None,
        description="If the reaction is 'postpone', specify a new plan that creates maximum dramatic tension and advances your ideological agenda. The plan should involve direct confrontation or emotional revelation."
    )
