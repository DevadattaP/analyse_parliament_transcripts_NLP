from fastapi import APIRouter, UploadFile, File, Form, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import os
from typing import Optional

router = APIRouter(prefix="/upload", tags=["upload"])

# Initialize templates
templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

@router.get("/", response_class=HTMLResponse)
async def upload_page(request: Request):
    """Serve the upload page"""
    # Try to serve static upload.html first
    static_dir = Path(__file__).parent.parent / "static"
    upload_html = static_dir / "upload.html"
    
    if upload_html.exists():
        with open(upload_html, 'r', encoding='utf-8') as f:
            return HTMLResponse(content=f.read())
    
    # Fallback to template if static file doesn't exist
    return templates.TemplateResponse("upload.html", {"request": request})

@router.post("/")
async def handle_upload(
    request: Request,
    file: UploadFile = File(...)
):
    """Handle file upload from web form"""
    try:
        # Save the file temporarily
        uploads_dir = Path("data/uploads")
        uploads_dir.mkdir(exist_ok=True, parents=True)
        
        # Generate unique filename
        import uuid
        file_id = str(uuid.uuid4())
        file_ext = Path(file.filename).suffix
        filename = f"{file_id}{file_ext}"
        file_path = uploads_dir / filename
        
        # Save file
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Create processing request (similar to documents endpoint)
        
        # Return success response
        return {
            "success": True,
            "document_id": file_id,
            "message": "Document uploaded successfully",
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }