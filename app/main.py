from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.database import init_db
from app.api import router as api_router

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB & pre-generate library questions on startup
    init_db()
    yield


app = FastAPI(
    title="BlackBox Arena",
    description="CodeDecode-style black-box coding practice arena.",
    lifespan=lifespan
)

# Include API endpoints
app.include_router(api_router)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index():
    """Serve the single-page application shell."""
    if (BASE_DIR / "index.html").exists():
        return FileResponse(str(BASE_DIR / "index.html"))
    return FileResponse(str(STATIC_DIR / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
