import json
import os
import re
from core.ui_icons import Icons

_translations = {}
_current_lang = "hu"

def load_locales():
    """Load all .json files from the locales directory."""
    global _translations
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    locales_path = os.path.join(base_path, "locales")
    
    if not os.path.exists(locales_path):
        print(f"Warning: Locales path not found at {locales_path}")
        return

    for filename in os.listdir(locales_path):
        if filename.endswith(".json"):
            lang_code = filename[:-5]
            try:
                with open(os.path.join(locales_path, filename), "r", encoding="utf-8") as f:
                    _translations[lang_code] = json.load(f)
            except Exception as e:
                print(f"Error loading locale {filename}: {e}")

def set_language(lang_code):
    global _current_lang
    _current_lang = lang_code.lower()

def t(key, **kwargs):
    """
    Translates a key based on the current language.
    Supports icon placeholders like {SUCCESS} and dynamic kwargs.
    """
    global _current_lang
    # Get translation for current language, fallback to English, then to the key itself
    lang_dict = _translations.get(_current_lang, _translations.get("en", {}))
    text = lang_dict.get(key)
    
    if text is None:
        text = _translations.get("en", {}).get(key, key)

    # 1. Replace Icon placeholders: {SUCCESS} -> Icons.SUCCESS
    if isinstance(text, str) and "{" in text:
        placeholders = re.findall(r"\{([A-Z0-9_]+)\}", text)
        for p in placeholders:
            if hasattr(Icons, p):
                icon_val = getattr(Icons, p)
                text = text.replace(f"{{{p}}}", str(icon_val))
    
    # 2. Support for dynamic variables
    if kwargs and isinstance(text, str):
        try:
            text = text.format(**kwargs)
        except:
            pass
            
    return text
