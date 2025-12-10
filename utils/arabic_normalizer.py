"""Arabic text normalization utilities."""
import re

# Arabic diacritics (تشكيل)
_AR_DIACRITICS = re.compile(r"[\u0617-\u061A\u064B-\u0652]")
# Tatweel (تطويل)
_TATWEEL = "\u0640"


def normalize_ar(s: str) -> str:
    """
    Normalize Arabic text for better matching.
    
    - Converts (أ/إ/آ → ا)
    - Converts (ى → ي)
    - Removes diacritics (تشكيل)
    - Converts Arabic-Indic digits (٠١٢٣) to Latin (0123)
    - Removes tatweel (ـ)
    - Converts to lowercase and strips
    
    Args:
        s: Arabic text to normalize
        
    Returns:
        Normalized Arabic text
    """
    if not s:
        return ""
    
    s = s.strip().lower()
    
    # Remove tatweel
    s = s.replace(_TATWEEL, "")
    
    # Remove diacritics
    s = _AR_DIACRITICS.sub("", s)
    
    # Normalize Alef variations
    s = s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    
    # Normalize other variations
    s = s.replace("ى", "ي").replace("ؤ", "و").replace("ئ", "ي")
    
    # Convert Arabic-Indic digits to Latin
    trans = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
    s = s.translate(trans)
    
    return s

