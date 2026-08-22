"""FastAPI application entry point for SuperApp."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from superapp.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Verify Ollama connection on startup
    import ollama

    try:
        client = ollama.Client(host=settings.ollama_host)
        client.list()
        print(f"✅ Connected to Ollama at {settings.ollama_host}")
    except Exception as e:
        print(f"⚠️  Could not connect to Ollama at {settings.ollama_host}: {e}")
        print("   Make sure Ollama is running: ollama serve")

    yield


app = FastAPI(
    title="SuperApp",
    description="The Negative-Space & Contradiction Engine",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount static files and templates
base_dir = os.path.dirname(os.path.abspath(__file__))
dashboard_dir = os.path.join(base_dir, "dashboard")

app.mount(
    "/static",
    StaticFiles(directory=os.path.join(dashboard_dir, "static")),
    name="static",
)

templates = Jinja2Templates(directory=os.path.join(dashboard_dir, "templates"))

# Import and include API routes
from superapp.api.routes import router as api_router  # noqa: E402
from superapp.api.routes import ui_router  # noqa: E402

app.include_router(api_router, prefix="/api", tags=["api"])
app.include_router(ui_router, tags=["ui"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=True)
