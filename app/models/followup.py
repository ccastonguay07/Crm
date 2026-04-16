from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, event
from sqlalchemy.orm import relationship

from app.database import Base


class FollowUp(Base):
    __tablename__ = "followups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    contact_id = Column(Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False)
    description = Column(String, nullable=False)
    due_date = Column(Date, nullable=False)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    contact = relationship("Contact", back_populates="followups")


@event.listens_for(FollowUp, "before_update")
def update_followup_updated_at(mapper, connection, target):
    target.updated_at = datetime.utcnow()
