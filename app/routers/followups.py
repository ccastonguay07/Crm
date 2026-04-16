from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.crud import followups as crud_followups
from app.database import get_db
from app.schemas.followup import FollowUpOut, FollowUpUpdate

router = APIRouter(prefix="/api/followups", tags=["followups"])


@router.get("", response_model=list[FollowUpOut])
def list_all_followups(overdue: bool = False, completed: bool = False, db: Session = Depends(get_db)):
    return crud_followups.get_all_followups(db, overdue_only=overdue, completed=completed)


@router.put("/{followup_id}", response_model=FollowUpOut)
def update_followup(followup_id: int, data: FollowUpUpdate, db: Session = Depends(get_db)):
    obj = crud_followups.update_followup(db, followup_id, data)
    if not obj:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    return obj


@router.delete("/{followup_id}", status_code=204)
def delete_followup(followup_id: int, db: Session = Depends(get_db)):
    deleted = crud_followups.delete_followup(db, followup_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Follow-up not found")
