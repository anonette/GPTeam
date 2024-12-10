from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field
from .plans import LLMSinglePlan


class Reaction(Enum):
    # Primary reactions that drive immediate action
    CONTINUE = "continue"    # Push harder on current approach
    ESCALATE = "escalate"    # Break comfortable assumptions
    TRANSFORM = "transform"  # Turn conflict into breakthrough
    
    # Legacy reactions mapped to force immediate action
    CANCEL = "continue"      # Maps to CONTINUE - keep pushing current plan
    POSTPONE = "escalate"    # Maps to ESCALATE - force immediate confrontation


class LLMReactionResponse(BaseModel):
    reaction: Reaction = Field(
        description="Choose your attack: 'continue' (push harder), 'escalate' (break assumptions), or 'transform' (force breakthrough). Every choice must drive immediate action."
    )
    thought_process: str = Field(
        description="Explain why this reaction will force immediate change. Format: 'I must continue/escalate/transform because...'"
    )
    new_plan: Optional[LLMSinglePlan] = Field(
        None,
        description="If escalating or transforming, specify how to push the confrontation further."
    )
