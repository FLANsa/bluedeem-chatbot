"""Date parser for Arabic relative dates."""
from datetime import datetime, timedelta
from typing import Optional
import pytz
import re
import config


RIYADH_TZ = pytz.timezone(config.TIMEZONE)


# Arabic day names mapping
ARABIC_DAYS = {
    'السبت': 5, 'الاحد': 6, 'الاثنين': 0, 'الثلاثاء': 1,
    'الاربعاء': 2, 'الخميس': 3, 'الجمعة': 4,
    'سبت': 5, 'احد': 6, 'اثنين': 0, 'ثلاثاء': 1,
    'اربعاء': 2, 'خميس': 3, 'جمعة': 4
}


def get_today_riyadh() -> datetime:
    """Get current date in Riyadh timezone."""
    return datetime.now(RIYADH_TZ).date()


def parse_relative_date(text: str) -> Optional[datetime.date]:
    """
    Parse Arabic relative date expressions.
    
    Supports:
    - اليوم / اليوم
    - بكرا / بكرة
    - بعد بكرا / بعد بكرة
    - السبت الجاي / سبت الجاي
    - etc.
    
    Args:
        text: Arabic text containing date reference
        
    Returns:
        Parsed date or None if not found
    """
    if not text:
        return None
    
    text_lower = text.lower().strip()
    today = get_today_riyadh()
    
    # اليوم
    if 'اليوم' in text_lower or 'هذا اليوم' in text_lower:
        return today
    
    # بكرا / بكرة
    if 'بكرا' in text_lower or 'بكرة' in text_lower:
        if 'بعد' in text_lower:
            return today + timedelta(days=2)
        return today + timedelta(days=1)
    
    # بعد بكرا
    if 'بعد بكرا' in text_lower or 'بعد بكرة' in text_lower:
        return today + timedelta(days=2)
    
    # Day of week matching (السبت الجاي, etc.)
    for day_name, day_num in ARABIC_DAYS.items():
        if day_name in text_lower:
            # Calculate next occurrence of this day
            current_weekday = today.weekday()
            days_ahead = day_num - current_weekday
            if days_ahead <= 0:
                days_ahead += 7
            return today + timedelta(days=days_ahead)
    
    # Try to parse as date string (YYYY-MM-DD, DD/MM/YYYY, etc.)
    date_patterns = [
        r'(\d{4})-(\d{2})-(\d{2})',  # YYYY-MM-DD
        r'(\d{2})/(\d{2})/(\d{4})',  # DD/MM/YYYY
        r'(\d{2})-(\d{2})-(\d{4})',  # DD-MM-YYYY
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                if '-' in pattern:
                    if len(match.group(1)) == 4:  # YYYY-MM-DD
                        year, month, day = match.groups()
                    else:  # DD-MM-YYYY
                        day, month, year = match.groups()
                else:  # DD/MM/YYYY
                    day, month, year = match.groups()
                
                return datetime(int(year), int(month), int(day)).date()
            except ValueError:
                continue
    
    return None

