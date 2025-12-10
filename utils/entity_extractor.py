"""Quick entity extraction using Regex before LLM."""
import re
from typing import List, Dict, Any
from utils.arabic_normalizer import normalize_ar

# Phone number patterns (Saudi)
PHONE_RE = re.compile(r"(?:\+?966|0)?5\d{8}\b")

# Time patterns (HH:MM or HH.MM)
TIME_RE = re.compile(r"\b([01]?\d|2[0-3])[:\.]([0-5]\d)\b")

# Date patterns (simple - can be enhanced)
DATE_RE = re.compile(r"\b(اليوم|بكرا|بعد بكرا|السبت|الأحد|الاثنين|الثلاثاء|الأربعاء|الخميس|الجمعة)\b")


def quick_extract_entities(msg: str) -> List[Dict[str, Any]]:
    """
    Quickly extract entities using Regex before LLM.
    
    Extracts:
    - phone: Saudi phone numbers
    - time: Time in HH:MM format
    - date: Relative dates (اليوم, بكرا, etc.)
    
    Args:
        msg: User message
        
    Returns:
        List of extracted entities with type, value, and confidence
    """
    if not msg:
        return []
    
    entities = []
    normalized = normalize_ar(msg)
    
    # Extract phone numbers
    phone_match = PHONE_RE.search(normalized)
    if phone_match:
        phone_value = phone_match.group(0)
        # Normalize phone (remove +966, ensure starts with 0 or 05)
        if phone_value.startswith("966"):
            phone_value = "0" + phone_value[3:]
        elif phone_value.startswith("+966"):
            phone_value = "0" + phone_value[4:]
        elif not phone_value.startswith("0"):
            phone_value = "0" + phone_value
        entities.append({
            "type": "phone",
            "value": phone_value,
            "confidence": 0.95
        })
    
    # Extract time
    time_match = TIME_RE.search(normalized)
    if time_match:
        hour = int(time_match.group(1))
        minute = time_match.group(2)
        time_value = f"{hour:02d}:{minute}"
        entities.append({
            "type": "time",
            "value": time_value,
            "confidence": 0.9
        })
    
    # Extract relative dates
    date_match = DATE_RE.search(normalized)
    if date_match:
        date_value = date_match.group(1)
        entities.append({
            "type": "date",
            "value": date_value,
            "confidence": 0.85
        })
    
    return entities


def merge_entities(llm_entities: List[Dict], extracted_entities: List[Dict]) -> List[Dict]:
    """
    Merge LLM entities with Regex-extracted entities.
    
    Prefers LLM entities but adds Regex entities if not present.
    
    Args:
        llm_entities: Entities from LLM
        extracted_entities: Entities from Regex
        
    Returns:
        Merged list of entities
    """
    merged = []
    llm_types = {e.get("type") for e in llm_entities if isinstance(e, dict)}
    
    # Add LLM entities
    merged.extend(llm_entities)
    
    # Add extracted entities if type not in LLM entities
    for ext_ent in extracted_entities:
        if ext_ent.get("type") not in llm_types:
            merged.append(ext_ent)
    
    return merged

