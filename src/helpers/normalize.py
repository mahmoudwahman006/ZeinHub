"""Arabic/English text normalization, adapted from rag_pipeline.py's
_clean_text/_normalize_arabic/_normalize_text (same technique, reimplemented
from correct Unicode — the pasted reference script's Arabic characters came
through mojibake'd, e.g. "Ø£Ø¥Ø¢" instead of "أإآ", so those exact regex
patterns couldn't be copied byte-for-byte). Needs pyarabic (requirements-ml.txt)
for tashkeel stripping.
"""

import re
import unicodedata

from langdetect import DetectorFactory, detect

DetectorFactory.seed = 0  # deterministic language detection, matching rag_pipeline.py

_BOILERPLATE_PATTERNS = [
    r"page \d+ of \d+",
    r"confidential",
    r"https?://\S+",
    r"\bcompany name\b",
    r"\bprivate & confidential\b",
]

_ARABIC_BOILERPLATE_PATTERNS = [
    r"صفحة\s*\d+\s*من\s*\d+",
    r"سري",
    r"سري\s*للغاية",
]

_ARABIC_INDIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
_WESTERN_DIGITS = "0123456789"
_NUMERAL_TABLE = str.maketrans(_ARABIC_INDIC_DIGITS, _WESTERN_DIGITS)

# Hamza forms unify to bare alif, ta-marbuta to ha, alif-maqsura/ya to ya —
# the standard Arabic search-normalization set, same as rag_pipeline.py used.
_HAMZA_PATTERN = re.compile("[أإآ]")
_TA_MARBUTA_PATTERN = re.compile("ة")
_YA_PATTERN = re.compile("[ىي]")
_TATWEEL_PATTERN = re.compile("ـ+")


def normalize_numerals(text: str) -> str:
    """Arabic-Indic digits (٠-٩) -> Western digits (0-9)."""
    return text.translate(_NUMERAL_TABLE)


def clean_text(text: str) -> str:
    """Whitespace + boilerplate cleanup, plus numeral normalization —
    numerals aren't script-exclusive to Arabic-language documents, so this
    always runs regardless of detected language."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\n", " ").replace("\t", " ").replace("\r", " ")
    text = re.sub(r"\s+", " ", text).strip()
    text = normalize_numerals(text)

    for pattern in _BOILERPLATE_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip()


def normalize_arabic(text: str) -> str:
    """Hamza/ta-marbuta/ya unification, diacritics + tatweel stripping,
    plus Arabic-specific boilerplate removal."""
    import pyarabic.araby as araby

    for pattern in _ARABIC_BOILERPLATE_PATTERNS:
        text = re.sub(pattern, "", text)
    text = _HAMZA_PATTERN.sub("ا", text)
    text = _TA_MARBUTA_PATTERN.sub("ه", text)
    text = _YA_PATTERN.sub("ي", text)
    text = _TATWEEL_PATTERN.sub("", text)  # strip tatweel/kashida (OCR artifact)
    text = araby.strip_tashkeel(text)  # remove diacritics
    return re.sub(r"\s+", " ", text).strip()


def normalize_text(text: str, lang: str) -> str:
    """Apply language-specific normalization end-to-end."""
    text = clean_text(text)
    if lang == "ar":
        text = normalize_arabic(text)
    return text


def detect_language_safe(text: str) -> str:
    """Shared by app/ingestion/loaders.py (tagging a loaded document) and
    app/retrieval/retrieval.py (normalizing a live query the same way its
    matching document text was normalized at ingestion time — see
    retrieve_chunks()'s own comment for why that symmetry matters)."""
    try:
        return detect(text)
    except Exception:
        return "unknown"
