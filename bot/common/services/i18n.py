import contextvars

_lang_ctx = contextvars.ContextVar("lang", default="en")

import json
import os
from pathlib import Path

# Load locales from disk
BASE_DIR = Path(__file__).parent.parent.parent.parent # /app (docker) or project root
LOCALES_DIR = BASE_DIR / "bot" / "locales"

MESSAGES = {}

def load_locales():
    global MESSAGES
    for lang in ["en", "ru", "uz"]:
        try:
            path = LOCALES_DIR / f"{lang}.json"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    MESSAGES[lang] = json.load(f)
            else:
                # Fallback if file missing (shouldn't happen in docker if copied)
                # Try relative to current file if running locally
                local_path = Path("bot/locales") / f"{lang}.json"
                if local_path.exists():
                     with open(local_path, "r", encoding="utf-8") as f:
                        MESSAGES[lang] = json.load(f)
                else:
                    print(f"Warning: Locale {lang} not found at {path}")
                    MESSAGES[lang] = {}
        except Exception as e:
            print(f"Failed to load locale {lang}: {e}")
            MESSAGES[lang] = {}

# Initial load
load_locales()

def set_lang(lang: str):
    _lang_ctx.set(lang)

def get_lang() -> str:
    return _lang_ctx.get()

def t(key: str, **kwargs) -> str:
    lang = get_lang()
    # Fallback to English if key doesn't exist in target lang
    message = MESSAGES.get(lang, MESSAGES["en"]).get(key, MESSAGES["en"].get(key, key))
    if kwargs:
        return message.format(**kwargs)
    return message
