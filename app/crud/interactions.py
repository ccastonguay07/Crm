from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.interaction import Interaction
from app.schemas.interaction import InteractionCreate


def get_interactions(db: Session, contact_id: int, limit: int = 50) -> list[Interaction]:
    return (
        db.query(Interaction)
        .filter(Interaction.contact_id == contact_id)
        .order_by(Interaction.occurred_at.desc())
        .limit(limit)
        .all()
    )


def get_recent_interactions(db: Session, limit: int = 20) -> list[Interaction]:
    return db.query(Interaction).order_by(Interaction.occurred_at.desc()).limit(limit).all()


def create_interaction(db: Session, contact_id: int, data: InteractionCreate) -> Interaction:
    interaction = Interaction(
        contact_id=contact_id,
        type=data.type,
        summary=data.summary,
        occurred_at=data.occurred_at or datetime.utcnow(),
        source=data.source,
        raw_slack_text=data.raw_slack_text,
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    return interaction


def delete_interaction(db: Session, interaction_id: int) -> bool:
    obj = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True
