"""WhatsApp message formatting utilities."""
import re
from typing import List, Dict, Any


def format_whatsapp_text(text: str) -> str:
    """
    Format text for WhatsApp with proper formatting.
    
    WhatsApp supports:
    - *bold* for bold text
    - _italic_ for italic text
    - ~strikethrough~ for strikethrough
    - ```monospace``` for monospace
    
    Args:
        text: Plain text to format
        
    Returns:
        Formatted text with WhatsApp formatting
    """
    if not text:
        return text
    
    # Don't format if already formatted
    if '*' in text or '_' in text:
        return text
    
    lines = text.split('\n')
    formatted_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            formatted_lines.append('')
            continue
        
        # Format titles (lines ending with :)
        if line.endswith(':'):
            formatted_lines.append(f"*{line}*")
        # Format numbered lists (1. 2. etc.)
        elif re.match(r'^\d+\.', line):
            formatted_lines.append(line)
        # Format emoji lines (lines starting with emoji)
        elif line.startswith(('✅', '📍', '⏰', '💰', '⚠️', '⭐', '🏥')):
            formatted_lines.append(line)
        # Format doctor/service names (lines with "د." or "دكتورة")
        elif 'د.' in line or 'دكتورة' in line or 'دكتور' in line:
            # Bold the name part
            parts = re.split(r'(د\.?\s*[^،\n]+|دكتورة\s+[^،\n]+|دكتور\s+[^،\n]+)', line)
            formatted = ''
            for i, part in enumerate(parts):
                if re.match(r'د\.?\s*[^،\n]+|دكتورة\s+[^،\n]+|دكتور\s+[^،\n]+', part):
                    formatted += f"*{part}*"
                else:
                    formatted += part
            formatted_lines.append(formatted)
        else:
            formatted_lines.append(line)
    
    return '\n'.join(formatted_lines)


def format_list_for_whatsapp(items: List[str], title: str = "") -> str:
    """
    Format a list for WhatsApp with proper formatting.
    
    Args:
        items: List of items
        title: Optional title for the list
        
    Returns:
        Formatted list text
    """
    if not items:
        return "ما لقيت شي"
    
    formatted = []
    if title:
        formatted.append(f"*{title}*")
        formatted.append("")
    
    for i, item in enumerate(items, 1):
        formatted.append(f"{i}. {item}")
    
    return '\n'.join(formatted)


def format_doctor_info_for_whatsapp(doctor: Dict[str, Any]) -> str:
    """
    Format doctor information for WhatsApp.
    
    Args:
        doctor: Doctor dictionary
        
    Returns:
        Formatted doctor info text
    """
    parts = []
    
    name = doctor.get('doctor_name', '')
    if name:
        parts.append(f"*{name}*")
    
    specialty = doctor.get('specialty', '')
    if specialty:
        parts.append(f"التخصص: {specialty}")
    
    branch_id = doctor.get('branch_id', '')
    if branch_id:
        parts.append(f"📍 الفرع: {branch_id}")
    
    days = doctor.get('days', '')
    if days:
        parts.append(f"⏰ الدوام: {days}")
    
    time_from = doctor.get('time_from', '')
    time_to = doctor.get('time_to', '')
    if time_from and time_to:
        parts.append(f"⏰ الوقت: {time_from} - {time_to}")
    
    return '\n'.join(parts) if parts else "ما لقيت معلومات"


def format_service_info_for_whatsapp(service: Dict[str, Any]) -> str:
    """
    Format service information for WhatsApp.
    
    Args:
        service: Service dictionary
        
    Returns:
        Formatted service info text
    """
    parts = []
    
    name = service.get('service_name', '')
    if name:
        parts.append(f"*{name}*")
    
    description = service.get('description', '')
    if description:
        parts.append(description)
    
    price_sar = service.get('price_sar', '')
    if price_sar:
        parts.append(f"💰 السعر: {price_sar} ريال")
    
    duration = service.get('duration_minutes', '')
    if duration:
        parts.append(f"⏰ المدة: {duration} دقيقة")
    
    return '\n'.join(parts) if parts else "ما لقيت معلومات"

