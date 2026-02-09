from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from dotenv import load_dotenv
import logging

from app.routers import upload, api_fetch, danlon

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Get the base directory
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

app = FastAPI(
    title="Time Registration CSV Parser",
    description="Parse and process time registration CSV files with overtime calculations based on Danish automotive industry rules (DBR/Industriens Overenskomst 2026)",
    version="1.0.0"
)

# Include routers
app.include_router(upload.router)
app.include_router(api_fetch.router)
app.include_router(danlon.router)

# Mount static files from the built frontend (only if dist exists)
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")
    
    @app.get("/", response_class=FileResponse)
    async def home():
        """Serve the React app."""
        return FileResponse(str(FRONTEND_DIST / "index.html"))
else:
    @app.get("/")
    async def home():
        """Development message when frontend is not built."""
        return {
            "message": "Frontend not built yet. Run 'cd frontend && npm run build' to build the frontend.",
            "dev_server": "For development, run 'cd frontend && npm run dev' in a separate terminal."
        }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Time Registration CSV Parser"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
