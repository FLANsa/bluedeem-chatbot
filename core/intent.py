"""Intent classification using GPT-4.1-nano with Structured Outputs."""
from typing import Dict, Any, List
from openai import OpenAI
import os
import json
from models.schemas import IntentSchema, Entity
from utils.arabic_normalizer import normalize_ar
from utils.entity_extractor import quick_extract_entities, merge_entities
from rapidfuzz import process


def make_schema_strict(schema: dict) -> dict:
    """
    Recursively enforce OpenAI Structured Outputs strictness.
    
    Applies additionalProperties=False and required arrays to all nested objects.
    
    Args:
        schema: JSON schema dictionary
        
    Returns:
        Strict schema dictionary
    """
    if isinstance(schema, dict):
        t = schema.get("type")
        
        if t == "object":
            schema["additionalProperties"] = False
            props = schema.get("properties", {})
            if props:
                schema["required"] = list(props.keys())
                for k, v in props.items():
                    props[k] = make_schema_strict(v)
        
        elif t == "array":
            if "items" in schema:
                schema["items"] = make_schema_strict(schema["items"])
        
        else:
            # Handle nested schemas like anyOf/oneOf/allOf
            for key in ("anyOf", "oneOf", "allOf"):
                if key in schema and isinstance(schema[key], list):
                    schema[key] = [make_schema_strict(s) for s in schema[key]]
        
        # Handle $defs / definitions
        for key in ("$defs", "definitions"):
            if key in schema and isinstance(schema[key], dict):
                schema[key] = {k: make_schema_strict(v) for k, v in schema[key].items()}
    
    return schema


class IntentClassifier:
    """Intent classifier using GPT-4.1-nano with optimized performance."""
    
    def __init__(self):
        """Initialize intent classifier."""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        self.client = OpenAI(api_key=api_key)
        self.model = os.getenv('LLM_MODEL_INTENT', 'gpt-4o-mini')
        
        # Load doctors data once (performance optimization)
        try:
            from data.handler import data_handler
            self._doctors = data_handler.get_doctors()
            # Prepare normalized doctor names for fast matching
            self._doctor_names = [d.get("doctor_name", "") for d in self._doctors if d.get("doctor_name")]
            self._doctor_names_normalized = [normalize_ar(name) for name in self._doctor_names]
        except Exception:
            self._doctors = []
            self._doctor_names = []
            self._doctor_names_normalized = []
        
        # Prepare schema once (performance optimization)
        json_schema = IntentSchema.model_json_schema()
        self._schema = make_schema_strict(json_schema)
        
        # System prompt with improved examples
        self._system_prompt = """أنت مصنف نوايا لشات بوت عيادة. صنّف الرسالة وحدد الكيانات.

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
- doctor_name: اسم الطبيب (قد يكتب "د." أو "دكتور" أو "دكتورة" قبل الاسم)
- service_name: اسم الخدمة
- branch_id: معرف الفرع
- phone: رقم الجوال السعودي
- date: تاريخ (اليوم، بكرا، بعد بكرا، يوم الأسبوع)
- time: وقت (HH:MM)

next_action:
- respond_directly: رد مباشر من البيانات
- ask_clarification: اسأل سؤال توضيحي (استخدم عندما تحتاج معلومات إضافية)
- use_llm: استخدم LLM للرد
- start_booking: ابدأ عملية الحجز (فقط عند طلب صريح للحجز)

قواعد مهمة:
- **مهم جداً:** "اهلا" أو "هلا" أو "مرحبا" أو "هاي" → intent=greeting + use_llm (دائماً!)
- إذا كانت الرسالة فيها "حجز" بدون (فرع/طبيب/خدمة/وقت واضح) → intent=booking و next_action=ask_clarification
- إذا "وين" أو "الموقع" أو "موقع" أو "عطني الموقع" → intent=branch + use_llm
- إذا "مين" مع "اطباء" أو "دكاتره" أو "دكاترة" → intent=doctor + use_llm (مهم جداً!)
- إذا "مين اطباء" مع تخصص (أسنان/جلدية/أطفال/عظام/نساء) → intent=doctor + use_llm
- إذا "متى" مع "تفتح" أو "دوام" → intent=hours
- إذا "شكر" أو "تمام" → intent=thanks

أمثلة:
- "هلا" → greeting + use_llm
- "السلام عليكم" → greeting + use_llm
- "مرحبا" → greeting + use_llm
- "عندي استفسار" → general + use_llm
- "ما اسمك؟" → general + use_llm
- "من أنت؟" → general + use_llm
- "كيف أحجز؟" → general + use_llm
- "وين العيادة؟" → branch + use_llm
- "عطني الموقع" → branch + use_llm
- "الموقع" → branch + use_llm
- "متى تفتحون؟" → hours + use_llm
- "متى اوقات الدوام؟" → hours + use_llm
- "متى تفتح الفروع؟" → hours + use_llm
- "مين الاطباء الي عندكم؟" → doctor + use_llm
- "مين الدكاتره الي عندكم" → doctor + use_llm
- "مين اطباء الاسنان الموجودين؟" → doctor + use_llm
- "مين اطباء الاطفال" → doctor + use_llm
- "مين اطباء الجلدية" → doctor + use_llm
- "قائمة الأطباء" → doctor + use_llm
- "حجز" → booking + ask_clarification
- "ابي احجز" → booking + ask_clarification
- "ابي احجز عند د. محمد" → booking + start_booking + doctor_name="د. محمد"
- "شكرا" → thanks + use_llm
- "تمام" → thanks + use_llm"""
    
    def classify(self, message: str, context: Dict[str, Any] = None) -> IntentSchema:
        """
        Classify intent and extract entities.
        
        Process:
        1. Quick entity extraction (Regex + normalization)
        2. Quick greeting/thanks/goodbye check (before LLM for speed)
        3. LLM Structured Output
        4. Merge entities
        5. Fallback if needed
        
        Args:
            message: User message
            context: Optional context (previous messages, etc.)
            
        Returns:
            IntentSchema with intent, entities, confidence, next_action
        """
        # 1) Quick entity extraction before LLM
        extracted_entities = quick_extract_entities(message)
        
        # 2) Quick check for common intents (greeting/thanks/goodbye/doctor) before LLM
        message_normalized = normalize_ar(message)
        message_lower = message_normalized.lower().strip()
        message_clean = message_lower.replace(' ', '').replace('،', '').replace(',', '')
        message_original_lower = message.strip().lower()
        
        # Greetings - check FIRST (before anything else) for simple greetings
        # This is critical for first messages like "اهلا" or "هلا"
        simple_greetings = ['هلا', 'اهلا', 'مرحبا', 'هاي', 'أهلا', 'أهلاً', 'هلاً']
        if (message_clean in simple_greetings or 
            message_original_lower in simple_greetings or
            message_clean.startswith('هلا') or 
            message_clean.startswith('اهلا') or
            message_original_lower.startswith('هلا') or
            message_original_lower.startswith('اهلا')):
            return IntentSchema(
                intent="greeting",
                entities=[Entity(**e) for e in extracted_entities] if extracted_entities else [],
                confidence=0.98,
                next_action="use_llm"
            )
        
        # Doctor queries with "مين اطباء" - check early (but after greetings)
        if ('مين' in message_lower and ('اطباء' in message_lower or 'دكاتره' in message_lower or 'دكاترة' in message_lower)):
            return IntentSchema(
                intent="doctor",
                entities=[Entity(**e) for e in extracted_entities] if extracted_entities else [],
                confidence=0.95,
                next_action="use_llm"
            )
        
        # Greetings - extended check for longer greetings
        greeting_keywords = ['مرحبا', 'اهلا', 'السلام', 'هاي', 'هلا', 'كيف حالك', 'كيفك', 'السلام عليكم', 'وعليكم السلام']
        if any(keyword in message_lower for keyword in greeting_keywords):
            return IntentSchema(
                intent="greeting",
                entities=[Entity(**e) for e in extracted_entities] if extracted_entities else [],
                confidence=0.95,
                next_action="use_llm"
            )
        
        # Thanks - check second
        thanks_keywords = ['شكر', 'شكرا', 'مشكور', 'مشكورة', 'يعطيك', 'الله يعطيك', 'تسلم', 'تسلمين', 'تمام']
        if any(keyword in message_lower for keyword in thanks_keywords):
            return IntentSchema(
                intent="thanks",
                entities=[Entity(**e) for e in extracted_entities] if extracted_entities else [],
                confidence=0.95,
                next_action="use_llm"
            )
        
        # Goodbye - check third
        goodbye_keywords = ['مع السلامة', 'باي', 'وداع', 'الله يوفقك']
        if any(keyword in message_lower for keyword in goodbye_keywords):
            return IntentSchema(
                intent="goodbye",
                entities=[Entity(**e) for e in extracted_entities] if extracted_entities else [],
                confidence=0.95,
                next_action="use_llm"
            )
        
        # 3) LLM Structured Output
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": message}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "intent_classification",
                        "schema": self._schema,
                        "strict": True
                    }
                },
                temperature=0,  # Deterministic classification
            )
            
            # Parse the response
            content = response.choices[0].message.content
            if content:
                try:
                    data = json.loads(content)
                    
                    # Merge entities (LLM + Regex)
                    llm_entities = data.get("entities", [])
                    merged_entities = merge_entities(llm_entities, extracted_entities)
                    data["entities"] = merged_entities
                    
                    result = IntentSchema(**data)
                    return result
                except Exception as parse_error:
                    # Fallback if parsing fails
                    return self._fallback_classify(message, extracted_entities)
            else:
                return self._fallback_classify(message, extracted_entities)
            
        except Exception as e:
            # Fallback to simple rule-based classification
            return self._fallback_classify(message, extracted_entities)
    
    def _fallback_classify(self, message: str, extracted_entities: List[Dict] = None) -> IntentSchema:
        """
        Simplified fallback rule-based classification.
        
        Only covers: greeting/thanks/goodbye + hours with clear keywords + explicit booking.
        Rest is left to LLM (gpt-4.1-nano is fast).
        
        Args:
            message: User message
            extracted_entities: Pre-extracted entities from Regex
            
        Returns:
            IntentSchema
        """
        if extracted_entities is None:
            extracted_entities = []
        
        message_lower = normalize_ar(message)  # Use normalized Arabic
        message_clean = message_lower.replace(' ', '').replace('،', '').replace(',', '')
        
        entities = list(extracted_entities) if extracted_entities else []
        
        # Greetings - clear keywords (already handled in classify, but keep as fallback)
        greeting_keywords = ['مرحبا', 'اهلا', 'السلام', 'هاي', 'هلا', 'كيف حالك', 'كيفك', 'السلام عليكم', 'وعليكم السلام']
        # Check exact matches first for common greetings
        if (message_clean in ['هلا', 'اهلا', 'مرحبا', 'هاي'] or 
            any(keyword in message_lower for keyword in greeting_keywords)):
            return IntentSchema(
                intent="greeting",
                entities=[Entity(**e) for e in entities] if entities else [],
                confidence=0.9,
                next_action="use_llm"
            )
        
        # Thanks - clear keywords
        if any(word in message_lower for word in ['شكر', 'شكرا', 'مشكور', 'مشكورة', 'يعطيك', 'الله يعطيك', 'تسلم', 'تسلمين', 'تمام']):
            return IntentSchema(
                intent="thanks",
                entities=[Entity(**e) for e in entities] if entities else [],
                confidence=0.9,
                next_action="use_llm"
            )
        
        # Goodbye - clear keywords
        if any(word in message_lower for word in ['مع السلامة', 'باي', 'وداع', 'الله يوفقك']):
            return IntentSchema(
                intent="goodbye",
                entities=[Entity(**e) for e in entities] if entities else [],
                confidence=0.9,
                next_action="use_llm"
            )
        
        # Hours - clear keywords
        if any(phrase in message_lower for phrase in [
            'متى تفتح', 'متى تفتحون', 'اوقات الدوام', 'متى الدوام',
            'متى دوامكم', 'متى الفروع تفتح', 'اوقات الفروع', 'اوقات العمل'
        ]):
            return IntentSchema(
                intent="hours",
                entities=[Entity(**e) for e in entities] if entities else [],
                confidence=0.9,
                next_action="use_llm"
            )
        
        # Explicit booking - very clear keywords only
        if any(phrase in message_lower for phrase in ['ابي احجز', 'اريد احجز', 'حاب احجز']) and any(word in message_lower for word in ['عند', 'مع', 'دكتور']):
            # Try to extract doctor name using rapidfuzz
            if self._doctor_names:
                # Use rapidfuzz for fast matching
                message_normalized = normalize_ar(message)
                best_match = process.extractOne(
                    message_normalized,
                    self._doctor_names_normalized,
                    score_cutoff=60  # 60% similarity threshold
                )
                
                if best_match:
                    # Find original doctor name
                    match_index = self._doctor_names_normalized.index(best_match[0])
                    doctor_name = self._doctor_names[match_index]
                    entities.append({
                        'type': 'doctor_name',
                        'value': doctor_name,
                        'confidence': 0.9
                    })
            
            return IntentSchema(
                intent="booking",
                entities=[Entity(**e) for e in entities] if entities else [],
                confidence=0.9,
                next_action="start_booking"
            )
        
        # Check for "مين اطباء" patterns - very common doctor queries
        if ('مين' in message_lower and ('اطباء' in message_lower or 'دكاتره' in message_lower or 'دكاترة' in message_lower)):
            return IntentSchema(
                intent="doctor",
                entities=[Entity(**e) for e in entities] if entities else [],
                confidence=0.95,
                next_action="use_llm"
            )
        
        # Check for simple keywords that should be handled
        # "أطباء" or "اطباء" (after normalization) → doctor
        if message_clean in ['اطباء', 'أطباء', 'طبيب', 'دكتور', 'دكتورة']:
            return IntentSchema(
                intent="doctor",
                entities=[Entity(**e) for e in entities] if entities else [],
                confidence=0.9,
                next_action="use_llm"
            )
        
        # "فروع" or "فرع" → branch
        if message_clean in ['فروع', 'فرع', 'عنوان', 'مكان']:
            return IntentSchema(
                intent="branch",
                entities=[Entity(**e) for e in entities] if entities else [],
                confidence=0.9,
                next_action="use_llm"
            )
        
        # "خدمات" or "خدمة" → service
        if message_clean in ['خدمات', 'خدمة']:
            return IntentSchema(
                intent="service",
                entities=[Entity(**e) for e in entities] if entities else [],
                confidence=0.9,
                next_action="use_llm"
            )
        
        # If nothing matches, return unclear (let LLM handle it)
        return IntentSchema(
            intent="unclear",
            entities=[Entity(**e) for e in entities] if entities else [],
            confidence=0.5,
            next_action="ask_clarification"
        )
