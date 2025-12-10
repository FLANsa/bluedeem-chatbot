"""LLM agent using GPT-4.1-mini with Structured Outputs and Function Calling."""
from typing import Dict, Any, List
import json
from openai import OpenAI
import os
from cachetools import TTLCache
from models.schemas import AgentResponseSchema, make_schema_strict
from data.handler import data_handler
from core.context import context_manager
from utils.arabic_normalizer import normalize_ar


class ChatAgent:
    """Chat agent using GPT-4.1-mini."""
    
    def __init__(self):
        """Initialize chat agent."""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        self.client = OpenAI(api_key=api_key)
        self.model = os.getenv('LLM_MODEL_AGENT', 'gpt-4o-mini')
        self._schema = make_schema_strict(AgentResponseSchema.model_json_schema())
        # Cache responses for short window to reduce cost on repeated asks
        self._response_cache = TTLCache(maxsize=300, ttl=120)
    
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
        # Quick cache for repeated messages (same intent + normalized message + entities)
        cache_key = None
        try:
            norm_msg = normalize_ar(message) if message else ""
            ent_key = tuple(sorted([f"{e.get('type','')}:{e.get('value','')}" for e in entities]))
            cache_key = (intent, norm_msg, ent_key)
            if cache_key in self._response_cache:
                cached = self._response_cache[cache_key]
                return AgentResponseSchema(**cached)
        except Exception:
            pass

        FAST_INTENTS = {"greeting", "thanks", "goodbye"}
        if intent in FAST_INTENTS:
            if intent == "greeting":
                return AgentResponseSchema(
                    response_text="هلا والله 👋 شلون أقدر أخدمك؟ تبي أطباء ولا خدمات ولا فروع؟",
                    needs_clarification=True,
                    suggested_questions=["أطباء", "خدمات", "فروع", "مواعيد الدوام", "حجز"]
                )
            if intent == "thanks":
                return AgentResponseSchema(
                    response_text="العفو والله ✅ إذا تبي أي شي أنا حاضر.",
                    needs_clarification=False,
                    suggested_questions=["أطباء", "خدمات", "فروع", "حجز"]
                )
            if intent == "goodbye":
                return AgentResponseSchema(
                    response_text="حياك الله 👋 بأي وقت تحتاجنا.",
                    needs_clarification=False,
                    suggested_questions=[]
                )

        system_prompt = """أنت موظف استقبال محترف ودافئ في عيادة بلو ديم 🏥. مهمتك مساعدة المرضى بكل ود واحترافية.

شخصيتك وأسلوبك:
- أنت محترف ودافئ، تستخدم لغة طبيعية وودودة لكن احترافية
- بلهجة نجدية طبيعية ومريحة
- تفاعلي واستباقي: اقترح خطوات تالية أو أسئلة مفيدة
- ذكي في استخدام السياق: تربط الأسئلة الحالية بالمحادثة السابقة
- مرن في طول الرد: حسب نوع السؤال (بسيط = قصير، معقد = أطول)

قواعد أساسية:
1) طول الرد مرن: 2-6 جمل حسب الحاجة (أسئلة بسيطة = 2-3 جمل، أسئلة معقدة = 4-6 جمل)
2) لا تخترع أي معلومة؛ استخدم فقط البيانات المتوفرة في الرسالة
3) إذا ما فيه بيانات كافية: اسأل سؤال توضيحي واحد + اقترح 2–4 خيارات
4) لا تبدأ الحجز إلا بطلب صريح (\"ابي احجز\"/\"حجز\"/\"ابي موعد\")
5) قوائم (أطباء/فروع/خدمات): اعرض 3–6 عناصر مختصرة مع أهم معلومة
6) إيموجي قليلة: ✅ 📍 ⏰ 💰 (حد أقصى 2)

استخدام السياق بذكاء:
- اربط الأسئلة الحالية بالمحادثة السابقة
- إذا سأل المستخدم عن شيء تم ذكره سابقاً، استخدم السياق لفهم ما يقصده
- أبرز المعلومات المهمة من المحادثة السابقة
- كن استباقياً: اقترح خطوات تالية أو أسئلة مفيدة

شكل الرد حسب intent:
- greeting: رحّب بسرعة ودافئ + خيارات (أطباء/خدمات/فروع/دوام/حجز)
- doctor: لو doctor_name اعرض التخصص + الفرع + أوقات مختصرة + معلومات إضافية مفيدة. لو قائمة/تخصص اعرض 3–6 أسماء ثم اسأل عن التخصص
- service: لو service_name اعرض وصف مفيد + السعر/المدة إن وجدت. لو قائمة اعرض 3–6 خدمات مع السعر إن وجد
- branch: اعرض 2–4 فروع مع المدينة/عنوان مختصر + رقم/رابط إن وجد
- hours: اعرض ساعات الدوام لكل فرع بشكل واضح ومفيد
- booking: إذا طلب الحجز صراحة، اشرح الخطوات بوضوح واطلب 2–3 معلومات (الاسم، الجوال، الطبيب/الخدمة، الوقت المفضل)
- general/faq/contact: جاوب بشكل مفيد وواضح اعتماداً على البيانات، وإذا مبهم اسأل سؤال واحد فقط
- **unclear/faq (مهم جداً):** إذا كانت النية unclear أو faq، استخدم البيانات المتوفرة (الأطباء/الخدمات/الفروع) لفهم ما يقصده المستخدم ورد عليه بناءً على البيانات. لا تقل "ما قدرت أفهم" - حاول تفهم من السياق والبيانات المتوفرة ورد بشكل مفيد. إذا كان السؤال عن شيء موجود في البيانات، اذكره مباشرة
- **أسئلة متابعة (مهم جداً):** إذا كان المستخدم يسأل عن شيء تم ذكره في المحادثة السابقة (مثل: "هل بس هذولا؟" أو "غيرهم؟" أو "كم عددهم؟" أو "هل عندكم غيرهم؟")، استخدم المحادثة السابقة لفهم ما يقصده ورد عليه بناءً على البيانات المتوفرة. إذا كان السؤال عن "هل هناك المزيد؟" أو "غيرهم؟"، افحص البيانات وأخبره بالعدد الكامل أو إذا كان هناك المزيد

مخرجاتك يجب أن تكون JSON يطابق schema (response_text, needs_clarification, suggested_questions). response_text لازم يكون عربي نجدي طبيعي وواضح."""
        
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
        
        user_prompt_parts.append("\n**تعليمات مهمة للرد:**")
        user_prompt_parts.append("1. رد بلهجة نجدية طبيعية وودودة واحترافية")
        user_prompt_parts.append("2. طول الرد مرن: 2-6 جمل حسب نوع السؤال (بسيط = 2-3 جمل، معقد = 4-6 جمل)")
        user_prompt_parts.append("3. استخدم السياق بذكاء: اربط الأسئلة الحالية بالمحادثة السابقة")
        user_prompt_parts.append("4. كن استباقياً: اقترح خطوات تالية أو أسئلة مفيدة")
        user_prompt_parts.append("5. استخدم جميع المعلومات المتاحة من البيانات")
        user_prompt_parts.append("6. إذا كان المستخدم يسأل عن شيء تم ذكره في المحادثة السابقة (مثل: 'هل بس هذولا؟' أو 'غيرهم؟' أو 'كم عددهم؟')، استخدم المحادثة السابقة لفهم ما يقصده ورد عليه بناءً على البيانات المتوفرة")
        user_prompt_parts.append("7. لا تقل 'ما قدرت أفهم' - حاول تفهم من السياق والبيانات ورد بشكل مفيد")
        
        user_prompt = "\n".join(user_prompt_parts)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.4,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "agent_response",
                        "schema": self._schema,
                        "strict": True
                    }
                }
            )
            
            content = response.choices[0].message.content
            if content:
                try:
                    data = json.loads(content)
                    result = AgentResponseSchema(**data)
                    try:
                        if cache_key:
                            self._response_cache[cache_key] = result.dict()
                    except Exception:
                        pass
                    return result
                except Exception as parse_error:
                    raise Exception(f"Failed to parse response: {parse_error}")
            else:
                raise Exception("Empty response from API")
            
        except Exception as e:
            import logging
            logging.exception(f"Agent error: {e}")
            message_lower = message.lower()

            if intent == "doctor":
                return AgentResponseSchema(
                    response_text="تمام ✅ تبي قائمة كل الأطباء ولا تخصص معيّن؟ (أسنان/جلدية/أطفال/نساء)",
                    needs_clarification=True,
                    suggested_questions=["أطباء الأسنان", "أطباء الجلدية", "أطباء الأطفال", "كل الأطباء"]
                )
            if intent == "branch":
                return AgentResponseSchema(
                    response_text="أكيد 📍 تبي فروع أي مدينة؟ ولا أعطيك كل الفروع؟",
                    needs_clarification=True,
                    suggested_questions=["كل الفروع", "فروع الرياض", "فروع جدة"]
                )
            if intent == "service":
                return AgentResponseSchema(
                    response_text="على الرحب والسعة 💡 تبي قائمة الخدمات ولا خدمة معينة؟",
                    needs_clarification=True,
                    suggested_questions=["خدمات الأسنان", "خدمات الجلدية", "كل الخدمات"]
                )
            if intent == "booking":
                return AgentResponseSchema(
                    response_text="أساعدك بالحجز. عطيني اسمك ورقمك والخدمة أو الطبيب المفضل.",
                    needs_clarification=True,
                    suggested_questions=["حجز مع طبيب أسنان", "حجز خدمة جلدية", "حجز قريب موعد"]
                )
            if intent == "hours":
                return AgentResponseSchema(
                    response_text="أقدر أعطيك أوقات الدوام. تبي كل الفروع ولا مدينة معينة؟",
                    needs_clarification=True,
                    suggested_questions=["أوقات فروع الرياض", "أوقات فروع جدة", "كل الفروع"]
                )
            if intent == "contact":
                return AgentResponseSchema(
                    response_text="للتواصل: تبي أرقام أو موقع الفروع؟",
                    needs_clarification=True,
                    suggested_questions=["أرقام الفروع", "مواقع الفروع"]
                )
            if intent == "general":
                if "اسمك" in message_lower or "من أنت" in message_lower or "مين انت" in message_lower:
                    return AgentResponseSchema(
                        response_text="اسمي مساعد بلو ديم 🏥 كيف أقدر أساعدك اليوم؟ عندك استفسار عن أطباء أو خدمات أو حجز؟",
                        needs_clarification=False,
                        suggested_questions=["أطباء", "خدمات", "حجز", "فروع"]
                    )
                if "استفسار" in message_lower or "سؤال" in message_lower:
                    return AgentResponseSchema(
                        response_text="أهلاً! كيف أقدر أساعدك؟ عندك استفسار عن إيش؟ (أطباء/خدمات/حجز/فروع)",
                        needs_clarification=True,
                        suggested_questions=["أطباء", "خدمات", "حجز", "فروع"]
                    )
                if "كيف أحجز" in message_lower or "كيف احجز" in message_lower:
                    return AgentResponseSchema(
                        response_text="الحجز سهل! قولي اسم الطبيب أو الخدمة اللي تبيها، وأنا أساعدك تحجز. أو قولي 'حجز' للبدء.",
                        needs_clarification=False,
                        suggested_questions=["حجز", "أطباء", "خدمات"]
                    )
            
            # For unclear/faq intents, try to provide helpful response based on available data
            if intent in ["unclear", "faq"]:
                # Check if we have data available
                from data.handler import data_handler
                doctors = data_handler.get_doctors()
                services = data_handler.get_services()
                branches = data_handler.get_branches()
                
                # Try to understand the message and provide helpful response
                if doctors or services or branches:
                    # We have data - provide helpful response
                    options = []
                    if doctors:
                        options.append("أطباء")
                    if services:
                        options.append("خدمات")
                    if branches:
                        options.append("فروع")
                    
                    if options:
                        return AgentResponseSchema(
                            response_text=f"أهلاً! كيف أقدر أساعدك؟ عندك استفسار عن: {' أو '.join(options)}؟",
                            needs_clarification=True,
                            suggested_questions=options + ["حجز", "مواعيد الدوام"]
                        )
            
            # Last resort - but still helpful
            return AgentResponseSchema(
                response_text="أهلاً! كيف أقدر أساعدك؟ عندك استفسار عن أطباء أو خدمات أو فروع؟",
                needs_clarification=True,
                suggested_questions=["أطباء", "فروع", "خدمات", "حجز"]
            )
    
    def _prepare_context(self, intent: str, entities: List[Dict[str, Any]], context: Dict[str, Any] = None, relevant_data: Dict[str, Any] = None, message: str = "") -> str:
        """Prepare context data for LLM. Keep it minimal to reduce failures."""
        FAST_INTENTS = {"greeting", "thanks", "goodbye"}
        if intent in FAST_INTENTS:
            return ""

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
        
        message_lower = normalize_ar(message) if message else ""
        MAX_ITEMS = 12
        
        # Check for follow-up questions (like "هل بس هذولا؟" or "غيرهم؟" or "كم عددهم؟")
        # If detected, send full data instead of limited
        follow_up_keywords = ['بس', 'غيرهم', 'غيرها', 'غير', 'عددهم', 'عددها', 'كم', 'كلهم', 'كلها', 'كل', 'هذولا', 'هذولا', 'هذي', 'هذا']
        is_follow_up = any(keyword in message_lower for keyword in follow_up_keywords)
        
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
                    filtered_doctors = [d for d in doctors if normalize_ar(d.get('specialty', '')) == normalize_ar(specialty)]
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
                total = len(filtered_doctors)
                # If follow-up question, send all data; otherwise limit
                if is_follow_up:
                    context_parts.append(f"أطباء {specialty_found} (العدد الكامل: {total}):\n{json.dumps(doctors_list, ensure_ascii=False, indent=2)}")
                else:
                    doctors_list = doctors_list[:MAX_ITEMS]
                    context_parts.append(f"أطباء {specialty_found} (عرض {len(doctors_list)} من أصل {total}):\n{json.dumps(doctors_list, ensure_ascii=False, indent=2)}")
            elif doctors:
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
                total = len(doctors_list)
                doctors_list = doctors_list[:MAX_ITEMS]
                context_parts.append(f"الأطباء (عرض {len(doctors_list)} من أصل {total}):\n{json.dumps(doctors_list, ensure_ascii=False, indent=2)}")
        
        elif intent == "service":
            if 'services' in relevant_data:
                services = relevant_data['services']
            elif 'all_services' in relevant_data:
                services = relevant_data['all_services']
            else:
                services = data_handler.get_services()
            
            if service_name:
                service = data_handler.find_service_by_name(service_name)
                if service:
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
                    context_parts.append(f"معلومات الخدمة المطلوبة:\n{json.dumps(service_info, ensure_ascii=False, indent=2)}")
                    
                    available_branch_ids = service.get('available_branch_ids', [])
                    if available_branch_ids:
                        branches = data_handler.get_branches()
                        available_branches = [b for b in branches if b.get('branch_id') in available_branch_ids]
                        if available_branches:
                            context_parts.append(f"الفروع المتاحة للخدمة:\n{json.dumps(available_branches[:MAX_ITEMS], ensure_ascii=False, indent=2)}")
            elif services:
                services_list = []
                for svc in services:
                    services_list.append({
                        "service_name": svc.get('service_name', ''),
                        "specialty": svc.get('specialty', ''),
                        "price_sar": svc.get('price_sar', ''),
                        "duration_minutes": svc.get('duration_minutes', '')
                    })
                total = len(services_list)
                services_list = services_list[:MAX_ITEMS]
                context_parts.append(f"الخدمات (عرض {len(services_list)} من أصل {total}):\n{json.dumps(services_list, ensure_ascii=False, indent=2)}")
        
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
                total = len(branches_list)
                branches_list = branches_list[:MAX_ITEMS]
                context_parts.append(f"الفروع (عرض {len(branches_list)} من أصل {total}):\n{json.dumps(branches_list, ensure_ascii=False, indent=2)}")
        
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
                total = len(branches_list)
                branches_list = branches_list[:MAX_ITEMS]
                context_parts.append(f"أوقات الدوام للفروع (عرض {len(branches_list)} من أصل {total}):\n{json.dumps(branches_list, ensure_ascii=False, indent=2)}")
        
        # For general questions، قدم ملخصاً صغيراً فقط
        elif intent == "general":
            try:
                counts = {
                    "doctors": len(data_handler.get_doctors() or []),
                    "services": len(data_handler.get_services() or []),
                    "branches": len(data_handler.get_branches() or [])
                }
                context_parts.append(f"ملخص سريع: أطباء={counts['doctors']}, خدمات={counts['services']}, فروع={counts['branches']}")
            except Exception:
                pass
        
        # For unclear/faq intents, provide comprehensive data so LLM can understand and respond
        elif intent in ["unclear", "faq"]:
            # Get all available data
            doctors = relevant_data.get('doctors') or relevant_data.get('all_doctors') or data_handler.get_doctors()
            services = relevant_data.get('services') or relevant_data.get('all_services') or data_handler.get_services()
            branches = relevant_data.get('branches') or relevant_data.get('all_branches') or data_handler.get_branches()
            
            # Send summary of available data (limited to avoid huge prompts)
            if doctors:
                doctors_summary = []
                for doc in doctors[:6]:  # Top 6 only
                    name = doc.get('doctor_name', '')
                    specialty = doc.get('specialty', '')
                    if name:
                        doctors_summary.append({"name": name, "specialty": specialty})
                if doctors_summary:
                    context_parts.append(f"الأطباء المتاحون (عرض {len(doctors_summary)} من أصل {len(doctors)}):\n{json.dumps(doctors_summary, ensure_ascii=False, indent=2)}")
            
            if services:
                services_summary = []
                for svc in services[:6]:  # Top 6 only
                    name = svc.get('service_name', '')
                    specialty = svc.get('specialty', '')
                    price = svc.get('price_sar', '')
                    if name:
                        services_summary.append({"name": name, "specialty": specialty, "price": price})
                if services_summary:
                    context_parts.append(f"الخدمات المتاحة (عرض {len(services_summary)} من أصل {len(services)}):\n{json.dumps(services_summary, ensure_ascii=False, indent=2)}")
            
            if branches:
                branches_summary = []
                for branch in branches[:4]:  # Top 4 only
                    name = branch.get('branch_name', '')
                    city = branch.get('city', '')
                    address = branch.get('address', '')
                    if name:
                        branches_summary.append({"name": name, "city": city, "address": address})
                if branches_summary:
                    context_parts.append(f"الفروع المتاحة (عرض {len(branches_summary)} من أصل {len(branches)}):\n{json.dumps(branches_summary, ensure_ascii=False, indent=2)}")
        
        return "\n\n".join(context_parts) if context_parts else "لا توجد بيانات محددة"

