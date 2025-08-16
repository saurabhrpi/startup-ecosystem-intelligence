"""
Name Guard: Robust, general-purpose validator to decide if a string looks like a real person's name.

Principles:
- No hard-coded banned substrings or blacklists.
- Use general morphological signals (length, letters/digits/punct ratios, token counts, casing patterns).
- Use NER (spaCy) PERSON detection when available.
- Optional LLM fallback for ambiguous cases via USE_LLM_NAME_GUARD=true.

Return: True if likely a real person name (in any language), else False.
"""

from __future__ import annotations

import os
import re
import unicodedata
from functools import lru_cache
from typing import Optional

_USE_LLM = os.getenv("USE_LLM_NAME_GUARD", "true").lower() == "true"


@lru_cache(maxsize=1)
def _load_spacy_model():
    try:
        import spacy
        # Try small English model; if not present, fall back to a blank pipeline
        try:
            return spacy.load("en_core_web_sm")
        except Exception:
            return spacy.blank("en")
    except Exception:
        return None


def _letters_ratio(text: str) -> float:
    total = len(text)
    if total == 0:
        return 0.0
    letters = sum(1 for ch in text if unicodedata.category(ch).startswith("L"))
    return letters / total


def _is_title_like_token(tok: str) -> bool:
    # Title-like for Latin scripts: John, A., J.D., etc.
    if len(tok) == 0:
        return False
    if tok[:1].isupper() and (len(tok) == 1 or tok[1:].islower()):
        return True
    if len(tok) == 2 and tok[0].isupper() and tok[1] == ".":
        return True
    if len(tok) == 3 and tok[0].isupper() and tok[1] == "." and tok[2] == tok[2].upper():
        return True
    return False


def _llm_is_person_name(name: str) -> Optional[bool]:
    if not _USE_LLM:
        return None
    try:
        import openai
        openai.api_key = os.getenv("OPENAI_API_KEY")
        msg = [
            {"role": "system", "content": "Reply only with Yes or No. Is this a real person's name (any language)?"},
            {"role": "user", "content": name},
        ]
        resp = openai.chat.completions.create(
            model="gpt-4",
            messages=msg,
            temperature=0,
            max_tokens=3,
        )
        ans = (resp.choices[0].message.content or "").strip().lower()
        if ans.startswith("y"):
            return True
        if ans.startswith("n"):
            return False
        return None
    except Exception:
        return None


@lru_cache(maxsize=4096)
def is_probable_person_name(raw_name: str) -> bool:
    name = (raw_name or "").strip()
    if not name:
        return False

    # Morphological signals (language-agnostic)
    score = 0.0
    n = len(name)
    if 4 <= n <= 80:
        score += 0.2

    letters_ratio = _letters_ratio(name)
    if letters_ratio >= 0.6:
        score += 0.2

    if any(ch.isdigit() for ch in name):
        score -= 0.2

    punct_count = sum(1 for ch in name if unicodedata.category(ch).startswith("P"))
    if punct_count <= 3:
        score += 0.05

    tokens = [t for t in re.split(r"[\s\-]+", name) if t]
    if 2 <= len(tokens) <= 4:
        score += 0.2

    # Casing pattern for Latin scripts; neutral for others
    title_like = sum(1 for t in tokens if _is_title_like_token(t))
    if title_like >= max(2, len(tokens) - 1):
        score += 0.15

    # Quick decision on strong signals
    if score >= 0.8:
        return True
    if score <= 0.2:
        return False

    # NER/POS-based validation when available
    nlp = _load_spacy_model()
    if nlp is not None:
        try:
            doc = nlp(name)
            # Accept if a PERSON entity covers most of the string (spaCy often splits titles/affixes)
            person_tokens = sum(1 for ent in doc.ents if ent.label_ == "PERSON" for _ in ent.text.split())
            if person_tokens >= max(2, len(tokens) - 1):
                return True
            # POS-based fallback: require primarily proper nouns and name particles
            name_particles = {"van","von","de","da","del","della","di","le","la","el","al","bin","binti","bte","ibn","abu"}
            content_tokens = [t for t in doc if t.is_alpha]
            if content_tokens:
                propn_count = sum(1 for t in content_tokens if t.pos_ == "PROPN")
                allowed_misc = sum(1 for t in content_tokens if t.text.lower() in name_particles)
                disallowed = sum(1 for t in content_tokens if t.pos_ in {"NOUN","VERB","ADJ","AUX","ADV"} and t.text.lower() not in name_particles)
                # Accept if at least two PROPN and no disallowed content words
                if propn_count >= 2 and disallowed == 0:
                    return True
                # Otherwise, accept if majority are PROPN/particles and length reasonable
                if (propn_count + allowed_misc) / max(1, len(content_tokens)) >= 0.7 and len(tokens) >= 2:
                    return True
            # If NER flags ORG/PRODUCT but not PERSON, lean negative
            if any(ent.label_ in {"ORG", "PRODUCT", "GPE"} for ent in doc.ents) and not any(ent.label_ == "PERSON" for ent in doc.ents):
                score -= 0.2
        except Exception:
            pass

    if score >= 0.6:
        return True
    if score <= 0.3:
        return False

    # LLM fallback for ambiguous cases (optional)
    verdict = _llm_is_person_name(name)
    if verdict is not None:
        return verdict

    # Default conservative
    return False


