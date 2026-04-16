from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.crud import contacts as crud_contacts
from app.crud import interactions as crud_interactions
from app.crud import followups as crud_followups
from app.database import get_db
from app.schemas.contact import ContactCreate, ContactOut, ContactUpdate
from app.schemas.interaction import InteractionCreate, InteractionOut
from app.schemas.followup import FollowUpCreate, FollowUpOut

router = APIRouter(prefix="/api/contacts", tags=["contacts"])


@router.get("", response_model=list[ContactOut])
def list_contacts(
    search: Optional[str] = None,
    tag: Optional[str] = None,
    company: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    return crud_contacts.get_contacts(db, search=search, tag=tag, company=company, limit=limit, offset=offset)


@router.post("", response_model=ContactOut, status_code=201)
def create_contact(data: ContactCreate, db: Session = Depends(get_db)):
    return crud_contacts.create_contact(db, data)


@router.get("/{contact_id}", response_model=ContactOut)
def get_contact(contact_id: int, db: Session = Depends(get_db)):
    contact = crud_contacts.get_contact(db, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.put("/{contact_id}", response_model=ContactOut)
def update_contact(contact_id: int, data: ContactUpdate, db: Session = Depends(get_db)):
    contact = crud_contacts.get_contact(db, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return crud_contacts.update_contact(db, contact, data)


@router.delete("/{contact_id}", status_code=204)
def delete_contact(contact_id: int, db: Session = Depends(get_db)):
    contact = crud_contacts.get_contact(db, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    crud_contacts.delete_contact(db, contact)


@router.get("/{contact_id}/interactions", response_model=list[InteractionOut])
def list_interactions(contact_id: int, db: Session = Depends(get_db)):
    contact = crud_contacts.get_contact(db, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return crud_interactions.get_interactions(db, contact_id)


@router.post("/{contact_id}/interactions", response_model=InteractionOut, status_code=201)
def add_interaction(contact_id: int, data: InteractionCreate, db: Session = Depends(get_db)):
    contact = crud_contacts.get_contact(db, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    interaction = crud_interactions.create_interaction(db, contact_id, data)
    crud_contacts.update_last_contacted(db, contact)
    return interaction


@router.get("/{contact_id}/followups", response_model=list[FollowUpOut])
def list_followups(contact_id: int, db: Session = Depends(get_db)):
    contact = crud_contacts.get_contact(db, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return crud_followups.get_followups(db, contact_id)


@router.post("/{contact_id}/followups", response_model=FollowUpOut, status_code=201)
def add_followup(contact_id: int, data: FollowUpCreate, db: Session = Depends(get_db)):
    contact = crud_contacts.get_contact(db, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return crud_followups.create_followup(db, contact_id, data)
