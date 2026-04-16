from datetime import datetime
from difflib import SequenceMatcher
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.contact import Contact
from app.models.tag import Tag
from app.schemas.contact import ContactCreate, ContactUpdate


def _get_or_create_tags(db: Session, tag_names: list[str]) -> list[Tag]:
    tags = []
    for name in tag_names:
        name = name.strip().lower()
        if not name:
            continue
        tag = db.query(Tag).filter(Tag.name == name).first()
        if not tag:
            tag = Tag(name=name)
            db.add(tag)
            db.flush()
        tags.append(tag)
    return tags


def get_contact(db: Session, contact_id: int) -> Optional[Contact]:
    return db.query(Contact).filter(Contact.id == contact_id).first()


def get_contacts(
    db: Session,
    search: Optional[str] = None,
    tag: Optional[str] = None,
    company: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Contact]:
    q = db.query(Contact)
    if search:
        term = f"%{search}%"
        q = q.filter(
            or_(
                Contact.full_name.ilike(term),
                Contact.email.ilike(term),
                Contact.company.ilike(term),
                Contact.notes.ilike(term),
            )
        )
    if company:
        q = q.filter(Contact.company.ilike(f"%{company}%"))
    if tag:
        q = q.join(Contact.tags).filter(Tag.name == tag.lower())
    return q.order_by(Contact.updated_at.desc()).offset(offset).limit(limit).all()


def create_contact(db: Session, data: ContactCreate) -> Contact:
    tag_objs = _get_or_create_tags(db, data.tags)
    contact = Contact(
        **data.model_dump(exclude={"tags"}),
    )
    contact.tags = tag_objs
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def update_contact(db: Session, contact: Contact, data: ContactUpdate) -> Contact:
    update_data = data.model_dump(exclude_unset=True, exclude={"tags"})
    for field, value in update_data.items():
        setattr(contact, field, value)
    if data.tags is not None:
        contact.tags = _get_or_create_tags(db, data.tags)
    db.commit()
    db.refresh(contact)
    return contact


def delete_contact(db: Session, contact: Contact) -> None:
    db.delete(contact)
    db.commit()


def find_contact_by_name(db: Session, name: str) -> Optional[Contact]:
    """Exact case-insensitive match first, then fuzzy fallback."""
    exact = db.query(Contact).filter(Contact.full_name.ilike(name)).first()
    if exact:
        return exact
    all_contacts = db.query(Contact).all()
    best_match = None
    best_score = 0.0
    for c in all_contacts:
        score = SequenceMatcher(None, name.lower(), c.full_name.lower()).ratio()
        if score > best_score:
            best_score = score
            best_match = c
    if best_score >= 0.75:
        return best_match
    return None


def get_all_contact_names(db: Session) -> list[str]:
    return [c.full_name for c in db.query(Contact.full_name).all()]


def update_last_contacted(db: Session, contact: Contact) -> None:
    contact.last_contacted_at = datetime.utcnow()
    db.commit()
