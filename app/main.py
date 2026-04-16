import subprocess
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.routers import contacts, interactions, followups, web

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run database migrations on startup
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
    yield


app = FastAPI(title="Personal CRM", lifespan=lifespan)

app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(web.router)
app.include_router(contacts.router)
app.include_router(interactions.router)
app.include_router(followups.router)
