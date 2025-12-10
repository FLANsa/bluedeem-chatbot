"""Saudi phone number validation and normalization."""
import re
from typing import Optional


SAUDI_PHONE_PATTERN = re.compile(r'^(?:\+966|00966|966|0)?5\d{8}$')


def normalize_phone(phone: str) -> Optional[str]:
    """
    Normalize Saudi phone number to format: 05XXXXXXXX
    
    Args:
        phone: Phone number string
        
    Returns:
        Normalized phone number or None if invalid
    """
    if not phone:
        return None
    
    # Remove all non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', phone.strip())
    
    # Remove country code prefixes
    if cleaned.startswith('+966'):
        cleaned = '0' + cleaned[4:]
    elif cleaned.startswith('00966'):
        cleaned = '0' + cleaned[5:]
    elif cleaned.startswith('966'):
        cleaned = '0' + cleaned[3:]
    
    # Ensure starts with 0
    if not cleaned.startswith('0'):
        cleaned = '0' + cleaned
    
    # Validate format
    if SAUDI_PHONE_PATTERN.match(cleaned):
        return cleaned
    
    return None


def validate_phone(phone: str) -> bool:
    """
    Validate Saudi phone number.
    
    Args:
        phone: Phone number string
        
    Returns:
        True if valid, False otherwise
    """
    normalized = normalize_phone(phone)
    return normalized is not None

