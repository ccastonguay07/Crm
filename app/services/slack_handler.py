"""Slack Bolt app — handles DMs, mentions, and /crm slash command."""
import logging
import re
from datetime import datetime, timedelta

from slack_bolt import App

from app.config import get_settings
from app.crud.contacts import get_all_contact_names, get_contacts, find_contact_by_name
from app.database import SessionLocal
from app.services import claude_parser, contact_service

logger = logging.getLogger(__name__)

settings = get_settings()

# Build the App only when tokens are present.
if settings.slack_bot_token and settings.slack_signing_secret:
    slack_app = App(
        token=settings.slack_bot_token,
        signing_secret=settings.slack_signing_secret,
    )
    _event = slack_app.event
    _command = slack_app.command
else:
    slack_app = None
    def _event(name):       # no-op decorator
        return lambda f: f
    def _command(name):     # no-op decorator
        return lambda f: f

HELP_TEXT = (
    "*Personal CRM Bot* — talk to me naturally!\n\n"
    "*Examples (DM me):*\n"
    "• `Add Jane Doe, works at Stripe, email jane@stripe.com`\n"
    "• `Met John today at the conference — he's interested in the API`\n"
    "• `Update Sarah Chen — new title: VP Engineering`\n"
    "• `Remind me to follow up with John next Tuesday`\n"
    "• `Add note to Jane: she prefers async communication`\n"
    "• `Show me all contacts at Google`\n"
    "• `Who do I know at Y Combinator?`\n\n"
    "*Slash command:*\n"
    "• `/crm show Jane Doe` — quick profile card\n"
    "• `/crm search Google` — search contacts\n"
    "• `/crm reconnect` — contacts you haven't talked to in a while\n"
    "• `/crm help` — show this message\n\n"
    f"Web UI: {settings.web_base_url}"
)


def _build_reply(result: dict, contact) -> str:
    """Format the bot's response message."""
    msg = result["message"]

    if contact and result["action"] in ("created", "updated", "interaction_logged", "followup_added"):
        profile_url = f"{settings.web_base_url}/contacts/{contact.id}"
        msg += f"\n<{profile_url}|View profile>"

    return msg


@_event("message")
def handle_message(body, say, logger):
    event = body.get("event", {})

    # Ignore bot messages and non-DM subtypes
    if event.get("bot_id") or event.get("subtype"):
        return

    # Only handle DMs (channel_type == 'im') or direct mentions
    channel_type = event.get("channel_type", "")
    text = event.get("text", "").strip()

    if not text:
        return

    if text.lower() in ("help", "?", "/help"):
        say(HELP_TEXT)
        return

    logger.info(f"Slack message received: {text[:100]}")

    with SessionLocal() as db:
        known_names = get_all_contact_names(db)
        try:
            parsed = claude_parser.parse_slack_message(text, known_names)
        except Exception as e:
            logger.error(f"Claude parse error: {e}")
            say("Sorry, I had trouble understanding that. Please try again.")
            return

        try:
            result = contact_service.apply_parsed_intent(db, parsed, raw_text=text)
        except Exception as e:
            logger.error(f"Contact service error: {e}")
            say("Something went wrong while updating your CRM. Please try again.")
            return

    contact = result.get("contact")
    reply = _build_reply(result, contact)
    say(reply)


@_event("app_mention")
def handle_mention(body, say, logger):
    """Strip the bot mention and re-use the DM handler logic."""
    event = body.get("event", {})
    text = event.get("text", "")
    text = re.sub(r"<@[A-Z0-9]+>", "", text).strip()

    if not text or text.lower() in ("help", "?"):
        say(HELP_TEXT)
        return

    body["event"]["text"] = text
    body["event"]["channel_type"] = "im"
    handle_message(body, say, logger)


# ---------------------------------------------------------------------------
# /crm slash command
# ---------------------------------------------------------------------------

@_command("/crm")
def handle_crm_command(ack, respond, command, logger):
    ack()
    text = (command.get("text") or "").strip()
    parts = text.split(None, 1)
    subcommand = parts[0].lower() if parts else "help"
    arg = parts[1].strip() if len(parts) > 1 else ""

    if subcommand in ("help", ""):
        respond(HELP_TEXT)
        return

    with SessionLocal() as db:
        if subcommand == "show":
            if not arg:
                respond("Usage: `/crm show <name>`")
                return
            contact = find_contact_by_name(db, arg)
            if not contact:
                respond(f"No contact found matching *{arg}*.")
                return
            respond(blocks=_contact_profile_blocks(contact))

        elif subcommand == "search":
            if not arg:
                respond("Usage: `/crm search <term>`")
                return
            contacts = get_contacts(db, search=arg, limit=8)
            if not contacts:
                respond(f"No contacts found for *{arg}*.")
                return
            lines = [f"• *<{settings.web_base_url}/contacts/{c.id}|{c.full_name}>*"
                     + (f" — {c.company}" if c.company else "")
                     + (f", {c.job_title}" if c.job_title else "")
                     for c in contacts]
            respond(f"Found {len(contacts)} contact(s) for *{arg}*:\n" + "\n".join(lines))

        elif subcommand == "reconnect":
            cutoff = datetime.utcnow() - timedelta(days=30)
            all_contacts = get_contacts(db, limit=10000)
            stale = [
                c for c in all_contacts
                if not c.last_contacted_at or c.last_contacted_at < cutoff
            ]
            stale.sort(key=lambda c: c.last_contacted_at or datetime.min)
            if not stale:
                respond(":white_check_mark: You're all caught up — no reconnects needed!")
                return
            lines = []
            for c in stale[:10]:
                if c.last_contacted_at:
                    days = (datetime.utcnow() - c.last_contacted_at).days
                    lines.append(f"• *<{settings.web_base_url}/contacts/{c.id}|{c.full_name}>* — {days} days ago")
                else:
                    lines.append(f"• *<{settings.web_base_url}/contacts/{c.id}|{c.full_name}>* — never contacted")
            respond(f":wave: *{len(stale)} contact(s) to reconnect with:*\n" + "\n".join(lines))

        else:
            respond(f"Unknown subcommand `{subcommand}`. Try `/crm help`.")


def _contact_profile_blocks(contact) -> list:
    """Build a Slack Block Kit profile card for a contact."""
    title_line = " | ".join(filter(None, [contact.job_title, contact.company]))
    details = []
    if contact.email:
        details.append(f":email: {contact.email}")
    if contact.phone:
        details.append(f":phone: {contact.phone}")
    if contact.location:
        details.append(f":round_pushpin: {contact.location}")
    if contact.last_contacted_at:
        details.append(f":calendar: Last contacted {contact.last_contacted_at.strftime('%b %d, %Y')}")
    if contact.tags:
        details.append(":label: " + ", ".join(t.name for t in contact.tags))

    text = f"*<{settings.web_base_url}/contacts/{contact.id}|{contact.full_name}>*"
    if title_line:
        text += f"\n{title_line}"
    if details:
        text += "\n" + " · ".join(details)

    return [{"type": "section", "text": {"type": "mrkdwn", "text": text}}]
