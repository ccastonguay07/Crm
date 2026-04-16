from typing import Optional

from pydantic import BaseModel

INTENTS = [
    "create_contact",
    "update_contact",
    "add_note",
    "log_interaction",
    "add_followup",
    "query",
    "unknown",
]


class FieldsToUpdate(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    linkedin_url: Optional[str] = None
    twitter_handle: Optional[str] = None
    github_username: Optional[str] = None
    website_url: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None


class ParsedInteraction(BaseModel):
    type: Optional[str] = None  # meeting/call/email/slack/note/other
    summary: Optional[str] = None
    occurred_at: Optional[str] = None  # ISO8601 string


class ParsedFollowUp(BaseModel):
    description: Optional[str] = None
    due_date: Optional[str] = None  # ISO8601 date string


class ParsedQueryFilter(BaseModel):
    company: Optional[str] = None
    tag: Optional[str] = None
    search_term: Optional[str] = None


class ParsedIntent(BaseModel):
    intent: str  # one of INTENTS
    contact_name: Optional[str] = None
    fields_to_update: FieldsToUpdate = FieldsToUpdate()
    note_text: Optional[str] = None
    interaction: Optional[ParsedInteraction] = None
    followup: Optional[ParsedFollowUp] = None
    tags: list[str] = []
    query_filter: Optional[ParsedQueryFilter] = None
    confidence: float = 1.0
    clarification_needed: Optional[str] = None
