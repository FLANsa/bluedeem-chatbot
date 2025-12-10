"""Webhook routes for platforms."""
from fastapi import APIRouter, Request, HTTPException, status, Query
from typing import Optional
import json
from core.router import Router
from platforms.whatsapp import WhatsAppHandler
from platforms.instagram import InstagramHandler
from platforms.tiktok import TikTokHandler
from middleware.rate_limit import rate_limiter
from middleware.logging import log_request, generate_request_id
from middleware.security import verify_webhook_signature
from models.booking import ProcessedMessage
from data.db import get_database_session

router = APIRouter()

# Platform handlers
whatsapp_handler = WhatsAppHandler()
instagram_handler = InstagramHandler()
tiktok_handler = TikTokHandler()

# Router
chat_router = Router()


def check_message_dedupe(platform: str, message_id: str) -> bool:
    """
    Check if message was already processed.
    
    Returns:
        True if already processed, False otherwise
    """
    if not message_id:
        return False
    
    db = get_database_session()
    existing = db.query(ProcessedMessage).filter(
        ProcessedMessage.platform == platform,
        ProcessedMessage.message_id == message_id
    ).first()
    
    if existing:
        return True
    
    # Mark as processed
    processed = ProcessedMessage(
        platform=platform,
        message_id=message_id
    )
    db.add(processed)
    db.commit()
    return False


@router.get("/webhook/whatsapp")
async def whatsapp_webhook_verify(
    mode: str = Query(...),
    token: str = Query(...),
    challenge: str = Query(...)
):
    """WhatsApp webhook verification (GET)."""
    result = whatsapp_handler.verify_webhook(mode, token, challenge)
    if result:
        return int(challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """WhatsApp webhook handler (POST)."""
    request_id = generate_request_id()
    
    try:
        # Verify signature (optional - can be disabled in development)
        # verify_webhook_signature(request, whatsapp_handler)
        
        # Parse request
        body = await request.json()
        user_id, message_text, metadata = whatsapp_handler.parse_incoming(body)
        
        if not user_id or not message_text:
            return {"status": "ok"}  # Ignore non-message events
        
        # Check dedupe
        message_id = metadata.get("message_id", "")
        if check_message_dedupe("whatsapp", message_id):
            return {"status": "ok", "message": "already_processed"}
        
        # Rate limiting
        if not rate_limiter.is_allowed(user_id):
            response_text = "⚠️ كثرة الرسائل. انتظر شوي."
            whatsapp_handler.send_outgoing(user_id, response_text)
            return {"status": "ok", "rate_limited": True}
        
        # Process message
        response_text = chat_router.process(user_id, "whatsapp", message_text)
        
        # Send response
        whatsapp_handler.send_outgoing(user_id, response_text, metadata)
        
        # Log
        log_request(request_id, user_id, "whatsapp", message_text, response_text, metadata)
        
        return {"status": "ok"}
        
    except Exception as e:
        log_request(request_id, "unknown", "whatsapp", "", "", {"error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook/instagram")
async def instagram_webhook(request: Request):
    """Instagram webhook handler (POST)."""
    request_id = generate_request_id()
    
    try:
        body = await request.json()
        user_id, message_text, metadata = instagram_handler.parse_incoming(body)
        
        if not user_id or not message_text:
            return {"status": "ok"}
        
        # Check dedupe
        message_id = metadata.get("message_id", "")
        if check_message_dedupe("instagram", message_id):
            return {"status": "ok", "message": "already_processed"}
        
        # Rate limiting
        if not rate_limiter.is_allowed(user_id):
            response_text = "⚠️ كثرة الرسائل. انتظر شوي."
            instagram_handler.send_outgoing(user_id, response_text)
            return {"status": "ok", "rate_limited": True}
        
        # Process message
        response_text = chat_router.process(user_id, "instagram", message_text)
        
        # Send response
        instagram_handler.send_outgoing(user_id, response_text, metadata)
        
        # Log
        log_request(request_id, user_id, "instagram", message_text, response_text, metadata)
        
        return {"status": "ok"}
        
    except Exception as e:
        log_request(request_id, "unknown", "instagram", "", "", {"error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook/tiktok")
async def tiktok_webhook(request: Request):
    """TikTok webhook handler (POST)."""
    request_id = generate_request_id()
    
    try:
        body = await request.json()
        user_id, message_text, metadata = tiktok_handler.parse_incoming(body)
        
        if not user_id or not message_text:
            return {"status": "ok"}
        
        # Check dedupe
        message_id = metadata.get("message_id", "")
        if check_message_dedupe("tiktok", message_id):
            return {"status": "ok", "message": "already_processed"}
        
        # Rate limiting
        if not rate_limiter.is_allowed(user_id):
            response_text = "⚠️ كثرة الرسائل. انتظر شوي."
            tiktok_handler.send_outgoing(user_id, response_text)
            return {"status": "ok", "rate_limited": True}
        
        # Process message
        response_text = chat_router.process(user_id, "tiktok", message_text)
        
        # Send response
        tiktok_handler.send_outgoing(user_id, response_text, metadata)
        
        # Log
        log_request(request_id, user_id, "tiktok", message_text, response_text, metadata)
        
        return {"status": "ok"}
        
    except Exception as e:
        log_request(request_id, "unknown", "tiktok", "", "", {"error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))

