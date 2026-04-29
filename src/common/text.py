from __future__ import annotations


def normalize_text_basic(value: object) -> str:
    return str(value or "").strip()


def normalize_text_folded(value: object) -> str:
    text = normalize_text_basic(value).lower()
    replacements = {
        "Ã¡": "a",
        "Ã©": "e",
        "Ã­": "i",
        "Ã³": "o",
        "Ãº": "u",
        "Ã±": "n",
        "ÃƒÂ¡": "a",
        "ÃƒÂ©": "e",
        "ÃƒÂ­": "i",
        "ÃƒÂ³": "o",
        "ÃƒÂº": "u",
        "ÃƒÂ±": "n",
        "ã¡": "a",
        "ã©": "e",
        "ã­": "i",
        "ã³": "o",
        "ãº": "u",
        "ã±": "n",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return " ".join(text.split())
