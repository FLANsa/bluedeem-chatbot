"""Router layer: intent → data lookup → formatter/LLM decision."""
from typing import Dict, Any, Optional, Tuple, List
from core.intent import IntentClassifier
from core.agent import ChatAgent
# Removed formatter imports - using LLM for all responses
from core.booking import BookingManager
from data.handler import data_handler
from utils.date_parser import parse_relative_date
from core.context import context_manager
try:
    from core.learning import learning_system
except ImportError:
    # Fallback if learning module doesn't exist
    learning_system = None


class Router:
    """Router that decides whether to use formatter or LLM."""
    
    def __init__(self):
        """Initialize router."""
        self.intent_classifier = IntentClassifier()
        self.agent = ChatAgent()
        self.booking_manager = BookingManager()
    
    def process(
        self,
        user_id: str,
        platform: str,
        message: str,
        context: Dict[str, Any] = None
    ) -> str:
        """
        Process message and return response.
        
        Args:
            user_id: User ID
            platform: Platform name
            message: User message
            context: Optional context
            
        Returns:
            Response text
        """
        # Get conversation history for context
        conversation_history = context_manager.get_recent_context(
            user_id, platform, limit=10
        )
        
        # Check if user is in booking flow (only if explicitly started)
        booking_state = self.booking_manager.get_state(user_id, platform)
        if booking_state:
            # Only process booking if user is actually in booking flow
            # Check if message is trying to cancel or exit booking
            message_lower = message.lower().strip()
            if any(word in message_lower for word in ['الغاء', 'إلغاء', 'خروج', 'خروج', 'لا', 'لا أريد', 'لا اريد']):
                # Clear booking state
                self.booking_manager.clear_state(user_id, platform)
                response = "تم إلغاء الحجز. كيف أقدر أساعدك؟"
                context_manager.add_to_context(user_id, platform, message, response)
                return response
            
            response, is_complete = self.booking_manager.process_message(
                user_id, platform, message
            )
            # Save to history
            context_manager.add_to_context(user_id, platform, message, response)
            return response
        
        # Classify intent (can use conversation history for better classification)
        intent_result = self.intent_classifier.classify(message, context)
        intent = intent_result.intent
        entities = [e.dict() for e in intent_result.entities]
        next_action = intent_result.next_action
        
        # Handle general questions first - direct to LLM
        if intent == "general":
            response = self._use_llm(
                message, intent, entities, context,
                user_id, platform, conversation_history
            )
            # Learn from interaction
            if learning_system:
                learning_system.learn_from_interaction(
                    user_id, platform, message, response, intent, entities
                )
            # Save to history
            context_manager.add_to_context(user_id, platform, message, response)
            return response
        
        # Handle booking intent - only start if explicitly requested
        # Don't start booking for simple queries like "أطباء" or "خدمات" or "مين أطباء الأسنان"
        if intent == "booking" and next_action == "start_booking":
            # Check if there's a doctor name in entities
            doctor_name = None
            for entity in entities:
                if entity.get('type') == 'doctor_name':
                    doctor_name = entity.get('value')
                    break
            
            # Only start booking if user explicitly requested it with clear booking intent
            # Don't start for just "حجز" - might be asking about booking process
            message_lower = message.lower().strip()
            
            # Explicit booking keywords that indicate user wants to book NOW
            explicit_booking_keywords = ['ابي احجز', 'اريد احجز', 'حاب احجز', 'عند', 'مع']
            
            # Check if message is just "حجز" or "احجز" - treat as question, not booking request
            if message_lower.strip() in ['حجز', 'احجز', 'موعد']:
                # User is asking about booking, not requesting to book - use LLM to explain
                is_explicit_booking = False
            else:
                # Check for explicit booking intent
                is_explicit_booking = any(keyword in message_lower for keyword in explicit_booking_keywords)
                
                # If doctor name found with "عند" or "مع", it's likely a booking request
                if not is_explicit_booking and doctor_name and ('عند' in message_lower or 'مع' in message_lower):
                    is_explicit_booking = True
            
            if is_explicit_booking:
                # Clear any existing booking state first
                self.booking_manager.clear_state(user_id, platform)
                
                # If doctor name found, start booking with doctor pre-filled
                if doctor_name:
                    # Start booking with doctor name
                    self.booking_manager.set_state(user_id, platform, "name", {"doctor_name": doctor_name})
                    response = f"✅ حجز عند {doctor_name}\n\nما اسمك؟"
                    context_manager.add_to_context(user_id, platform, message, response)
                    return response
                
                # Start booking flow
                response, _ = self.booking_manager.process_message(user_id, platform, message)
                context_manager.add_to_context(user_id, platform, message, response)
                return response
            else:
                # User is asking about booking but not explicitly requesting it - use LLM to explain
                # This handles cases like "حجز" (just asking about booking)
                response = self._use_llm(
                    message, intent, entities, context,
                    user_id, platform, conversation_history
                )
                context_manager.add_to_context(user_id, platform, message, response)
                return response
        
        # Handle thanks and goodbye intents directly
        if intent == "thanks":
            response = "الله يعطيك العافية! 😊 إذا عندك أي استفسار ثاني، أنا موجود."
            context_manager.add_to_context(user_id, platform, message, response)
            return response
        
        if intent == "goodbye":
            response = "مع السلامة! الله يوفقك. إذا احتجت شي ثاني، أنا موجود."
            context_manager.add_to_context(user_id, platform, message, response)
            return response
        
        # For simple queries, use direct formatter for speed
        # Only use LLM for complex queries or when context is needed
        if intent in ["doctor", "service", "branch"]:
            # Always try direct response first for speed (especially for simple list requests)
            response = self._respond_directly(intent, entities, message, relevant_data={})
            if response:
                context_manager.add_to_context(user_id, platform, message, response)
                return response
        
        # For complex queries or when entities are present, use LLM
        # Gather relevant data for context
        relevant_data = self._gather_relevant_data(intent, entities)
        
        # Use LLM for intelligent responses
        response = self._use_llm(
            message, intent, entities, context,
            user_id, platform, conversation_history,
            relevant_data=relevant_data
        )
        
        # Learn from interaction
        if learning_system:
            learning_system.learn_from_interaction(
                user_id, platform, message, response, intent, entities
            )
        
        # Save to history
        context_manager.add_to_context(user_id, platform, message, response)
        return response
    
    def _gather_relevant_data(
        self,
        intent: str,
        entities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Gather relevant data based on intent and entities for LLM context."""
        relevant_data = {}
        
        # Extract entities
        doctor_name = None
        service_name = None
        branch_id = None
        date_str = None
        
        for entity in entities:
            entity_type = entity.get('type', '')
            entity_value = entity.get('value', '')
            
            if entity_type == 'doctor_name':
                doctor_name = entity_value
            elif entity_type == 'service_name':
                service_name = entity_value
            elif entity_type == 'branch_id':
                branch_id = entity_value
            elif entity_type == 'date':
                date_str = entity_value
        
        # Gather data based on intent
        if intent == "doctor":
            if doctor_name:
                doctor = data_handler.find_doctor_by_name(doctor_name)
                if doctor:
                    relevant_data['doctor'] = doctor
                    # Get availability if date mentioned
                    if date_str:
                        parsed_date = parse_relative_date(date_str)
                        if parsed_date:
                            availability = data_handler.get_doctor_availability_today(
                                doctor.get('doctor_id')
                            )
                            if availability:
                                relevant_data['availability'] = availability
            else:
                # Get all doctors
                doctors = data_handler.get_doctors()
                relevant_data['doctors'] = doctors
        
        elif intent == "service":
            if service_name:
                service = data_handler.find_service_by_name(service_name)
                if service:
                    relevant_data['service'] = service
                    # Get branches where service is available
                    branches = data_handler.get_branches()
                    relevant_data['branches'] = branches
            else:
                # Get all services
                services = data_handler.get_services()
                relevant_data['services'] = services
        
        elif intent == "branch":
            if branch_id:
                branch = data_handler.get_branch_by_id(branch_id)
                if branch:
                    relevant_data['branch'] = branch
            else:
                # Get all branches
                branches = data_handler.get_branches()
                relevant_data['branches'] = branches
        
        elif intent in ["hours", "contact", "general"]:
            # Get all relevant data for general questions
            branches = data_handler.get_branches()
            if branches:
                relevant_data['branches'] = branches
        
        # Always include some general data for context
        if 'doctors' not in relevant_data:
            relevant_data['all_doctors'] = data_handler.get_doctors()
        if 'services' not in relevant_data:
            relevant_data['all_services'] = data_handler.get_services()
        if 'branches' not in relevant_data:
            relevant_data['all_branches'] = data_handler.get_branches()
        
        return relevant_data
    
    def _respond_directly(
        self,
        intent: str,
        entities: List[Dict[str, Any]],
        message: str = "",
        relevant_data: Dict[str, Any] = None
    ) -> str:
        """Generate direct response without LLM for simple queries - faster."""
        message_lower = message.lower() if message else ""
        
        if intent == "doctor":
            # Check if asking about a specific doctor by name
            doctor_name_entity = next((e for e in entities if e.get('type') == 'doctor_name'), None)
            doctor_name_from_entity = doctor_name_entity.get('value') if doctor_name_entity else None
            
            # Also check message for doctor names (fuzzy match)
            if not doctor_name_from_entity:
                doctors = data_handler.get_doctors()
                for doc in doctors:
                    doc_name = doc.get('doctor_name', '').lower()
                    # Check if message contains doctor name or part of it
                    if doc_name and any(part in message_lower for part in doc_name.split() if len(part) > 2):
                        # Found a doctor name in message
                        doctor_name_from_entity = doc.get('doctor_name')
                        break
            
            # If specific doctor requested, return their info
            if doctor_name_from_entity:
                doctor = data_handler.find_doctor_by_name(doctor_name_from_entity)
                if doctor:
                    # Get branch info
                    branch_id = doctor.get('branch_id', '')
                    branch = None
                    if branch_id:
                        branch = data_handler.get_branch_by_id(branch_id)
                    
                    # Format doctor info - include ALL available information
                    name = doctor.get('doctor_name', '')
                    specialty = doctor.get('specialty', '')
                    days = doctor.get('days', '')
                    time_from = doctor.get('time_from', '')
                    time_to = doctor.get('time_to', '')
                    experience = doctor.get('experience_years', '')
                    qualifications = doctor.get('qualifications', '')
                    
                    response = f"✅ {name}\n"
                    if specialty:
                        response += f"التخصص: {specialty}\n"
                    if experience:
                        response += f"⏰ الخبرة: {experience} سنة\n"
                    if qualifications:
                        response += f"📜 المؤهلات: {qualifications}\n"
                    if branch:
                        branch_name = branch.get('branch_name', '')
                        branch_address = branch.get('address', '')
                        branch_city = branch.get('city', '')
                        if branch_name:
                            location = f"{branch_name}"
                            if branch_address:
                                location += f" - {branch_address}"
                            if branch_city:
                                location += f", {branch_city}"
                            response += f"📍 الفرع: {location}\n"
                    elif branch_id:
                        response += f"📍 الفرع: {branch_id}\n"
                    if days:
                        response += f"⏰ الدوام: {days}\n"
                    if time_from and time_to:
                        response += f"⏰ الوقت: {time_from} - {time_to}\n"
                    
                    return response.strip()
                else:
                    return f"⚠️ ما لقيت طبيب باسم '{doctor_name_from_entity}'."
            
            # Otherwise, show list of doctors
            doctors = data_handler.get_doctors()
            if not doctors:
                return "⚠️ ما لقيت أطباء متاحين حالياً."
            
            # Check if asking about specific specialty
            specialty_keywords = {
                'أسنان': 'أسنان',
                'اسنان': 'أسنان',
                'الأسنان': 'أسنان',
                'الاسنان': 'أسنان',
                'جلدية': 'جلدية',
                'الجلدية': 'جلدية',
                'نساء': 'نساء وولادة',
                'ولادة': 'نساء وولادة',
                'أطفال': 'أطفال',
                'اطفال': 'أطفال',
                'عظام': 'عظام',
                'العظام': 'عظام'
            }
            
            # Filter by specialty if mentioned
            filtered_doctors = doctors
            specialty_found = None
            for keyword, specialty in specialty_keywords.items():
                if keyword in message_lower:
                    filtered_doctors = [d for d in doctors if d.get('specialty', '') == specialty]
                    specialty_found = specialty
                    if filtered_doctors:
                        break
            
            # Format doctors list
            doctor_list = []
            for doc in filtered_doctors:
                name = doc.get('doctor_name', '')
                specialty = doc.get('specialty', '')
                if name:
                    doctor_list.append(f"{name} ({specialty})" if specialty else name)
            
            if doctor_list:
                title = f"🏥 أطباء {specialty_found}:" if specialty_found else "🏥 الأطباء المتاحون:"
                return f"{title}\n\n" + "\n".join([f"{i+1}. {d}" for i, d in enumerate(doctor_list)])
            return "⚠️ ما لقيت أطباء متاحين."
        
        elif intent == "service":
            services = data_handler.get_services()
            if not services:
                return "⚠️ ما لقيت خدمات متاحة حالياً."
            
            # Format services list
            service_list = []
            for svc in services:
                name = svc.get('service_name', '')
                price = svc.get('price_sar', '')
                if name:
                    price_str = f" - {price} ريال" if price else ""
                    service_list.append(f"{name}{price_str}")
            
            if service_list:
                return f"💰 الخدمات المتاحة:\n\n" + "\n".join([f"{i+1}. {s}" for i, s in enumerate(service_list)])
            return "⚠️ ما لقيت خدمات متاحة."
        
        elif intent == "branch":
            branches = data_handler.get_branches()
            if not branches:
                return "⚠️ ما لقيت فروع متاحة حالياً."
            
            # Format branches list
            branch_list = []
            for branch in branches:
                name = branch.get('branch_name', '')
                address = branch.get('address', '')
                city = branch.get('city', '')
                if name:
                    location = f" - {address}, {city}" if address and city else (f" - {address}" if address else "")
                    branch_list.append(f"{name}{location}")
            
            if branch_list:
                return f"📍 الفروع:\n\n" + "\n".join([f"{i+1}. {b}" for i, b in enumerate(branch_list)])
            return "⚠️ ما لقيت فروع متاحة."
        
        return None  # Use LLM for other cases
    
    def _use_llm(
        self,
        message: str,
        intent: str,
        entities: List[Dict[str, Any]],
        context: Dict[str, Any],
        user_id: str = None,
        platform: str = None,
        conversation_history: List[Dict[str, Any]] = None,
        relevant_data: Dict[str, Any] = None
    ) -> str:
        """Use LLM for intelligent and complete responses."""
        # Merge relevant_data into context
        if relevant_data:
            if context is None:
                context = {}
            context['relevant_data'] = relevant_data
        
        agent_response = self.agent.generate_response(
            message, intent, entities, context,
            user_id=user_id,
            platform=platform,
            conversation_history=conversation_history
        )
        return agent_response.response_text

