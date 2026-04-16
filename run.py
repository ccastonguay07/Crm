"""Entry point: starts the FastAPI web server, Slack socket handler, and scheduler."""
import logging
import threading

import uvicorn
from slack_bolt.adapter.socket_mode import SocketModeHandler

from app.config import get_settings
from app.services.scheduler import start_scheduler, stop_scheduler
from app.services import slack_handler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


def start_slack():
    if not slack_handler.slack_app or not settings.slack_app_token:
        logger.warning(
            "Slack tokens not configured — Slack bot disabled. "
            "Set SLACK_BOT_TOKEN, SLACK_APP_TOKEN, and SLACK_SIGNING_SECRET in .env to enable it."
        )
        return
    logger.info("Starting Slack Socket Mode handler...")
    handler = SocketModeHandler(slack_handler.slack_app, settings.slack_app_token)
    handler.start()


if __name__ == "__main__":
    slack_thread = threading.Thread(target=start_slack, daemon=True)
    slack_thread.start()

    start_scheduler()

    try:
        logger.info(f"Starting web server at http://{settings.app_host}:{settings.app_port}")
        uvicorn.run(
            "app.main:app",
            host=settings.app_host,
            port=settings.app_port,
            reload=settings.debug,
        )
    finally:
        stop_scheduler()
