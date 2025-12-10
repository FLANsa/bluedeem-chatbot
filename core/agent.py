"""LLM agent using GPT-4.1-mini with Structured Outputs and Function Calling."""
from typing import Dict, Any, Optional, List
import json
from openai import OpenAI
import os
from models.schemas import AgentResponseSchema
from data.handler import data_handler
from core.context import context_manager


class ChatAgent:
    """Chat agent using GPT-4.1-mini."""
    
    def __init__(self):
        """Initialize chat agent."""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        self.client = OpenAI(api_key=api_key)
        self.model = os.getenv('LLM_MODEL_AGENT', 'gpt-4o-mini')
    
    def generate_response(
        self,
        message: str,
        intent: str,
        entities: List[Dict[str, Any]],
        context: Dict[str, Any] = None,
        user_id: str = None,
        platform: str = None,
        conversation_history: List[Dict[str, Any]] = None
    ) -> AgentResponseSchema:
        """
        Generate response using LLM with Structured Outputs.
        
        Args:
            message: User message
            intent: Detected intent
            entities: Extracted entities
            context: Optional context
            
        Returns:
            AgentResponseSchema with response_text, needs_clarification, suggested_questions
        """
        system_prompt = """أنت مساعد شخصي ذكي وودود لشات بوت عيادة "بلو ديم". أنت مساعد طبيعي ومفيد.

**مهمتك الأساسية:**
- اكتشف تلقائياً ما يريده العميل من رسالته
- ارد بطريقة ذكية وكاملة ومفيدة - استخدم البيانات المتاحة من Google Sheets
- **مهم جداً:** عندما يسأل عن "أطباء" أو "فروع" أو "خدمات"، اعرض القائمة بشكل مختصر مع المعلومات الأساسية فقط
- **مهم جداً:** عندما يسأل "مين أطباء الأسنان"، اعرض أسماء الأطباء فقط بشكل مختصر
- استخدم البيانات المتاحة بشكل طبيعي في ردك - لا تخترع معلومات
- لا تستخدم قوالب ثابتة - كن طبيعياً وذكياً ومفيداً
- **كن مختصراً جداً - لا تكرر المعلومات ولا تطول في الشرح (2-3 جمل كحد أقصى)**
- إذا سأل عن قائمة، قدم القائمة بشكل مختصر مع المعلومات الأساسية فقط
- **مهم جداً:** إذا سأل عن الأطباء أو الخدمات، لا تبدأ عملية الحجز تلقائياً - فقط قدم المعلومات
- **لا تبدأ الحجز إلا إذا طلب المستخدم ذلك صراحة (مثل "ابي احجز" أو "حجز")**
- **استخدم البيانات من Google Sheets دائماً - لا تقل "ما عندي معلومات" إذا كانت البيانات متوفرة**
- كن ودوداً وطبيعياً في اللهجة النجدية - لكن مختصراً جداً

**الشخصية والأسلوب:**
1. استخدم اللهجة النجدية 100% (بدون فصحى) - طبيعية وودودة
2. كن طبيعياً في الرد - ردود متعددة الجمل لكن مختصرة (2-3 جمل كحد أقصى)
3. استخدم السياق من المحادثة السابقة لفهم ما يقصده المستخدم
4. إذا ذكر المستخدم شيئاً سابقاً (مثل "هو" أو "الطبيب" أو "الفرع")، استخدم السياق لفهمه
5. كن استباقياً - اقترح أشياء مفيدة بناءً على السياق
6. لا تكرر نفس المعلومات إلا إذا طلب المستخدم ذلك
7. لا تخترع معلومات - استخدم فقط البيانات المتوفرة
8. إذا غير واضح: ابدأ بـ "عذراً" + قدم خيارات (أطباء/فروع/خدمات/حجز)
9. استخدم الإيموجي باعتدال: ✅ 📍 ⏰ 💰 ⚠️ ⭐

**اللهجة النجدية الطبيعية:**
- استخدم "أنا" بدل "أنا"
- استخدم "شلون" بدل "كيف"
- استخدم "وين" بدل "أين"
- استخدم "شلونك" بدل "كيف حالك"
- استخدم "الله يعطيك العافية" بدل "شكراً لك"
- كن طبيعياً وودوداً - مثل صديق يساعدك

**فهم السياق:**
- استخدم المحادثة السابقة لفهم ما يقصده المستخدم
- إذا قال "هو" أو "هي"، راجع السياق لفهم من يقصد
- إذا سأل عن شيء ذكرناه سابقاً، استخدم المعلومات السابقة
- كن ذكياً في ربط المعلومات

**الرد على الأسئلة العامة:**
- عند السؤال "ما اسمك؟" أو "من أنت؟": رد بـ "اسمي مساعد بلو ديم 🏥" + توجيه للخدمات المتاحة
- عند "عندي استفسار": رد بطريقة ودودة "أهلاً! كيف أقدر أساعدك؟ عندك استفسار عن إيش؟ (أطباء/خدمات/حجز)"
- عند "كيف أحجز؟": اشرح خطوات الحجز بشكل بسيط + توجيه للبدء
- عند "وين العيادة؟": اعرض الفروع المتاحة مع عناوينها
- عند أي سؤال عام متعلق بالعيادة: رد بشكل مفيد + قدم خيارات للخدمات المتاحة

**الرد على أسئلة الدوام/الأوقات:**
- عند "متى تفتحون؟" أو "متى اوقات الدوام؟": استخدم بيانات الفروع (hours_weekdays و hours_weekend) لعرض أوقات الدوام لكل فرع
- عند "متى تفتح الفروع؟": اعرض أوقات الدوام لكل فرع من بيانات الفروع
- استخدم البيانات المتاحة من Google Sheets - لا تخترع أوقات
- كن مختصراً - اعرض الأوقات بشكل واضح ومباشر
- مثال: "⏰ دوامنا: الأحد-الخميس: 9 صباحاً - 6 مساءً، الجمعة-السبت: 2 مساءً - 8 مساءً"

**أمثلة على الردود المختصرة:**
- عند "أطباء": "عندنا أطباء في تخصصات مختلفة. مين تبي؟ (أسنان/جلدية/أطفال/نساء)"
- عند "خدمات": "خدماتنا متنوعة. عندك استفسار عن خدمة معينة؟"
- عند "مين أطباء الأسنان": "أطباء الأسنان: د. محمد العتيبي، د. فاطمة السالم"
- عند "مين الاطباء الي عندكم": "عندنا أطباء في تخصصات مختلفة: أسنان، جلدية، أطفال، نساء وولادة، عظام. مين تبي؟"
- عند "الدكتورة سارة ب اي فرع": "الدكتورة سارة في فرع الرياض - العليا"
- عند "متى تفتحون؟": "⏰ دوامنا: الأحد-الخميس: 9 صباحاً - 6 مساءً، الجمعة-السبت: 2 مساءً - 8 مساءً"

**تذكر:**
- **مختصر جداً (2-3 جمل كحد أقصى)**
- **استخدم البيانات المتاحة دائماً**
- **لا تبدأ الحجز إلا إذا طلب صراحة**
- **كن طبيعياً وودوداً لكن مختصراً**"""
        
        # Get conversation history context
        conversation_context = ""
        if conversation_history:
            conversation_context = context_manager.build_context_string(
                conversation_history,
                max_length=1500
            )
        
        # Prepare context with available data (use relevant_data from router if available)
        relevant_data = context.get('relevant_data', {}) if context else {}
        context_data = self._prepare_context(intent, entities, context, relevant_data=relevant_data, message=message)
        
        # Build user prompt with context
        user_prompt_parts = [f"الرسالة الحالية: {message}"]
        
        if conversation_context:
            user_prompt_parts.append(f"\nالمحادثة السابقة:\n{conversation_context}")
        
        user_prompt_parts.append(f"\nالنية: {intent}")
        user_prompt_parts.append(f"الكيانات: {entities}")
        
        if context_data:
            user_prompt_parts.append(f"\nالبيانات المتوفرة:\n{context_data}")
        
        user_prompt_parts.append("\n**مهم جداً:** رد بلهجة نجدية طبيعية وودودة ومختصرة جداً (2-3 جمل كحد أقصى). استخدم السياق لفهم ما يقصده المستخدم. استخدم جميع المعلومات المتاحة من البيانات. لا تطول في الرد - كن مختصراً ومباشراً.")
        
        user_prompt = "\n".join(user_prompt_parts)
        
        try:
            # Use create() with response_format for structured outputs
            # In OpenAI 1.12.0, structured outputs use response_format with json_schema
            from models.schemas import AgentResponseSchema
            import json
            
            # Get JSON schema from Pydantic model
            json_schema = AgentResponseSchema.model_json_schema()
            # OpenAI requires additionalProperties: false
            json_schema["additionalProperties"] = False
            # OpenAI requires all properties to be in required array
            if "properties" in json_schema:
                json_schema["required"] = list(json_schema["properties"].keys())
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "agent_response",
                        "schema": json_schema,
                        "strict": True
                    }
                }
            )
            
            # Parse the response
            content = response.choices[0].message.content
            if content:
                try:
                    data = json.loads(content)
                    result = AgentResponseSchema(**data)
                    return result
                except Exception as parse_error:
                    raise Exception(f"Failed to parse response: {parse_error}")
            else:
                raise Exception("Empty response from API")
            
        except Exception as e:
            # Log error for debugging
            import logging
            logging.error(f"Agent error: {e}")
            # Fallback response - but try to be helpful for general questions
            if intent == "general":
                # For general questions, provide a more helpful fallback
                message_lower = message.lower()
                if "اسمك" in message_lower or "من أنت" in message_lower or "مين انت" in message_lower:
                    return AgentResponseSchema(
                        response_text="اسمي مساعد بلو ديم 🏥 كيف أقدر أساعدك اليوم؟ عندك استفسار عن أطباء أو خدمات أو حجز؟",
                        needs_clarification=False,
                        suggested_questions=["أطباء", "خدمات", "حجز", "فروع"]
                    )
                elif "استفسار" in message_lower or "سؤال" in message_lower:
                    return AgentResponseSchema(
                        response_text="أهلاً! كيف أقدر أساعدك؟ عندك استفسار عن إيش؟ (أطباء/خدمات/حجز/فروع)",
                        needs_clarification=True,
                        suggested_questions=["أطباء", "خدمات", "حجز", "فروع"]
                    )
                elif "كيف أحجز" in message_lower or "كيف احجز" in message_lower:
                    return AgentResponseSchema(
                        response_text="الحجز سهل! قولي اسم الطبيب أو الخدمة اللي تبيها، وأنا أساعدك تحجز. أو قولي 'حجز' للبدء.",
                        needs_clarification=False,
                        suggested_questions=["حجز", "أطباء", "خدمات"]
                    )
            
            # Default fallback
            return AgentResponseSchema(
                response_text="عذراً، ما قدرت أفهم طلبك. جرب تسأل عن أطباء أو فروع أو خدمات.",
                needs_clarification=True,
                suggested_questions=["أطباء", "فروع", "خدمات", "حجز"]
            )
    
    def _prepare_context(self, intent: str, entities: List[Dict[str, Any]], context: Dict[str, Any] = None, relevant_data: Dict[str, Any] = None, message: str = "") -> str:
        """Prepare comprehensive context data for LLM to generate intelligent responses."""
        context_parts = []
        
        # Extract entity values
        doctor_name = None
        service_name = None
        branch_id = None
        date_str = None
        
        for entity in entities:
            if entity.get('type') == 'doctor_name':
                doctor_name = entity.get('value')
            elif entity.get('type') == 'service_name':
                service_name = entity.get('value')
            elif entity.get('type') == 'branch_id':
                branch_id = entity.get('value')
            elif entity.get('type') == 'date':
                date_str = entity.get('value')
        
        # Use relevant_data from router if available, otherwise fetch from data_handler
        if relevant_data is None:
            relevant_data = {}
        
        message_lower = message.lower() if message else ""
        
        # Prepare comprehensive context based on intent
        if intent == "doctor":
            # Always get doctors data
            if 'doctors' in relevant_data:
                doctors = relevant_data['doctors']
            elif 'all_doctors' in relevant_data:
                doctors = relevant_data['all_doctors']
            else:
                doctors = data_handler.get_doctors()
            
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
            
            filtered_doctors = doctors
            specialty_found = None
            for keyword, specialty in specialty_keywords.items():
                if keyword in message_lower:
                    filtered_doctors = [d for d in doctors if d.get('specialty', '') == specialty]
                    specialty_found = specialty
                    if filtered_doctors:
                        break
            
            if doctor_name:
                # Specific doctor requested - include ALL available information
                doctor = data_handler.find_doctor_by_name(doctor_name)
                if doctor:
                    # Include comprehensive doctor information including experience and qualifications
                    doctor_info = {
                        "doctor_name": doctor.get('doctor_name', ''),
                        "specialty": doctor.get('specialty', ''),
                        "branch_id": doctor.get('branch_id', ''),
                        "days": doctor.get('days', ''),
                        "time_from": doctor.get('time_from', ''),
                        "time_to": doctor.get('time_to', ''),
                        "phone": doctor.get('phone', ''),
                        "email": doctor.get('email', ''),
                        "experience_years": doctor.get('experience_years', ''),
                        "qualifications": doctor.get('qualifications', ''),
                        "notes": doctor.get('notes', '')
                    }
                    context_parts.append(f"معلومات الطبيب المطلوب (استخدم جميع المعلومات المتاحة بما فيها الخبرة والمؤهلات):\n{json.dumps(doctor_info, ensure_ascii=False, indent=2)}")
                    
                    # Get branch information
                    branch_id = doctor.get('branch_id', '')
                    if branch_id:
                        branch = data_handler.get_branch_by_id(branch_id)
                        if branch:
                            context_parts.append(f"معلومات الفرع:\n{json.dumps(branch, ensure_ascii=False, indent=2)}")
                    
                    # Get availability if date mentioned
                    if 'availability' in relevant_data:
                        context_parts.append(f"التوفر: {json.dumps(relevant_data['availability'], ensure_ascii=False)}")
                    elif date_str:
                        # Try to get availability for the date
                        availability = data_handler.get_doctor_availability(date_str, doctor.get('doctor_id'))
                        if availability:
                            context_parts.append(f"التوفر: {json.dumps(availability, ensure_ascii=False)}")
            elif specialty_found and filtered_doctors:
                # Filtered by specialty - show filtered doctors in compact format
                doctors_list = []
                for doc in filtered_doctors:
                    doctors_list.append({
                        "doctor_name": doc.get('doctor_name', ''),
                        "specialty": doc.get('specialty', ''),
                        "branch_id": doc.get('branch_id', ''),
                        "days": doc.get('days', ''),
                        "time_from": doc.get('time_from', ''),
                        "time_to": doc.get('time_to', '')
                    })
                context_parts.append(f"أطباء {specialty_found} ({len(filtered_doctors)} طبيب):\n{json.dumps(doctors_list, ensure_ascii=False, indent=2)}")
            elif doctors:
                # All doctors - show in compact format
                doctors_list = []
                for doc in doctors:
                    doctors_list.append({
                        "doctor_name": doc.get('doctor_name', ''),
                        "specialty": doc.get('specialty', ''),
                        "branch_id": doc.get('branch_id', ''),
                        "days": doc.get('days', ''),
                        "time_from": doc.get('time_from', ''),
                        "time_to": doc.get('time_to', '')
                    })
                context_parts.append(f"الأطباء ({len(doctors)} طبيب):\n{json.dumps(doctors_list, ensure_ascii=False, indent=2)}")
        
        elif intent == "service":
            # Always get services data
            if 'services' in relevant_data:
                services = relevant_data['services']
            elif 'all_services' in relevant_data:
                services = relevant_data['all_services']
            else:
                services = data_handler.get_services()
            
            if service_name:
                # Specific service requested - include all available information
                service = data_handler.find_service_by_name(service_name)
                if service:
                    # Include comprehensive service information
                    service_info = {
                        "service_name": service.get('service_name', ''),
                        "specialty": service.get('specialty', ''),
                        "description": service.get('description', ''),
                        "price_sar": service.get('price_sar', ''),
                        "price_range": service.get('price_range', ''),
                        "duration_minutes": service.get('duration_minutes', ''),
                        "preparation_required": service.get('preparation_required', ''),
                        "available_branch_ids": service.get('available_branch_ids', ''),
                        "popular": service.get('popular', '')
                    }
                    context_parts.append(f"معلومات الخدمة المطلوبة (استخدم جميع المعلومات المتاحة):\n{json.dumps(service_info, ensure_ascii=False, indent=2)}")
                    
                    # Get branches where service is available
                    available_branch_ids = service.get('available_branch_ids', [])
                    if available_branch_ids:
                        branches = data_handler.get_branches()
                        available_branches = [b for b in branches if b.get('branch_id') in available_branch_ids]
                        if available_branches:
                            context_parts.append(f"الفروع المتاحة للخدمة:\n{json.dumps(available_branches, ensure_ascii=False, indent=2)}")
                    else:
                        # If no specific branches, show all branches
                        branches = data_handler.get_branches()
                        if branches:
                            context_parts.append(f"الفروع المتاحة:\n{json.dumps(branches, ensure_ascii=False, indent=2)}")
            elif services:
                # All services - show in compact format
                services_list = []
                for svc in services:
                    services_list.append({
                        "service_name": svc.get('service_name', ''),
                        "specialty": svc.get('specialty', ''),
                        "price_sar": svc.get('price_sar', ''),
                        "duration_minutes": svc.get('duration_minutes', '')
                    })
                context_parts.append(f"الخدمات ({len(services)} خدمة):\n{json.dumps(services_list, ensure_ascii=False, indent=2)}")
        
        elif intent == "branch":
            # Always get branches data
            if 'branches' in relevant_data:
                branches = relevant_data['branches']
            elif 'all_branches' in relevant_data:
                branches = relevant_data['all_branches']
            else:
                branches = data_handler.get_branches()
            
            if branch_id:
                # Specific branch requested
                branch = data_handler.get_branch_by_id(branch_id)
                if branch:
                    context_parts.append(f"معلومات الفرع المطلوب:\n{json.dumps(branch, ensure_ascii=False, indent=2)}")
            elif branches:
                # All branches - show in compact format
                branches_list = []
                for branch in branches:
                    branches_list.append({
                        "branch_name": branch.get('branch_name', ''),
                        "address": branch.get('address', ''),
                        "city": branch.get('city', ''),
                        "phone": branch.get('phone', ''),
                        "hours_weekdays": branch.get('hours_weekdays', ''),
                        "hours_weekend": branch.get('hours_weekend', '')
                    })
                context_parts.append(f"الفروع ({len(branches)} فرع):\n{json.dumps(branches_list, ensure_ascii=False, indent=2)}")
        
        # For hours questions, provide branch hours information
        elif intent == "hours":
            # Always get branches data with hours information
            if 'branches' in relevant_data:
                branches = relevant_data['branches']
            elif 'all_branches' in relevant_data:
                branches = relevant_data['all_branches']
            else:
                branches = data_handler.get_branches()
            
            if branches:
                branches_list = []
                for branch in branches:
                    branch_info = {
                        "branch_name": branch.get('branch_name', ''),
                        "hours_weekdays": branch.get('hours_weekdays', ''),
                        "hours_weekend": branch.get('hours_weekend', ''),
                        "address": branch.get('address', ''),
                        "city": branch.get('city', '')
                    }
                    branches_list.append(branch_info)
                context_parts.append(f"أوقات الدوام للفروع:\n{json.dumps(branches_list, ensure_ascii=False, indent=2)}")
        
        # For general questions, provide clinic information in compact format
        elif intent == "general":
            # Add available doctors (with more details)
            doctors = data_handler.get_doctors()
            if doctors:
                doctors_list = []
                for d in doctors:
                    doctors_list.append({
                        "doctor_name": d.get('doctor_name', ''),
                        "specialty": d.get('specialty', ''),
                        "branch_id": d.get('branch_id', ''),
                        "phone": d.get('phone', '')
                    })
                context_parts.append(f"الأطباء ({len(doctors)} طبيب):\n{json.dumps(doctors_list, ensure_ascii=False, indent=2)}")
            
            # Add available services (with more details)
            services = data_handler.get_services()
            if services:
                services_list = []
                for s in services:
                    services_list.append({
                        "service_name": s.get('service_name', ''),
                        "specialty": s.get('specialty', ''),
                        "price_sar": s.get('price_sar', ''),
                        "duration_minutes": s.get('duration_minutes', ''),
                        "description": s.get('description', '')
                    })
                context_parts.append(f"الخدمات ({len(services)} خدمة):\n{json.dumps(services_list, ensure_ascii=False, indent=2)}")
            
            # Add available branches (with more details)
            branches = data_handler.get_branches()
            if branches:
                branches_list = []
                for b in branches:
                    branches_list.append({
                        "branch_name": b.get('branch_name', ''),
                        "address": b.get('address', ''),
                        "city": b.get('city', ''),
                        "phone": b.get('phone', ''),
                        "hours_weekdays": b.get('hours_weekdays', ''),
                        "hours_weekend": b.get('hours_weekend', '')
                    })
                context_parts.append(f"الفروع ({len(branches)} فرع):\n{json.dumps(branches_list, ensure_ascii=False, indent=2)}")
        
        # Always include general data if not already included (with more details)
        if not context_parts:
            doctors = data_handler.get_doctors()
            services = data_handler.get_services()
            branches = data_handler.get_branches()
            if doctors:
                doctors_list = []
                for d in doctors:
                    doctors_list.append({
                        "doctor_name": d.get('doctor_name', ''),
                        "specialty": d.get('specialty', ''),
                        "branch_id": d.get('branch_id', ''),
                        "phone": d.get('phone', '')
                    })
                context_parts.append(f"الأطباء ({len(doctors)} طبيب):\n{json.dumps(doctors_list, ensure_ascii=False, indent=2)}")
            if services:
                services_list = []
                for s in services:
                    services_list.append({
                        "service_name": s.get('service_name', ''),
                        "specialty": s.get('specialty', ''),
                        "price_sar": s.get('price_sar', ''),
                        "duration_minutes": s.get('duration_minutes', ''),
                        "description": s.get('description', '')
                    })
                context_parts.append(f"الخدمات ({len(services)} خدمة):\n{json.dumps(services_list, ensure_ascii=False, indent=2)}")
            if branches:
                branches_list = []
                for b in branches:
                    branches_list.append({
                        "branch_name": b.get('branch_name', ''),
                        "address": b.get('address', ''),
                        "city": b.get('city', ''),
                        "phone": b.get('phone', ''),
                        "hours_weekdays": b.get('hours_weekdays', ''),
                        "hours_weekend": b.get('hours_weekend', '')
                    })
                context_parts.append(f"الفروع ({len(branches)} فرع):\n{json.dumps(branches_list, ensure_ascii=False, indent=2)}")
        
        return "\n\n".join(context_parts) if context_parts else "لا توجد بيانات محددة"

