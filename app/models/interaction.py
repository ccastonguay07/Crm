from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    contact_id = Column(Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False)
    type = Column(String, nullable=False, default="note")  # meeting/call/email/slack/note/other
    summary = Column(String, nullable=False)
    occurred_at = Column(DateTime, default=datetime.utcnow)
    source = Column(String, default="manual")  # 'slack' or 'manual'
    raw_slack_text = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    contact = relationship("Contact", back_populates="interactions")
