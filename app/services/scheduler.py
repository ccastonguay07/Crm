"""
Scheduled jobs: daily digest, birthday reminders, reconnect reminders.
All jobs are registered here and started from run.py.
"""
import logging
from datetime import date, datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.database import SessionLocal

logger = logging.getLogger(__name__)
settings = get_settings()

_scheduler = BackgroundScheduler(timezone="UTC")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_slack_client():
    from slack_sdk import WebClient
    return WebClient(token=settings.slack_bot_token)


def _send_dm(client, text: str, blocks=None):
    """Open a DM with the bot owner and send a message."""
    if not settings.slack_owner_user_id:
        logger.warning("SLACK_OWNER_USER_ID not set — skipping scheduled notification.")
        return
    try:
        resp = client.conversations_open(users=settings.slack_owner_user_id)
        channel = resp["channel"]["id"]
        client.chat_postMessage(channel=channel, text=text, blocks=blocks)
    except Exception as e:
        logger.error(f"Failed to send scheduled DM: {e}")


# ---------------------------------------------------------------------------
# Job: Daily digest
# ---------------------------------------------------------------------------

def daily_digest():
    if not settings.slack_bot_token or not settings.slack_owner_user_id:
        return

    from app.crud.followups import get_all_followups, get_upcoming_followups
    from app.crud.contacts import get_contacts

    client = _get_slack_client()
    today = date.today()

    with SessionLocal() as db:
        overdue = get_all_followups(db, overdue_only=True)
        upcoming = get_upcoming_followups(db, days=7)

        # Reconnect: contacts not contacted in 30+ days
        all_contacts = get_contacts(db, limit=10000)
        cutoff_30 = datetime.utcnow() - timedelta(days=30)
        cutoff_60 = datetime.utcnow() - timedelta(days=60)
        cutoff_90 = datetime.utcnow() - timedelta(days=90)

        reconnect_90 = [
            c for c in all_contacts
            if c.last_contacted_at and c.last_contacted_at < cutoff_90
        ]
        reconnect_60 = [
            c for c in all_contacts
            if c.last_contacted_at and cutoff_90 <= c.last_contacted_at < cutoff_60
        ]
        reconnect_30 = [
            c for c in all_contacts
            if c.last_contacted_at and cutoff_60 <= c.last_contacted_at < cutoff_30
        ]
        never_contacted = [c for c in all_contacts if not c.last_contacted_at][:5]

        # Upcoming birthdays (next 7 days)
        birthday_contacts = []
        for c in all_contacts:
            if c.birthday:
                bday_this_year = c.birthday.replace(year=today.year)
                if today <= bday_this_year <= today + timedelta(days=7):
                    birthday_contacts.append((c, bday_this_year))

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"Good morning! CRM digest for {today.strftime('%A, %B %d')}"},
        }
    ]

    # Overdue follow-ups
    if overdue:
        lines = [f"• *<{settings.web_base_url}/contacts/{f.contact.id}|{f.contact.full_name}>* — {f.description} _(due {f.due_date})_" for f in overdue[:5]]
        if len(overdue) > 5:
            lines.append(f"_...and {len(overdue) - 5} more_")
        blocks += [
            {"type": "section", "text": {"type": "mrkdwn", "text": f":red_circle: *{len(overdue)} overdue follow-up(s)*\n" + "\n".join(lines)}},
            {"type": "divider"},
        ]

    # Upcoming follow-ups
    if upcoming:
        lines = [f"• *<{settings.web_base_url}/contacts/{f.contact.id}|{f.contact.full_name}>* — {f.description} _(due {f.due_date})_" for f in upcoming[:5]]
        blocks += [
            {"type": "section", "text": {"type": "mrkdwn", "text": f":calendar: *{len(upcoming)} follow-up(s) this week*\n" + "\n".join(lines)}},
            {"type": "divider"},
        ]

    # Birthdays
    if birthday_contacts:
        lines = []
        for c, bday in birthday_contacts:
            days_until = (bday - today).days
            suffix = "Today! :birthday:" if days_until == 0 else f"in {days_until} day(s)"
            lines.append(f"• *<{settings.web_base_url}/contacts/{c.id}|{c.full_name}>* — {suffix}")
        blocks += [
            {"type": "section", "text": {"type": "mrkdwn", "text": ":cake: *Upcoming birthdays*\n" + "\n".join(lines)}},
            {"type": "divider"},
        ]

    # Reconnect suggestions
    reconnect_lines = []
    for c in reconnect_90[:3]:
        days = (datetime.utcnow() - c.last_contacted_at).days
        reconnect_lines.append(f"• *<{settings.web_base_url}/contacts/{c.id}|{c.full_name}>* — {days} days ago")
    for c in reconnect_60[:2]:
        days = (datetime.utcnow() - c.last_contacted_at).days
        reconnect_lines.append(f"• *<{settings.web_base_url}/contacts/{c.id}|{c.full_name}>* — {days} days ago")
    if never_contacted:
        for c in never_contacted[:2]:
            reconnect_lines.append(f"• *<{settings.web_base_url}/contacts/{c.id}|{c.full_name}>* — never contacted")

    if reconnect_lines:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": ":wave: *Time to reconnect*\n" + "\n".join(reconnect_lines)},
        })

    if len(blocks) == 1:
        # Only the header — nothing to report
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": ":white_check_mark: All caught up! No follow-ups or reconnects needed today."},
        })

    _send_dm(client, text=f"CRM digest for {today}", blocks=blocks)
    logger.info("Daily digest sent.")


# ---------------------------------------------------------------------------
# Scheduler setup
# ---------------------------------------------------------------------------

def start_scheduler():
    if not settings.slack_bot_token:
        logger.info("Slack not configured — scheduler disabled.")
        return

    digest_hour, digest_minute = _parse_digest_time(settings.digest_time)

    _scheduler.add_job(
        daily_digest,
        CronTrigger(hour=digest_hour, minute=digest_minute),
        id="daily_digest",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    _scheduler.start()
    logger.info(f"Scheduler started. Daily digest at {settings.digest_time} UTC.")


def stop_scheduler():
    if _scheduler.running:
        _scheduler.shutdown(wait=False)


def _parse_digest_time(time_str: str) -> tuple[int, int]:
    """Parse 'HH:MM' into (hour, minute), defaulting to 09:00."""
    try:
        h, m = time_str.split(":")
        return int(h), int(m)
    except Exception:
        return 9, 0
