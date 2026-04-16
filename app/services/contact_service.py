"""Orchestrates Claude-parsed intents into database operations."""
from datetime import datetime
from typing import Optional

from dateutil import parser as dateutil_parser
from sqlalchemy.orm import Session

from app.crud import contacts as crud_contacts
from app.crud import followups as crud_followups
from app.crud import interactions as crud_interactions
from app.models.contact import Contact
from app.schemas.contact import ContactCreate, ContactUpdate
from app.schemas.followup import FollowUpCreate
from app.schemas.interaction import InteractionCreate
from app.schemas.slack_parse import ParsedIntent


def apply_parsed_intent(
    db: Session, parsed: ParsedIntent, raw_text: str
) -> dict:
    """
    Dispatch on parsed.intent and mutate the DB accordingly.
    Returns a dict with keys: action (str), contact (Contact|None), message (str).
    """
    intent = parsed.intent
    contact_name = parsed.contact_name

    if intent == "query":
        return _handle_query(db, parsed)

    if intent == "unknown" or parsed.confidence < 0.5:
        msg = parsed.clarification_needed or (
            "I didn't understand that. Try:\n"
            "• \"Add Jane Doe, works at Stripe, email jane@stripe.com\"\n"
            "• \"Met John today at the conference\"\n"
            "• \"Remind me to follow up with Sarah next Tuesday\"\n"
            "• \"Show me contacts at Google\""
        )
        return {"action": "unknown", "contact": None, "message": msg}

    if parsed.clarification_needed and parsed.confidence < 0.7:
        return {"action": "clarify", "contact": None, "message": parsed.clarification_needed}

    # All other intents need a contact name
    if not contact_name:
        return {
            "action": "clarify",
            "contact": None,
            "message": "Who are you referring to? Please include the contact's full name.",
        }

    contact = crud_contacts.find_contact_by_name(db, contact_name)

    if intent == "create_contact":
        if contact:
            # Contact exists — merge data in instead of duplicating
            contact = _update_contact_fields(db, contact, parsed, raw_text)
            return {
                "action": "updated",
                "contact": contact,
                "message": f"I found an existing contact for *{contact.full_name}* and updated their profile.",
            }
        contact = _create_contact(db, contact_name, parsed, raw_text)
        return {
            "action": "created",
            "contact": contact,
            "message": f"Created contact *{contact.full_name}*.",
        }

    if not contact:
        return {
            "action": "not_found",
            "contact": None,
            "message": (
                f"I couldn't find a contact named *{contact_name}*. "
                "Want me to create them? Just say \"Add {name}\" with their details."
            ),
        }

    if intent == "update_contact":
        contact = _update_contact_fields(db, contact, parsed, raw_text)
        return {"action": "updated", "contact": contact, "message": f"Updated *{contact.full_name}*."}

    if intent in ("add_note", "log_interaction"):
        interaction = _log_interaction(db, contact, parsed, raw_text)
        return {
            "action": "interaction_logged",
            "contact": contact,
            "message": f"Logged a {interaction.type} for *{contact.full_name}*.",
        }

    if intent == "add_followup":
        followup = _add_followup(db, contact, parsed)
        if followup:
            return {
                "action": "followup_added",
                "contact": contact,
                "message": f"Added a follow-up for *{contact.full_name}* on {followup.due_date}.",
            }
        return {
            "action": "clarify",
            "contact": contact,
            "message": f"When should I remind you to follow up with *{contact.full_name}*?",
        }

    return {"action": "unknown", "contact": None, "message": "I didn't understand that request."}


def _create_contact(db: Session, name: str, parsed: ParsedIntent, raw_text: str) -> Contact:
    fields = parsed.fields_to_update
    data = ContactCreate(
        full_name=name,
        email=fields.email,
        phone=fields.phone,
        company=fields.company,
        job_title=fields.job_title,
        linkedin_url=fields.linkedin_url,
        twitter_handle=fields.twitter_handle,
        github_username=fields.github_username,
        website_url=fields.website_url,
        location=fields.location,
        notes=fields.notes,
        tags=parsed.tags,
    )
    contact = crud_contacts.create_contact(db, data)

    # Log an initial interaction if there's content
    _log_interaction(db, contact, parsed, raw_text)
    _add_followup(db, contact, parsed)

    return contact


def _update_contact_fields(db: Session, contact: Contact, parsed: ParsedIntent, raw_text: str) -> Contact:
    fields = parsed.fields_to_update
    update_dict = {
        k: v for k, v in {
            "email": fields.email,
            "phone": fields.phone,
            "company": fields.company,
            "job_title": fields.job_title,
            "linkedin_url": fields.linkedin_url,
            "twitter_handle": fields.twitter_handle,
            "github_username": fields.github_username,
            "website_url": fields.website_url,
            "location": fields.location,
            "notes": fields.notes,
        }.items() if v is not None
    }

    # Merge tags (add, don't replace)
    existing_tag_names = [t.name for t in contact.tags]
    new_tags = existing_tag_names + [t for t in parsed.tags if t not in existing_tag_names]

    data = ContactUpdate(**update_dict, tags=new_tags if new_tags else None)
    contact = crud_contacts.update_contact(db, contact, data)

    _log_interaction(db, contact, parsed, raw_text)
    _add_followup(db, contact, parsed)

    return contact


def _log_interaction(db: Session, contact: Contact, parsed: ParsedIntent, raw_text: str) -> Optional[object]:
    summary = None
    interaction_type = "note"
    occurred_at = None

    if parsed.interaction and parsed.interaction.summary:
        summary = parsed.interaction.summary
        interaction_type = parsed.interaction.type or "note"
        if parsed.interaction.occurred_at:
            try:
                occurred_at = dateutil_parser.parse(parsed.interaction.occurred_at)
            except Exception:
                occurred_at = None
    elif parsed.note_text:
        summary = parsed.note_text
        interaction_type = "note"

    if not summary:
        return None

    data = InteractionCreate(
        type=interaction_type,
        summary=summary,
        occurred_at=occurred_at,
        source="slack",
        raw_slack_text=raw_text,
    )
    interaction = crud_interactions.create_interaction(db, contact.id, data)
    crud_contacts.update_last_contacted(db, contact)
    return interaction


def _add_followup(db: Session, contact: Contact, parsed: ParsedIntent) -> Optional[object]:
    if not parsed.followup or not parsed.followup.due_date:
        return None
    try:
        due_date = dateutil_parser.parse(parsed.followup.due_date).date()
    except Exception:
        return None
    description = parsed.followup.description or "Follow up"
    data = FollowUpCreate(description=description, due_date=due_date)
    return crud_followups.create_followup(db, contact.id, data)


def _handle_query(db: Session, parsed: ParsedIntent) -> dict:
    qf = parsed.query_filter
    contacts = crud_contacts.get_contacts(
        db,
        search=qf.search_term if qf else None,
        company=qf.company if qf else None,
        tag=qf.tag if qf else None,
        limit=10,
    )
    if not contacts:
        return {"action": "query", "contact": None, "message": "No contacts found matching that criteria."}

    lines = [f"Found {len(contacts)} contact(s):"]
    for c in contacts:
        line = f"• *{c.full_name}*"
        if c.company:
            line += f" — {c.company}"
        if c.job_title:
            line += f", {c.job_title}"
        lines.append(line)
    return {"action": "query", "contact": None, "message": "\n".join(lines)}
