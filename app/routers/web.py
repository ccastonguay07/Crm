from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.crud import contacts as crud_contacts
from app.crud import followups as crud_followups
from app.crud import interactions as crud_interactions
from app.crud import tags as crud_tags
from app.database import get_db
from app.schemas.contact import ContactCreate, ContactUpdate
from app.schemas.followup import FollowUpCreate
from app.schemas.interaction import InteractionCreate

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="app/templates")


def flash(request: Request, message: str, category: str = "success"):
    if "_messages" not in request.session:
        request.session["_messages"] = []
    request.session["_messages"].append({"message": message, "category": category})


def get_flashed_messages(request: Request):
    messages = request.session.pop("_messages", [])
    return messages


templates.env.globals["get_flashed_messages"] = get_flashed_messages


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    total_contacts = len(crud_contacts.get_contacts(db, limit=10000))
    from datetime import timedelta
    week_ago = datetime.utcnow() - timedelta(days=7)
    all_contacts = crud_contacts.get_contacts(db, limit=10000)
    added_this_week = sum(1 for c in all_contacts if c.created_at and c.created_at >= week_ago)
    overdue = crud_followups.get_all_followups(db, overdue_only=True)
    upcoming = crud_followups.get_upcoming_followups(db, days=7)
    recent_contacts = crud_contacts.get_contacts(db, limit=5)
    recent_interactions = crud_interactions.get_recent_interactions(db, limit=10)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "total_contacts": total_contacts,
            "added_this_week": added_this_week,
            "overdue_followups": overdue,
            "upcoming_followups": upcoming,
            "recent_contacts": recent_contacts,
            "recent_interactions": recent_interactions,
        },
    )


@router.get("/contacts", response_class=HTMLResponse)
def contacts_list(
    request: Request,
    search: Optional[str] = None,
    tag: Optional[str] = None,
    company: Optional[str] = None,
    db: Session = Depends(get_db),
):
    contacts = crud_contacts.get_contacts(db, search=search, tag=tag, company=company)
    all_tags = crud_tags.get_tags(db)
    return templates.TemplateResponse(
        "contacts/list.html",
        {
            "request": request,
            "contacts": contacts,
            "all_tags": all_tags,
            "search": search or "",
            "active_tag": tag or "",
            "active_company": company or "",
        },
    )


@router.get("/contacts/new", response_class=HTMLResponse)
def contact_new_form(request: Request, db: Session = Depends(get_db)):
    all_tags = crud_tags.get_tags(db)
    return templates.TemplateResponse(
        "contacts/create.html", {"request": request, "all_tags": all_tags}
    )


@router.post("/contacts/new")
async def contact_create(
    request: Request,
    full_name: str = Form(...),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    company: Optional[str] = Form(None),
    job_title: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    profile_photo_url: Optional[str] = Form(None),
    linkedin_url: Optional[str] = Form(None),
    twitter_handle: Optional[str] = Form(None),
    github_username: Optional[str] = Form(None),
    website_url: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    tag_list = [t.strip() for t in (tags or "").split(",") if t.strip()]
    data = ContactCreate(
        full_name=full_name,
        email=email or None,
        phone=phone or None,
        company=company or None,
        job_title=job_title or None,
        notes=notes or None,
        profile_photo_url=profile_photo_url or None,
        linkedin_url=linkedin_url or None,
        twitter_handle=twitter_handle or None,
        github_username=github_username or None,
        website_url=website_url or None,
        location=location or None,
        tags=tag_list,
    )
    contact = crud_contacts.create_contact(db, data)
    flash(request, f"Contact '{contact.full_name}' created successfully.")
    return RedirectResponse(url=f"/contacts/{contact.id}", status_code=303)


@router.get("/contacts/{contact_id}", response_class=HTMLResponse)
def contact_detail(request: Request, contact_id: int, db: Session = Depends(get_db)):
    contact = crud_contacts.get_contact(db, contact_id)
    if not contact:
        return RedirectResponse(url="/contacts", status_code=302)
    interactions = crud_interactions.get_interactions(db, contact_id)
    followups = crud_followups.get_followups(db, contact_id)
    return templates.TemplateResponse(
        "contacts/detail.html",
        {
            "request": request,
            "contact": contact,
            "interactions": interactions,
            "followups": followups,
            "today": date.today(),
        },
    )


@router.get("/contacts/{contact_id}/edit", response_class=HTMLResponse)
def contact_edit_form(request: Request, contact_id: int, db: Session = Depends(get_db)):
    contact = crud_contacts.get_contact(db, contact_id)
    if not contact:
        return RedirectResponse(url="/contacts", status_code=302)
    all_tags = crud_tags.get_tags(db)
    return templates.TemplateResponse(
        "contacts/edit.html",
        {"request": request, "contact": contact, "all_tags": all_tags},
    )


@router.post("/contacts/{contact_id}/edit")
async def contact_update(
    request: Request,
    contact_id: int,
    full_name: str = Form(...),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    company: Optional[str] = Form(None),
    job_title: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    profile_photo_url: Optional[str] = Form(None),
    linkedin_url: Optional[str] = Form(None),
    twitter_handle: Optional[str] = Form(None),
    github_username: Optional[str] = Form(None),
    website_url: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    contact = crud_contacts.get_contact(db, contact_id)
    if not contact:
        return RedirectResponse(url="/contacts", status_code=302)
    tag_list = [t.strip() for t in (tags or "").split(",") if t.strip()]
    data = ContactUpdate(
        full_name=full_name,
        email=email or None,
        phone=phone or None,
        company=company or None,
        job_title=job_title or None,
        notes=notes or None,
        profile_photo_url=profile_photo_url or None,
        linkedin_url=linkedin_url or None,
        twitter_handle=twitter_handle or None,
        github_username=github_username or None,
        website_url=website_url or None,
        location=location or None,
        tags=tag_list,
    )
    crud_contacts.update_contact(db, contact, data)
    flash(request, f"Contact '{contact.full_name}' updated successfully.")
    return RedirectResponse(url=f"/contacts/{contact_id}", status_code=303)


@router.post("/contacts/{contact_id}/delete")
def contact_delete(request: Request, contact_id: int, db: Session = Depends(get_db)):
    contact = crud_contacts.get_contact(db, contact_id)
    if contact:
        name = contact.full_name
        crud_contacts.delete_contact(db, contact)
        flash(request, f"Contact '{name}' deleted.")
    return RedirectResponse(url="/contacts", status_code=303)


@router.post("/contacts/{contact_id}/interactions")
async def add_interaction_web(
    request: Request,
    contact_id: int,
    type: str = Form("note"),
    summary: str = Form(...),
    db: Session = Depends(get_db),
):
    contact = crud_contacts.get_contact(db, contact_id)
    if not contact:
        return RedirectResponse(url="/contacts", status_code=302)
    data = InteractionCreate(type=type, summary=summary)
    crud_interactions.create_interaction(db, contact_id, data)
    crud_contacts.update_last_contacted(db, contact)
    flash(request, "Interaction logged.")
    return RedirectResponse(url=f"/contacts/{contact_id}", status_code=303)


@router.post("/contacts/{contact_id}/followups")
async def add_followup_web(
    request: Request,
    contact_id: int,
    description: str = Form(...),
    due_date: date = Form(...),
    db: Session = Depends(get_db),
):
    contact = crud_contacts.get_contact(db, contact_id)
    if not contact:
        return RedirectResponse(url="/contacts", status_code=302)
    data = FollowUpCreate(description=description, due_date=due_date)
    crud_followups.create_followup(db, contact_id, data)
    flash(request, "Follow-up added.")
    return RedirectResponse(url=f"/contacts/{contact_id}", status_code=303)


@router.get("/followups", response_class=HTMLResponse)
def followups_list(request: Request, db: Session = Depends(get_db)):
    overdue = crud_followups.get_all_followups(db, overdue_only=True)
    upcoming = crud_followups.get_upcoming_followups(db, days=7)
    all_open = crud_followups.get_all_followups(db)
    completed = crud_followups.get_all_followups(db, completed=True)
    return templates.TemplateResponse(
        "followups/list.html",
        {
            "request": request,
            "overdue": overdue,
            "upcoming": upcoming,
            "all_open": all_open,
            "completed": completed,
            "today": date.today(),
        },
    )


@router.post("/followups/{followup_id}/complete")
def complete_followup_web(request: Request, followup_id: int, db: Session = Depends(get_db)):
    crud_followups.complete_followup(db, followup_id)
    flash(request, "Follow-up marked as complete.")
    return RedirectResponse(url="/followups", status_code=303)
