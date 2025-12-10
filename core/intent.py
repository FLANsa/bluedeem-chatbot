"""Intent classification using GPT-4.1-nano with Structured Outputs."""
from typing import Dict, Any, List
from openai import OpenAI
import config
from models.schemas import IntentSchema, Entity


class IntentClassifier:
    """Intent classifier using GPT-4.1-nano."""
    
    def __init__(self):
        """Initialize intent classifier."""
        if not config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.model = config.LLM_MODEL_INTENT
    
    def classify(self, message: str, context: Dict[str, Any] = None) -> IntentSchema:
        """
        Classify intent and extract entities.
        
        Args:
            message: User message
            context: Optional context (previous messages, etc.)
            
        Returns:
            IntentSchema with intent, entities, confidence, next_action
        """
        system_prompt = """أنت مصنف نوايا لشات بوت عيادة. صنّف الرسالة وحدد الكيانات.

النوايا المتاحة:
- greeting: تحية
- doctor: سؤال عن طبيب
- branch: سؤال عن فرع
- service: سؤال عن خدمة
- booking: طلب حجز
- hours: سؤال عن الدوام
- contact: طلب التواصل
- faq: سؤال متكرر
- thanks: شكر
- goodbye: وداع
- unclear: غير واضح
- general: أسئلة عامة متعلقة بالعيادة (استفسارات، أسئلة شخصية عن البوت، أسئلة كيف/وين/متى المتعلقة بالعيادة)

الكيانات:
- doctor_name: اسم الطبيب
- service_name: اسم الخدمة
- branch_id: معرف الفرع
- phone: رقم الجوال
- date: تاريخ
- time: وقت

next_action:
- respond_directly: رد مباشر من البيانات
- ask_clarification: اسأل سؤال توضيحي
- use_llm: استخدم LLM للرد
- start_booking: ابدأ عملية الحجز

أمثلة:
- "عندي استفسار" → general + use_llm
- "ما اسمك؟" → general + use_llm
- "من أنت؟" → general + use_llm
- "كيف أحجز؟" → general + use_llm
- "وين العيادة؟" → general + use_llm"""
        
        try:
            # Use create() with response_format for structured outputs
            # In OpenAI 1.12.0, structured outputs use response_format with json_schema
            import json
            
            # Get JSON schema from Pydantic model
            json_schema = IntentSchema.model_json_schema()
            # OpenAI requires additionalProperties: false
            json_schema["additionalProperties"] = False
            # OpenAI requires all properties to be in required array
            if "properties" in json_schema:
                json_schema["required"] = list(json_schema["properties"].keys())
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "intent_classification",
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
                    result = IntentSchema(**data)
                    return result
                except Exception as parse_error:
                    # Fallback if parsing fails
                    return self._fallback_classify(message)
            else:
                return self._fallback_classify(message)
            
        except Exception as e:
            # Fallback to simple rule-based classification
            return self._fallback_classify(message)
    
    def _fallback_classify(self, message: str) -> IntentSchema:
        """Fallback rule-based classification."""
        message_lower = message.lower().strip()
        message_clean = message_lower.replace(' ', '').replace('،', '').replace(',', '')
        
        entities = []
        
        # Check for general questions first (before booking to avoid false positives)
        if any(word in message_lower for word in ['استفسار', 'سؤال', 'عندي سؤال', 'عندي استفسار', 'استفسارات']):
            intent = "general"
            next_action = "use_llm"
            return IntentSchema(
                intent=intent,
                entities=[],
                confidence=0.9,
                next_action=next_action
            )
        elif any(word in message_lower for word in ['ما اسمك', 'من انت', 'مين انت', 'من أنت', 'مين أنت']):
            intent = "general"
            next_action = "use_llm"
            return IntentSchema(
                intent=intent,
                entities=[],
                confidence=0.9,
                next_action=next_action
            )
        elif any(phrase in message_lower for phrase in ['كيف أحجز', 'كيف احجز', 'كيف اسوي حجز', 'كيف أسوي حجز', 'كيف احجز موعد']):
            intent = "general"
            next_action = "use_llm"
            return IntentSchema(
                intent=intent,
                entities=[],
                confidence=0.9,
                next_action=next_action
            )
        elif any(phrase in message_lower for phrase in ['وين العيادة', 'وين العياده', 'وينكم', 'وين أنتم']):
            intent = "general"
            next_action = "use_llm"
            return IntentSchema(
                intent=intent,
                entities=[],
                confidence=0.9,
                next_action=next_action
            )
        elif any(phrase in message_lower for phrase in ['متى الدوام', 'متى دوامكم', 'متى تفتحون', 'متى تفتح']):
            intent = "general"
            next_action = "use_llm"
            return IntentSchema(
                intent=intent,
                entities=[],
                confidence=0.9,
                next_action=next_action
            )
        
        # Check for booking with doctor name (after general questions)
        # Only trigger if explicitly requesting booking (not just asking about doctors)
        elif any(word in message_lower for word in ['احجز', 'حجز', 'موعد', 'ابي احجز', 'اريد احجز']) and any(word in message_lower for word in ['عند', 'مع', 'دكتور']):
            # Try to extract doctor name
            from data.handler import data_handler
            doctors = data_handler.get_doctors()
            best_match = None
            best_score = 0
            
            # Extract potential doctor name from message
            message_words = message_lower.split()
            potential_names = []
            
            # Find words after "دكتور" or "عند"
            for i, word in enumerate(message_words):
                if word in ['دكتور', 'دكتورة', 'عند', 'مع'] and i + 1 < len(message_words):
                    potential_name = ' '.join(message_words[i+1:i+4])
                    if len(potential_name.strip()) > 2:
                        potential_names.append(potential_name.strip())
            
            # If no explicit name found, use all words > 3 chars
            if not potential_names:
                potential_names = [w for w in message_words if len(w) > 3]
            
            # Use fuzzy matching
            from rapidfuzz import fuzz
            
            for doctor in doctors:
                doctor_name_full = doctor.get('doctor_name', '')
                doctor_name_lower = doctor_name_full.lower()
                name_clean = doctor_name_lower.replace('د.', '').replace('دكتورة', '').replace('دكتور', '').strip()
                
                # Try fuzzy matching with potential names
                for potential in potential_names:
                    # Exact match
                    if potential in name_clean or name_clean in potential:
                        score = 100
                        if score > best_score:
                            best_score = score
                            best_match = doctor_name_full
                    # Fuzzy match each word
                    else:
                        for word in potential.split():
                            if len(word) > 2:
                                for name_part in name_clean.split():
                                    if len(name_part) > 2:
                                        ratio = fuzz.ratio(word, name_part)
                                        if ratio > 70:  # 70% similarity
                                            if ratio > best_score:
                                                best_score = ratio
                                                best_match = doctor_name_full
                
                # Also check if full name (without titles) appears
                if name_clean in message_lower:
                    best_match = doctor_name_full
                    best_score = 100
                    break
            
            if best_match:
                entities.append({
                    'type': 'doctor_name',
                    'value': best_match,
                    'confidence': 0.9
                })
                return IntentSchema(
                    intent="booking",
                    entities=[Entity(**e) for e in entities],
                    confidence=0.9,
                    next_action="start_booking"
                )
            
            # Booking without specific doctor
            intent = "booking"
            next_action = "start_booking"
        
        # Check for questions about branches (but not if asking about specific doctor's branch)
        # First check if message contains doctor name
        from data.handler import data_handler
        has_doctor_name = False
        doctors = data_handler.get_doctors()
        for doctor in doctors:
            doctor_name = doctor.get('doctor_name', '').lower()
            name_parts = doctor_name.replace('د.', '').replace('دكتورة', '').replace('دكتور', '').strip().split()
            for part in name_parts:
                if len(part) > 3 and part in message_lower:
                    has_doctor_name = True
                    entities.append({
                        'type': 'doctor_name',
                        'value': doctor.get('doctor_name', ''),
                        'confidence': 0.8
                    })
                    break
            if has_doctor_name:
                break
        
        # If asking about branch but has doctor name, it's a doctor query
        if has_doctor_name and any(word in message_lower for word in ['فرع', 'وين', 'ب اي', 'في اي']):
            intent = "doctor"
            next_action = "use_llm"
        elif any(word in message_lower for word in ['وين فروع', 'وين فرع', 'فروعكم', 'فروع', 'فرع', 'عنوان', 'مكان', 'وين']):
            intent = "branch"
            next_action = "use_llm"
        
        # Simple keyword matching - check exact matches first
        elif message_clean in ['أطباء', 'اطباء', 'طبيب', 'دكتور', 'دكتورة']:
            intent = "doctor"
            next_action = "use_llm"
        elif message_clean in ['فروع', 'فرع', 'عنوان', 'مكان']:
            intent = "branch"
            next_action = "use_llm"
        elif message_clean in ['خدمات', 'خدمة', 'سعر', 'تكلفة']:
            intent = "service"
            next_action = "use_llm"
        elif message_clean in ['حجز', 'احجز', 'موعد']:
            # "حجز" alone is a question about booking, not a booking request
            # Only start booking if there are explicit booking keywords
            intent = "general"  # Treat as general question about booking
            next_action = "use_llm"
        
        # Greetings - expanded
        elif any(word in message_lower for word in ['مرحبا', 'أهلا', 'السلام', 'هاي', 'هلا', 'كيف حالك', 'كيفك', 'كيف الحال', 'السلام عليكم', 'وعليكم السلام']):
            intent = "greeting"
            next_action = "use_llm"
        
        # Doctor queries
        elif any(word in message_lower for word in ['طبيب', 'دكتور', 'دكتورة']):
            # Try to extract doctor name
            from data.handler import data_handler
            doctors = data_handler.get_doctors()
            for doctor in doctors:
                doctor_name = doctor.get('doctor_name', '').lower()
                name_parts = doctor_name.replace('د.', '').replace('دكتورة', '').replace('دكتور', '').strip().split()
                for part in name_parts:
                    if len(part) > 3 and part in message_lower:
                        entities.append({
                            'type': 'doctor_name',
                            'value': doctor.get('doctor_name', ''),
                            'confidence': 0.8
                        })
                        break
            intent = "doctor"
            next_action = "use_llm"
        
        # Service queries
        elif any(word in message_lower for word in ['خدمة', 'سعر', 'تكلفة', 'كم']):
            intent = "service"
            next_action = "use_llm"
        
        # Hours queries
        elif any(word in message_lower for word in ['دوام', 'ساعات', 'متى', 'وقت']):
            intent = "hours"
            next_action = "use_llm"
        
        # Thanks - expanded to catch "شكرا" and variations
        elif any(word in message_lower for word in ['شكر', 'شكرا', 'شكراً', 'مشكور', 'مشكورة', 'يعطيك', 'الله يعطيك', 'الله يعطيك العافية', 'تسلم', 'تسلمين']):
            intent = "thanks"
            next_action = "use_llm"
        
        # Goodbye
        elif any(word in message_lower for word in ['مع السلامة', 'باي', 'وداع', 'الله يوفقك']):
            intent = "goodbye"
            next_action = "use_llm"
        else:
            intent = "unclear"
            next_action = "ask_clarification"
        
        return IntentSchema(
            intent=intent,
            entities=[Entity(**e) for e in entities] if entities else [],
            confidence=0.8,
            next_action=next_action
        )

