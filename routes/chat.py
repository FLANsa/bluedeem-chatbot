"""Chat API route for web UI testing."""
# Load environment variables FIRST
from dotenv import load_dotenv
load_dotenv()

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from core.router import Router
from pathlib import Path

router = APIRouter()

# Initialize router
chat_router = Router()


class ChatRequest(BaseModel):
    """Chat request model."""
    user_id: str
    platform: str
    message: str


class ChatResponse(BaseModel):
    """Chat response model."""
    response: str


@router.get("/ui", response_class=HTMLResponse)
async def chat_ui():
    """Serve chat UI."""
    html_path = Path(__file__).parent.parent / "static" / "index.html"
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="UI file not found")
    
    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@router.post("/api/chat", response_model=ChatResponse)
async def chat_api(request: ChatRequest):
    """
    Chat API endpoint for web UI.
    
    Args:
        request: Chat request with user_id, platform, and message
        
    Returns:
        Chat response with bot message
    """
    import logging
    import traceback
    
    try:
        response_text = chat_router.process(
            user_id=request.user_id,
            platform=request.platform,
            message=request.message
        )
        
        return ChatResponse(response=response_text)
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        error_detail = traceback.format_exc()
        logger.error(f"Error in chat_api: {str(e)}\n{error_detail}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing message: {str(e)}"
        )


@router.options("/api/chat")
async def chat_api_options():
    """Handle CORS preflight requests."""
    from fastapi import Response
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        }
    )

