"""Booking state machine."""
from typing import Dict, Any, Optional
from datetime import datetime
import json
import httpx
from models.booking import BookingTicket, ConversationState
from data.db import get_database_session
from utils.phone import validate_phone, normalize_phone
from utils.date_parser import parse_relative_date
import os
from core.formatter import format_booking_question, format_booking_confirmation


class BookingManager:
    """Booking state machine manager."""
    
    STATES = ["name", "phone", "service", "branch", "date_time", "done"]
    
    def __init__(self):
        """Initialize booking manager."""
        self.db = get_database_session()
    
    def get_state(self, user_id: str, platform: str) -> Optional[ConversationState]:
        """Get current booking state."""
        return self.db.query(ConversationState).filter(
            ConversationState.user_id == user_id,
            ConversationState.platform == platform
        ).first()
    
    def set_state(self, user_id: str, platform: str, state: str, data: Dict[str, Any]):
        """Set booking state."""
        conv_state = self.get_state(user_id, platform)
        
        if conv_state:
            conv_state.state = state
            conv_state.set_data(data)
            conv_state.updated_at = datetime.utcnow()
        else:
            conv_state = ConversationState(
                user_id=user_id,
                platform=platform,
                state=state,
                data_json=json.dumps(data, ensure_ascii=False)
            )
            self.db.add(conv_state)
        
        self.db.commit()
        return conv_state
    
    def process_message(self, user_id: str, platform: str, message: str) -> tuple[str, bool]:
        """
        Process booking message.
        
        Returns:
            (response_text, is_complete)
        """
        current_state_obj = self.get_state(user_id, platform)
        
        if not current_state_obj:
            # Start booking
            self.set_state(user_id, platform, "name", {})
            return format_booking_question("name", {}), False
        
        current_state = current_state_obj.state
        collected_data = current_state_obj.get_data()
        
        # Process based on current state
        if current_state == "name":
            collected_data["name"] = message.strip()
            self.set_state(user_id, platform, "phone", collected_data)
            return format_booking_question("phone", collected_data), False
        
        elif current_state == "phone":
            normalized_phone = normalize_phone(message)
            if not normalized_phone:
                return "⚠️ الرقم مو صحيح. جرب مرة ثانية (مثال: 0501234567)", False
            
            collected_data["phone"] = normalized_phone
            self.set_state(user_id, platform, "service", collected_data)
            return format_booking_question("service", collected_data), False
        
        elif current_state == "service":
            # Check if message contains doctor name (for direct booking)
            service_text = message.strip()
            
            # If service is already a doctor name (from pre-fill), use it
            if "service" in collected_data and collected_data["service"]:
                service_text = collected_data["service"]
            
            collected_data["service"] = service_text
            # Branch is optional, but we'll ask
            self.set_state(user_id, platform, "branch", collected_data)
            return format_booking_question("branch", collected_data), False
        
        elif current_state == "branch":
            # Branch is optional - user can skip
            if message.strip().lower() not in ['تخطى', 'skip', 'لا', '']:
                collected_data["branch"] = message.strip()
            self.set_state(user_id, platform, "date_time", collected_data)
            return format_booking_question("date_time", collected_data), False
        
        elif current_state == "date_time":
            # Date/time is optional
            if message.strip().lower() not in ['تخطى', 'skip', 'لا', '']:
                parsed_date = parse_relative_date(message)
                if parsed_date:
                    collected_data["date"] = parsed_date.strftime('%Y-%m-%d')
                else:
                    collected_data["date"] = message.strip()
                collected_data["time"] = message.strip()  # Simplified
            
            # Complete booking
            return self._complete_booking(user_id, platform, collected_data)
        
        return "شكراً لك!", True
    
    def _complete_booking(self, user_id: str, platform: str, data: Dict[str, Any]) -> tuple[str, bool]:
        """Complete booking and create ticket."""
        # Create booking ticket - all data in one organized template
        ticket_data = {
            "booking_id": f"BD-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{user_id[:6]}",
            "user_id": user_id,
            "platform": platform,
            "patient_name": data.get("name", ""),
            "patient_phone": data.get("phone", ""),
            "service_requested": data.get("service", ""),
            "doctor_name": data.get("doctor_name", ""),
            "preferred_branch": data.get("branch", ""),
            "preferred_date": data.get("date", ""),
            "preferred_time": data.get("time", ""),
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "notes": f"حجز جديد من {platform}"
        }
        
        # Save to database
        ticket = BookingTicket(
            user_id=user_id,
            platform=platform,
            payload_json=json.dumps(ticket_data, ensure_ascii=False),
            status="pending"
        )
        self.db.add(ticket)
        self.db.commit()
        
        # Send to Google Apps Script (optional)
        google_apps_script_url = os.getenv('GOOGLE_APPS_SCRIPT_URL', '')
        if google_apps_script_url:
            try:
                self._send_to_google_apps_script(ticket_data)
            except Exception as e:
                # Log error but don't fail
                import logging
                logging.warning(f"Error sending to Google Apps Script: {e}")
        
        # Clear state
        conv_state = self.get_state(user_id, platform)
        if conv_state:
            self.db.delete(conv_state)
            self.db.commit()
        
        return format_booking_confirmation(), True
    
    def _send_to_google_apps_script(self, ticket_data: Dict[str, Any]):
        """Send booking ticket to Google Apps Script."""
        if not google_apps_script_url:
            return
        
        try:
            with httpx.Client(timeout=10.0) as client:
                # Google Apps Script expects form data or query params
                response = client.post(
                    google_apps_script_url,
                    json={"action": "create_booking", **ticket_data},
                    follow_redirects=True
                )
                response.raise_for_status()
        except Exception as e:
            # Log but don't fail - booking is already saved in DB
            import logging
            logging.warning(f"Failed to send to Google Apps Script: {e}")
    
    def clear_state(self, user_id: str, platform: str):
        """Clear booking state."""
        conv_state = self.get_state(user_id, platform)
        if conv_state:
            self.db.delete(conv_state)
            self.db.commit()
            return True
        return False
    
    def cancel_booking(self, user_id: str, platform: str):
        """Cancel current booking."""
        return self.clear_state(user_id, platform)

