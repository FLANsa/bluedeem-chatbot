"""Security middleware for webhook verification."""
from typing import Optional
from fastapi import Request, HTTPException, status


def verify_webhook_signature(
    request: Request,
    platform_handler,
    signature_header: str = "X-Hub-Signature-256"
) -> bool:
    """
    Verify webhook signature.
    
    Args:
        request: FastAPI request
        platform_handler: Platform handler instance
        signature_header: Signature header name
        
    Returns:
        True if verified, raises HTTPException if not
    """
    signature = request.headers.get(signature_header)
    
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing signature header"
        )
    
    # Read request body
    body = request.body()
    
    # Verify signature
    if not platform_handler.verify_signature(body, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature"
        )
    
    return True

