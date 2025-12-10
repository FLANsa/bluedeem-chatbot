"""
Intent classification using GPT-4.1-nano with Structured Outputs + strong rule-based scorer.

- Fast high-confidence rules first (no LLM).

- LLM Structured Outputs when uncertain.

- Robust caching with sha256 key.

- Arabic normalization everywhere.
"""


from __future__ import annotations


from typing import Dict, Any, List, Optional, Tuple
import os
import json
import re
import hashlib
from cachetools import TTLCache
from openai import OpenAI
from rapidfuzz import process


from models.schemas import IntentSchema, Entity
from utils.arabic_normalizer import normalize_ar
from utils.entity_extractor import quick_extract_entities, merge_entities


# ---------------------------
# JSON Schema strict helper
# ---------------------------


def make_schema_strict(schema: dict) -> dict:
    """Recursively enforce strict JSON schema for OpenAI Structured Outputs."""
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
            for key in ("anyOf", "oneOf", "allOf"):
                if key in schema and isinstance(schema[key], list):
                    schema[key] = [make_schema_strict(s) for s in schema[key]]

        for key in ("$defs", "definitions"):
            if key in schema and isinstance(schema[key], dict):
                schema[key] = {k: make_schema_strict(v) for k, v in schema[key].items()}

    return schema


# ---------------------------
# Constants / keywords
# ---------------------------


SIMPLE_GREETINGS = {"هلا", "اهلا", "أهلا", "اهلاً", "أهلاً", "مرحبا", "هاي", "هلاً"}

GREETING_HINTS = ["السلام عليكم", "وعليكم السلام", "شلونك", "كيفك", "هلا", "اهلا", "مرحبا", "هاي", "السلام"]


THANKS_HINTS = ["شكرا", "شكراً", "شكر", "مشكور", "مشكورة", "يعطيك", "الله يعطيك", "تسلم", "تسلمين", "تمام", "بيض الله وجهك"]

GOODBYE_HINTS = ["مع السلامة", "باي", "وداع", "الله يوفقك", "يلا سلام", "نشوفك", "في امان الله"]


HOURS_HINTS = [
    "متى تفتح", "متى تفتحون", "اوقات الدوام", "اوقات العمل", "متى الدوام", "ساعات العمل",
    "متى تفتح الفروع", "متى الفروع تفتح", "اوقات الفروع", "دوامكم"
]


BRANCH_HINTS = ["وين", "الموقع", "موقع", "عنوان", "فروع", "فرع", "مكانكم", "لوكيشن", "لوكيشنكم"]

SERVICE_HINTS = ["خدمة", "خدمات", "سعر", "اسعار", "كم سعر", "تكلفة", "بكم", "كم تكلف", "مدة", "كم دقيقة"]


BOOKING_WORDS = ["حجز", "احجز", "موعد", "ابي احجز", "أبي احجز", "ابغى احجز", "أبغى احجز", "ابي موعد", "أبي موعد", "ابغى موعد"]

BOOKING_STRICT = ["ابي احجز", "أبي احجز", "ابغى احجز", "أبغى احجز", "ابي موعد", "أبي موعد", "ابغى موعد", "أبغى موعد"]


GENERAL_HINTS = ["استفسار", "سؤال", "عندي سؤال", "عندي استفسار", "من انت", "مين انت", "ما اسمك", "اسمك", "كيف احجز", "شلون احجز", "طريقة الحجز"]


WANT_VERBS = ["ابي", "أبي", "ابغى", "أبغى", "اريد", "أريد", "احتاج", "أحتاج", "دلني", "رشح", "اقترح"]

HAVE_VERBS = ["عندي", "معي", "عندنا"]  # نستخدمها بحذر (كثير منها وصف حالة)


SPECIALTY_MAP = {
    "اسنان": "أسنان",
    "جلدية": "جلدية",
    "اطفال": "أطفال",
    "عظام": "عظام",
    "نساء": "نساء وولادة",
    "ولادة": "نساء وولادة",
    "باطنية": "باطنية",
}
SPECIALTY_KEYS = set(SPECIALTY_MAP.keys())


DOCTOR_LIST_HINTS = ["مين الاطباء", "مين أطباء", "قائمة الاطباء", "قائمة الأطباء", "اسماء الاطباء", "أسماء الأطباء", "مين الدكاتره", "مين الدكاترة"]

BEST_DOCTOR_HINTS = ["مين احسن", "مين أفضل", "مين افضل", "افضل", "أحسن", "احسن"]


def _clean_key(s: str) -> str:
    s = s.strip()
    s = re.sub(r"[^\w\u0600-\u06FF]+", "", s, flags=re.UNICODE)  # remove punctuation (keep Arabic)
    return s


def _sha_key(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _extract_name_hint(msg_norm: str) -> str:
    # msg_norm already normalized; keep simple triggers
    tokens = msg_norm.split()
    triggers = {"دكتور", "دكتوره", "دكتورة", "د", "د.", "مع", "عند"}
    for i, t in enumerate(tokens):
        if t in triggers and i + 1 < len(tokens):
            return " ".join(tokens[i + 1 : i + 4])
    return msg_norm


# ---------------------------
# Classifier
# ---------------------------


class IntentClassifier:
    """Hybrid intent classifier: high-confidence rules + LLM structured outputs."""

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        self.client = OpenAI(api_key=api_key)
        self.model = os.getenv("LLM_MODEL_INTENT", "gpt-4o-mini")

        # Cache: intent results for 5 minutes
        self._intent_cache: TTLCache[str, dict] = TTLCache(maxsize=800, ttl=300)

        # Load doctors once for fast name matching (optional)
        self._doctor_names: List[str] = []
        self._doctor_names_norm: List[str] = []
        try:
            from data.handler import data_handler
            doctors = data_handler.get_doctors() or []
            self._doctor_names = [d.get("doctor_name", "") for d in doctors if d.get("doctor_name")]
            self._doctor_names_norm = [normalize_ar(n).lower().strip() for n in self._doctor_names]
        except Exception:
            pass

        # Strict schema once
        schema = IntentSchema.model_json_schema()
        self._schema = make_schema_strict(schema)

        # Keep prompt short + strong rules
        self._system_prompt = """أنت مصنف نوايا لشات بوت عيادة. أعطِ نتيجة JSON مطابقة للـ schema فقط.

النوايا: greeting, doctor, branch, service, booking, hours, contact, faq, thanks, goodbye, general, unclear
الكيانات: doctor_name, service_name, branch_id, phone, date, time
next_action: respond_directly, ask_clarification, use_llm, start_booking

قواعد:
- التحية (هلا/اهلا/مرحبا/السلام عليكم/هاي) => greeting + use_llm
- الشكر (شكرا/تمام/يعطيك العافية) => thanks + use_llm
- الوداع (باي/مع السلامة) => goodbye + use_llm
- أوقات الدوام (متى تفتحون/اوقات الدوام) => hours + use_llm
- الفروع/الموقع (وين/الموقع/عنوان/فرع/فروع) => branch + use_llm
- الخدمات/الأسعار (خدمة/سعر/تكلفة/بكم) => service + use_llm
- الحجز: إذا طلب صريح (حجز/احجز/موعد) => booking
  - إذا ما فيه تفاصيل كافية => booking + ask_clarification
  - إذا فيه (doctor_name أو service_name أو date/time) => booking + start_booking
- الأطباء: (مين الأطباء/قائمة الأطباء/أبي طبيب/أفضل دكتور/أحسن طبيب) => doctor + use_llm
- unclear فقط إذا الرسالة ما تنطبق على شيء."""

    def classify(self, message: str, context: Dict[str, Any] | None = None) -> IntentSchema:
        msg = (message or "").strip()
        if not msg:
            return self._make("unclear", [], 0.5, "ask_clarification")

        msg_norm = normalize_ar(msg).lower().strip()
        msg_clean = _clean_key(msg_norm)

        cache_key = _sha_key(msg_norm)
        if cache_key in self._intent_cache:
            return IntentSchema(**self._intent_cache[cache_key])

        extracted = quick_extract_entities(msg) or []

        # -------------------------
        # High-confidence scorer
        # -------------------------
        scores = {
            "greeting": 0,
            "thanks": 0,
            "goodbye": 0,
            "hours": 0,
            "branch": 0,
            "service": 0,
            "booking": 0,
            "doctor": 0,
            "general": 0,
        }

        # greeting (very strong)
        if msg_clean in {_clean_key(x) for x in SIMPLE_GREETINGS} or msg_clean.startswith(("هلا", "اهلا")):
            scores["greeting"] += 12
        if any(k in msg_norm for k in GREETING_HINTS):
            scores["greeting"] += 7

        # thanks/goodbye
        if any(k in msg_norm for k in THANKS_HINTS):
            scores["thanks"] += 10
        if any(k in msg_norm for k in GOODBYE_HINTS):
            scores["goodbye"] += 10

        # booking
        if any(k in msg_norm for k in BOOKING_WORDS):
            scores["booking"] += 9
            if any(k in msg_norm for k in BOOKING_STRICT):
                scores["booking"] += 2

        # hours / branch / service
        if any(k in msg_norm for k in HOURS_HINTS):
            scores["hours"] += 9
        if any(k in msg_norm for k in BRANCH_HINTS):
            scores["branch"] += 7
        if any(k in msg_norm for k in SERVICE_HINTS):
            scores["service"] += 6

        # doctor list queries
        if any(k in msg_norm for k in DOCTOR_LIST_HINTS) or ("مين" in msg_norm and ("اطباء" in msg_norm or "دكاتره" in msg_norm or "دكاترة" in msg_norm)):
            scores["doctor"] += 9

        # "best doctor" queries -> doctor (but agent must avoid ranking; classification is doctor)
        if "مين" in msg_norm and any(k in msg_norm for k in BEST_DOCTOR_HINTS):
            if any(x in msg_norm for x in ["طبيب", "دكتور", "دكتورة", "دكاتره", "دكاترة"]) or any(s in msg_norm for s in SPECIALTY_KEYS):
                scores["doctor"] += 8

        # "I want doctor" -> only with WANT verbs (avoid 'عندي طبيب ...')
        if any(v in msg_norm for v in WANT_VERBS):
            if any(s in msg_norm for s in SPECIALTY_KEYS) or any(x in msg_norm for x in ["طبيب", "دكتور", "دكتورة"]):
                scores["doctor"] += 7

        # general hints
        if any(k in msg_norm for k in GENERAL_HINTS):
            scores["general"] += 8

        # Resolve strong intent without LLM
        best_intent, best_score = max(scores.items(), key=lambda x: x[1])

        # Entity-based next_action for booking
        def booking_action() -> str:
            has_key = any(e.get("type") in {"doctor_name", "service_name", "date", "time"} for e in extracted)
            return "start_booking" if has_key else "ask_clarification"

        # Priority overrides (avoid false conflicts)
        if scores["greeting"] >= 10:
            res = self._make("greeting", extracted, 0.98, "use_llm")
            self._cache(cache_key, res)
            return res

        if scores["thanks"] >= 10:
            res = self._make("thanks", extracted, 0.97, "use_llm")
            self._cache(cache_key, res)
            return res

        if scores["goodbye"] >= 10:
            res = self._make("goodbye", extracted, 0.97, "use_llm")
            self._cache(cache_key, res)
            return res

        if scores["booking"] >= 9:
            # try doctor name hint only when booking + with triggers
            extracted2 = self._maybe_add_doctor_name(msg_norm, extracted)
            res = self._make("booking", extracted2, 0.92, booking_action())
            self._cache(cache_key, res)
            return res

        if scores["hours"] >= 9:
            res = self._make("hours", extracted, 0.92, "use_llm")
            self._cache(cache_key, res)
            return res

        # If short message (<= 2 words) and contains branch/service/doctor keywords, handle; else general
        if len(msg_norm.split()) <= 2:
            if scores["doctor"] >= 7:
                res = self._make("doctor", extracted, 0.88, "use_llm")
                self._cache(cache_key, res)
                return res
            if scores["branch"] >= 6:
                res = self._make("branch", extracted, 0.86, "use_llm")
                self._cache(cache_key, res)
                return res
            if scores["service"] >= 6:
                res = self._make("service", extracted, 0.86, "use_llm")
                self._cache(cache_key, res)
                return res
            # tiny messages default to greeting/general instead of unclear
            res = self._make("general", extracted, 0.75, "use_llm")
            self._cache(cache_key, res)
            return res

        # Medium confidence rules
        if scores["doctor"] >= 8:
            res = self._make("doctor", extracted, 0.9, "use_llm")
            self._cache(cache_key, res)
            return res

        # Branch/service conflict resolution: if "كم" + service keywords => service, else if "وين" => branch
        if scores["branch"] >= 7 and "وين" in msg_norm:
            res = self._make("branch", extracted, 0.88, "use_llm")
            self._cache(cache_key, res)
            return res

        if scores["service"] >= 7:
            res = self._make("service", extracted, 0.86, "use_llm")
            self._cache(cache_key, res)
            return res

        if scores["general"] >= 8:
            res = self._make("general", extracted, 0.86, "use_llm")
            self._cache(cache_key, res)
            return res

        # -------------------------
        # LLM Structured Outputs
        # -------------------------
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": msg},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "intent_classification",
                        "schema": self._schema,
                        "strict": True,
                    },
                },
            )

            content = response.choices[0].message.content
            if not content:
                raise RuntimeError("Empty response")

            data = json.loads(content)

            # Merge entities: LLM + regex
            llm_entities = data.get("entities", []) or []
            merged = merge_entities(llm_entities, extracted)

            data["entities"] = merged

            # Safety: booking next_action normalization
            if data.get("intent") == "booking":
                has_key = any(e.get("type") in {"doctor_name", "service_name", "date", "time"} for e in merged)
                data["next_action"] = "start_booking" if has_key else "ask_clarification"

            result = IntentSchema(**data)
            self._intent_cache[cache_key] = result.model_dump()
            return result

        except Exception:
            res = self._fallback_classify(msg, extracted)
            self._cache(cache_key, res)
            return res

    # -------------------------
    # Helpers
    # -------------------------

    def _cache(self, key: str, res: IntentSchema) -> None:
        try:
            self._intent_cache[key] = res.model_dump()
        except Exception:
            pass

    def _make(self, intent: str, entities: List[Dict[str, Any]], confidence: float, next_action: str) -> IntentSchema:
        ent_models = [Entity(**e) for e in (entities or [])]
        return IntentSchema(
            intent=intent,
            entities=ent_models,
            confidence=float(confidence),
            next_action=next_action,
        )

    def _maybe_add_doctor_name(self, msg_norm: str, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # if already has doctor_name, keep it
        if any(e.get("type") == "doctor_name" for e in (entities or [])):
            return entities

        # only attempt if message includes booking triggers related to doctor
        if not any(k in msg_norm for k in ["دكتور", "دكتورة", "عند", "مع"]):
            return entities

        if not self._doctor_names_norm:
            return entities

        hint = _extract_name_hint(msg_norm)
        best = process.extractOne(hint, self._doctor_names_norm, score_cutoff=72)
        if not best:
            return entities

        match_norm = best[0]
        idx = self._doctor_names_norm.index(match_norm)
        doctor_name = self._doctor_names[idx]

        out = list(entities or [])
        out.append({"type": "doctor_name", "value": doctor_name, "confidence": 0.9})
        return out

    def _fallback_classify(self, message: str, extracted: Optional[List[Dict[str, Any]]] = None) -> IntentSchema:
        msg_norm = normalize_ar(message).lower().strip()
        msg_clean = _clean_key(msg_norm)
        extracted = extracted or []

        # greeting
        if msg_clean in {_clean_key(x) for x in SIMPLE_GREETINGS} or any(k in msg_norm for k in GREETING_HINTS):
            return self._make("greeting", extracted, 0.85, "use_llm")

        # thanks
        if any(k in msg_norm for k in THANKS_HINTS):
            return self._make("thanks", extracted, 0.85, "use_llm")

        # goodbye
        if any(k in msg_norm for k in GOODBYE_HINTS):
            return self._make("goodbye", extracted, 0.85, "use_llm")

        # booking
        if any(k in msg_norm for k in BOOKING_WORDS):
            extracted2 = self._maybe_add_doctor_name(msg_norm, extracted)
            has_key = any(e.get("type") in {"doctor_name", "service_name", "date", "time"} for e in extracted2)
            return self._make("booking", extracted2, 0.8, "start_booking" if has_key else "ask_clarification")

        # hours
        if any(k in msg_norm for k in HOURS_HINTS):
            return self._make("hours", extracted, 0.8, "use_llm")

        # doctor
        if any(k in msg_norm for k in DOCTOR_LIST_HINTS) or ("مين" in msg_norm and ("اطباء" in msg_norm or "دكاتره" in msg_norm or "دكاترة" in msg_norm)):
            return self._make("doctor", extracted, 0.8, "use_llm")

        # branch/service quick
        if any(k in msg_norm for k in BRANCH_HINTS):
            return self._make("branch", extracted, 0.75, "use_llm")

        if any(k in msg_norm for k in SERVICE_HINTS):
            return self._make("service", extracted, 0.75, "use_llm")

        # default
        return self._make("unclear", extracted, 0.5, "ask_clarification")
