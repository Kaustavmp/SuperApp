import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from superapp.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    provider_name = settings.llm_provider
    try:
        if provider_name == "ollama":
            import ollama

            client = ollama.Client(host=settings.ollama_host)
            client.list()
            print(f"✅ Connected to Ollama at {settings.ollama_host}")
        else:
            print(f"✅ LLM provider configured: {provider_name}")
    except Exception as e:
        label = "Ollama" if provider_name == "ollama" else provider_name.title()
        print(f"⚠️  Could not connect to {label}: {e}")

    yield


app = FastAPI(
    title="SuperApp",
    description="SuperApp - Document analysis, coverage gaps, and contradiction detection platform",
    version="1.0.0",
    lifespan=lifespan,
)

base_dir = os.path.dirname(os.path.abspath(__file__))
dashboard_dir = os.path.join(base_dir, "dashboard")

app.mount(
    "/static",
    StaticFiles(directory=os.path.join(dashboard_dir, "static")),
    name="static",
)

templates = Jinja2Templates(directory=os.path.join(dashboard_dir, "templates"))

from superapp.api.routes import router as api_router  # noqa: E402
from superapp.api.routes import ui_router  # noqa: E402

app.include_router(api_router, prefix="/api", tags=["api"])
app.include_router(ui_router, tags=["ui"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=settings.debug)
