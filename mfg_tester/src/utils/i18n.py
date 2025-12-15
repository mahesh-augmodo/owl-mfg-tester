import gettext
import locale
import sys
import os
import subprocess
import re


def get_system_locale():
    """
    Robustly detects the system UI language.
    """
    # 1. PRIORITY: Check for LANG environment variable
    # This handles both system defaults (on Linux) and manual overrides
    # Example input: "zh_CN.UTF-8" or just "zh_CN"env_lang =
    # os.environ.get('LANG')
    env_lang = os.environ.get('LANG')
    if env_lang:
        # Strip encoding (remove anything after a dot), e.g., "zh_CN.UTF-8" ->
        # "zh_CN"
        return env_lang.split('.')[0]

    lang_code = None

    # --- 2. macOS Detection ---
    if sys.platform == 'darwin':
        try:
            output = subprocess.check_output(
                "defaults read -g AppleLanguages", shell=True
            ).decode('utf-8')
            match = re.search(r'"([a-zA-Z0-9-]+)"', output)
            if match:
                lang_code = match.group(1)
        except Exception:
            pass

    # --- 3. Windows Detection ---
    elif sys.platform == 'win32':
        import ctypes
        try:
            windll = ctypes.windll.kernel32
            lang_id = windll.GetUserDefaultUILanguage()
            lang_code = locale.windows_locale.get(lang_id)
        except Exception:
            pass

    # --- 4. Standard Fallback ---
    if not lang_code:
        lang_code = locale.getdefaultlocale()[0]

    # --- 5. Final Safety Checks ---
    if not lang_code or lang_code == 'C':
        lang_code = 'en'

    return lang_code.replace('-', '_')

# --- Setup the Global Translator ---


localedir = "locale"
detected_lang = get_system_locale()

# Create a priority list of languages to try
languages_to_try = [detected_lang]

# LOGIC: If it's any kind of English (en_IE, en_GB), fallback to en
if detected_lang.startswith('en'):
    languages_to_try.append('en')

print(f"Debug: Detected System Locale: {detected_lang}")
print(f"Debug: Language priority list: {languages_to_try}")

try:
    # gettext will try the first in list, if missing, it tries the next
    translator = gettext.translation(
        'messages', localedir, languages=languages_to_try)
    _ = translator.gettext
    print(
        f"Debug: Loaded translation for: {
            translator.info().get(
                'language',
                'unknown')}")
except FileNotFoundError:
    print(
        f"Debug: No translation found in {languages_to_try}. Using source code default.")
    _ = gettext.gettext

__all__ = ['_', 'get_system_locale']

if __name__ == "__main__":
    print(f"Testing translation: {_('Connecting to device...')}")
