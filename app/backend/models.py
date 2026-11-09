from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field

ActionType = Literal["escalate_master_data", "escalate_artwork", "book_maintenance"]


class ActionIn(BaseModel):
    launch_id: str = Field(min_length=1, max_length=40)
    action_type: ActionType
    owner: str = Field(min_length=1, max_length=120)
    due_date: date
    equipment: Optional[str] = Field(default=None, max_length=60)
    note: Optional[str] = Field(default=None, max_length=1000)


class GenieAsk(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    space: Literal["demand", "manufacturing"]
    conversation_id: Optional[str] = None
