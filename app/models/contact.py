from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Integer, String, event
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.tag import contact_tags


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True)
    phone = Column(String)
    company = Column(String)
    job_title = Column(String)
    notes = Column(String)
    profile_photo_url = Column(String)
    linkedin_url = Column(String)
    twitter_handle = Column(String)
    github_username = Column(String)
    website_url = Column(String)
    location = Column(String)
    birthday = Column(Date)
    last_contacted_at = Column(DateTime)
    slack_user_id = Column(String, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    tags = relationship("Tag", secondary=contact_tags, backref="contacts", lazy="selectin")
    interactions = relationship(
        "Interaction", back_populates="contact", cascade="all, delete-orphan", lazy="dynamic"
    )
    followups = relationship(
        "FollowUp", back_populates="contact", cascade="all, delete-orphan", lazy="dynamic"
    )


@event.listens_for(Contact, "before_update")
def update_contact_updated_at(mapper, connection, target):
    target.updated_at = datetime.utcnow()
