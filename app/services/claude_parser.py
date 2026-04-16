import json
from datetime import date

import anthropic

from app.config import get_settings
from app.schemas.slack_parse import ParsedIntent

SYSTEM_PROMPT = """You are a personal CRM assistant that parses natural language messages into structured data.

Return ONLY a valid JSON object with this exact schema:
{{
  "intent": "<one of: create_contact, update_contact, add_note, log_interaction, add_followup, query, unknown>",
  "contact_name": "<full name string or null>",
  "fields_to_update": {{
    "email": "<string or null>",
    "phone": "<string or null>",
    "company": "<string or null>",
    "job_title": "<string or null>",
    "linkedin_url": "<string or null>",
    "twitter_handle": "<string or null>",
    "github_username": "<string or null>",
    "website_url": "<string or null>",
    "location": "<string or null>",
    "notes": "<string or null>"
  }},
  "note_text": "<string or null>",
  "interaction": {{
    "type": "<one of: meeting, call, email, slack, note, other — or null>",
    "summary": "<string or null>",
    "occurred_at": "<ISO8601 datetime string or null>"
  }},
  "followup": {{
    "description": "<string or null>",
    "due_date": "<ISO8601 date string or null>"
  }},
  "tags": ["<string>"],
  "query_filter": {{
    "company": "<string or null>",
    "tag": "<string or null>",
    "search_term": "<string or null>"
  }},
  "confidence": <float 0.0-1.0>,
  "clarification_needed": "<string or null>"
}}

Rules:
- Today's date is {today}. Resolve relative dates ("next week", "tomorrow", "in 3 days") to absolute ISO dates.
- Known contacts: {known_contacts}
- Only populate fields_to_update for fields explicitly mentioned. Do not infer.
- If you cannot identify a contact name, set contact_name to null and set clarification_needed.
- For queries like "show me contacts at Google" or "who do I know at Google", use intent=query.
- If the message creates a contact AND adds a note or interaction, use intent=create_contact and include all data.
- Interaction types: meeting (in-person/video), call (phone), email, slack (chat), note (written note), other.
- Return ONLY the JSON object, no markdown, no explanation.
"""


def parse_slack_message(text: str, known_contact_names: list[str]) -> ParsedIntent:
    settings = get_settings()
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    today_str = date.today().isoformat()
    known_str = ", ".join(known_contact_names[:50]) if known_contact_names else "none yet"

    system = SYSTEM_PROMPT.format(today=today_str, known_contacts=known_str)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": text}],
        )
        raw = response.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        return ParsedIntent(**data)
    except Exception as e:
        return ParsedIntent(
            intent="unknown",
            confidence=0.0,
            clarification_needed=f"I couldn't parse that message (error: {type(e).__name__}). Please try rephrasing.",
        )
