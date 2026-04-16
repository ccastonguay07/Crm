"""Slack Bolt app — handles DMs and mentions, parses them via Claude, updates the CRM."""
import logging

from slack_bolt import App

from app.config import get_settings
from app.crud.contacts import get_all_contact_names
from app.database import SessionLocal
from app.services import claude_parser, contact_service

logger = logging.getLogger(__name__)

settings = get_settings()

slack_app = App(
    token=settings.slack_bot_token,
    signing_secret=settings.slack_signing_secret,
)

HELP_TEXT = (
    "*Personal CRM Bot* — talk to me naturally!\n\n"
    "*Examples:*\n"
    "• `Add Jane Doe, works at Stripe, email jane@stripe.com`\n"
    "• `Met John today at the conference — he's interested in the API`\n"
    "• `Update Sarah Chen — new title: VP Engineering`\n"
    "• `Remind me to follow up with John next Tuesday`\n"
    "• `Add note to Jane: she prefers async communication`\n"
    "• `Show me all contacts at Google`\n"
    "• `Who do I know at Y Combinator?`\n\n"
    f"View your contacts at {settings.web_base_url}"
)


def _build_reply(result: dict, contact) -> str:
    """Format the bot's response message."""
    msg = result["message"]

    if contact and result["action"] in ("created", "updated", "interaction_logged", "followup_added"):
        profile_url = f"{settings.web_base_url}/contacts/{contact.id}"
        msg += f"\n<{profile_url}|View profile>"

    return msg


@slack_app.event("message")
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


@slack_app.event("app_mention")
def handle_mention(body, say, logger):
    """Strip the bot mention and re-use the DM handler logic."""
    event = body.get("event", {})
    text = event.get("text", "")
    # Remove <@BOTID> from the text
    import re
    text = re.sub(r"<@[A-Z0-9]+>", "", text).strip()

    if not text or text.lower() in ("help", "?"):
        say(HELP_TEXT)
        return

    # Fake a minimal body for the message handler
    body["event"]["text"] = text
    body["event"]["channel_type"] = "im"
    handle_message(body, say, logger)
