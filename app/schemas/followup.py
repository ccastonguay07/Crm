from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class FollowUpCreate(BaseModel):
    description: str
    due_date: date


class FollowUpUpdate(BaseModel):
    description: Optional[str] = None
    due_date: Optional[date] = None
    is_completed: Optional[bool] = None


class FollowUpOut(BaseModel):
    id: int
    contact_id: int
    description: str
    due_date: date
    is_completed: bool
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}
