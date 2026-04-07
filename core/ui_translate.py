import json
import os
import re
from core.ui_icons import Icons

_translations = {}
_current_lang = "hu"

def load_locales():
    """This function finds all our language files (the .json ones) and loads them into the bot!"""
    global _translations
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    locales_path = os.path.join(base_path, "locales")
    
    if not os.path.exists(locales_path):
        # Oh no! We couldn't find the folder where the translations are kept.
        print(f"Warning: Locales path not found at {locales_path}")
        return

    for filename in os.listdir(locales_path):
        if filename.endswith(".json"):
            lang_code = filename[:-5]
            try:
                with open(os.path.join(locales_path, filename), "r", encoding="utf-8") as f:
                    _translations[lang_code] = json.load(f)
            except Exception as e:
                # There was a problem reading one of the language files.
                print(f"Error loading locale {filename}: {e}")

def set_language(lang_code):
    global _current_lang
    _current_lang = lang_code.lower()

def t(key, **kwargs):
    """
    This is the main translation function! It takes a key, finds the right words in the 
    current language, and replaces things like {SUCCESS} with actual emojis!
    """
    global _current_lang
    # We try to find the word in the user's language. If we can't, we use English. 
    # If even that's missing, we just show the key itself so the bot doesn't crash!
    lang_dict = _translations.get(_current_lang, _translations.get("en", {}))
    text = lang_dict.get(key)
    
    if text is None:
        text = _translations.get("en", {}).get(key, key)

    # Step 1: We look for things like {SUCCESS} in the text and replace them with actual emojis from our list!
    if isinstance(text, str) and "{" in text:
        placeholders = re.findall(r"\{([A-Z0-9_]+)\}", text)
        for p in placeholders:
            if hasattr(Icons, p):
                icon_val = getattr(Icons, p)
                text = text.replace(f"{{{p}}}", str(icon_val))
    
    # Step 2: If the message needs extra information (like a username or a number), we put it in here!
    if kwargs and isinstance(text, str):
        try:
            text = text.format(**kwargs)
        except:
            pass
            
    return text
