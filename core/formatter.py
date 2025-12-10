"""Response formatter with Najdi dialect templates."""
from typing import Dict, Any


def format_booking_confirmation() -> str:
    """Format booking confirmation message."""
    return "✅ تم استلام طلبك وبنرجع لك نأكد الموعد"


def format_booking_question(state: str, data: Dict[str, Any]) -> str:
    """Format booking question based on state - keep it simple and direct."""
    if state == "name":
        return "ما اسمك؟"
    elif state == "phone":
        name = data.get("name", "")
        if name:
            return f"مرحباً {name}! ما رقم جوالك؟"
        return "ما رقم جوالك؟"
    elif state == "service":
        return "أي خدمة تبي تحجز؟"
    elif state == "branch":
        return "أي فرع تفضل؟ (أو اكتب 'تخطى' للتخطي)"
    elif state == "date_time":
        return "متى تبي الموعد؟ (أو اكتب 'تخطى' للتخطي)"
    else:
        return "شكراً لك!"

