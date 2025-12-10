"""Router layer: intent → data lookup → formatter/LLM decision."""
from typing import Dict, Any, List
from core.intent import IntentClassifier
from core.agent import ChatAgent
from core.booking import BookingManager
from data.handler import data_handler
from utils.date_parser import parse_relative_date
from core.context import context_manager
try:
    from core.learning import learning_system
except ImportError:
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
        
        booking_state = self.booking_manager.get_state(user_id, platform)
        if booking_state:
            message_lower = message.lower().strip()
            if any(word in message_lower for word in ['الغاء', 'إلغاء', 'خروج', 'لا', 'لا أريد', 'لا اريد']):
                self.booking_manager.clear_state(user_id, platform)
                response = "تم إلغاء الحجز. كيف أقدر أساعدك؟"
                context_manager.add_to_context(user_id, platform, message, response)
                return response
            
            response, _ = self.booking_manager.process_message(user_id, platform, message)
            context_manager.add_to_context(user_id, platform, message, response)
            return response
        
        intent_result = self.intent_classifier.classify(message, context)
        intent = intent_result.intent
        entities = [e.dict() for e in intent_result.entities]
        next_action = intent_result.next_action
        
        if intent == "unclear":
            from utils.arabic_normalizer import normalize_ar
            message_normalized = normalize_ar(message)
            message_lower = message_normalized.lower().strip()
            message_clean = message_lower.replace(' ', '').replace('،', '').replace(',', '')
            message_original_lower = message.strip().lower()
            
            simple_greetings = ['هلا', 'اهلا', 'مرحبا', 'هاي', 'أهلا', 'أهلاً', 'هلاً']
            if (message_clean in simple_greetings or 
                message_original_lower in simple_greetings or
                message_clean.startswith('هلا') or 
                message_clean.startswith('اهلا') or
                message_original_lower.startswith('هلا') or
                message_original_lower.startswith('اهلا')):
                intent = "greeting"
                next_action = "use_llm"
            else:
                response = self._use_llm(
                    message, intent, entities, context,
                    user_id, platform, conversation_history
                )
                context_manager.add_to_context(user_id, platform, message, response)
                return response
        
        # Handle general questions - direct to LLM
        if intent == "general":
            response = self._use_llm(
                message, intent, entities, context,
                user_id, platform, conversation_history
            )
            if learning_system:
                learning_system.learn_from_interaction(
                    user_id, platform, message, response, intent, entities
                )
            context_manager.add_to_context(user_id, platform, message, response)
            return response
        
        # Handle booking intent
        message_lower = message.lower().strip()
        explicit_booking_keywords = ['ابي احجز', 'اريد احجز', 'حاب احجز', 'ابي احجز عنده', 'اريد احجز عنده']
        is_booking_request = any(keyword in message_lower for keyword in explicit_booking_keywords)
        
        if is_booking_request or (intent == "booking" and next_action == "start_booking"):
            # Check if there's a doctor name in entities
            doctor_name = None
            for entity in entities:
                if entity.get('type') == 'doctor_name':
                    doctor_name = entity.get('value')
                    break
            
            # If no doctor name in entities, try to extract from conversation history
            if not doctor_name and conversation_history:
                # Look for doctor names in recent conversation
                doctors = data_handler.get_doctors()
                for hist_item in reversed(conversation_history[:5]):  # Check last 5 messages
                    hist_message = hist_item.get('message', '').lower()
                    hist_response = hist_item.get('response', '').lower()
                    
                    # Check if response contains doctor name
                    for doctor in doctors:
                        doctor_name_full = doctor.get('doctor_name', '')
                        doctor_name_lower = doctor_name_full.lower()
                        name_parts = doctor_name_lower.replace('د.', '').replace('دكتورة', '').replace('دكتور', '').strip().split()
                        
                        # Check if doctor name appears in recent conversation
                        for part in name_parts:
                            if len(part) > 3 and (part in hist_message or part in hist_response):
                                doctor_name = doctor_name_full
                                break
                        if doctor_name:
                            break
                    if doctor_name:
                        break
            
            # Check if message is just "حجز" or "احجز" - treat as question, not booking request
            if message_lower.strip() in ['حجز', 'احجز', 'موعد']:
                is_explicit_booking = False
            else:
                is_explicit_booking = is_booking_request or (intent == "booking" and next_action == "start_booking")
                if not is_explicit_booking and doctor_name and ('عند' in message_lower or 'عنده' in message_lower):
                    is_explicit_booking = True
            
            if is_explicit_booking:
                self.booking_manager.clear_state(user_id, platform)
                if doctor_name:
                    self.booking_manager.set_state(user_id, platform, "name", {"doctor_name": doctor_name})
                    response = f"✅ حجز عند {doctor_name}\n\nما اسمك؟"
                else:
                    response, _ = self.booking_manager.process_message(user_id, platform, message)
                context_manager.add_to_context(user_id, platform, message, response)
                return response
            elif intent == "booking" and next_action != "start_booking":
                response = self._use_llm(
                    message, intent, entities, context,
                    user_id, platform, conversation_history
                )
                context_manager.add_to_context(user_id, platform, message, response)
                return response
        
        if intent == "hours":
            branches = data_handler.get_branches()
            if not branches:
                response = "⚠️ ما لقيت معلومات عن الدوام حالياً."
            else:
                hours_list = []
                for branch in branches:
                    name = branch.get('branch_name', '')
                    weekdays = branch.get('hours_weekdays', '')
                    weekend = branch.get('hours_weekend', '')
                    if name:
                        hours_info = f"{name}:"
                        if weekdays:
                            hours_info += f" الأسبوع: {weekdays}"
                        if weekend:
                            hours_info += f" | نهاية الأسبوع: {weekend}"
                        hours_list.append(hours_info)
                
                if hours_list:
                    response = "⏰ أوقات الدوام:\n\n" + "\n".join([f"{i+1}. {h}" for i, h in enumerate(hours_list)])
                else:
                    response = "⚠️ ما لقيت معلومات عن الدوام حالياً."
            context_manager.add_to_context(user_id, platform, message, response)
            return response
        
        if intent == "thanks":
            response = "الله يعطيك العافية! 😊 إذا عندك أي استفسار ثاني، أنا موجود."
            context_manager.add_to_context(user_id, platform, message, response)
            return response
        
        if intent == "goodbye":
            response = "مع السلامة! الله يوفقك. إذا احتجت شي ثاني، أنا موجود."
            context_manager.add_to_context(user_id, platform, message, response)
            return response
        
        if intent == "contact":
            branches = data_handler.get_branches()
            if branches:
                contact_info = []
                for branch in branches:
                    name = branch.get('branch_name', '')
                    phone = branch.get('phone', '')
                    email = branch.get('email', '')
                    address = branch.get('address', '')
                    city = branch.get('city', '')
                    if name:
                        info = f"{name}"
                        if phone:
                            info += f"\n📞 {phone}"
                        if email:
                            info += f"\n📧 {email}"
                        if address:
                            info += f"\n📍 {address}"
                        if city:
                            info += f", {city}"
                        contact_info.append(info)
                
                if contact_info:
                    response = "📞 معلومات التواصل:\n\n" + "\n\n".join([f"{i+1}. {info}" for i, info in enumerate(contact_info)])
                else:
                    response = "📞 للتواصل: تواصل معنا على الأرقام المتاحة في الفروع."
            else:
                response = "📞 للتواصل: تواصل معنا على الأرقام المتاحة في الفروع."
            context_manager.add_to_context(user_id, platform, message, response)
            return response
        
        if intent == "faq":
            message_lower = message.lower()
            if not any(word in message_lower for word in ['كيف', 'طريقة', 'خطوات']):
                # Common FAQ - direct response
                response = "عذراً، ما قدرت أفهم سؤالك بالضبط. تبي تعرف عن:\n• أطباء\n• فروع\n• خدمات\n• حجز"
                context_manager.add_to_context(user_id, platform, message, response)
                return response
        
        if intent in ["doctor", "service", "branch"]:
            response = self._respond_directly(intent, entities, message)
            if response:
                context_manager.add_to_context(user_id, platform, message, response)
                return response
        
        relevant_data = self._gather_relevant_data(intent, entities)
        response = self._use_llm(
            message, intent, entities, context,
            user_id, platform, conversation_history,
            relevant_data=relevant_data
        )
        
        if learning_system:
            learning_system.learn_from_interaction(
                user_id, platform, message, response, intent, entities
            )
        
        context_manager.add_to_context(user_id, platform, message, response)
        return response
    
    def _gather_relevant_data(
        self,
        intent: str,
        entities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Gather relevant data based on intent and entities for LLM context."""
        relevant_data = {}
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
        
        if intent == "doctor":
            if doctor_name:
                doctor = data_handler.find_doctor_by_name(doctor_name)
                if doctor:
                    relevant_data['doctor'] = doctor
                    if date_str:
                        parsed_date = parse_relative_date(date_str)
                        if parsed_date:
                            availability = data_handler.get_doctor_availability_today(doctor.get('doctor_id'))
                            if availability:
                                relevant_data['availability'] = availability
            else:
                relevant_data['doctors'] = data_handler.get_doctors()
        
        elif intent == "service":
            if service_name:
                service = data_handler.find_service_by_name(service_name)
                if service:
                    relevant_data['service'] = service
                    relevant_data['branches'] = data_handler.get_branches()
            else:
                relevant_data['services'] = data_handler.get_services()
        
        elif intent == "branch":
            if branch_id:
                branch = data_handler.get_branch_by_id(branch_id)
                if branch:
                    relevant_data['branch'] = branch
            else:
                relevant_data['branches'] = data_handler.get_branches()
        
        elif intent == "hours":
            branches = data_handler.get_branches()
            if branches:
                relevant_data['branches'] = branches
                for branch in branches:
                    branch['hours_weekdays'] = branch.get('hours_weekdays', '')
                    branch['hours_weekend'] = branch.get('hours_weekend', '')
        
        elif intent in ["contact", "general"]:
            branches = data_handler.get_branches()
            if branches:
                relevant_data['branches'] = branches
        
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
        message: str = ""
    ) -> str:
        """Generate direct response without LLM for simple queries."""
        from utils.arabic_normalizer import normalize_ar
        
        message_normalized = normalize_ar(message) if message else ""
        message_lower = message_normalized.lower() if message_normalized else ""
        
        if intent == "doctor":
            doctors = data_handler.get_doctors()
            if not doctors:
                return "⚠️ ما لقيت أطباء متاحين حالياً."
            
            # Specialty mapping (normalized)
            specialty_keywords = {
                'اسنان': 'أسنان',
                'جلدية': 'جلدية',
                'نساء': 'نساء وولادة',
                'ولادة': 'نساء وولادة',
                'اطفال': 'أطفال',
                'عظام': 'عظام',
                'باطنية': 'باطنية'
            }
            
            filtered_doctors = doctors
            specialty_found = None
            # Check normalized message for specialty keywords
            for keyword, specialty in specialty_keywords.items():
                if keyword in message_lower:
                    filtered_doctors = [d for d in doctors if normalize_ar(d.get('specialty', '')) == keyword]
                    specialty_found = specialty
                    if filtered_doctors:
                        break
            
            if specialty_found and filtered_doctors:
                doctor_list = []
                for doc in filtered_doctors:
                    name = doc.get('doctor_name', '')
                    specialty = doc.get('specialty', '')
                    if name:
                        doctor_list.append(f"{name} ({specialty})" if specialty else name)
                
                if doctor_list:
                    title = f"🏥 أطباء {specialty_found}:"
                    return f"{title}\n\n" + "\n".join([f"{i+1}. {d}" for i, d in enumerate(doctor_list)])
            
            doctor_name_entity = next((e for e in entities if e.get('type') == 'doctor_name'), None)
            doctor_name_from_entity = doctor_name_entity.get('value') if doctor_name_entity else None
            
            if not doctor_name_from_entity and not specialty_found:
                for doc in doctors:
                    doc_name = doc.get('doctor_name', '').lower()
                    if doc_name and any(part in message_lower for part in doc_name.split() if len(part) > 3):
                        doctor_name_from_entity = doc.get('doctor_name')
                        break
            
            if doctor_name_from_entity:
                doctor = data_handler.find_doctor_by_name(doctor_name_from_entity)
                if doctor:
                    branch_id = doctor.get('branch_id', '')
                    branch = data_handler.get_branch_by_id(branch_id) if branch_id else None
                    
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
            
            doctor_list = []
            for doc in doctors:
                name = doc.get('doctor_name', '')
                specialty = doc.get('specialty', '')
                if name:
                    doctor_list.append(f"{name} ({specialty})" if specialty else name)
            
            if doctor_list:
                return f"🏥 الأطباء المتاحون:\n\n" + "\n".join([f"{i+1}. {d}" for i, d in enumerate(doctor_list)])
            return "⚠️ ما لقيت أطباء متاحين."
        
        elif intent == "service":
            services = data_handler.get_services()
            if not services:
                return "⚠️ ما لقيت خدمات متاحة حالياً."
            
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
        
        return None
    
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

