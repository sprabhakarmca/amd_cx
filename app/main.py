from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from app.api import feedback, chat, categories, review, knowledge, observability
from config.settings import settings
import os

settings.validate()

app = FastAPI(
    title="Feedback System API",
    description="LangGraph-powered feedback collection and analysis system",
    version="1.0.0"
)

BASE_DIR = Path(__file__).parent
static_dir = BASE_DIR / "static"

app.include_router(feedback.router)
app.include_router(chat.router)
app.include_router(categories.router)
app.include_router(review.router)
app.include_router(knowledge.router)
app.include_router(observability.router)

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def root():
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "Feedback System API is running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)