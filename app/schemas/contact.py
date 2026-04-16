from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class TagOut(BaseModel):
    id: int
    name: str
    color: str

    model_config = {"from_attributes": True}


class ContactBase(BaseModel):
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    notes: Optional[str] = None
    profile_photo_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    twitter_handle: Optional[str] = None
    github_username: Optional[str] = None
    website_url: Optional[str] = None
    location: Optional[str] = None
    birthday: Optional[date] = None
    slack_user_id: Optional[str] = None


class ContactCreate(ContactBase):
    tags: list[str] = []


class ContactUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    notes: Optional[str] = None
    profile_photo_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    twitter_handle: Optional[str] = None
    github_username: Optional[str] = None
    website_url: Optional[str] = None
    location: Optional[str] = None
    birthday: Optional[date] = None
    slack_user_id: Optional[str] = None
    tags: Optional[list[str]] = None


class ContactOut(ContactBase):
    id: int
    last_contacted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    tags: list[TagOut] = []

    model_config = {"from_attributes": True}
