from datetime import datetime
from typing import Optional

from pydantic import BaseModel

INTERACTION_TYPES = ["meeting", "call", "email", "slack", "note", "other"]


class InteractionCreate(BaseModel):
    type: str = "note"
    summary: str
    occurred_at: Optional[datetime] = None
    source: str = "manual"
    raw_slack_text: Optional[str] = None


class InteractionOut(BaseModel):
    id: int
    contact_id: int
    type: str
    summary: str
    occurred_at: datetime
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}
