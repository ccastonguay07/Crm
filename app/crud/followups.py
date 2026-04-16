from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.followup import FollowUp
from app.schemas.followup import FollowUpCreate, FollowUpUpdate


def get_followups(db: Session, contact_id: int) -> list[FollowUp]:
    return (
        db.query(FollowUp)
        .filter(FollowUp.contact_id == contact_id)
        .order_by(FollowUp.due_date.asc())
        .all()
    )


def get_all_followups(
    db: Session, overdue_only: bool = False, completed: bool = False
) -> list[FollowUp]:
    q = db.query(FollowUp).filter(FollowUp.is_completed == completed)
    if overdue_only:
        q = q.filter(FollowUp.due_date < date.today())
    return q.order_by(FollowUp.due_date.asc()).all()


def get_upcoming_followups(db: Session, days: int = 7) -> list[FollowUp]:
    today = date.today()
    from datetime import timedelta
    end = today + timedelta(days=days)
    return (
        db.query(FollowUp)
        .filter(FollowUp.is_completed == False, FollowUp.due_date >= today, FollowUp.due_date <= end)
        .order_by(FollowUp.due_date.asc())
        .all()
    )


def create_followup(db: Session, contact_id: int, data: FollowUpCreate) -> FollowUp:
    followup = FollowUp(contact_id=contact_id, description=data.description, due_date=data.due_date)
    db.add(followup)
    db.commit()
    db.refresh(followup)
    return followup


def update_followup(db: Session, followup_id: int, data: FollowUpUpdate) -> Optional[FollowUp]:
    obj = db.query(FollowUp).filter(FollowUp.id == followup_id).first()
    if not obj:
        return None
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(obj, field, value)
    if data.is_completed is True and obj.completed_at is None:
        obj.completed_at = datetime.utcnow()
    elif data.is_completed is False:
        obj.completed_at = None
    db.commit()
    db.refresh(obj)
    return obj


def delete_followup(db: Session, followup_id: int) -> bool:
    obj = db.query(FollowUp).filter(FollowUp.id == followup_id).first()
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True


def complete_followup(db: Session, followup_id: int) -> Optional[FollowUp]:
    return update_followup(db, followup_id, FollowUpUpdate(is_completed=True))
