from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.crud import interactions as crud_interactions
from app.database import get_db

router = APIRouter(prefix="/api/interactions", tags=["interactions"])


@router.delete("/{interaction_id}", status_code=204)
def delete_interaction(interaction_id: int, db: Session = Depends(get_db)):
    deleted = crud_interactions.delete_interaction(db, interaction_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Interaction not found")
