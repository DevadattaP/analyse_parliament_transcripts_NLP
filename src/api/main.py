from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import logging
from fastapi.responses import FileResponse
from pathlib import Path
from .config import config
from .routes import upload
from .middlewares.no_cache import NoCacheMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Ministry Paragraph Classification API",
    description="Upload a parliamentary PDF and run ministry classification per paragraph.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS
origins = config.get("api.cors_origins", ["*"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(NoCacheMiddleware)

# Mount static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir, check_dir=not config.get("api.debug", False)), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with API information"""
    index_path = Path(__file__).parent / "static" / "index.html"

    if not index_path.exists():
        return HTMLResponse(content="index.html was not found", status_code=404)

    return FileResponse(index_path)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ministry-classification-api",
        "version": "1.0.0"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc),
            "path": request.url.path
        }
    )

app.include_router(upload.router)

if __name__ == "__main__":
    import uvicorn
    
    host = config.get("api.host", "0.0.0.0")
    port = config.get("api.port", 8000)
    reload = config.get("api.reload", True)
    
    logger.info(f"🌐 Starting server on {host}:{port}")
    
    uvicorn.run(
        "src.api.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )