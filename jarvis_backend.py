"""
J.A.R.V.I.S  v3  —  Advanced AI Desktop Voice Assistant + Full Agent
======================================================================
Run:  python jarvis_backend.py
Dashboard:  http://localhost:7798

AGENT CAPABILITIES:
  🎬 YouTube    — open, search, play video, scroll feed
  💬 WhatsApp   — open web, find contact, type & send message (Selenium)
  📱 Telegram   — open desktop app, search contact, send message (PyAutoGUI)
  📸 Instagram  — open, search, scroll, send DM (Selenium)
  🐦 Twitter/X  — open, search, compose & post tweet (Selenium)
  🎵 Spotify    — open desktop app, search & play song/artist
  📧 Gmail      — compose, fill fields, send email (Selenium)
  🔵 Facebook   — open, search, post (Selenium)
  💼 LinkedIn   — open, search people/jobs (Selenium)
  🟠 Reddit     — open, search, browse subreddit (Selenium)
  🌐 Chrome     — navigate URLs, click elements, fill forms (Selenium)
  📁 File Ops   — open folder, create/delete files, move files
  🖥️  Desktop    — take screenshot, resize windows, switch apps
  🔔 Reminders  — set timed reminders with voice alert
  🧮 Calculator — evaluate expressions, percent calculations
  📰 News       — fetch real headlines by topic via Google News RSS
  🌤️  Weather    — get live weather via wttr.in
  💻 System     — CPU/RAM/disk/battery info
  🔊 Volume     — set, up, down, mute via key-press

Install:
  pip install groq openai SpeechRecognition pyaudio pyautogui pyperclip psutil
  pip install pynput pillow pyttsx3 requests feedparser
  pip install selenium webdriver-manager
  pip install pycaw comtypes          (Windows volume control - optional)

AI Models:
  PRIMARY:  NVIDIA Nemotron-3 Nano 30B  (reasoning + streaming via NVIDIA API)
  FALLBACK: Groq LLaMA 3.3 70B         (fast, reliable)

Voice commands:
  "open brave browser"        → opens Brave
  "open chrome and search X"  → Selenium search
  "set volume to 50"          → exact volume
  "take screenshot"           → saves to Desktop
  "open gmail write leave application" → AI-written email
  "enable wake word"          → hey jarvis always-on
  "set custom prompt X"       → change AI personality
"""

# ─────────────────────────────────────────────────────────────────────────────
#  STANDARD IMPORTS
# ─────────────────────────────────────────────────────────────────────────────

import tkinter as tk
import threading
import time
import os
import sys
import json
import re
import math
import platform
import subprocess
import webbrowser
import wave
import tempfile
import struct
import shutil
from datetime import datetime, timedelta
from urllib.parse import quote_plus, parse_qs, urlparse
from http.server import HTTPServer, BaseHTTPRequestHandler

import pyautogui
import pyperclip
import psutil

pyautogui.FAILSAFE = False
pyautogui.PAUSE    = 0.02

# ─────────────────────────────────────────────────────────────────────────────
#  OPTIONAL IMPORTS
# ─────────────────────────────────────────────────────────────────────────────

try:
    import speech_recognition as sr
    HAS_SR = True
except ImportError:
    HAS_SR = False
    print("[WARN] pip install SpeechRecognition pyaudio")

try:
    import groq as groq_lib
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False
    print("[ERROR] pip install groq")

try:
    from pynput import keyboard as pynput_kb
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False
    print("[WARN] pip install pynput")

try:
    import pyttsx3
    HAS_TTS = True
except Exception:
    HAS_TTS = False
    print("[WARN] pip install pyttsx3")

try:
    import requests as req_lib
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("[WARN] pip install requests")

try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False
    print("[WARN] pip install feedparser")

try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
    HAS_PYCAW = True
except ImportError:
    HAS_PYCAW = False  # will use key-press fallback

try:
    from openai import OpenAI as OpenAI_SDK
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    print("[WARN] pip install openai  (NVIDIA Nemotron disabled)")


try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.common.exceptions import (TimeoutException, NoSuchElementException,
                                            WebDriverException, StaleElementReferenceException)
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False
    print("[WARN] pip install selenium webdriver-manager  (browser agent disabled)")

# ─────────────────────────────────────────────────────────────────────────────
#  CONSTANTS & CONFIG
# ─────────────────────────────────────────────────────────────────────────────

# ── Auto-load .env file (if exists) ───────────────────────────────────────────
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env_path):
    with open(_env_path, encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

OS             = platform.system()           # Windows / Darwin / Linux
GROQ_API_KEY    = os.environ.get("GROQ_API_KEY", "")
NVIDIA_API_KEY  = os.environ.get("NVIDIA_API_KEY", "")
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
NVIDIA_MODEL    = "nvidia/nemotron-3-nano-30b-a3b"
DASHBOARD_PORT = 7798
FRONTEND_FILE  = "jarvis_frontend.html"



# ── Storage paths ─────────────────────────────────────────────────────────────
JARVIS_DIR         = os.path.join(os.path.expanduser("~"), ".jarvis")
PREFS_FILE         = os.path.join(JARVIS_DIR, "preferences.json")
CUSTOM_CMDS_FILE   = os.path.join(JARVIS_DIR, "custom_commands.json")
CONV_HISTORY_FILE  = os.path.join(JARVIS_DIR, "conversation_history.json")
os.makedirs(JARVIS_DIR, exist_ok=True)

# ── User preferences (persisted) ──────────────────────────────────────────────
def _load_prefs() -> dict:
    try:
        with open(PREFS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_prefs(prefs: dict):
    try:
        with open(PREFS_FILE, "w") as f:
            json.dump(prefs, f, indent=2)
    except Exception:
        pass

PREFS = _load_prefs()

def get_pref(key: str, default=None):
    return PREFS.get(key, default)

def set_pref(key: str, value):
    PREFS[key] = value
    _save_prefs(PREFS)

# ── Custom user commands ───────────────────────────────────────────────────────
def _load_custom_commands() -> dict:
    try:
        with open(CUSTOM_CMDS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_custom_commands(cmds: dict):
    try:
        with open(CUSTOM_CMDS_FILE, "w") as f:
            json.dump(cmds, f, indent=2)
    except Exception:
        pass

CUSTOM_COMMANDS = _load_custom_commands()
# Example: {"good morning": "open gmail and type Good morning team"}

# ── Conversation memory (rolling context) ─────────────────────────────────────
MAX_CONV_HISTORY = 20   # keep last N exchanges

def _load_conv_history() -> list:
    try:
        with open(CONV_HISTORY_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []

def _save_conv_history(hist: list):
    try:
        with open(CONV_HISTORY_FILE, "w") as f:
            json.dump(hist[-MAX_CONV_HISTORY:], f, indent=2)
    except Exception:
        pass

CONV_HISTORY = _load_conv_history()   # [{role, content}, ...]

def add_to_history(role: str, content: str):
    """Add a message to rolling conversation history."""
    CONV_HISTORY.append({"role": role, "content": content})
    if len(CONV_HISTORY) > MAX_CONV_HISTORY * 2:
        del CONV_HISTORY[:MAX_CONV_HISTORY]
    _save_conv_history(CONV_HISTORY)

def clear_history():
    global CONV_HISTORY
    CONV_HISTORY = []
    _save_conv_history(CONV_HISTORY)

# ── Wake word config ───────────────────────────────────────────────────────────
WAKE_WORD        = get_pref("wake_word", "hey jarvis")
WAKE_WORD_ENABLED = get_pref("wake_word_enabled", False)

# ── Custom AI persona/prompt ───────────────────────────────────────────────────
CUSTOM_AI_PROMPT = get_pref("custom_ai_prompt", "")
# e.g. "Make me sound more professional" or "Respond like Tony Stark"

# ── Audio device index (None = default mic) ───────────────────────────────────
MIC_DEVICE_INDEX = get_pref("mic_device_index", None)

# ── Smart skip: don't send simple dictation through AI ─────────────────────────
SMART_SKIP_ENABLED = get_pref("smart_skip", True)

# ── Streaming TTS flag ──────────────────────────────────────────────────────────
STREAM_TTS = get_pref("stream_tts", False)

# Overlay colours
BG    = "#050e18"
BLUE  = "#00d4ff"
GREEN = "#00ff88"
RED   = "#ff3c3c"
AMBER = "#ffbe00"

# ─────────────────────────────────────────────────────────────────────────────
#  GLOBAL STATE
# ─────────────────────────────────────────────────────────────────────────────

try:
    HOLD_KEY = pynput_kb.Key.ctrl_r if HAS_PYNPUT else None
except Exception:
    HOLD_KEY = None

_paste_lock    = threading.Lock()
_exec_lock     = threading.Lock()
_tts_lock      = threading.Lock()
_restore_timer = None
_overlay_ref   = None
_reminder_thread_started = False

CTX = {
    "last_app": None, "last_action": None,
    "compose_open": False, "recipient": None,
    "reminders": [],
}

STATS = {
    "sessions": 0, "words": 0, "streak": 1, "wpm": 0,
    "mins_saved": 0.0,
    "session_start": datetime.now().isoformat(),
}
ACTIVITY_LOG = []   # [{time, type, command, result}, ...]


def _log(cmd_type: str, command: str, result: str):
    ACTIVITY_LOG.insert(0, {
        "time":    datetime.now().strftime("%H:%M"),
        "type":    cmd_type,
        "command": command[:80],
        "result":  result[:120],
    })
    if len(ACTIVITY_LOG) > 50:
        ACTIVITY_LOG.pop()
    STATS["sessions"] += 1
    STATS["words"]    += len(command.split())


# ═════════════════════════════════════════════════════════════════════════════
#  TEXT-TO-SPEECH
# ═════════════════════════════════════════════════════════════════════════════

def speak(text: str, blocking: bool = False):
    """Speak text. Supports word-by-word streaming TTS when STREAM_TTS=True."""
    if not HAS_TTS or not text:
        return

    def _run_stream():
        """Stream TTS: speak sentence by sentence for faster first-word latency."""
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        for sentence in sentences:
            if not sentence.strip():
                continue
            with _tts_lock:
                try:
                    engine = pyttsx3.init()
                    rate = get_pref("tts_rate", 165)
                    vol  = get_pref("tts_volume", 0.9)
                    engine.setProperty('rate', rate)
                    engine.setProperty('volume', vol)
                    engine.say(sentence)
                    engine.runAndWait()
                except Exception:
                    pass

    def _run():
        with _tts_lock:
            try:
                engine = pyttsx3.init()
                rate = get_pref("tts_rate", 165)
                vol  = get_pref("tts_volume", 0.9)
                engine.setProperty('rate', rate)
                engine.setProperty('volume', vol)
                engine.say(text)
                engine.runAndWait()
            except Exception:
                pass

    runner = _run_stream if STREAM_TTS else _run
    if blocking:
        runner()
    else:
        threading.Thread(target=runner, daemon=True).start()


def list_microphones() -> list:
    """Return list of available microphones for audio device selection."""
    mics = []
    try:
        import pyaudio
        pa = pyaudio.PyAudio()
        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            if info.get('maxInputChannels', 0) > 0:
                mics.append({"index": i, "name": info['name']})
        pa.terminate()
    except Exception:
        pass
    return mics


# ═════════════════════════════════════════════════════════════════════════════
#  WEB / NEWS / WEATHER / CALCULATOR / SYSINFO
# ═════════════════════════════════════════════════════════════════════════════

NEWS_FEEDS = {
    "ai":       "https://news.google.com/rss/search?q=artificial+intelligence&hl=en-IN&gl=IN&ceid=IN:en",
    "tech":     "https://news.google.com/rss/search?q=technology&hl=en-IN&gl=IN&ceid=IN:en",
    "india":    "https://news.google.com/rss/topics/CAAqIQgKIhtDQkFTRGdvSUwyMHZNRFZ4ZERBU0FtVnVLQUFQAQ?hl=en-IN&gl=IN&ceid=IN:en",
    "world":    "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx1YlY4U0FtVnVHZ0pKVGlnQVAB?hl=en-IN&gl=IN&ceid=IN:en",
    "business": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pKVGlnQVAB?hl=en-IN&gl=IN&ceid=IN:en",
    "sports":   "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp1ZEdvU0FtVnVHZ0pKVGlnQVAB?hl=en-IN&gl=IN&ceid=IN:en",
    "science":  "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNR1ptZHpJU0FtVnVHZ0pKVGlnQVAB?hl=en-IN&gl=IN&ceid=IN:en",
    "general":  "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en",
}


def fetch_news(topic: str = "general", count: int = 5) -> list:
    key      = topic.lower().strip()
    feed_url = NEWS_FEEDS.get(key,
        f"https://news.google.com/rss/search?q={quote_plus(topic)}&hl=en-IN&gl=IN&ceid=IN:en")
    try:
        if HAS_FEEDPARSER:
            feed = feedparser.parse(feed_url)
            out  = []
            for entry in feed.entries[:count]:
                src = getattr(getattr(entry, "source", None), "title", "")
                out.append({"title": entry.title, "source": src, "link": entry.link})
            return out
        elif HAS_REQUESTS:
            resp   = req_lib.get(feed_url, timeout=8)
            titles = re.findall(r'<title><!\[CDATA\[(.*?)\]\]></title>', resp.text)
            links  = re.findall(r'<link>(https?://[^<]+)</link>', resp.text)
            return [{"title": t, "source": "", "link": l}
                    for t, l in zip(titles[1:count+1], links[:count])]
    except Exception as e:
        return [{"title": f"News error: {e}", "source": "", "link": ""}]
    return []


def web_search_text(query: str) -> str:
    """Search web + Groq extraction. Returns plain text. Never speaks."""
    if not HAS_REQUESTS:
        return "Install requests: pip install requests"

    JARVIS_SYS = ("You are Jarvis, a smart real-time AI assistant. "
                  "Never mention knowledge cutoff. Always give a direct, confident answer. "
                  "Answer in 1-3 sentences max.")

    # 1. DuckDuckGo instant
    try:
        r = req_lib.get(
            f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_redirect=1&no_html=1",
            timeout=3)
        abstract = r.json().get("AbstractText", "")
        if abstract and len(abstract) > 20:
            return abstract[:500]
    except Exception:
        pass

    # 2. DDG HTML scrape → Groq extraction
    try:
        hdrs = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r    = req_lib.get(f"https://html.duckduckgo.com/html/?q={quote_plus(query)}",
                           headers=hdrs, timeout=5)
        snippets = re.findall(r'class="result__snippet[^>]*>(.*?)</a>',
                              r.text, flags=re.IGNORECASE | re.DOTALL)
        if snippets:
            cleaned = []
            for s in snippets[:4]:
                s = re.sub(r'<[^>]+>', '', s)
                s = re.sub(r'&\w+;', ' ', s)
                s = re.sub(r'\s+', ' ', s).strip()
                cleaned.append(s)
            context = " ".join(cleaned)
            # Try NVIDIA first (better reasoning)
            if nvidia_client:
                try:
                    prompt = (f"{JARVIS_SYS}\n\n"
                              f"Question: {query}\nContext: {context[:2000]}\n\n"
                              f"Answer in 1-2 sentences:")
                    ans = _nvidia_stream_parse(prompt)
                    if ans: return ans
                except Exception: pass
            # Groq fallback
            if groq_client:
                try:
                    r = groq_client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role":"system","content": JARVIS_SYS},
                            {"role":"user",  "content": f"Question: {query}\nContext: {context[:2000]}"}
                        ],
                        max_tokens=150, temperature=0.1
                    )
                    return r.choices[0].message.content.strip()
                except Exception: pass
            return context[:350]
    except Exception:
        pass

    # 3. NVIDIA knowledge fallback (reasoning)
    if nvidia_client:
        try:
            ans = _nvidia_stream_parse(f"{JARVIS_SYS}\n\nAnswer directly in 1-3 sentences: {query}")
            if ans: return ans
        except Exception: pass

    # 4. Groq knowledge fallback
    if groq_client:
        try:
            r = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role":"system","content": JARVIS_SYS},
                    {"role":"user",  "content": query}
                ],
                max_tokens=150, temperature=0.2
            )
            return r.choices[0].message.content.strip()
        except Exception: pass

    return f"No answer found for: {query}"


def get_weather(city: str = "Mumbai") -> str:
    if not HAS_REQUESTS:
        return "requests not installed"
    try:
        r = req_lib.get(f"https://wttr.in/{quote_plus(city)}?format=3", timeout=6)
        return r.text.strip()
    except Exception as e:
        return f"Weather error: {e}"


def calculate_expr(expr: str) -> str:
    expr = expr.lower()
    expr = re.sub(r'percent\s+of', '* 0.01 *', expr)
    expr = re.sub(r'(\d+(?:\.\d+)?)\s*percent', r'(\1 * 0.01)', expr)
    expr = re.sub(r'[^0-9+\-*/().\s]', '', expr).strip()
    if not expr:
        return "Could not parse expression"
    try:
        result = eval(expr, {"__builtins__": {}})
        return f"{expr} = {round(result, 6)}"
    except Exception as e:
        return f"Calculation error: {e}"


def get_system_info() -> dict:
    cpu  = psutil.cpu_percent(interval=0.5)
    ram  = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    info = {
        "cpu": cpu,
        "ram_pct": ram.percent,
        "ram_used_mb": ram.used // 1024 // 1024,
        "ram_total_mb": ram.total // 1024 // 1024,
        "disk_pct": disk.percent,
        "battery": None,
    }
    try:
        batt = psutil.sensors_battery()
        if batt:
            info["battery"] = {"percent": round(batt.percent), "charging": batt.power_plugged}
    except Exception:
        pass
    return info


# ═════════════════════════════════════════════════════════════════════════════
#  REMINDERS
# ═════════════════════════════════════════════════════════════════════════════

def _reminder_worker():
    while True:
        now   = datetime.now()
        fired = []
        for r in CTX["reminders"]:
            if now >= r[0]:
                speak(f"Reminder: {r[1]}")
                if _overlay_ref:
                    _overlay_ref.root.after(0, lambda m=r[1]: _overlay_ref.show_result(f"⏰ {m}"))
                fired.append(r)
        for r in fired:
            CTX["reminders"].remove(r)
        time.sleep(5)


def add_reminder(message: str, minutes: float = 1.0) -> str:
    global _reminder_thread_started
    CTX["reminders"].append((datetime.now() + timedelta(minutes=minutes), message))
    if not _reminder_thread_started:
        _reminder_thread_started = True
        threading.Thread(target=_reminder_worker, daemon=True).start()
    return f"Reminder set: '{message}' in {minutes:.0f} min"


# ═════════════════════════════════════════════════════════════════════════════
#  LOW-LEVEL DESKTOP ACTIONS  (PyAutoGUI)
# ═════════════════════════════════════════════════════════════════════════════

def _run(cmd):  subprocess.Popen(cmd, shell=True)
def _press(k):  pyautogui.press(k)
def _hot(*k):   pyautogui.hotkey(*k)


def do_type(text: str, enter: bool = False) -> str:
    """Paste text via clipboard. Thread-safe."""
    if not text:
        return ""
    global _restore_timer
    with _paste_lock:
        if _restore_timer and _restore_timer.is_alive():
            _restore_timer.cancel()
        try:    old_clip = pyperclip.paste()
        except: old_clip = ""
        time.sleep(0.15)
        pyperclip.copy(text)
        time.sleep(0.05)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.12)
        if enter:
            time.sleep(0.08)
            _press('enter')
        def _restore(orig):
            time.sleep(0.8)
            try: pyperclip.copy(orig)
            except: pass
        t = threading.Thread(target=_restore, args=(old_clip,), daemon=True)
        t.start()
        _restore_timer = t
    return f"Typed: {text[:50]}"


def do_type_with_limit(text: str, char_limit: int, enter: bool = False) -> str:
    if char_limit > 0:
        text = text[:char_limit] if len(text) >= char_limit else text.ljust(char_limit)
    return do_type(text, enter)


def do_click(button='left', x=None, y=None):
    if x is not None and y is not None: pyautogui.click(x, y, button=button)
    else:                                pyautogui.click(button=button)
    return f"Clicked ({button})"


def do_double_click(x=None, y=None):
    if x is not None and y is not None: pyautogui.doubleClick(x, y)
    else:                                pyautogui.doubleClick()
    return "Double-clicked"


def do_right_click(x=None, y=None):
    if x is not None and y is not None: pyautogui.rightClick(x, y)
    else:                                pyautogui.rightClick()
    return "Right-clicked"


def do_drag(x1, y1, x2, y2, duration=0.4):
    pyautogui.drag(x1, y1, x2-x1, y2-y1, duration=duration, button='left')
    return f"Dragged ({x1},{y1})→({x2},{y2})"


def do_repeat_click(n: int, button='left', interval=0.3):
    for _ in range(n):
        pyautogui.click(button=button)
        time.sleep(interval)
    return f"Clicked {n} times"


def do_scroll(direction='down', amt=3):
    pyautogui.scroll(-amt if direction == 'down' else amt)
    return f"Scrolled {direction}"


def do_key(combo: str):
    parts = [k.strip().lower() for k in combo.split('+')]
    _press(parts[0]) if len(parts) == 1 else _hot(*parts)
    return f"Key: {combo}"


def do_volume(direction: str, steps: int = 5) -> str:
    if OS == "Windows":
        return do_volume_win(direction, steps)
    elif OS == "Darwin":
        delta = steps * 10 if direction == "up" else -steps * 10
        subprocess.run(["osascript", "-e",
            f"set volume output volume (output volume of (get volume settings) + {delta})"])
    else:
        subprocess.run(["amixer", "-q", "sset", "Master",
            f"{steps*5}%{'+' if direction == 'up' else '-'}"])
    return f"Volume {direction}"


def do_volume_set(percent: int) -> str:
    """Set system volume to exact percent using Windows Core Audio API."""
    percent = max(0, min(100, percent))
    if OS == "Windows":
        # Method 1: Windows Core Audio API via pycaw (most reliable)
        if HAS_PYCAW:
            try:
                from ctypes import cast, POINTER
                devices  = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume   = cast(interface, POINTER(IAudioEndpointVolume))
                volume.SetMasterVolumeLevelScalar(percent / 100.0, None)
                return f"Volume set to {percent}%"
            except Exception as _pycaw_err:
                print(f"[VOL] pycaw error: {_pycaw_err}")
        # Method 2: PowerShell (no extra install needed)
        try:
            ps_cmd = (
                f"$obj = New-Object -ComObject WScript.Shell; "
                f"$vol = {percent}; "
                f"Add-Type -TypeDefinition '"
                f"using System.Runtime.InteropServices;"
                f"[Guid(\"5CDF2C82-841E-4546-9722-0CF74078229A\"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]"
                f"public interface IAudioEndpointVolume {{ }}"
                f"'; "
                f"(New-Object -ComObject Shell.Application).setvolume($vol)"
            )
            # Simpler PowerShell approach
            subprocess.run(
                ["powershell", "-c",
                 f"[System.Media.SystemSounds]::Beep;",],
                capture_output=True, timeout=2
            )
            # Use nircmd if available, else key-press
            nircmd_paths = [
                r"C:\Windows\nircmd.exe",
                r"C:\nircmd\nircmd.exe",
                os.path.expandvars(r"%APPDATA%\nircmd.exe"),
            ]
            for p in nircmd_paths:
                if os.path.exists(p):
                    subprocess.run([p, "setsysvolume", str(int(percent * 655.35))],
                                   capture_output=True)
                    return f"Volume set to {percent}%"
        except Exception:
            pass
        # Method 3: Key-press fallback (approximate)
        _press('volumemute'); time.sleep(0.05); _press('volumemute')
        for _ in range(50): _press('volumedown'); time.sleep(0.008)
        steps = round(percent / 2)
        for _ in range(steps): _press('volumeup'); time.sleep(0.008)
        return f"Volume ~{percent}% (key-press method)"
    elif OS == "Darwin":
        subprocess.run(["osascript", "-e", f"set volume output volume {percent}"])
    else:
        subprocess.run(["amixer", "-q", "sset", "Master", f"{percent}%"])
    return f"Volume set to {percent}%"


def get_current_volume_pct() -> int:
    """Get current Windows volume as 0-100 int. Returns -1 on failure."""
    if HAS_PYCAW:
        try:
            from ctypes import cast, POINTER
            devices   = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume    = cast(interface, POINTER(IAudioEndpointVolume))
            return round(volume.GetMasterVolumeLevelScalar() * 100)
        except Exception:
            pass
    return -1


def do_volume_win(direction: str, steps: int = 5) -> str:
    """Volume up/down — uses pycaw for precise control, falls back to key-press."""
    if HAS_PYCAW:
        try:
            from ctypes import cast, POINTER
            devices   = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume    = cast(interface, POINTER(IAudioEndpointVolume))
            current   = round(volume.GetMasterVolumeLevelScalar() * 100)
            delta     = steps * 2  # each "step" = 2%
            new_vol   = max(0, min(100, current + delta if direction == "up" else current - delta))
            volume.SetMasterVolumeLevelScalar(new_vol / 100.0, None)
            return f"Volume {direction}: {new_vol}%"
        except Exception:
            pass
    # Fallback: key presses
    key = "volumeup" if direction == "up" else "volumedown"
    for _ in range(steps):
        _press(key)
        time.sleep(0.03)
    return f"Volume {direction}"


def do_volume_by(delta_pct: int) -> str:
    """Increase or decrease volume by exact percentage."""
    if HAS_PYCAW:
        try:
            from ctypes import cast, POINTER
            devices   = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume    = cast(interface, POINTER(IAudioEndpointVolume))
            current   = round(volume.GetMasterVolumeLevelScalar() * 100)
            new_vol   = max(0, min(100, current + delta_pct))
            volume.SetMasterVolumeLevelScalar(new_vol / 100.0, None)
            speak(f"Volume {new_vol} percent")
            return f"Volume: {current}% → {new_vol}%"
        except Exception:
            pass
    # Fallback key presses (1 press ≈ 2%)
    steps = abs(delta_pct) // 2 or 1
    return do_volume_win("up" if delta_pct > 0 else "down", steps)


def do_screenshot() -> str:
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Try Desktop first, fallback to Pictures, then home
    for folder in [
        os.path.join(os.path.expanduser("~"), "Desktop"),
        os.path.join(os.path.expanduser("~"), "Pictures"),
        os.path.expanduser("~"),
    ]:
        if os.path.exists(folder):
            p = os.path.join(folder, f"jarvis_{ts}.png")
            try:
                # Give focus a moment before capturing
                time.sleep(0.3)
                img = pyautogui.screenshot()
                img.save(p)
                speak(f"Screenshot saved.")
                # Open it automatically
                if OS == "Windows":
                    os.startfile(p)
                elif OS == "Darwin":
                    subprocess.Popen(["open", p])
                else:
                    subprocess.Popen(["xdg-open", p])
                return f"Screenshot saved: {p}"
            except Exception as e:
                print(f"[SCREENSHOT] Error: {e}")
                continue
    return "Screenshot failed: no writable folder found"


def do_lock():
    cmds = {"Windows":"rundll32.exe user32.dll,LockWorkStation",
            "Darwin":"pmset displaysleepnow","Linux":"gnome-screensaver-command -l"}
    _run(cmds.get(OS, "")); return "Locked"


def do_shutdown():  _run("shutdown /s /t 3" if OS == "Windows" else "shutdown -h now"); return "Shutting down"
def do_restart():   _run("shutdown /r /t 3" if OS == "Windows" else "shutdown -r now"); return "Restarting"
def do_sleep():
    cmds = {"Windows":"rundll32.exe powrprof.dll,SetSuspendState 0,1,0",
            "Darwin":"pmset sleepnow","Linux":"systemctl suspend"}
    _run(cmds.get(OS, "")); return "Sleeping"


def do_close_app(name: str) -> str:
    killed = []
    for p in psutil.process_iter(['name', 'pid']):
        try:
            if name.lower() in p.info['name'].lower():
                p.kill(); killed.append(p.info['name'])
        except Exception:
            pass
    return f"Closed: {', '.join(set(killed))}" if killed else f"Not found: {name}"


# ─── App URLs & Paths ─────────────────────────────────────────────────────────
APP_URLS = {
    "gmail":"https://mail.google.com","youtube":"https://youtube.com",
    "whatsapp":"https://web.whatsapp.com","twitter":"https://twitter.com",
    "instagram":"https://instagram.com","facebook":"https://facebook.com",
    "linkedin":"https://linkedin.com","github":"https://github.com",
    "netflix":"https://netflix.com","reddit":"https://reddit.com",
    "google":"https://google.com","outlook":"https://outlook.live.com",
    "chatgpt":"https://chat.openai.com","amazon":"https://amazon.in",
    "notion":"https://notion.so","figma":"https://figma.com",
    "maps":"https://maps.google.com","translate":"https://translate.google.com",
    "drive":"https://drive.google.com","meet":"https://meet.google.com",
    "teams":"https://teams.microsoft.com","spotify":"https://open.spotify.com",
}
APP_WIN = {
    "chrome":r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "firefox":r"C:\Program Files\Mozilla Firefox\firefox.exe",
    "notepad":"notepad.exe","calculator":"calc.exe",
    "explorer":"explorer.exe","file manager":"explorer.exe","files":"explorer.exe",
    "cmd":"cmd.exe","terminal":"wt.exe","powershell":"powershell.exe",
    "task manager":"taskmgr.exe","paint":"mspaint.exe",
    "vscode":"code","vs code":"code","visual studio code":"code",
    "visual studio":"code","vs":"code",
    "word":r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
    "excel":r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
    "powerpoint":r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",
    "settings":"start ms-settings:","control panel":"control",
    "spotify":os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"),
    "telegram":os.path.expandvars(r"%APPDATA%\Telegram Desktop\Telegram.exe"),
    "discord":os.path.expandvars(r"%LOCALAPPDATA%\Discord\Discord.exe"),
    "slack":os.path.expandvars(r"%LOCALAPPDATA%\slack\slack.exe"),
    "zoom":os.path.expandvars(r"%APPDATA%\Zoom\bin\Zoom.exe"),
    "vlc":r"C:\Program Files\VideoLAN\VLC\vlc.exe",
    # Brave Browser — multiple install locations
    "brave": (
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
        if os.path.exists(r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe")
        else os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe")
    ),
    "brave browser": (
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
        if os.path.exists(r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe")
        else os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe")
    ),
    # Microsoft Edge
    "edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "microsoft edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    # Opera
    "opera": os.path.expandvars(r"%LOCALAPPDATA%\Programs\Opera\launcher.exe"),
    # Vivaldi
    "vivaldi": os.path.expandvars(r"%LOCALAPPDATA%\Vivaldi\Application\vivaldi.exe"),
    # WhatsApp desktop
    "whatsapp desktop": os.path.expandvars(r"%LOCALAPPDATA%\WhatsApp\WhatsApp.exe"),
    # OBS
    "obs": r"C:\Program Files\obs-studio\bin\64bit\obs64.exe",
    # Winrar / 7zip
    "winrar": r"C:\Program Files\WinRAR\WinRAR.exe",
}
APP_MAC = {
    "chrome":"open -a 'Google Chrome'","safari":"open -a Safari",
    "notepad":"open -a TextEdit","calculator":"open -a Calculator",
    "files":"open -a Finder","terminal":"open -a Terminal",
    "vscode":"code","spotify":"open -a Spotify","vlc":"open -a VLC",
    "zoom":"open -a zoom.us","slack":"open -a Slack","discord":"open -a Discord",
    "telegram":"open -a Telegram",
}
APP_LINUX = {
    "chrome":"google-chrome","firefox":"firefox","notepad":"gedit",
    "calculator":"gnome-calculator","files":"nautilus","terminal":"gnome-terminal",
    "vscode":"code","spotify":"spotify","vlc":"vlc","telegram":"telegram-desktop",
}


# Built-in shell commands that don't need path checks
_SHELL_CMDS = {"notepad","calc","explorer","taskmgr","mspaint","cmd","wt",
               "powershell","control","code","start"}

def _launch(cmd: str):
    """Launch an app safely — uses Popen list form to avoid 'not recognized' errors."""
    cmd = str(cmd).strip()
    if OS != "Windows":
        subprocess.Popen(cmd, shell=True); return
    # Windows: if it's a full path, use Popen list form (no shell needed)
    if os.path.exists(cmd):
        subprocess.Popen([cmd], creationflags=0x00000008)  # DETACHED_PROCESS
        return
    # Shell builtins / short commands — use shell=True
    subprocess.Popen(cmd, shell=True)


def do_open_app(name: str) -> str:
    n = name.lower().strip()
    # Strip filler words
    n = re.sub(r'^(?:open|the|launch|start|run)\s+', '', n).strip()
    if not n or n in ("app","","a","an"):
        return "Please say which app to open"

    # 1. URL map (open in browser)
    for k, u in APP_URLS.items():
        if k in n:
            webbrowser.open(u); CTX["last_app"] = k
            return f"Opened {k}"

    # 2. OS app map — exact/substring match
    mp = APP_WIN if OS == "Windows" else (APP_MAC if OS == "Darwin" else APP_LINUX)
    for k, c in mp.items():
        if k in n:
            c = str(c).strip()
            if OS == "Windows":
                # Skip if path not found (unless it's a builtin)
                if c.split()[0].rstrip(".exe") not in _SHELL_CMDS and not os.path.exists(c):
                    # Check alternate local install path
                    local = os.path.join(
                        os.path.expandvars(r"%LOCALAPPDATA%"),
                        os.path.basename(os.path.dirname(c)),
                        os.path.basename(c))
                    if os.path.exists(local):
                        c = local
                    elif k in APP_URLS:
                        webbrowser.open(APP_URLS[k])
                        return f"Opened {k} (web fallback)"
                    else:
                        print(f"[WARN] {k} not found at: {c}")
                        continue
            _launch(c)
            CTX["last_app"] = k
            return f"Opened {k}"

    # 3. Partial / fuzzy match
    for k, c in mp.items():
        c = str(c).strip()
        if n[:4] in k or k[:4] in n:
            if OS == "Windows" and not os.path.exists(c) and c.split()[0] not in _SHELL_CMDS:
                continue
            _launch(c)
            CTX["last_app"] = k
            return f"Opened {k}"

    # 4. Last resort — just try the name
    _launch(name)
    return f"Attempted: {name}"


def do_gmail_url(to=None, subject=None, body=None) -> str:
    url = "https://mail.google.com/mail/?view=cm&fs=1"
    if to:      url += f"&to={to}"
    if subject: url += f"&su={subject.replace(' ','%20')}"
    if body:    url += f"&body={body.replace(' ','%20')}"
    webbrowser.open(url); CTX["compose_open"] = True
    return f"Gmail compose → {to or 'new'}"


def do_clipboard_ai(instruction: str) -> str:
    try:    clipboard_text = pyperclip.paste()
    except: return "Could not read clipboard"
    if not clipboard_text.strip(): return "Clipboard is empty"
    if not groq_client: return "Groq not available"
    try:
        r = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role":"system","content":"Apply the instruction to the text. Reply with ONLY the result."},
                {"role":"user","content":f"Instruction: {instruction}\n\nText:\n{clipboard_text[:3000]}"}
            ],
            max_tokens=800, temperature=0.3)
        result = r.choices[0].message.content.strip()
        pyperclip.copy(result); do_type(result)
        return f"Clipboard AI done: {instruction}"
    except Exception as e:
        return f"Clipboard AI error: {e}"


def do_edit_selected_ai(instruction: str) -> str:
    """Select all text in the active field, copy it, apply AI instruction, replace it.
    This handles commands like 'make this 300 characters', 'make it shorter',
    'expand this to 500 characters', 'rewrite in 200 words', etc.
    The AI rewrites the CONTENT to match the instruction — it does NOT type
    the instruction itself."""
    # Step 1: Select all + Copy
    _hot('ctrl', 'a')
    time.sleep(0.15)
    _hot('ctrl', 'c')
    time.sleep(0.25)
    try:
        selected_text = pyperclip.paste()
    except:
        return "Could not read selected text"
    if not selected_text.strip():
        return "No text selected — nothing to edit"

    # Step 2: Use AI to apply the editing instruction
    client = nvidia_client or groq_client
    if not client:
        return "No AI client available"
    model = "nvidia/llama-3.3-nemotron-super-49b-v1" if client == nvidia_client else "llama-3.3-70b-versatile"
    try:
        r = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content":
                    "You are an expert text editor. The user gives you text and an editing instruction. "
                    "Apply the instruction EXACTLY. For character/word limits, rewrite the text so it "
                    "meets the target length while preserving the meaning. "
                    "Reply with ONLY the edited text — no quotes, no explanation, no preamble."},
                {"role": "user", "content":
                    f"INSTRUCTION: {instruction}\n\n"
                    f"ORIGINAL TEXT:\n{selected_text[:3000]}"}
            ],
            max_tokens=1200, temperature=0.3)
        result = r.choices[0].message.content.strip()
        # Step 3: Replace selected text with edited version
        pyperclip.copy(result)
        time.sleep(0.05)
        _hot('ctrl', 'v')  # paste over selected text
        time.sleep(0.15)
        return f"Text edited: {instruction}"
    except Exception as e:
        return f"Edit error: {e}"



# ─── Routines ─────────────────────────────────────────────────────────────────
def do_news_routine(topic="general", count=5) -> str:
    items = fetch_news(topic, count)
    if not items: return "No news found"
    lines = [f"Top {topic.upper()} News — {datetime.now().strftime('%d %b %Y')}"]
    for i, item in enumerate(items, 1):
        src = f" [{item['source']}]" if item.get('source') else ""
        lines.append(f"{i}. {item['title']}{src}")
    do_type("\n".join(lines))
    return f"News: {topic} ({count} items)"


def do_web_search_routine(query: str) -> str:
    result = web_search_text(query)
    do_type(result)
    return f"Answer: {result[:80]}"


def do_calculate_routine(expr: str) -> str:
    result = calculate_expr(expr)
    do_type(result)
    return result


def do_weather_routine(city="Mumbai") -> str:
    result = get_weather(city)
    do_type(result)
    return f"Weather: {result}"


def do_system_info_routine() -> str:
    d    = get_system_info()
    text = (f"CPU: {d['cpu']}% | RAM: {d['ram_pct']}% "
            f"({d['ram_used_mb']}MB/{d['ram_total_mb']}MB) | Disk: {d['disk_pct']}%")
    if d.get("battery"):
        b = d["battery"]
        text += f" | Battery: {b['percent']}%{'(charging)' if b['charging'] else ''}"
    do_type(text)
    return text


# ═════════════════════════════════════════════════════════════════════════════
#  ██████╗ ██████╗  ██████╗ ██╗    ██╗███████╗███████╗██████╗
#  ██╔══██╗██╔══██╗██╔═══██╗██║    ██║██╔════╝██╔════╝██╔══██╗
#  ██████╔╝██████╔╝██║   ██║██║ █╗ ██║███████╗█████╗  ██████╔╝
#  ██╔══██╗██╔══██╗██║   ██║██║███╗██║╚════██║██╔══╝  ██╔══██╗
#  ██████╔╝██║  ██║╚██████╔╝╚███╔███╔╝███████║███████╗██║  ██║
#  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝  ╚══╝╚══╝ ╚══════╝╚══════╝╚═╝  ╚═╝
#  AGENT MODULE — Full Browser + Desktop Automation
# ═════════════════════════════════════════════════════════════════════════════

# ── Shared Chrome Driver (reused, auto-restart on crash) ─────────────────────
_driver      = None
_driver_lock = threading.Lock()


def _get_driver(headless: bool = False):
    """Return a live Chrome WebDriver. Creates/restarts as needed."""
    global _driver
    with _driver_lock:
        # Test if existing driver is alive
        if _driver is not None:
            try:
                _ = _driver.current_url
                return _driver
            except Exception:
                _driver = None

        if not HAS_SELENIUM:
            return None

        opts = ChromeOptions()
        if headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--disable-extensions")
        opts.add_argument("--start-maximized")
        opts.add_argument("--user-data-dir=" + os.path.join(tempfile.gettempdir(), "jarvis_chrome"))
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
        # ── Silence ALL Chrome/GPU/GCM noise ─────────────────────────────────
        opts.add_argument("--log-level=3")           # only fatal errors
        opts.add_argument("--silent")
        opts.add_argument("--disable-logging")
        opts.add_argument("--disable-gpu-logging")
        opts.add_argument("--disable-background-networking")  # kills GCM/FCM
        opts.add_argument("--disable-component-update")
        opts.add_argument("--disable-default-apps")
        opts.add_argument("--no-first-run")
        opts.add_argument("--no-default-browser-check")
        opts.add_argument("--disable-features=Translate,BackForwardCache")
        opts.add_argument("--disable-client-side-phishing-detection")
        opts.add_argument("--disable-sync")           # stops GCM registration
        opts.add_argument("--metrics-recording-only")
        opts.add_argument("--no-report-upload")
        opts.add_argument("--disable-breakpad")
        opts.add_argument("--disable-crash-reporter")
        opts.add_experimental_option("excludeSwitches",
            ["enable-automation", "enable-logging", "load-extension"])
        opts.set_capability("goog:loggingPrefs",
            {"browser":"OFF","driver":"OFF","performance":"OFF"})
        # Set env to suppress AMD GPU extension error at OS level
        import os as _os
        _os.environ.setdefault("CHROME_LOG_FILE", "nul" if OS=="Windows" else "/dev/null")

        # Try plain Chrome first (chromedriver must be in PATH)
        import subprocess as _sp, io as _io
        _DEVNULL = _sp.DEVNULL

        def _stealth(driver):
            driver.execute_script(
                "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
            return driver

        # Try plain chrome (chromedriver in PATH)
        try:
            svc = ChromeService(log_output=_DEVNULL)
            _driver = webdriver.Chrome(service=svc, options=opts)
            return _stealth(_driver)
        except Exception:
            pass

        # Auto-download chromedriver via webdriver-manager
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            import logging as _lg
            # Silence webdriver-manager download messages
            _lg.getLogger("WDM").setLevel(_lg.ERROR)
            svc2 = ChromeService(ChromeDriverManager().install(), log_output=_DEVNULL)
            _driver = webdriver.Chrome(service=svc2, options=opts)
            return _stealth(_driver)
        except Exception as e:
            print(f"[AGENT] Chrome driver failed: {e}")
            return None


def _wait(driver, by, selector, timeout=10, clickable=False):
    """Wait for element. Returns element or raises TimeoutException."""
    condition = (EC.element_to_be_clickable if clickable
                 else EC.presence_of_element_located)
    return WebDriverWait(driver, timeout).until(condition((by, selector)))


def _safe_click(driver, by, selector, timeout=10):
    try:
        el = _wait(driver, by, selector, timeout, clickable=True)
        driver.execute_script("arguments[0].scrollIntoView({block:'center'})", el)
        time.sleep(0.2)
        el.click()
        return el
    except Exception:
        return None


def _safe_type(el, text, clear_first=True):
    try:
        if clear_first:
            el.clear()
        el.send_keys(text)
        return True
    except Exception:
        return False


def _close_driver():
    global _driver
    with _driver_lock:
        if _driver:
            try: _driver.quit()
            except: pass
            _driver = None
    return "Browser closed"


# ─────────────────────────────────────────────────────────────────────────────
#  1. YOUTUBE AGENT
# ─────────────────────────────────────────────────────────────────────────────

def agent_youtube(query: str = "", action: str = "search") -> str:
    """
    open youtube                    → opens YouTube home
    open youtube search karan aujla → searches
    play karan aujla on youtube     → searches + clicks first video
    youtube scroll down             → scrolls feed
    """
    driver = _get_driver()

    if not driver:
        url = (f"https://youtube.com/results?search_query={quote_plus(query)}"
               if query else "https://youtube.com")
        webbrowser.open(url)
        return f"YouTube opened (browser fallback): {query}"

    try:
        # Navigate to YouTube if not already there
        if "youtube.com" not in driver.current_url:
            driver.get("https://www.youtube.com")
            time.sleep(2.5)

        if action == "scroll":
            amt = 800 if "down" in query else -800
            driver.execute_script(f"window.scrollBy(0, {amt})")
            return f"YouTube scrolled {query}"

        if query:
            # Find and use the search box
            try:
                search_box = _wait(driver, By.NAME, "search_query", timeout=8)
                search_box.clear()
                search_box.send_keys(query)
                search_box.send_keys(Keys.RETURN)
                time.sleep(2.5)
            except TimeoutException:
                driver.get(f"https://www.youtube.com/results?search_query={quote_plus(query)}")
                time.sleep(2.5)

            if action in ("play", "watch", "open"):
                # Click first video result
                try:
                    videos = WebDriverWait(driver, 8).until(
                        EC.presence_of_all_elements_located(
                            (By.CSS_SELECTOR, "ytd-video-renderer #video-title")))
                    if videos:
                        first_title = videos[0].text.strip()
                        driver.execute_script("arguments[0].scrollIntoView()", videos[0])
                        videos[0].click()
                        time.sleep(1.5)
                        return f"YouTube playing: {first_title or query}"
                except Exception:
                    pass
                return f"YouTube searched: {query} (could not auto-click)"

        return f"YouTube {'searched: ' + query if query else 'opened'}"

    except Exception as e:
        print(f"[AGENT YouTube] {e}")
        webbrowser.open(f"https://youtube.com/results?search_query={quote_plus(query)}")
        return f"YouTube fallback: {query}"


# ─────────────────────────────────────────────────────────────────────────────
#  2. WHATSAPP WEB AGENT  (Selenium — no more pyautogui triple-paste glitch)
# ─────────────────────────────────────────────────────────────────────────────

def agent_whatsapp(contact: str = "", message: str = "",
                   send: bool = True, attach: str = "") -> str:
    """
    open whatsapp message tarun hello   → opens WA, finds Tarun, sends hello
    whatsapp send mom I am coming       → same
    open whatsapp                       → just opens
    """
    driver = _get_driver()
    if not driver:
        # Fallback to pyautogui version
        webbrowser.open("https://web.whatsapp.com")
        time.sleep(4.5)
        if contact:
            _hot('ctrl', 'f'); time.sleep(0.7)
            with _paste_lock:
                pyperclip.copy(contact); time.sleep(0.07)
                pyautogui.hotkey('ctrl', 'v'); time.sleep(0.10)
            time.sleep(1.6); _press('enter'); time.sleep(1.3)
        if message:
            time.sleep(0.5)
            with _paste_lock:
                pyperclip.copy(message); time.sleep(0.08)
                pyautogui.hotkey('ctrl', 'v'); time.sleep(0.12)
            time.sleep(0.15)
            if send: _press('enter')
        return f"WhatsApp {'sent' if send else 'typed'} to {contact}: {message}"

    try:
        # Navigate to WhatsApp Web if not there
        if "web.whatsapp.com" not in driver.current_url:
            driver.get("https://web.whatsapp.com")
            print("[AGENT WA] Waiting for WhatsApp Web... (scan QR if first time)")
            # Wait up to 40s for QR scan or auto-login
            WebDriverWait(driver, 40).until(
                EC.any_of(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="chat-list"]')),
                    EC.presence_of_element_located((By.CSS_SELECTOR, '#side')),
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[aria-label="Chat list"]')),
                ))
            time.sleep(1.5)

        if contact:
            # Try multiple selector strategies for the search box
            search_selectors = [
                '[data-testid="search-container"] [contenteditable]',
                '[data-testid="chat-list-search"]',
                'div[contenteditable="true"][data-tab="3"]',
                'input[title="Search input textbox"]',
            ]
            search_opened = False
            for sel in search_selectors:
                try:
                    # Click search icon first
                    try:
                        _safe_click(driver, By.CSS_SELECTOR,
                                    '[data-testid="search-container"]', timeout=3)
                        time.sleep(0.5)
                    except Exception:
                        pass
                    search_box = _wait(driver, By.CSS_SELECTOR, sel, timeout=4)
                    search_box.clear()
                    search_box.send_keys(contact)
                    search_opened = True
                    break
                except Exception:
                    continue

            if not search_opened:
                return f"WhatsApp: could not open search for '{contact}'"

            time.sleep(1.8)

            # Click first chat result
            result_selectors = [
                '[data-testid="cell-frame-container"]',
                '[aria-label*="' + contact + '"]',
                '._21S-L',
            ]
            clicked = False
            for sel in result_selectors:
                try:
                    results = driver.find_elements(By.CSS_SELECTOR, sel)
                    if results:
                        results[0].click()
                        clicked = True
                        break
                except Exception:
                    continue

            if not clicked:
                return f"WhatsApp: contact '{contact}' not found"
            time.sleep(1.2)

        if message:
            # Find message input box
            msg_selectors = [
                '[data-testid="conversation-compose-box-input"]',
                'div[contenteditable="true"][data-tab="10"]',
                'div[contenteditable="true"][title="Type a message"]',
                'footer div[contenteditable="true"]',
            ]
            msg_box = None
            for sel in msg_selectors:
                try:
                    msg_box = _wait(driver, By.CSS_SELECTOR, sel, timeout=5)
                    break
                except Exception:
                    continue

            if msg_box is None:
                return f"WhatsApp: could not find message box for {contact}"

            msg_box.click()
            time.sleep(0.3)
            # Use clipboard paste for reliable message input
            driver.execute_script("arguments[0].focus()", msg_box)
            pyperclip.copy(message)
            msg_box.send_keys(Keys.CONTROL, 'v')
            time.sleep(0.4)

            if send:
                msg_box.send_keys(Keys.RETURN)
                return f"WhatsApp ✓ sent to {contact}: {message}"
            return f"WhatsApp typed to {contact}: {message}"

        return f"WhatsApp opened{' for ' + contact if contact else ''}"

    except Exception as e:
        print(f"[AGENT WA] Error: {e}")
        return f"WhatsApp error: {str(e)[:80]}"


# ─────────────────────────────────────────────────────────────────────────────
#  3. TELEGRAM AGENT  (PyAutoGUI — Desktop App)
# ─────────────────────────────────────────────────────────────────────────────

def agent_telegram(contact: str = "", message: str = "",
                   send: bool = True) -> str:
    """
    open telegram message mom hello  → opens Telegram desktop, finds mom, sends hello
    telegram open                    → just opens Telegram
    """
    # Find and launch Telegram desktop
    if OS == "Windows":
        tg_paths = [
            os.path.expandvars(r"%APPDATA%\Telegram Desktop\Telegram.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Telegram Desktop\Telegram.exe"),
            r"C:\Program Files\Telegram Desktop\Telegram.exe",
            r"C:\Users\Public\Desktop\Telegram.lnk",
        ]
        launched = False
        for path in tg_paths:
            if os.path.exists(path):
                subprocess.Popen([path])
                launched = True
                break
        if not launched:
            # Windows Store / protocol
            try: subprocess.Popen("start telegram:", shell=True)
            except: webbrowser.open("https://web.telegram.org")
    elif OS == "Darwin":
        subprocess.Popen(["open", "-a", "Telegram"])
    else:
        subprocess.Popen(["telegram-desktop"])

    time.sleep(3.5)  # wait for app window

    if contact:
        # Ctrl+F (Telegram: open search)
        _hot('ctrl', 'f')
        time.sleep(0.9)

        # Type contact name character by character (more reliable in Telegram)
        for char in contact:
            pyautogui.typewrite(char, interval=0.07)
        time.sleep(1.8)

        # First result should be highlighted — press Enter to open chat
        _press('enter')
        time.sleep(1.0)
        _press('escape')  # close search bar if it remains open
        time.sleep(0.4)

    if message:
        # Click bottom-center of screen (message input area)
        sw, sh = pyautogui.size()
        pyautogui.click(sw // 2, int(sh * 0.93))
        time.sleep(0.4)

        # Paste the message
        with _paste_lock:
            pyperclip.copy(message)
            time.sleep(0.06)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.2)

        if send:
            _press('enter')
            return f"Telegram ✓ sent to {contact}: {message}"
        return f"Telegram typed to {contact}: {message}"

    return f"Telegram opened{' for ' + contact if contact else ''}"


# ─────────────────────────────────────────────────────────────────────────────
#  4. INSTAGRAM AGENT  (Selenium)
# ─────────────────────────────────────────────────────────────────────────────

def agent_instagram(action: str = "open", query: str = "",
                    dm_user: str = "", dm_msg: str = "",
                    post_text: str = "") -> str:
    """
    open instagram                     → opens homepage
    instagram search karan aujla       → searches
    instagram scroll down              → scrolls feed
    instagram dm username hello        → sends DM
    """
    driver = _get_driver()
    if not driver:
        webbrowser.open("https://instagram.com")
        return "Instagram opened (browser fallback)"

    try:
        if "instagram.com" not in driver.current_url:
            driver.get("https://www.instagram.com")
            time.sleep(3.5)
            # Dismiss cookie/login popups if present
            for btn_text in ["Accept All", "Allow all cookies", "Not Now"]:
                try:
                    btn = driver.find_element(
                        By.XPATH, f'//*[contains(text(),"{btn_text}")]')
                    btn.click()
                    time.sleep(0.8)
                    break
                except Exception:
                    pass

        if action == "scroll":
            direction = -800 if "down" in query.lower() else 800
            driver.execute_script(f"window.scrollBy(0, {direction})")
            return f"Instagram scrolled {'down' if direction < 0 else 'up'}"

        if action == "search" and query:
            # Click the search icon in the sidebar
            search_selectors = [
                'a[href="/explore/"]',
                '[aria-label="Search"]',
                'svg[aria-label="Search"]',
            ]
            for sel in search_selectors:
                try:
                    _safe_click(driver, By.CSS_SELECTOR, sel, timeout=5)
                    break
                except Exception:
                    continue
            time.sleep(1.2)

            # Type in search box
            search_input_sels = [
                'input[aria-label="Search input"]',
                'input[placeholder="Search"]',
                'input[name="queryBox"]',
            ]
            for sel in search_input_sels:
                try:
                    inp = _wait(driver, By.CSS_SELECTOR, sel, timeout=5)
                    inp.clear(); inp.send_keys(query)
                    break
                except Exception:
                    continue
            time.sleep(1.8)
            return f"Instagram searched: {query}"

        if action == "dm" and dm_user:
            driver.get(f"https://www.instagram.com/{dm_user}/")
            time.sleep(2.5)
            try:
                # Click Message button on profile
                msg_btn = WebDriverWait(driver, 6).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, '//button[text()="Message" or contains(text(),"Message")]')))
                msg_btn.click()
                time.sleep(2.5)
                # Find message input in DM window
                msg_input = WebDriverWait(driver, 6).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR,
                         '[placeholder="Message..."], [aria-label="Message"],'
                         '[aria-label="Type a message"]')))
                msg_input.send_keys(dm_msg)
                msg_input.send_keys(Keys.RETURN)
                return f"Instagram DM ✓ sent to {dm_user}: {dm_msg}"
            except Exception as e:
                return f"Instagram DM error: {e}"

        return f"Instagram {'opened' if action == 'open' else action}"

    except Exception as e:
        print(f"[AGENT IG] {e}")
        webbrowser.open("https://instagram.com")
        return f"Instagram fallback: {str(e)[:60]}"


# ─────────────────────────────────────────────────────────────────────────────
#  5. TWITTER / X AGENT  (Selenium)
# ─────────────────────────────────────────────────────────────────────────────

def agent_twitter(action: str = "open", query: str = "",
                  tweet_text: str = "") -> str:
    """
    open twitter                    → opens feed
    twitter search karan aujla     → searches
    tweet hello everyone           → composes + types tweet
    twitter scroll                 → scrolls feed
    """
    driver = _get_driver()
    if not driver:
        if query:
            webbrowser.open(f"https://twitter.com/search?q={quote_plus(query)}")
        else:
            webbrowser.open("https://twitter.com")
        return f"Twitter opened (fallback)"

    try:
        current = driver.current_url
        if "twitter.com" not in current and "x.com" not in current:
            driver.get("https://twitter.com")
            time.sleep(3.5)

        if action == "scroll":
            direction = -800 if "down" in query.lower() else 800
            driver.execute_script(f"window.scrollBy(0, {direction})")
            return f"Twitter scrolled {'down' if direction < 0 else 'up'}"

        if action == "search" and query:
            # Click search bar
            search_selectors = [
                '[data-testid="SearchBox_Search_Input"]',
                'input[aria-label="Search query"]',
                'input[placeholder="Search"]',
            ]
            for sel in search_selectors:
                try:
                    sb = _wait(driver, By.CSS_SELECTOR, sel, timeout=5, clickable=True)
                    sb.clear(); sb.send_keys(query); sb.send_keys(Keys.RETURN)
                    time.sleep(2)
                    return f"Twitter searched: {query}"
                except Exception:
                    continue
            # Navigate directly
            driver.get(f"https://twitter.com/search?q={quote_plus(query)}")
            time.sleep(2)
            return f"Twitter searched: {query}"

        if action in ("tweet", "post") and tweet_text:
            # Click compose tweet button
            tweet_btn_sels = [
                '[data-testid="SideNav_NewTweet_Button"]',
                'a[href="/compose/tweet"]',
                '[aria-label="Tweet"]',
                '[aria-label="Post"]',
            ]
            composed = False
            for sel in tweet_btn_sels:
                try:
                    _safe_click(driver, By.CSS_SELECTOR, sel, timeout=5)
                    composed = True; break
                except Exception:
                    continue

            if composed:
                time.sleep(1.2)
                textarea_sels = [
                    '[data-testid="tweetTextarea_0"]',
                    '[aria-label="Tweet text"]',
                    'div[role="textbox"]',
                ]
                for sel in textarea_sels:
                    try:
                        tb = _wait(driver, By.CSS_SELECTOR, sel, timeout=5)
                        tb.send_keys(tweet_text)
                        return f"Twitter ✓ tweet composed: {tweet_text[:60]}"
                    except Exception:
                        continue

        return f"Twitter {action}"

    except Exception as e:
        print(f"[AGENT Twitter] {e}")
        webbrowser.open("https://twitter.com")
        return f"Twitter fallback: {str(e)[:60]}"


# ─────────────────────────────────────────────────────────────────────────────
#  6. SPOTIFY AGENT  (Desktop App first, Web fallback)
# ─────────────────────────────────────────────────────────────────────────────

def agent_spotify(query: str = "", action: str = "play") -> str:
    """
    play karan aujla on spotify   → opens Spotify, searches, plays
    spotify search lofi            → searches
    open spotify                   → just opens
    """
    if OS == "Windows":
        spotify_exe = os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe")
        if os.path.exists(spotify_exe):
            # Check if Spotify is already running
            spotify_running = any("Spotify" in p.name()
                                  for p in psutil.process_iter(['name']))
            if not spotify_running:
                subprocess.Popen([spotify_exe])
                time.sleep(4.0)
            else:
                # Bring to foreground — Alt+Tab or find window
                time.sleep(0.5)

            if query:
                # Spotify desktop shortcut: Ctrl+L opens search
                _hot('ctrl', 'l')
                time.sleep(0.8)
                with _paste_lock:
                    pyperclip.copy(query)
                    time.sleep(0.05)
                    pyautogui.hotkey('ctrl', 'v')
                time.sleep(0.3)
                _press('enter')
                time.sleep(1.5)

                if action == "play":
                    # Press Tab to go to first result then Enter
                    _press('enter')
                return f"Spotify ✓ {'playing' if action == 'play' else 'searching'}: {query}"
            return "Spotify opened"

    elif OS == "Darwin":
        subprocess.Popen(["open", "-a", "Spotify"])
        time.sleep(3.5)
        if query:
            _hot('cmd', 'l')
            time.sleep(0.8)
            pyautogui.typewrite(query, interval=0.05)
            _press('enter')
            time.sleep(1.5)
            if action == "play": _press('enter')
        return f"Spotify {'playing' if query else 'opened'}: {query}"

    # Fallback: Spotify Web
    driver = _get_driver()
    if driver:
        try:
            driver.get(f"https://open.spotify.com/search/{quote_plus(query)}")
            time.sleep(2)
            return f"Spotify Web: {query}"
        except Exception:
            pass

    webbrowser.open(f"https://open.spotify.com/search/{quote_plus(query)}")
    return f"Spotify opened (browser): {query}"


# ─────────────────────────────────────────────────────────────────────────────
#  7. GMAIL AGENT  (Selenium — full compose workflow)
# ─────────────────────────────────────────────────────────────────────────────

def agent_gmail(to: str = "", subject: str = "",
                body: str = "", send: bool = False) -> str:
    """
    compose email to tarun subject hello body how are you   → composes
    send email to tarun hello how are you                   → composes + sends
    open gmail                                               → opens inbox
    """
    driver = _get_driver()
    if not driver:
        return do_gmail_url(to, subject, body)

    try:
        if "mail.google.com" not in driver.current_url:
            driver.get("https://mail.google.com")
            time.sleep(3.5)

        if not to and not subject and not body:
            return "Gmail opened"

        # Click Compose button
        compose_sels = ['[gh="cm"]', '.T-I.T-I-KE', '[aria-label="Compose"]',
                        'div[data-tooltip*="Compose"]']
        composed = False
        for sel in compose_sels:
            try:
                _safe_click(driver, By.CSS_SELECTOR, sel, timeout=5)
                composed = True; break
            except Exception:
                continue

        if not composed:
            return do_gmail_url(to, subject, body)  # fallback

        time.sleep(1.5)

        if to:
            to_sels = ['input[name="to"]', 'textarea[name="to"]',
                       '[aria-label="To"]', '[data-hovercard-id]']
            for sel in to_sels:
                try:
                    tf = _wait(driver, By.CSS_SELECTOR, sel, timeout=5)
                    tf.send_keys(to + Keys.TAB); time.sleep(0.5); break
                except Exception:
                    continue

        if subject:
            try:
                sf = _wait(driver, By.NAME, "subjectbox", timeout=4)
                sf.send_keys(subject + Keys.TAB); time.sleep(0.3)
            except Exception:
                pass

        if body:
            # If body is an instruction (not literal text), generate it with AI
            instruction_keywords = ["write","compose","draft","create","generate","make"]
            body_is_instruction  = any(body.lower().startswith(k) for k in instruction_keywords)
            if body_is_instruction and groq_client:
                try:
                    r_body = groq_client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role":"system","content":"You are a professional email writer. Write a complete, formal email body. Output ONLY the email body text, no subject line, no greetings prefix needed."},
                            {"role":"user","content":f"Write an email body for: {body}"}
                        ],
                        max_tokens=400, temperature=0.4
                    )
                    body = r_body.choices[0].message.content.strip()
                    print(f"[GMAIL] AI generated body ({len(body)} chars)")
                except Exception as e:
                    print(f"[GMAIL] Body generation failed: {e}")
            body_sels = [
                '[role="textbox"][aria-label*="Body"]',
                '[aria-label="Message Body"]',
                'div[role="textbox"].Am.Al',
            ]
            for sel in body_sels:
                try:
                    bf = _wait(driver, By.CSS_SELECTOR, sel, timeout=4)
                    bf.click()
                    # Use clipboard paste for long bodies (more reliable than send_keys)
                    pyperclip.copy(body)
                    import pyautogui as _pg
                    _pg.hotkey("ctrl","v")
                    time.sleep(0.3)
                    break
                except Exception:
                    continue

        if send:
            send_sels = ['[data-tooltip*="Send"]', '[aria-label*="Send"]',
                         '.T-I.J-J5-Ji.aoO']
            for sel in send_sels:
                try:
                    _safe_click(driver, By.CSS_SELECTOR, sel, timeout=4)
                    return f"Gmail ✓ sent to {to}"
                except Exception:
                    continue

        return f"Gmail ✓ composed to {to}"

    except Exception as e:
        print(f"[AGENT Gmail] {e}")
        return do_gmail_url(to, subject, body)


# ─────────────────────────────────────────────────────────────────────────────
#  8. CHROME / BROWSER AGENT  (Selenium — general navigation)
# ─────────────────────────────────────────────────────────────────────────────

def agent_chrome(url: str = "", search: str = "",
                 action: str = "open", scroll: str = "") -> str:
    """
    open chrome go to github.com         → navigates to URL
    chrome search python tutorials       → Google search
    chrome scroll down                   → scrolls page
    chrome back / chrome forward         → navigation
    chrome refresh                       → refresh
    chrome new tab                       → opens new tab
    """
    driver = _get_driver()
    if not driver:
        target = url or (f"https://google.com/search?q={quote_plus(search)}" if search else "https://google.com")
        webbrowser.open(target)
        return f"Chrome opened: {target}"

    try:
        if action == "back":
            driver.back(); return "Chrome: went back"
        if action == "forward":
            driver.forward(); return "Chrome: went forward"
        if action == "refresh":
            driver.refresh(); return "Chrome: refreshed"
        if action == "new_tab":
            driver.execute_script("window.open('https://www.google.com','_blank')")
            driver.switch_to.window(driver.window_handles[-1])
            return "Chrome: new tab opened"
        if action == "scroll" or scroll:
            direction = scroll or search
            amt = -900 if "down" in direction else 900
            driver.execute_script(f"window.scrollBy(0,{amt})")
            return f"Chrome scrolled {'down' if amt < 0 else 'up'}"
        if action == "close_tab":
            driver.execute_script("window.close()")
            if driver.window_handles:
                driver.switch_to.window(driver.window_handles[-1])
            return "Chrome: tab closed"

        # Navigate to URL
        if url:
            if not url.startswith("http"):
                url = "https://" + url
            driver.get(url)
            time.sleep(2)
            return f"Chrome ✓ opened: {url}"

        # Google search
        if search:
            driver.get(f"https://www.google.com/search?q={quote_plus(search)}")
            time.sleep(2)
            return f"Chrome searched: {search}"

        return "Chrome: no action specified"

    except Exception as e:
        print(f"[AGENT Chrome] {e}")
        return f"Chrome error: {str(e)[:60]}"


# ─────────────────────────────────────────────────────────────────────────────
#  9. FACEBOOK AGENT
# ─────────────────────────────────────────────────────────────────────────────

def agent_facebook(action: str = "open", query: str = "",
                   post_text: str = "") -> str:
    driver = _get_driver()
    if not driver:
        webbrowser.open("https://facebook.com"); return "Facebook opened"
    try:
        if "facebook.com" not in driver.current_url:
            driver.get("https://facebook.com"); time.sleep(3.5)
        if action == "search" and query:
            sb = _wait(driver, By.CSS_SELECTOR,
                       '[aria-label="Search Facebook"], input[type="search"]', timeout=8)
            sb.click(); sb.send_keys(query); sb.send_keys(Keys.RETURN); time.sleep(2)
            return f"Facebook searched: {query}"
        if action == "scroll":
            driver.execute_script(f"window.scrollBy(0,{'800' if 'down' in query else '-800'})")
            return f"Facebook scrolled"
        return "Facebook opened"
    except Exception as e:
        webbrowser.open("https://facebook.com")
        return f"Facebook fallback: {str(e)[:60]}"


# ─────────────────────────────────────────────────────────────────────────────
#  10. LINKEDIN AGENT
# ─────────────────────────────────────────────────────────────────────────────

def agent_linkedin(action: str = "open", query: str = "",
                   search_type: str = "all") -> str:
    """
    open linkedin                       → opens feed
    linkedin search karan aujla         → searches people/posts
    linkedin search jobs python         → searches jobs
    """
    driver = _get_driver()
    if not driver:
        webbrowser.open("https://linkedin.com"); return "LinkedIn opened"
    try:
        if "linkedin.com" not in driver.current_url:
            driver.get("https://linkedin.com"); time.sleep(3.5)
        if action == "search" and query:
            sb_sels = ['.search-global-typeahead input',
                       '[aria-label="Search"]', 'input[placeholder*="Search"]']
            for sel in sb_sels:
                try:
                    sb = _wait(driver, By.CSS_SELECTOR, sel, timeout=5, clickable=True)
                    sb.click(); sb.clear(); sb.send_keys(query); sb.send_keys(Keys.RETURN)
                    time.sleep(2)
                    if search_type == "jobs":
                        try:
                            jobs_tab = driver.find_element(
                                By.XPATH, '//button[contains(text(),"Jobs")]')
                            jobs_tab.click(); time.sleep(1.5)
                        except Exception:
                            pass
                    return f"LinkedIn searched: {query}"
                except Exception:
                    continue
        if action == "scroll":
            driver.execute_script(f"window.scrollBy(0,{'800' if 'down' in query else '-800'})")
            return "LinkedIn scrolled"
        return "LinkedIn opened"
    except Exception as e:
        webbrowser.open("https://linkedin.com")
        return f"LinkedIn fallback: {str(e)[:60]}"


# ─────────────────────────────────────────────────────────────────────────────
#  11. REDDIT AGENT
# ─────────────────────────────────────────────────────────────────────────────

def agent_reddit(action: str = "open", query: str = "",
                 subreddit: str = "") -> str:
    driver = _get_driver()
    if not driver:
        url = (f"https://reddit.com/r/{subreddit}" if subreddit
               else f"https://reddit.com/search?q={quote_plus(query)}" if query
               else "https://reddit.com")
        webbrowser.open(url); return f"Reddit opened"
    try:
        if "reddit.com" not in driver.current_url:
            start = (f"https://reddit.com/r/{subreddit}" if subreddit else "https://reddit.com")
            driver.get(start); time.sleep(2.5)
        if action == "search" and query:
            driver.get(f"https://www.reddit.com/search/?q={quote_plus(query)}")
            time.sleep(2)
            return f"Reddit searched: {query}"
        if action == "scroll":
            driver.execute_script(f"window.scrollBy(0,{'900' if 'down' in query else '-900'})")
            return "Reddit scrolled"
        return f"Reddit opened: {subreddit or 'home'}"
    except Exception as e:
        webbrowser.open("https://reddit.com")
        return f"Reddit fallback: {str(e)[:60]}"


# ─────────────────────────────────────────────────────────────────────────────
#  12. FILE OPERATIONS AGENT  (PyAutoGUI + OS commands)
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_path(path: str, base: str = None) -> str:
    """Resolve a path, defaulting to Desktop if relative."""
    if not base:
        base = os.path.join(os.path.expanduser("~"), "Desktop")
    FOLDER_MAP = {
        "desktop":   os.path.join(os.path.expanduser("~"), "Desktop"),
        "downloads": os.path.join(os.path.expanduser("~"), "Downloads"),
        "documents": os.path.join(os.path.expanduser("~"), "Documents"),
        "pictures":  os.path.join(os.path.expanduser("~"), "Pictures"),
        "music":     os.path.join(os.path.expanduser("~"), "Music"),
        "videos":    os.path.join(os.path.expanduser("~"), "Videos"),
        "home":      os.path.expanduser("~"),
        "temp":      tempfile.gettempdir(),
    }
    p = path.lower().strip()
    if p in FOLDER_MAP:
        return FOLDER_MAP[p]
    if os.path.isabs(path):
        return path
    return os.path.join(base, path)


def _open_in_explorer(path: str):
    if OS == "Windows":
        subprocess.Popen(["explorer", path])
    elif OS == "Darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def agent_file_ops(action: str, path: str = "", dest: str = "",
                   name: str = "") -> str:
    """
    Comprehensive file & folder operations.
    Actions: open_folder, open_file, create_folder, create_file,
             delete_file, delete_folder, rename_file, copy_file,
             list_folder, show_desktop
    """
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    target  = _resolve_path(name or path) if (name or path) else desktop

    # ── Open folder ───────────────────────────────────────────────────────────
    if action in ("open_folder", "open"):
        folder = _resolve_path(name or path) if (name or path) else desktop
        if not os.path.exists(folder):
            # Maybe they said a partial name — search Desktop
            matches = [f for f in os.listdir(desktop)
                       if (name or path).lower() in f.lower()
                       and os.path.isdir(os.path.join(desktop, f))]
            if matches:
                folder = os.path.join(desktop, matches[0])
            else:
                return f"Folder not found: {name or path}"
        _open_in_explorer(folder)
        speak(f"Opened {os.path.basename(folder)}")
        return f"Opened folder: {folder}"

    # ── Open file ─────────────────────────────────────────────────────────────
    if action == "open_file":
        if not os.path.exists(target):
            # Search Desktop for filename
            matches = [f for f in os.listdir(desktop)
                       if (name or path).lower() in f.lower()]
            if matches:
                target = os.path.join(desktop, matches[0])
            else:
                return f"File not found: {name or path}"
        if OS == "Windows":
            os.startfile(target)
        elif OS == "Darwin":
            subprocess.Popen(["open", target])
        else:
            subprocess.Popen(["xdg-open", target])
        speak(f"Opened {os.path.basename(target)}")
        return f"Opened: {target}"

    # ── Create folder ─────────────────────────────────────────────────────────
    if action in ("create_folder", "make_folder", "new_folder"):
        folder_name = name or path
        if not folder_name:
            return "Please say a folder name"
        # Default location: Desktop
        new_folder = os.path.join(desktop, folder_name)
        os.makedirs(new_folder, exist_ok=True)
        _open_in_explorer(new_folder)
        speak(f"Created folder {folder_name} on Desktop")
        return f"Created folder: {new_folder}"

    # ── Create file ───────────────────────────────────────────────────────────
    if action == "create_file":
        file_name = name or path
        if not file_name:
            return "Please say a file name"
        new_file = os.path.join(desktop, file_name)
        with open(new_file, "w", encoding="utf-8") as fh:
            fh.write("")
        speak(f"Created {file_name}")
        return f"Created file: {new_file}"

    # ── Delete file ───────────────────────────────────────────────────────────
    if action in ("delete_file", "delete"):
        if not os.path.exists(target):
            matches = [f for f in os.listdir(desktop)
                       if (name or path).lower() in f.lower()]
            if matches:
                target = os.path.join(desktop, matches[0])
            else:
                return f"Not found: {name or path}"
        if os.path.isdir(target):
            import shutil as _sh
            _sh.rmtree(target)
        else:
            os.remove(target)
        speak(f"Deleted {os.path.basename(target)}")
        return f"Deleted: {target}"

    # ── Delete folder ─────────────────────────────────────────────────────────
    if action == "delete_folder":
        import shutil as _sh
        folder_path = _resolve_path(name or path)
        if os.path.exists(folder_path):
            _sh.rmtree(folder_path)
            speak(f"Deleted folder {os.path.basename(folder_path)}")
            return f"Deleted folder: {folder_path}"
        return f"Folder not found: {name or path}"

    # ── Rename ────────────────────────────────────────────────────────────────
    if action == "rename_file":
        src_path = target
        dst_path = os.path.join(os.path.dirname(src_path), dest)
        if not os.path.exists(src_path):
            return f"Not found: {path}"
        os.rename(src_path, dst_path)
        speak(f"Renamed to {dest}")
        return f"Renamed: {path} → {dest}"

    # ── Copy file ─────────────────────────────────────────────────────────────
    if action == "copy_file":
        import shutil as _sh
        dst = _resolve_path(dest) if dest else os.path.join(desktop, os.path.basename(target))
        _sh.copy2(target, dst)
        speak("File copied")
        return f"Copied: {target} → {dst}"

    # ── List folder ───────────────────────────────────────────────────────────
    if action == "list_folder":
        folder = _resolve_path(name or path) if (name or path) else desktop
        if not os.path.isdir(folder):
            return f"Not a folder: {folder}"
        items = sorted(os.listdir(folder))
        if not items:
            do_type(f"{folder} is empty")
            return "Empty folder"
        lines = [f"Contents of {os.path.basename(folder)}:"]
        for item in items[:20]:
            prefix = "[DIR] " if os.path.isdir(os.path.join(folder,item)) else "      "
            lines.append(prefix + item)
        if len(items) > 20:
            lines.append(f"... and {len(items)-20} more")
        do_type("\n".join(lines))
        return f"Listed {len(items)} items"

    # ── Show desktop ──────────────────────────────────────────────────────────
    if action == "show_desktop":
        _open_in_explorer(desktop)
        return "Opened Desktop"

    return f"Unknown file action: {action}"


# ─────────────────────────────────────────────────────────────────────────────
#  AGENT MASTER DISPATCHER
# ─────────────────────────────────────────────────────────────────────────────

def do_agent_task(obj: dict) -> str:
    """Route agent_task JSON to the correct agent function."""
    platform_name = obj.get("platform", "").lower().strip()
    # "task" is the new sub-action key (avoids duplicate "action" key JSON bug)
    # Fall back to "action" for backward compatibility with local_parse()
    action = (obj.get("task") or obj.get("action", "open")).lower().strip()
    query         = obj.get("query",    "").strip()
    contact       = obj.get("contact",  "").strip()
    message       = obj.get("message",  "").strip()
    url           = obj.get("url",      "").strip()
    send          = bool(obj.get("send", True))
    subreddit     = obj.get("subreddit","").strip()
    dm_user       = obj.get("dm_user",  "").strip()
    dm_msg        = obj.get("dm_msg",   "").strip()
    tweet_text    = obj.get("tweet",    message).strip()
    post_text     = obj.get("post",     "").strip()
    scroll        = obj.get("scroll",   "").strip()
    file_path     = obj.get("path",     "").strip()
    dest_path     = obj.get("dest",     "").strip()
    file_name     = obj.get("name",     "").strip()
    search_type   = obj.get("search_type","all").strip()

    if   platform_name == "youtube":    return agent_youtube(query, action)
    elif platform_name == "whatsapp":   return agent_whatsapp(contact, message, send)
    elif platform_name == "telegram":   return agent_telegram(contact, message, send)
    elif platform_name == "instagram":  return agent_instagram(action, query, dm_user, dm_msg, post_text)
    elif platform_name == "twitter":    return agent_twitter(action, query, tweet_text)
    elif platform_name in ("x", "x.com"): return agent_twitter(action, query, tweet_text)
    elif platform_name == "spotify":    return agent_spotify(query, action)
    elif platform_name == "gmail":
        return agent_gmail(obj.get("to",""), obj.get("subject",""), obj.get("body",""), send)
    elif platform_name in ("chrome","browser","web"): return agent_chrome(url, query, action, scroll)
    elif platform_name == "facebook":   return agent_facebook(action, query, post_text)
    elif platform_name == "linkedin":   return agent_linkedin(action, query, search_type)
    elif platform_name == "reddit":     return agent_reddit(action, query, subreddit)
    elif platform_name == "files":
        # Map "task" key to action for file ops
        file_action = obj.get("task") or action
        return agent_file_ops(file_action, file_path, dest_path, file_name)
    elif platform_name == "close_browser": return _close_driver()
    else:
        return f"Unknown agent platform: {platform_name}"


# ═════════════════════════════════════════════════════════════════════════════
#  EXECUTOR  — routes JSON action objects to implementations
# ═════════════════════════════════════════════════════════════════════════════

def execute(obj: dict) -> str:
    a = obj.get("action", "")

    if   a == "open_app":      return do_open_app(obj.get("app", ""))
    elif a == "open_url":
        url = obj.get("url", "")
        webbrowser.open(url); return f"Opened: {url}"
    elif a == "search_web":
        q = obj.get("query", "")
        webbrowser.open(f"https://google.com/search?q={quote_plus(q)}")
        return f"Searched: {q}"
    elif a == "gmail_compose": return do_gmail_url(obj.get("to"), obj.get("subject"), obj.get("body"))
    elif a == "whatsapp":      return agent_whatsapp(obj.get("contact",""), obj.get("message",""), True)

    elif a == "type_text":
        text  = obj.get("text", "")
        limit = int(obj.get("char_limit", 0))
        enter = bool(obj.get("press_enter", False))
        return do_type_with_limit(text, limit, enter) if limit > 0 else do_type(text, enter)

    elif a == "edit_selected_ai":
        return do_edit_selected_ai(obj.get("instruction", "improve this text"))

    elif a == "delete_text":
        n = int(obj.get("chars", 1))
        for _ in range(n): _press('backspace'); time.sleep(0.02)
        return f"Deleted {n} chars"

    elif a == "select_all":   _hot('ctrl', 'a'); return "Selected all"
    elif a == "copy":         _hot('ctrl', 'c'); return "Copied"
    elif a == "paste":        _hot('ctrl', 'v'); return "Pasted"
    elif a == "undo":         _hot('ctrl', 'z'); return "Undo"
    elif a == "redo":         _hot('ctrl', 'y'); return "Redo"
    elif a == "new_line":     _press('enter'); return "New line"
    elif a == "clipboard_ai": return do_clipboard_ai(obj.get("instruction", "summarize"))

    elif a == "click":         return do_click(obj.get("button","left"), obj.get("x"), obj.get("y"))
    elif a == "double_click":  return do_double_click(obj.get("x"), obj.get("y"))
    elif a == "right_click":   return do_right_click(obj.get("x"), obj.get("y"))
    elif a == "move_mouse":    pyautogui.moveTo(obj.get("x",0), obj.get("y",0), duration=0.3); return "Moved"
    elif a == "drag":          return do_drag(obj["x1"], obj["y1"], obj["x2"], obj["y2"])
    elif a == "repeat_click":  return do_repeat_click(int(obj.get("times",2)), obj.get("button","left"), float(obj.get("interval",0.3)))
    elif a == "scroll":        return do_scroll(obj.get("direction","down"), int(obj.get("amount",3)))
    elif a == "press_key":     return do_key(obj.get("key",""))
    elif a == "switch_window": _hot('alt','tab'); return "Switched window"
    elif a == "close_window":  _hot('alt','f4'); return "Closed window"
    elif a == "minimize":      _hot('win','down'); return "Minimized"
    elif a == "maximize":      _hot('win','up'); return "Maximized"
    elif a == "show_desktop":  _hot('win','d'); return "Show desktop"
    elif a == "screenshot":    return do_screenshot()
    elif a == "volume_up":     return do_volume('up',  int(obj.get("steps",5)))
    elif a == "volume_down":   return do_volume('down',int(obj.get("steps",5)))
    elif a == "volume_by":     return do_volume_by(int(obj.get("delta",10)))
    elif a == "volume_mute":   _press('volumemute'); return "Muted"
    elif a == "volume_set":    return do_volume_set(int(obj.get("percent",50)))
    elif a == "lock_screen":   return do_lock()
    elif a == "shutdown":      return do_shutdown()
    elif a == "restart":       return do_restart()
    elif a == "sleep":         return do_sleep()
    elif a == "close_app":     return do_close_app(obj.get("app",""))
    elif a == "close_browser": return _close_driver()

    elif a == "datetime":
        now = datetime.now()
        msg = f"Time: {now.strftime('%I:%M %p')}, Date: {now.strftime('%A, %d %B %Y')}"
        do_type(msg); return msg

    elif a == "system_info":  return do_system_info_routine()
    elif a == "weather":      return do_weather_routine(obj.get("city","Mumbai"))
    elif a == "news":         return do_news_routine(obj.get("topic","general"), int(obj.get("count",5)))
    elif a == "calculate":    return do_calculate_routine(obj.get("expression",""))
    elif a == "web_search":   return do_web_search_routine(obj.get("query",""))
    elif a == "reminder":     return add_reminder(obj.get("message","reminder"), float(obj.get("minutes",5)))

    elif a == "chat":
        msg = obj.get("message",""); do_type(msg); return msg

    elif a == "speak":
        speak(obj.get("text","")); return "Spoke"

    # ── AGENT TASK (all browser/app automation) ───────────────────────────────
    elif a == "agent_task" or obj.get("_platform_action") == "agent_task":
        # Restore action for agent dispatcher if it was modified by _validate_action
        if "_platform_action" in obj:
            # action field now holds sub-action (search/play/message/etc.)
            pass  # do_agent_task reads obj.get("action","open") directly
        return do_agent_task(obj)

    elif a == "multi_step":
        steps = obj.get("steps", []); results = []
        for step in steps:
            delay = step.pop("delay_before", 0)
            if delay: time.sleep(float(delay))
            results.append(execute(step))
        return " → ".join(results)

    # ── CATCH ALL: if none of the above matched, recover with PyAutoGUI ─────────
    else:
        t = str(a).lower().strip()
        print(f"[JARVIS] Unhandled action='{a}' — auto-recovering with PyAutoGUI")

        # Try to execute via PyAutoGUI directly based on action name
        PYAUTOGUI_MAP = {
            "type":          lambda: do_type(obj.get("text", obj.get("message","")), False),
            "write":         lambda: do_type(obj.get("text", obj.get("message","")), False),
            "press":         lambda: do_key(obj.get("key","enter")),
            "hotkey":        lambda: do_key(obj.get("key","ctrl+c")),
            "mouse_click":   lambda: do_click(obj.get("button","left"), obj.get("x"), obj.get("y")),
            "left_click":    lambda: do_click("left", obj.get("x"), obj.get("y")),
            "right_click":   lambda: do_right_click(obj.get("x"), obj.get("y")),
            "dbl_click":     lambda: do_double_click(obj.get("x"), obj.get("y")),
            "scroll_down":   lambda: do_scroll("down", obj.get("amount",3)),
            "scroll_up":     lambda: do_scroll("up",   obj.get("amount",3)),
            "move":          lambda: (pyautogui.moveTo(obj.get("x",0), obj.get("y",0), duration=0.3), "Moved")[1],
            "open":          lambda: do_open_app(obj.get("app", obj.get("name", obj.get("url","")))),
            "launch":        lambda: do_open_app(obj.get("app", obj.get("name",""))),
            "close":         lambda: (do_close_app(obj.get("app","")) if obj.get("app") else (_hot('alt','f4') or "Closed")),
            "kill":          lambda: do_close_app(obj.get("app","unknown")),
            "search":        lambda: (webbrowser.open(f"https://google.com/search?q={quote_plus(obj.get('query',''))}") or f"Searched {obj.get('query','')}"),
            "navigate":      lambda: (webbrowser.open(obj.get("url","https://google.com")) or f"Navigated"),
            "goto":          lambda: (webbrowser.open(obj.get("url","https://google.com")) or "Navigated"),
            "browse":        lambda: (webbrowser.open(obj.get("url","https://google.com")) or "Opened"),
            "enter":         lambda: (_press("enter") or "Enter pressed"),
            "tab":           lambda: (_press("tab") or "Tab pressed"),
            "escape":        lambda: (_press("escape") or "Escaped"),
            "backspace":     lambda: (_press("backspace") or "Backspace"),
            "delete":        lambda: (_press("delete") or "Delete"),
            "save":          lambda: (_hot("ctrl","s") or "Saved"),
            "select_text":   lambda: (_hot("ctrl","a") or "Selected all"),
            "bold":          lambda: (_hot("ctrl","b") or "Bold"),
            "new_window":    lambda: (_hot("ctrl","n") or "New window"),
            "new_tab":       lambda: (_hot("ctrl","t") or "New tab"),
            "close_tab":     lambda: (_hot("ctrl","w") or "Tab closed"),
            "switch_tab":    lambda: (_hot("ctrl","tab") or "Switched tab"),
            "refresh":       lambda: (_press("f5") or "Refreshed"),
            "zoom_in":       lambda: (_hot("ctrl","=") or "Zoomed in"),
            "zoom_out":      lambda: (_hot("ctrl","-") or "Zoomed out"),
            "find":          lambda: (_hot("ctrl","f") or "Find opened"),
            "fullscreen":    lambda: (_press("f11") or "Fullscreen"),
            "taskbar":       lambda: (_hot("win","t") or "Taskbar"),
            "run_dialog":    lambda: (_hot("win","r") or "Run dialog"),
            "settings_open": lambda: (_hot("win","i") or "Settings"),
            "create_folder": lambda: agent_file_ops("create_folder", name=obj.get("name",obj.get("path","NewFolder"))),
            "new_folder":    lambda: agent_file_ops("create_folder", name=obj.get("name",obj.get("path","NewFolder"))),
            "folder_create": lambda: agent_file_ops("create_folder", name=obj.get("name","NewFolder")),
            "create_file":   lambda: agent_file_ops("create_file",   name=obj.get("name",obj.get("path","newfile.txt"))),
            "open_folder":   lambda: agent_file_ops("open_folder",   path=obj.get("path","desktop")),
            "open_file":     lambda: agent_file_ops("open_file",     path=obj.get("path","")),
            "delete_file":   lambda: agent_file_ops("delete_file",   name=obj.get("name",obj.get("path",""))),
            "list_files":    lambda: agent_file_ops("list_folder",   path=obj.get("path","desktop")),
            "vol_up":        lambda: do_volume("up", int(obj.get("steps",5))),
            "vol_down":      lambda: do_volume("down", int(obj.get("steps",5))),
            "vol_set":       lambda: do_volume_set(int(obj.get("percent",50))),
            "vol_mute":      lambda: (_press("volumemute") or "Muted"),
            "app_close":     lambda: do_close_app(obj.get("app","")),
            "task_kill":     lambda: do_close_app(obj.get("app",obj.get("process",""))),
            "show_window":   lambda: (_hot("win","up") or "Maximized"),
            "hide_window":   lambda: (_hot("win","down") or "Minimized"),
            "snap_left":     lambda: (_hot("win","left") or "Snapped left"),
            "snap_right":    lambda: (_hot("win","right") or "Snapped right"),
            "next_window":   lambda: (_hot("alt","tab") or "Switched"),
            "clipboard_copy":lambda: (_hot("ctrl","c") or "Copied"),
            "clipboard_paste":lambda:(_hot("ctrl","v") or "Pasted"),
            "ask":           lambda: do_web_search_routine(obj.get("query",obj.get("question",""))),
            "answer":        lambda: do_web_search_routine(obj.get("query",obj.get("question",""))),
            "google":        lambda: do_web_search_routine(obj.get("query","topic")),
            "message":       lambda: agent_whatsapp(obj.get("contact",""),obj.get("text",obj.get("body","")),True),
        }

        # Try exact match first
        fn = PYAUTOGUI_MAP.get(t)
        if fn:
            try:
                result = fn()
                return result if isinstance(result, str) else f"Done: {a}"
            except Exception as ex:
                print(f"[JARVIS] PyAutoGUI recovery '{a}' failed: {ex}")

        # Try partial key match
        for key, fn in PYAUTOGUI_MAP.items():
            if key in t or t in key:
                try:
                    result = fn()
                    return result if isinstance(result, str) else f"Done: {a}"
                except Exception:
                    pass

        # Absolute last resort — type the original text
        orig = obj.get("text", obj.get("message", obj.get("query", "")))
        if orig:
            return do_type(orig, False)

        speak(f"Command {a} not recognized. Please try again.")
        return f"Command '{a}' not recognized — please rephrase"



# ═════════════════════════════════════════════════════════════════════════════
#  JARVIS PERSONA  +  GROQ AI COMMAND PARSER
# ═════════════════════════════════════════════════════════════════════════════

# ── Initialize AI clients ─────────────────────────────────────────────────────
groq_client = None
if HAS_GROQ:
    try:
        groq_client = groq_lib.Groq(api_key=GROQ_API_KEY)
    except Exception as _e:
        print(f"  [WARN] Groq init failed: {_e}")

# NVIDIA Nemotron — reasoning model via OpenAI-compatible API
nvidia_client = None
if HAS_OPENAI:
    try:
        nvidia_client = OpenAI_SDK(
            base_url = NVIDIA_BASE_URL,
            api_key  = NVIDIA_API_KEY,
        )
        print("  ✅ NVIDIA Nemotron-3 Nano 30B (reasoning, streaming) ready")
    except Exception as e:
        print(f"  [WARN] NVIDIA init failed: {e}")
        nvidia_client = None

JARVIS_PERSONA = """You are Jarvis, a smart real-time AI assistant running on a local computer.
Capabilities: Answer real-time questions, execute commands, write text exactly as instructed, open apps, generate text, control browser, send messages, play music, follow instructions strictly.
Rules:
- Never say you do not have real-time access. Never mention knowledge cutoff.
- Always try to answer. If unsure, give best approximate answer.
- Follow user command exactly. Do not rewrite, shorten, or expand unless asked.
- If user says exact length, follow exact length strictly.
- If user says open app, open it. If user says search, search it. If user says send message, send it."""

SYSTEM_PROMPT = JARVIS_PERSONA + """

You are also a PC automation AI. Convert the user's spoken COMMAND to ONE JSON action object.
Reply ONLY with valid JSON. No markdown, no explanation.

═══════════════════════════════════════════════════
STANDARD ACTIONS
═══════════════════════════════════════════════════
{"action":"open_app","app":"<name>"}
{"action":"search_web","query":"<q>","engine":"google"}
{"action":"open_url","url":"<url>"}
{"action":"gmail_compose","to":"<>","subject":"<>","body":"<>"}
{"action":"type_text","text":"VERBATIM","char_limit":0,"press_enter":false}
  RULE: char_limit — if user says "write 300 characters X" set char_limit=300. text = verbatim, NEVER shorten.
{"action":"edit_selected_ai","instruction":"Rewrite the text to be exactly 300 characters long."}
  RULE: When user says "make this/it N characters/words" → select existing text and REWRITE it.
  This is EDITING, not typing. The user wants to MODIFY existing text to a target length.
  Examples: "make this 300 characters" → edit_selected_ai with instruction to rewrite to 300 chars
            "make this word in 300 characters" → same, rewrite to 300 characters
            "make it shorter" → edit_selected_ai instruction="make shorter"
            "expand this to 500 words" → edit_selected_ai instruction="expand to 500 words"
{"action":"delete_text","chars":1}
{"action":"select_all"} {"action":"copy"} {"action":"paste"} {"action":"undo"} {"action":"redo"}
{"action":"clipboard_ai","instruction":"summarize|fix grammar|translate to Hindi"}
{"action":"click","button":"left","x":null,"y":null}
{"action":"repeat_click","times":5,"button":"left","interval":0.3}
{"action":"scroll","direction":"down|up","amount":3}
{"action":"press_key","key":"ctrl+c"}
{"action":"switch_window"} {"action":"close_window"} {"action":"minimize"} {"action":"maximize"}
{"action":"screenshot"} {"action":"lock_screen"} {"action":"shutdown"} {"action":"restart"} {"action":"sleep"}
{"action":"volume_up","steps":5} {"action":"volume_down","steps":5} {"action":"volume_mute"}
{"action":"volume_set","percent":70}
{"action":"volume_by","delta":10}   ← increase volume by N%
{"action":"volume_by","delta":-10}  ← decrease volume by N%
{"action":"close_app","app":"<name>"}
{"action":"news","topic":"ai|tech|india|world|business|sports|science|general","count":5}
{"action":"weather","city":"Mumbai"}
{"action":"calculate","expression":"15 percent of 5000"}
{"action":"web_search","query":"<q>"}
{"action":"datetime"} {"action":"system_info"}
{"action":"reminder","message":"<msg>","minutes":5}
{"action":"speak","text":"<text>"}
{"action":"chat","message":"<reply>"}
{"action":"close_browser"}
{"action":"multi_step","steps":[{"action":"...","delay_before":0}]}

═══════════════════════════════════════════════════
AGENT TASK ACTIONS  (browser + desktop automation)
═══════════════════════════════════════════════════
{"action":"agent_task","platform":"youtube","task":"search","query":"karan aujla"}
{"action":"agent_task","platform":"youtube","task":"play","query":"karan aujla best songs"}
{"action":"agent_task","platform":"youtube","task":"scroll","query":"down"}
{"action":"agent_task","platform":"whatsapp","task":"message","contact":"Tarun","message":"hello","send":true}
{"action":"agent_task","platform":"telegram","task":"message","contact":"Mom","message":"coming home","send":true}
{"action":"agent_task","platform":"instagram","task":"open"}
{"action":"agent_task","platform":"instagram","task":"search","query":"karan aujla"}
{"action":"agent_task","platform":"instagram","task":"scroll","query":"down"}
{"action":"agent_task","platform":"instagram","task":"dm","dm_user":"username","dm_msg":"hey"}
{"action":"agent_task","platform":"twitter","task":"open"}
{"action":"agent_task","platform":"twitter","task":"search","query":"AI news"}
{"action":"agent_task","platform":"twitter","task":"tweet","tweet":"hello world"}
{"action":"agent_task","platform":"twitter","task":"scroll","query":"down"}
{"action":"agent_task","platform":"spotify","task":"play","query":"karan aujla songs"}
{"action":"agent_task","platform":"spotify","task":"search","query":"lofi beats"}
{"action":"agent_task","platform":"gmail","to":"x@gmail.com","subject":"hi","body":"how are you","send":false}
{"action":"agent_task","platform":"chrome","task":"open","url":"https://github.com"}
{"action":"agent_task","platform":"chrome","task":"search","query":"python tutorials"}
{"action":"agent_task","platform":"chrome","task":"scroll","scroll":"down"}
{"action":"agent_task","platform":"chrome","task":"back"}
{"action":"agent_task","platform":"chrome","task":"new_tab"}
{"action":"agent_task","platform":"facebook","task":"open"}
{"action":"agent_task","platform":"facebook","task":"search","query":"karan aujla"}
{"action":"agent_task","platform":"linkedin","task":"open"}
{"action":"agent_task","platform":"linkedin","task":"search","query":"software engineer","search_type":"jobs"}
{"action":"agent_task","platform":"reddit","task":"open","subreddit":"india"}
{"action":"agent_task","platform":"reddit","task":"search","query":"python tips"}
{"action":"agent_task","platform":"files","task":"open_folder","path":"downloads"}
{"action":"agent_task","platform":"files","task":"open_file","path":"report.pdf"}

═══════════════════════════════════════════════════
ROUTING RULES — CRITICAL
═══════════════════════════════════════════════════
CRITICAL: For agent_task, use "task" key for the sub-action — NOT "action"!
This avoids duplicate JSON keys that break parsing.

- "open youtube search karan aujla" → {"action":"agent_task","platform":"youtube","task":"search","query":"karan aujla"}
- "play karan aujla on youtube"     → {"action":"agent_task","platform":"youtube","task":"play","query":"karan aujla"}
- "youtube scroll down"             → {"action":"agent_task","platform":"youtube","task":"scroll","query":"down"}
- "open telegram message mom hello" → {"action":"agent_task","platform":"telegram","task":"message","contact":"mom","message":"hello","send":true}
- "send whatsapp to tarun hi"       → {"action":"agent_task","platform":"whatsapp","task":"message","contact":"tarun","message":"hi","send":true}
- "open instagram"                  → {"action":"agent_task","platform":"instagram","task":"open"}
- "instagram search karan"          → {"action":"agent_task","platform":"instagram","task":"search","query":"karan"}
- "instagram scroll"                → {"action":"agent_task","platform":"instagram","task":"scroll","query":"down"}
- "tweet hello world"               → {"action":"agent_task","platform":"twitter","task":"tweet","tweet":"hello world"}
- "open twitter"                    → {"action":"agent_task","platform":"twitter","task":"open"}
- "play karan aujla on spotify"     → {"action":"agent_task","platform":"spotify","task":"play","query":"karan aujla"}
- "open gmail compose leave application" → {"action":"agent_task","platform":"gmail","to":"","subject":"Leave Application","body":"write leave application","send":false}
- "open chrome go to github.com"    → {"action":"agent_task","platform":"chrome","task":"open","url":"https://github.com"}
- "chrome search python"            → {"action":"agent_task","platform":"chrome","task":"search","query":"python"}
- "open facebook"                   → {"action":"agent_task","platform":"facebook","task":"open"}
- "open linkedin search jobs python"→ {"action":"agent_task","platform":"linkedin","task":"search","query":"python","search_type":"jobs"}
- "search reddit python tips"       → {"action":"agent_task","platform":"reddit","task":"search","query":"python tips"}
- "open downloads folder"           → {"action":"agent_task","platform":"files","task":"open_folder","path":"downloads"}
- "close browser"                   → {"action":"close_browser"}
- For ANY question (who/what/price/news/when) → web_search action
- char_limit: "write 300 characters X" → type_text text=X char_limit=300 (NEVER truncate text field)
- EDITING existing text: "make this 300 characters" / "make it 300 chars" / "make this word in 300 characters" → edit_selected_ai instruction="Rewrite to 300 characters"
  CRITICAL: When user says "make this/it/the sentence X characters", they want to EDIT existing text, NOT type new text. Use edit_selected_ai.

ONLY output JSON."""


def _extract_json(raw: str):
    """
    Robustly extract the first complete JSON object from raw string.
    Handles: markdown fences, pretty-printed JSON, trailing text,
    single-quoted keys, and Nemotron multiline output.
    """
    import re as _re, json as _json
    # Strip markdown code fences
    raw = _re.sub(r'```json\s*|```', '', raw).strip()
    # Remove any <think>...</think> reasoning tags some models emit
    raw = _re.sub(r'<think>.*?</think>', '', raw, flags=_re.DOTALL).strip()

    # Find outermost { ... } block
    depth = 0; start = None
    for i, ch in enumerate(raw):
        if ch == '{':
            if start is None: start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start is not None:
                chunk = raw[start:i+1]
                try:
                    return _json.loads(chunk)
                except _json.JSONDecodeError:
                    # Try fixing common issues: single quotes, trailing commas
                    try:
                        fixed = _re.sub(r",\s*([}\]])", r"\1", chunk)  # trailing commas
                        fixed = fixed.replace("'", '"'  )              # single→double quotes
                        return _json.loads(fixed)
                    except Exception:
                        pass
                break
    # Last resort: try the whole string
    try:
        return _json.loads(raw)
    except Exception:
        return None


def _validate_action(obj: dict, original_text: str) -> dict:
    """
    Iron-clad post-processor. EVERY output is guaranteed to be a valid executable action.
    Handles: task/action key collisions, all unknown actions, partial speech, edge cases.
    """
    VALID_ACTIONS = {
        "open_app","open_url","search_web","gmail_compose","whatsapp",
        "type_text","delete_text","select_all","copy","paste","undo","redo","new_line",
        "clipboard_ai","click","double_click","right_click","move_mouse","drag",
        "repeat_click","scroll","press_key","switch_window","close_window",
        "minimize","maximize","show_desktop","screenshot","lock_screen",
        "shutdown","restart","sleep","close_app","close_browser",
        "volume_up","volume_down","volume_mute","volume_set","volume_by",
        "datetime","system_info","weather","news","calculate",
        "web_search","reminder","chat","speak","agent_task","multi_step",
    }

    PLATFORMS = {
        "youtube","instagram","twitter","telegram","whatsapp","spotify",
        "facebook","linkedin","reddit","chrome","browser","brave","edge",
        "gmail","files","netflix","amazon","github","notion","figma","maps",
    }

    # ── Step 1: Fix duplicate/misplaced action keys ──────────────────────────
    # If "platform" exists but outer "action" is not agent_task → fix it
    if "platform" in obj:
        outer = obj.get("action","")
        if outer != "agent_task":
            if outer in ("search","play","message","open","scroll","tweet",
                         "dm","post","back","forward","refresh","new_tab",
                         "create_folder","open_folder","open_file","list_folder"):
                # outer is actually the task/sub-action, not the outer action
                obj["task"] = outer
                obj["action"] = "agent_task"
            elif outer not in VALID_ACTIONS:
                obj["task"] = outer
                obj["action"] = "agent_task"

    # ── Step 2: Resolve action ───────────────────────────────────────────────
    action = obj.get("action", "")

    # ── Step 3: If still not valid → RECOVER using original text ────────────
    if action not in VALID_ACTIONS:
        t = original_text.lower().strip()
        print(f"[JARVIS RECOVER] action='{action}' | cmd='{t[:60]}'")

        # Platform-based agent task
        matched_platform = next((p for p in PLATFORMS if p in t), None)
        if matched_platform:
            sub = ("play"    if t.startswith("play") or "play" in t else
                   "search"  if "search" in t or "find" in t or "look" in t else
                   "message" if any(x in t for x in ["message","msg","send","text","whatsapp","telegram"]) else
                   "tweet"   if "tweet" in t else
                   "scroll"  if "scroll" in t else
                   "dm"      if "dm" in t else "open")
            # Extract query: remove platform + sub-action + filler words
            query = t
            for word in [matched_platform,"open","search","play","find","message","send",
                         "on","the","and","go","to","in","at","a","an","with","for"]:
                query = re.sub(rf"{re.escape(word)}", " ", query, flags=re.I)
            query = re.sub(r"\s+", " ", query).strip()
            return {"action":"agent_task","platform":matched_platform,"task":sub,"query":query}

        # Keyword routing
        starters_web = ["who ","what ","where ","when ","why ","how ",
                        "price of","tell me","find ","search for","is ","are ",
                        "does ","did ","was ","which ","define "]
        if any(t.startswith(w) for w in starters_web) or t.endswith("?"):
            return {"action":"web_search","query":original_text}

        if t.startswith("open "):
            app = original_text[5:].strip()
            return {"action":"open_app","app":app} if app else {"action":"chat","message":"Open which app?"}

        if t.startswith("play "):
            q = re.sub(r"(play|on youtube|on spotify|on music)","",t,flags=re.I).strip()
            return {"action":"agent_task","platform":"youtube","task":"play","query":q}

        if t.startswith("type ") or t.startswith("write "):
            body = re.sub(r"^(type|write)\s+","",t).strip()
            return {"action":"type_text","text":body,"press_enter":False}

        # Single word special cases
        WORD_MAP = {
            "screenshot":"screenshot","snap":"screenshot","capture":"screenshot",
            "mute":"volume_mute","unmute":"volume_mute","silence":"volume_mute",
            "minimize":"minimize","maximise":"maximize","maximize":"maximize",
            "lock":"lock_screen","sleep":"sleep","restart":"restart","shutdown":"shutdown",
            "copy":"copy","paste":"paste","undo":"undo","redo":"redo",
            "back":"press_key","forward":"press_key",
        }
        if t in WORD_MAP:
            mapped = WORD_MAP[t]
            if mapped == "press_key":
                return {"action":"press_key","key":"alt+left" if t=="back" else "alt+right"}
            return {"action":mapped}

        # Contains key verbs
        if "screenshot" in t: return {"action":"screenshot"}
        if "mute" in t:        return {"action":"volume_mute"}
        if "click" in t:       return {"action":"click","button":"left"}
        if "scroll" in t:
            return {"action":"scroll","direction":"down" if "down" in t else "up","amount":3}

        # Too short — dictate it
        if len(t.split()) <= 1 and t:
            return {"action":"type_text","text":original_text,"press_enter":False}

        # Fallback: type it verbatim
        return {"action":"type_text","text":original_text,"press_enter":False}

    # ── Step 4: Post-process valid actions ───────────────────────────────────

    # type_text: always restore verbatim original unless char_limit explicitly set
    if action == "type_text" and not obj.get("char_limit"):
        obj["text"] = original_text

    # agent_task: ensure task key is set
    if action == "agent_task" and not obj.get("task"):
        obj["task"] = obj.get("action_sub","open")

    return obj


def _nvidia_stream_parse(prompt: str) -> str:
    """
    Call NVIDIA Nemotron with reasoning + streaming.
    Returns the final content text (after reasoning chain-of-thought).
    Shows reasoning dots on overlay while thinking.
    """
    if not nvidia_client:
        return ""
    try:
        completion = nvidia_client.chat.completions.create(
            model       = NVIDIA_MODEL,
            messages    = [{"role":"user","content": prompt}],
            temperature = 0.1,
            top_p       = 1,
            max_tokens  = 1024,
            extra_body  = {
                "reasoning_budget":   1024,
                "chat_template_kwargs": {"enable_thinking": True},
            },
            stream = True,
        )
        reasoning_buf = []
        content_buf   = []
        for chunk in completion:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            # Collect reasoning tokens (chain-of-thought)
            reasoning = getattr(delta, "reasoning_content", None)
            if reasoning:
                reasoning_buf.append(reasoning)
            # Collect final content tokens
            if delta.content:
                content_buf.append(delta.content)
        final = "".join(content_buf).strip()
        if reasoning_buf:
            reasoning_text = "".join(reasoning_buf).strip()
            print(f"[NVIDIA REASONING] {reasoning_text[:120]}...")
        return final
    except Exception as e:
        print(f"[NVIDIA] Error: {e}")
        return ""


def ai_parse(text: str) -> dict:
    """
    Parse user command to action JSON.
    PRIMARY:  NVIDIA Nemotron-3 Nano 30B  (reasoning model, streaming)
    FALLBACK: Groq LLaMA 3.3 70B
    SAFETY:   _validate_action auto-fixes any bad/unknown actions
    """
    ctx = (f"Context: last_app={CTX['last_app']}, "
           f"compose_open={CTX['compose_open']}, recipient={CTX['recipient']}")

    # Build system prompt with optional custom persona
    custom = get_pref("custom_ai_prompt", "")
    sys_prompt = SYSTEM_PROMPT + "\n\n" + ctx
    if custom:
        sys_prompt += f"\n\nUser style: {custom}"

    # Rolling conversation context (last 10 messages)
    history_msgs = []
    recent = CONV_HISTORY[-10:] if CONV_HISTORY else []
    for msg in recent:
        if msg["role"] in ("user","assistant"):
            history_msgs.append({"role": msg["role"], "content": msg["content"][:200]})

    # ── PRIMARY: NVIDIA Nemotron (reasoning + streaming) ─────────────────────
    if nvidia_client:
        try:
            # Build a single prompt string for Nemotron
            # (it works best with a combined prompt rather than system+messages)
            full_prompt = (
                f"{sys_prompt}\n\n"
                f"{''.join([m['role'].upper() + ': ' + m['content'] + chr(10) for m in history_msgs])}"
                f"USER COMMAND: {text}\n\n"
                "Reply with ONLY valid JSON action object."
            )
            raw = _nvidia_stream_parse(full_prompt)
            if raw:
                obj = _extract_json(raw)
                if obj:
                    return _validate_action(obj, text)
                print(f"[NVIDIA] No JSON in response: {raw[:120]}")
        except Exception as e:
            print(f"[NVIDIA] Parse error: {e}")

    # ── FALLBACK: Groq LLaMA 3.3 70B ─────────────────────────────────────────
    if groq_client:
        try:
            messages = [{"role":"system","content": sys_prompt}]
            messages.extend(history_msgs)
            messages.append({"role":"user","content": text})
            r = groq_client.chat.completions.create(
                model      = "llama-3.3-70b-versatile",
                messages   = messages,
                max_tokens = 700,
                temperature= 0.0
            )
            raw = r.choices[0].message.content.strip()
            obj = _extract_json(raw)
            if obj:
                return _validate_action(obj, text)
            print(f"[GROQ] No JSON: {raw[:120]}")
        except Exception as e:
            print(f"[GROQ] Error: {e}")

    # ── Smart keyword fallback (zero AI) ─────────────────────────────────────
    t = text.lower().strip()
    if any(t.startswith(w) for w in ["who ","what ","where ","when ","why ","how ","price","tell me","find ","search "]):
        return {"action":"web_search","query":text}
    if t.startswith("open "):
        return {"action":"open_app","app":text[5:].strip()}
    if t.startswith("play "):
        q = re.sub(r"\b(play|on youtube|on spotify)\b","",t,flags=re.I).strip()
        return {"action":"agent_task","platform":"youtube","task":"play","query":q}
    return {"action":"type_text","text":text,"press_enter":False}


# ═════════════════════════════════════════════════════════════════════════════
#  LOCAL FAST-PATH PARSER  (no Groq needed for common patterns)
# ═════════════════════════════════════════════════════════════════════════════

COMMAND_TRIGGERS = [
    # App control
    "open ","close ","launch ","start ","run ","kill ",
    # Browser
    "chrome ","browser ","brave ","edge ","youtube ","instagram ",
    "twitter ","facebook ","linkedin ","reddit ","spotify ",
    "whatsapp ","telegram ","gmail ","r/",
    # Play / watch
    "play ","watch ","listen ","stream ",
    # Search
    "search ","find ","look up ","google ","browse ",
    # Mouse / click
    "click","double click","right click","auto click","auto-click",
    "move mouse","drag ","scroll ","scroll down","scroll up",
    # Keyboard
    "type ","write ","press ","hit ","press enter","new line",
    "select all","copy","paste","undo","redo","save","delete text",
    "ctrl ","alt ","win ","hotkey ","shortcut ",
    # Volume
    "volume","mute","unmute","louder","quieter",
    "increase volume","decrease volume","raise volume","lower volume",
    "turn up","turn down","set volume",
    # Window
    "minimize","maximize","show desktop","switch window",
    "close window","close tab","new tab","new window","snap ",
    "fullscreen","full screen","zoom in","zoom out","refresh",
    # System power
    "lock","lock screen","shutdown","shut down","restart","reboot","sleep","hibernate",
    # Screenshot
    "screenshot","screen shot","screen capture","snap screen","capture screen",
    # File / folder
    "make folder","create folder","new folder","delete folder",
    "open folder","open file","create file","delete file","rename ",
    "list desktop","list downloads","list files","show files",
    # Clipboard
    "summarize clipboard","fix grammar","fix spelling","translate clipboard",
    "rewrite","make it formal","make it shorter","make this","make it",
    "expand this","shorten this","make the ",
    # Knowledge / info
    "who is","what is","what are","where is","when is","why is","how to","how do","how does",
    "price of","tell me","explain","define","meaning of","search for","find me",
    # System info
    "system info","cpu","ram usage","memory","battery","disk usage",
    "what time","current time","date today","time now",
    # News / weather / calc
    "news","today news","latest news","weather ","calculate ","calc ",
    # Reminder
    "remind me","set reminder","set timer","set alarm",
    # Memory / settings
    "clear history","clear memory","show history","set custom prompt",
    "enable wake word","disable wake word","set wake word",
    "add command","list commands","enable smart skip","disable smart skip",
    "set voice speed","set tts rate",
    # Auto-routines
    "tweet ","send email","email to","message ","dm ",
    # Power / sleep
    "make the pc","make pc","put the pc","put pc","put the computer",
    "make the computer","sleep mode","pc sleep","computer sleep",
    "power off","turn off the","turn off pc","turn off computer",
]


def is_command(text: str) -> bool:
    """Returns True if text should be parsed as a command (not pure dictation)."""
    t = text.lower().strip()
    if not t: return False
    # Starts with a trigger keyword
    if any(t.startswith(tr.strip()) or t == tr.strip() for tr in COMMAND_TRIGGERS):
        return True
    # Ends with question mark
    if t.endswith("?"):
        return True
    # Contains key question words mid-sentence
    if any(f" {w} " in f" {t} " for w in ["is","are","was","were","does","did","will","can","could","would","should","has","have"]):
        return True
    return False


def local_parse(text: str):
    """
    Exhaustive fast-path parser using only regex — NO AI needed.
    Covers 200+ command patterns. If matched, instantly executes with PyAutoGUI.
    Only truly ambiguous/complex commands fall through to AI.
    """
    import re as _re
    t = text.lower().strip()
    # Remove filler words from start
    t_clean = _re.sub(r'^(?:please|jarvis|hey|ok|can you|could you|would you|just)\s+', '', t).strip()

    # ── SETTINGS ──────────────────────────────────────────────────────────────
    m = _re.search(r'set\s+(?:custom\s+)?(?:prompt|persona|style)\s+(.+)', t)
    if m:
        set_pref("custom_ai_prompt", m.group(1).strip())
        speak("Custom prompt updated.")
        return {"action":"chat","message":f"Custom AI prompt: {m.group(1)[:50]}"}
    if _re.search(r'clear\s+(?:custom\s+)?(?:prompt|persona)', t):
        set_pref("custom_ai_prompt",""); speak("Custom prompt cleared.")
        return {"action":"chat","message":"Custom prompt cleared."}
    if _re.search(r'enable\s+wake\s+word', t):
        set_pref("wake_word_enabled",True); speak("Wake word enabled.")
        return {"action":"chat","message":"Wake word enabled."}
    if _re.search(r'disable\s+wake\s+word', t):
        set_pref("wake_word_enabled",False); speak("Wake word disabled.")
        return {"action":"chat","message":"Wake word disabled."}
    m = _re.search(r'set\s+wake\s+word\s+(?:to\s+)?(.+)', t)
    if m:
        set_pref("wake_word", m.group(1).strip()); speak(f"Wake word: {m.group(1).strip()}")
        return {"action":"chat","message":f"Wake word set: {m.group(1).strip()}"}
    if _re.search(r'enable\s+smart\s+skip', t):
        set_pref("smart_skip",True); return {"action":"chat","message":"Smart skip enabled."}
    if _re.search(r'disable\s+smart\s+skip', t):
        set_pref("smart_skip",False); return {"action":"chat","message":"Smart skip disabled."}
    m = _re.search(r'set\s+(?:voice|tts|speech)\s+(?:speed|rate)\s+(\d+)', t)
    if m:
        set_pref("tts_rate",int(m.group(1))); speak(f"Voice speed {m.group(1)}")
        return {"action":"chat","message":f"TTS rate: {m.group(1)}"}
    m = _re.search(r'add\s+(?:custom\s+)?command\s+(.+?)\s+(?:to\s+do|means?|=|:)\s+(.+)', t)
    if m:
        CUSTOM_COMMANDS[m.group(1).strip()] = m.group(2).strip()
        _save_custom_commands(CUSTOM_COMMANDS)
        speak(f"Command added: {m.group(1).strip()}")
        return {"action":"chat","message":f"Command: '{m.group(1)}' → '{m.group(2)}'"}
    if _re.search(r'list\s+(?:custom\s+)?commands?', t):
        lines = [f"• {k} → {v}" for k,v in CUSTOM_COMMANDS.items()] if CUSTOM_COMMANDS else ["No custom commands."]
        do_type("\n".join(lines))
        return {"action":"chat","message":f"{len(CUSTOM_COMMANDS)} commands"}
    if _re.search(r'(?:show|list)\s+(?:conversation\s+)?history', t):
        lines = [f"{m['role'].upper()}: {m['content'][:60]}" for m in CONV_HISTORY[-8:]] if CONV_HISTORY else ["No history."]
        do_type("\n".join(lines))
        return {"action":"chat","message":"Showing history"}

    # ── NEWS ──────────────────────────────────────────────────────────────────
    for topic in ["ai","tech","technology","india","world","business","sports","science","health","crypto"]:
        if f"news {topic}" in t or f"{topic} news" in t:
            return {"action":"news","topic":topic,"count":5}
    if _re.search(r'^(?:today\s+)?(?:latest\s+)?(?:top\s+)?news$|^current news$', t):
        return {"action":"news","topic":"general","count":5}

    # ── WEATHER ───────────────────────────────────────────────────────────────
    m = _re.search(r'weather\s+(?:in\s+|of\s+|for\s+)?(.+)', t)
    if m: return {"action":"weather","city":m.group(1).strip().title()}
    if 'weather' in t: return {"action":"weather","city":"Mumbai"}

    # ── CALCULATE ─────────────────────────────────────────────────────────────
    m = _re.search(r'(?:calculate|calc|compute|what\s+is)\s+(.+?)(?:\s+(?:equals?|=).*)?$', t)
    if m and any(c in m.group(1) for c in '0123456789%'):
        return {"action":"calculate","expression":m.group(1).strip()}
    m = _re.search(r'(\d+(?:\.\d+)?)\s*(?:percent|%)\s+of\s+(\d+(?:\.\d+)?)', t)
    if m: return {"action":"calculate","expression":f"{m.group(1)}% of {m.group(2)}"}

    # ── SYSTEM INFO ───────────────────────────────────────────────────────────
    if any(x in t for x in ("system info","cpu usage","ram usage","battery status","disk usage","memory usage")):
        return {"action":"system_info"}

    # ── DATETIME ──────────────────────────────────────────────────────────────
    if any(x in t for x in ("what time","what is the time","current time","date today","today date","what is today")):
        return {"action":"datetime"}

    # ── REMINDERS ─────────────────────────────────────────────────────────────
    m = _re.search(r'remind\s+me\s+in\s+(\d+)\s*(min|minute|minutes|hour|hours|sec|second|seconds)\s+(?:to\s+)?(.+)', t)
    if m:
        n, unit, msg = int(m.group(1)), m.group(2), m.group(3)
        mins = n*60 if "hour" in unit else (n/60 if "sec" in unit else n)
        return {"action":"reminder","message":msg,"minutes":mins}
    m = _re.search(r'set\s+(?:a\s+)?(?:timer|reminder|alarm)\s+(?:for\s+)?(\d+)\s*(min|minute|minutes|hour|hours)', t)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        return {"action":"reminder","message":"Timer done","minutes":n*60 if "hour" in unit else n}

    # ── VOLUME ────────────────────────────────────────────────────────────────
    # Exact set
    m = _re.search(r'(?:set\s+)?(?:the\s+)?volume\s+(?:to\s+|at\s+)?(\d+)\s*(?:percent|%)?$', t)
    if m: return {"action":"volume_set","percent":int(m.group(1))}
    # Increase by N
    m = _re.search(r'(?:increase|raise|turn\s+up|boost|up)\s+(?:the\s+)?volume\s+(?:by\s+)?(\d+)', t)
    if m: return {"action":"volume_by","delta":int(m.group(1))}
    # Decrease by N
    m = _re.search(r'(?:decrease|lower|turn\s+down|reduce|down)\s+(?:the\s+)?volume\s+(?:by\s+)?(\d+)', t)
    if m: return {"action":"volume_by","delta":-int(m.group(1))}
    # Volume up by N (alternate)
    m = _re.search(r'volume\s+(?:up|increase)\s+(?:by\s+)?(\d+)', t)
    if m: return {"action":"volume_by","delta":int(m.group(1))}
    m = _re.search(r'volume\s+(?:down|decrease)\s+(?:by\s+)?(\d+)', t)
    if m: return {"action":"volume_by","delta":-int(m.group(1))}
    # Simple up/down
    if _re.search(r'^(?:volume\s+up|increase\s+volume|louder|turn\s+it\s+up)$', t):
        return {"action":"volume_by","delta":10}
    if _re.search(r'^(?:volume\s+down|decrease\s+volume|quieter|lower\s+it|turn\s+it\s+down)$', t):
        return {"action":"volume_by","delta":-10}
    if _re.search(r'^(?:mute|unmute|silence|toggle\s+mute)$', t):
        return {"action":"volume_mute"}
    if _re.search(r'(?:mute|silence)\s+(?:the\s+)?(?:sound|volume|audio)', t):
        return {"action":"volume_mute"}

    # ── SCREENSHOT ────────────────────────────────────────────────────────────
    if _re.search(r'(?:take\s+)?(?:a\s+)?(?:screenshot|screen\s+shot|screen\s+capture|screengrab|snap\s+screen|capture\s+screen)', t):
        return {"action":"screenshot"}

    # ── KEYBOARD SHORTCUTS ────────────────────────────────────────────────────
    if _re.search(r'^(?:select\s+all|ctrl\s*a)$', t): return {"action":"select_all"}
    if _re.search(r'^(?:copy|ctrl\s*c)$', t):          return {"action":"copy"}
    if _re.search(r'^(?:paste|ctrl\s*v)$', t):         return {"action":"paste"}
    if _re.search(r'^(?:undo|ctrl\s*z)$', t):          return {"action":"undo"}
    if _re.search(r'^(?:redo|ctrl\s*y)$', t):          return {"action":"redo"}
    if _re.search(r'^(?:save|ctrl\s*s)$', t):          return {"action":"press_key","key":"ctrl+s"}
    if _re.search(r'^(?:new\s+tab|ctrl\s*t)$', t):     return {"action":"press_key","key":"ctrl+t"}
    if _re.search(r'^(?:close\s+tab|ctrl\s*w)$', t):   return {"action":"press_key","key":"ctrl+w"}
    if _re.search(r'^new\s+window$', t):                return {"action":"press_key","key":"ctrl+n"}
    if _re.search(r'^(?:refresh|reload)\s*(?:page|tab)?$', t): return {"action":"press_key","key":"f5"}
    if _re.search(r'^(?:find|search\s+in\s+page|ctrl\s*f)$', t): return {"action":"press_key","key":"ctrl+f"}
    if _re.search(r'^(?:zoom\s+in|ctrl\s*plus)$', t):  return {"action":"press_key","key":"ctrl+="}
    if _re.search(r'^(?:zoom\s+out|ctrl\s*minus)$', t):return {"action":"press_key","key":"ctrl+-"}
    if _re.search(r'^(?:fullscreen|full\s+screen|f11)$', t): return {"action":"press_key","key":"f11"}
    if _re.search(r'^go\s+back$', t):                  return {"action":"press_key","key":"alt+left"}
    if _re.search(r'^go\s+forward$', t):               return {"action":"press_key","key":"alt+right"}
    m = _re.search(r'press\s+(.+)', t)
    if m: return {"action":"press_key","key":m.group(1).strip().replace(" ","+").replace("and","+")}

    # ── MOUSE / CLICK ─────────────────────────────────────────────────────────
    m = _re.search(r'click\s+(\d+)\s*times?', t)
    if m: return {"action":"repeat_click","times":int(m.group(1)),"button":"left","interval":0.3}
    m = _re.search(r'auto\s*click\s*(?:(\d+)\s*times?)?(?:\s*every\s*(\d+(?:\.\d+)?)\s*(?:sec|second)s?)?', t)
    if m:
        times = int(m.group(1)) if m.group(1) else 10
        interval = float(m.group(2)) if m.group(2) else 0.5
        return {"action":"repeat_click","times":times,"button":"left","interval":interval}
    if _re.search(r'^(?:click|left\s*click|auto\s*click)$', t):  return {"action":"click","button":"left"}
    if _re.search(r'^(?:double\s*click|dbl\s*click)$', t):       return {"action":"double_click"}
    if _re.search(r'^right\s*click$', t):                        return {"action":"right_click"}
    # Click at coordinates
    m = _re.search(r'click\s+(?:at\s+)?(?:x\s*[=:]?\s*)?(\d+)\s*[,\s]\s*(?:y\s*[=:]?\s*)?(\d+)', t)
    if m: return {"action":"click","button":"left","x":int(m.group(1)),"y":int(m.group(2))}
    m = _re.search(r'move\s+(?:mouse\s+)?(?:to\s+)?(\d+)\s*[,\s]\s*(\d+)', t)
    if m: return {"action":"move_mouse","x":int(m.group(1)),"y":int(m.group(2))}

    # ── SCROLL ────────────────────────────────────────────────────────────────
    m = _re.search(r'scroll\s+(down|up)\s*(?:(\d+)(?:\s*times?)?)?', t)
    if m:
        direction = m.group(1)
        amount = int(m.group(2)) if m.group(2) else 3
        return {"action":"scroll","direction":direction,"amount":amount}
    if _re.search(r'^scroll\s+down$|^scroll$', t):  return {"action":"scroll","direction":"down","amount":3}
    if _re.search(r'^scroll\s+up$', t):             return {"action":"scroll","direction":"up","amount":3}

    # ── WINDOW MANAGEMENT ─────────────────────────────────────────────────────
    if _re.search(r'^minimize(?:\s+window)?$', t):         return {"action":"minimize"}
    if _re.search(r'^maximize(?:\s+window)?$', t):         return {"action":"maximize"}
    if _re.search(r'^(?:show\s+desktop|win\s*d)$', t):     return {"action":"show_desktop"}
    if _re.search(r'^(?:switch\s+window|alt\s*tab|next\s+window)$', t): return {"action":"switch_window"}
    if _re.search(r'^(?:close\s+window|close\s+this|alt\s*f4)$', t):   return {"action":"close_window"}
    if _re.search(r'^snap\s+left$', t):  return {"action":"press_key","key":"win+left"}
    if _re.search(r'^snap\s+right$', t): return {"action":"press_key","key":"win+right"}
    m = _re.search(r'close\s+(?:app|application|program|process)\s+(.+)', t)
    if m: return {"action":"close_app","app":m.group(1).strip()}

    # ── SYSTEM POWER — matches all natural language variants ─────────────────
    # SLEEP — must check BEFORE open_app since "sleep" could be confused
    if _re.search(r'(?:^|\s)(?:put\s+(?:the\s+)?(?:pc|computer|laptop|system|windows?)\s+(?:to\s+)?sleep'
                  r'|make\s+(?:the\s+)?(?:pc|computer|laptop|system|windows?)\s+(?:go\s+to\s+)?sleep'
                  r'|sleep\s+(?:mode|the\s+pc|the\s+computer)?'
                  r'|(?:pc|computer|laptop)\s+sleep'
                  r'|hibernate|suspend'
                  r'|(?:^|\s)sleep(?:\s+mode)?$)', t):
        return {"action":"sleep"}

    # SHUTDOWN
    if _re.search(r'(?:shutdown|shut\s+down|power\s+off|turn\s+off)'
                  r'(?:\s+(?:the\s+)?(?:pc|computer|laptop|system|windows?))?', t):
        return {"action":"shutdown"}

    # RESTART
    if _re.search(r'(?:restart|reboot)(?:\s+(?:the\s+)?(?:pc|computer|laptop|system))?', t):
        return {"action":"restart"}

    # LOCK SCREEN
    if _re.search(r'(?:lock|lock\s+(?:the\s+)?(?:screen|pc|computer|windows?))', t):
        return {"action":"lock_screen"}

    # ── TYPING ────────────────────────────────────────────────────────────────
    # char-limited typing
    m = _re.search(r'(?:write|type)\s+(\d+)\s*(?:characters?|chars?)\s+(.*)', t)
    if m: return {"action":"type_text","text":m.group(2).strip(),"char_limit":int(m.group(1)),"press_enter":False}
    # delete chars
    m = _re.search(r'delete\s+(\d+)\s*(?:characters?|chars?|letters?)', t)
    if m: return {"action":"delete_text","chars":int(m.group(1))}
    if _re.search(r'^(?:new\s+line|enter|hit\s+enter|press\s+enter)$', t): return {"action":"new_line"}

    # ── EDIT SELECTED TEXT (AI rewrite with character/word limits) ─────────────
    # "make this in 300 characters" / "make this 300 characters"
    # "make it 300 characters" / "make the sentence 300 characters"
    # "write this in 300 characters" / "make this word in 300 characters"
    m = _re.search(r'(?:make|write|rewrite|change|convert|edit)\s+(?:this|it|the\s+\w+|that)\s+(?:in(?:to)?\s+)?(\d+)\s*(?:characters?|chars?|words?|letters?)', t)
    if m:
        count = int(m.group(1))
        unit = "characters" if any(u in t for u in ("char", "character", "letter")) else "words"
        return {"action":"edit_selected_ai","instruction":f"Rewrite the text to be exactly {count} {unit} long. Keep the same meaning but adjust the length to {count} {unit}."}
    # "make this in 300 characters" (alternate word order)
    m = _re.search(r'(?:make|write|rewrite|change)\s+(?:this|it|the\s+\w+)\s+(?:in(?:to)?\s+)?(\d+)\s*(?:characters?|chars?|words?)', t)
    if m:
        count = int(m.group(1))
        unit = "characters" if any(u in t for u in ("char", "character")) else "words"
        return {"action":"edit_selected_ai","instruction":f"Rewrite the text to be exactly {count} {unit} long. Keep the same meaning but adjust the length to {count} {unit}."}
    # "expand this to 500 characters" / "shorten this to 100 words"
    m = _re.search(r'(?:expand|shorten|resize|adjust|trim|extend|reduce)\s+(?:this|it|the\s+\w+)?\s*(?:to\s+)?(\d+)\s*(?:characters?|chars?|words?|letters?)', t)
    if m:
        count = int(m.group(1))
        unit = "characters" if any(u in t for u in ("char", "character", "letter")) else "words"
        return {"action":"edit_selected_ai","instruction":f"Rewrite the text to be exactly {count} {unit} long. Keep the same meaning."}
    # "make it longer" / "make it more detailed" / "make it concise"
    m = _re.search(r'(?:make|rewrite)\s+(?:this|it)\s+(longer|more\s+detailed|concise|brief|elaborate)', t)
    if m:
        style = m.group(1).strip()
        return {"action":"edit_selected_ai","instruction":f"Rewrite the text to be {style}. Keep the same meaning."}

    # ── CLIPBOARD AI ──────────────────────────────────────────────────────────
    if _re.search(r'summarize\s+clipboard', t):
        return {"action":"clipboard_ai","instruction":"summarize in 3 bullet points"}
    if _re.search(r'fix\s+(?:grammar|spelling|typos?)', t):
        return {"action":"clipboard_ai","instruction":"fix grammar and spelling"}
    m = _re.search(r'translate\s+(?:clipboard\s+)?(?:to|into)\s+(.+)', t)
    if m: return {"action":"clipboard_ai","instruction":f"translate to {m.group(1).strip()}"}
    if _re.search(r'rewrite\s+(?:clipboard|this)', t):
        return {"action":"clipboard_ai","instruction":"rewrite more professionally"}
    if _re.search(r'make\s+(?:it|this|clipboard)\s+(?:formal|professional)', t):
        return {"action":"clipboard_ai","instruction":"make more professional and formal"}
    if _re.search(r'make\s+(?:it|this)\s+shorter', t):
        return {"action":"clipboard_ai","instruction":"make shorter, keep key points"}

    # ── FILE & FOLDER OPERATIONS ───────────────────────────────────────────────
    # Create folder — handles ALL naming variants:
    # "make folder Projects"
    # "make a folder name as Projects"
    # "make a folder name is Projects"
    # "make a folder named Projects"
    # "make a folder called Projects"
    # "create folder on desktop name tarun"
    m = _re.search(
        r'(?:make|create|new|add)\s+(?:a\s+)?(?:new\s+)?folder\s+'
        r'(?:(?:with\s+)?name\s+(?:as\s+|is\s+|=\s+)?|named?\s+(?:as\s+|is\s+)?|called?\s+(?:as\s+|is\s+)?)?'
        r'(.+?)\s*(?:on\s+(?:the\s+)?desktop)?$', t)
    if m:
        folder_name = m.group(1).strip()
        # Clean up filler from name: "name as Tarun on vs" → "Tarun on vs" is ambiguous
        # but we keep it verbatim as the user said it
        folder_name = _re.sub(r'^(?:as|is|=|the)\s+', '', folder_name).strip()
        return {"action":"agent_task","platform":"files","task":"create_folder","name":folder_name}
    # Alternate: "make a folder on desktop called X"
    m = _re.search(
        r'(?:make|create)\s+(?:a\s+)?folder\s+'
        r'(?:on\s+(?:the\s+)?desktop\s+)?'
        r'(?:(?:with\s+)?name\s+(?:as\s+|is\s+)?|named?\s+(?:as\s+|is\s+)?|called?\s+(?:as\s+|is\s+)?)?(.+)', t)
    if m:
        folder_name = _re.sub(r'^(?:as|is|=|the)\s+', '', m.group(1).strip()).strip()
        return {"action":"agent_task","platform":"files","task":"create_folder","name":folder_name}
    # Create file
    m = _re.search(r'(?:create|make|new)\s+(?:a\s+)?(?:new\s+)?(?:text\s+)?file\s+(?:called\s+|named\s+)?(.+)', t)
    if m: return {"action":"agent_task","platform":"files","task":"create_file","name":m.group(1).strip()}
    # Delete file
    m = _re.search(r'delete\s+(?:the\s+)?file\s+(.+)', t)
    if m: return {"action":"agent_task","platform":"files","task":"delete_file","name":m.group(1).strip()}
    # Delete folder
    m = _re.search(r'delete\s+(?:the\s+)?folder\s+(.+)', t)
    if m: return {"action":"agent_task","platform":"files","task":"delete_folder","name":m.group(1).strip()}
    # Open specific folder
    m = _re.search(r'open\s+(?:the\s+)?(?:downloads?|desktop|documents?|pictures?|music|videos?|photos?)\s+folder', t)
    if m:
        folder = _re.search(r'(downloads?|desktop|documents?|pictures?|music|videos?|photos?)', t).group(1).rstrip('s').lower()
        folder = "downloads" if folder=="download" else "pictures" if folder in ("picture","photo","photos") else folder
        return {"action":"agent_task","platform":"files","task":"open_folder","path":folder}
    # Open named folder
    m = _re.search(r'open\s+(?:the\s+)?folder\s+(?:called\s+|named\s+)?(.+)', t)
    if m: return {"action":"agent_task","platform":"files","task":"open_folder","path":m.group(1).strip()}
    # Open file
    m = _re.search(r'open\s+(?:the\s+)?file\s+(.+)', t)
    if m: return {"action":"agent_task","platform":"files","task":"open_file","path":m.group(1).strip()}
    # List folder
    if _re.search(r'(?:list|show|what\s+is\s+in)\s+(?:the\s+)?(?:desktop|downloads?|documents?)\s*(?:folder)?', t):
        folder = "downloads" if "download" in t else "documents" if "document" in t else "desktop"
        return {"action":"agent_task","platform":"files","task":"list_folder","path":folder}

    # ── YOUTUBE ───────────────────────────────────────────────────────────────
    m = _re.search(r'(?:open\s+)?youtube\s+(?:and\s+)?(?:search|find|look\s*up)\s+(.+)', t)
    if m: return {"action":"agent_task","platform":"youtube","task":"search","query":m.group(1).strip()}
    m = _re.search(r'(?:play|watch)\s+(.+?)\s+(?:on\s+)?(?:youtube|yt)', t)
    if m: return {"action":"agent_task","platform":"youtube","task":"play","query":m.group(1).strip()}
    if _re.search(r'^(?:open\s+)?youtube$', t):
        return {"action":"agent_task","platform":"youtube","task":"open","query":""}
    if _re.search(r'youtube\s+scroll\s*(down|up)?', t):
        return {"action":"agent_task","platform":"youtube","task":"scroll","query":"down" if "down" in t else "up"}
    m = _re.search(r'^youtube\s+(.+)', t)
    if m: return {"action":"agent_task","platform":"youtube","task":"search","query":m.group(1).strip()}

    # ── WHATSAPP ──────────────────────────────────────────────────────────────
    m = _re.search(r'(?:open\s+)?whatsapp\s+(?:and\s+)?(?:message|msg|send|text)\s+(\S+)\s+(.*)', t)
    if m: return {"action":"agent_task","platform":"whatsapp","task":"message","contact":m.group(1).strip(),"message":m.group(2).strip(),"send":True}
    if _re.search(r'^(?:open\s+)?whatsapp$', t):
        return {"action":"agent_task","platform":"whatsapp","task":"open","contact":"","message":""}

    # ── TELEGRAM ──────────────────────────────────────────────────────────────
    m = _re.search(r'(?:open\s+)?telegram\s+(?:message|msg|send|text)\s+(\S+)\s+(.*)', t)
    if m: return {"action":"agent_task","platform":"telegram","task":"message","contact":m.group(1).strip(),"message":m.group(2).strip(),"send":True}
    if _re.search(r'^(?:open\s+)?telegram$', t):
        return {"action":"agent_task","platform":"telegram","task":"open","contact":"","message":""}

    # ── INSTAGRAM ─────────────────────────────────────────────────────────────
    m = _re.search(r'(?:open\s+)?instagram\s+(?:search|find)\s+(.*)', t)
    if m: return {"action":"agent_task","platform":"instagram","task":"search","query":m.group(1).strip()}
    m = _re.search(r'instagram\s+(?:dm|message)\s+(\S+)\s+(.*)', t)
    if m: return {"action":"agent_task","platform":"instagram","task":"dm","dm_user":m.group(1).strip(),"dm_msg":m.group(2).strip()}
    if _re.search(r'instagram\s+scroll', t):
        return {"action":"agent_task","platform":"instagram","task":"scroll","query":"down" if "down" in t else "up"}
    if _re.search(r'^(?:open\s+)?instagram$', t):
        return {"action":"agent_task","platform":"instagram","task":"open"}

    # ── TWITTER / X ───────────────────────────────────────────────────────────
    m = _re.search(r'^tweet\s+(.*)', t)
    if m: return {"action":"agent_task","platform":"twitter","task":"tweet","tweet":m.group(1).strip()}
    m = _re.search(r'(?:open\s+)?(?:twitter|x)\s+search\s+(.*)', t)
    if m: return {"action":"agent_task","platform":"twitter","task":"search","query":m.group(1).strip()}
    if _re.search(r'twitter\s+scroll', t):
        return {"action":"agent_task","platform":"twitter","task":"scroll","query":"down" if "down" in t else "up"}
    if _re.search(r'^(?:open\s+)?(?:twitter|x)$', t):
        return {"action":"agent_task","platform":"twitter","task":"open"}


    # ── SPOTIFY ────────────────────────────────────────────────────────────────────────────
    # 'play song X' / 'play the song X' / 'play X song'
    m = _re.search(r'play\s+(?:the\s+)?song\s+(.+)', t)
    if m: return {'action':'agent_task','platform':'spotify','task':'play','query':m.group(1).strip()}
    m = _re.search(r'play\s+(.+?)\s+(?:song|music|track|album)(?:\s|$)', t)
    if m: return {'action':'agent_task','platform':'spotify','task':'play','query':m.group(1).strip()}
    # 'play X on spotify'
    m = _re.search(r'(?:play|search)\s+(.+?)\s+(?:on\s+)?spotify', t)
    if m:
        return {'action':'agent_task','platform':'spotify','task':'play' if t.startswith('play') else 'search','query':m.group(1).strip()}
    m = _re.search(r'spotify\s+(?:play|search)?\s*(.*)', t)
    if m and m.group(1).strip():
        return {'action':'agent_task','platform':'spotify','task':'play','query':m.group(1).strip()}
    if _re.search(r'^(?:open\s+)?spotify$', t):
        return {'action':'agent_task','platform':'spotify','task':'open','query':''}
    # Generic 'play X' (no youtube) -> Spotify
    m = _re.search(r'^play\s+(.+)$', t)
    if m:
        q = m.group(1).strip()
        if 'youtube' not in q and 'yt' not in q:
            return {'action':'agent_task','platform':'spotify','task':'play','query':q}

    # ── FACEBOOK ──────────────────────────────────────────────────────────────
    m = _re.search(r'(?:open\s+)?facebook\s+search\s+(.*)', t)
    if m: return {"action":"agent_task","platform":"facebook","task":"search","query":m.group(1).strip()}
    if _re.search(r'^(?:open\s+)?facebook$', t):
        return {"action":"agent_task","platform":"facebook","task":"open"}

    # ── LINKEDIN ──────────────────────────────────────────────────────────────
    m = _re.search(r'(?:open\s+)?linkedin\s+(?:search\s+)?(?:jobs?\s+)?(.+)', t)
    if m:
        q = m.group(1).strip()
        stype = "jobs" if "job" in t else "all"
        return {"action":"agent_task","platform":"linkedin","task":"search","query":q,"search_type":stype}
    if _re.search(r'^(?:open\s+)?linkedin$', t):
        return {"action":"agent_task","platform":"linkedin","task":"open"}

    # ── REDDIT ────────────────────────────────────────────────────────────────
    m = _re.search(r'r/(\S+)', t)
    if m: return {"action":"agent_task","platform":"reddit","task":"open","subreddit":m.group(1).strip()}
    m = _re.search(r'(?:open\s+)?reddit\s+search\s+(.*)', t)
    if m: return {"action":"agent_task","platform":"reddit","task":"search","query":m.group(1).strip()}
    m = _re.search(r'(?:open\s+)?reddit\s+(\w+)', t)
    if m: return {"action":"agent_task","platform":"reddit","task":"open","subreddit":m.group(1).strip()}
    if _re.search(r'^(?:open\s+)?reddit$', t):
        return {"action":"agent_task","platform":"reddit","task":"open","subreddit":""}

    # ── CHROME / BROWSER ──────────────────────────────────────────────────────
    # Search in browser
    m = _re.search(r'(?:open\s+)?(?:chrome|browser|brave|edge)\s+(?:and\s+)?search\s+(.*)', t)
    if m: return {"action":"agent_task","platform":"chrome","task":"search","query":m.group(1).strip()}
    # Go to URL
    m = _re.search(r'(?:open\s+)?(?:chrome|browser|brave|edge)\s+(?:and\s+)?(?:go\s+to|open|navigate\s+to)\s+(https?://\S+|www\.\S+|\S+\.\w{2,})', t)
    if m:
        url = m.group(1).strip()
        if not url.startswith("http"): url = "https://"+url
        return {"action":"agent_task","platform":"chrome","task":"open","url":url}
    # Go to URL fallback: URL directly mentioned with chrome
    m = _re.search(r'(?:chrome|browser|brave|edge)\s+(https?://\S+|www\.\S+)', t)
    if m:
        url = m.group(1).strip()
        if not url.startswith("http"): url = "https://"+url
        return {"action":"agent_task","platform":"chrome","task":"open","url":url}
    # Look up / find in browser  
    m = _re.search(r'(?:open\s+)?(?:chrome|browser|brave|edge)\s+(?:and\s+)?(?:look\s+up|find|search\s+for)\s+(.*)', t)
    if m: return {"action":"agent_task","platform":"chrome","task":"search","query":m.group(1).strip()}
    if _re.search(r'chrome\s+scroll\s*(down|up)?', t):
        return {"action":"agent_task","platform":"chrome","task":"scroll","scroll":"down" if "down" in t else "up"}
    if _re.search(r'(?:chrome|browser)\s+back', t):
        return {"action":"agent_task","platform":"chrome","task":"back"}
    if _re.search(r'(?:chrome|browser)\s+(?:new\s+tab|open\s+tab)', t):
        return {"action":"agent_task","platform":"chrome","task":"new_tab"}
    if _re.search(r'(?:chrome|browser|page)\s+refresh|refresh\s+(?:the\s+)?(?:page|browser|tab)', t):
        return {"action":"agent_task","platform":"chrome","task":"refresh"}
    if _re.search(r'^(?:open\s+)?brave(?:\s+browser)?$', t):
        return {"action":"open_app","app":"brave"}
    if _re.search(r'^(?:open\s+)?(?:microsoft\s+)?edge$', t):
        return {"action":"open_app","app":"edge"}
    if _re.search(r'^close\s+(?:browser|chrome|brave|edge)$', t):
        return {"action":"close_browser"}

    # ── GMAIL ─────────────────────────────────────────────────────────────────
    m = _re.search(r'(?:open\s+)?gmail\s+(?:and\s+)?(?:write|compose|draft|send)\s+(?:a\s+)?(?:mail|email|message)?\s*(?:for|about|to)?\s*(.*)', t)
    if m:
        body = m.group(1).strip()
        return {"action":"agent_task","platform":"gmail","to":"","subject":body[:50] if body else "","body":f"write {body}" if body else "","send":False}

    # ── OPEN APP (generic — must be last app-related check) ───────────────────
    # Explicit app name aliases before generic match
    APP_ALIASES = {
        "vs code": "vscode", "vs": "vscode", "visual studio code": "vscode",
        "visual studio": "vscode", "vscode": "vscode",
        "brave": "brave", "brave browser": "brave",
        "edge": "edge", "microsoft edge": "edge",
        "notepad": "notepad", "note pad": "notepad",
        "file manager": "explorer", "files": "explorer",
        "task manager": "taskmgr", "task mgr": "taskmgr",
        "command prompt": "cmd", "command line": "cmd",
        "windows terminal": "wt", "terminal": "wt",
        "control panel": "control",
        "calculator": "calc", "calc": "calc",
        "paint": "mspaint",
    }
    m = _re.search(r'^open\s+(.+)', t)
    if m:
        app = m.group(1).strip()
        # Check alias map first
        app_lower = app.lower()
        if app_lower in APP_ALIASES:
            return {"action":"open_app","app":APP_ALIASES[app_lower]}
        # Not a URL → open app
        if not any(app.startswith(x) for x in ["http","www"]):
            return {"action":"open_app","app":app}

    # ── CLOSE APP ─────────────────────────────────────────────────────────────
    m = _re.search(r'^close\s+(.+)', t)
    if m:
        app = m.group(1).strip()
        if app not in ("window","tab","browser","chrome","brave","edge"):
            return {"action":"close_app","app":app}

    # ── "SEARCH X" → smart routing ───────────────────────────────────────────
    # "search Karan Aujla" / "search for Karan" → YouTube (person/artist)
    # "search Python tutorial" → Chrome Google search
    m = _re.search(r'^search\s+(?:for\s+)?(.+)$', t)
    if m:
        q = m.group(1).strip()
        # If it sounds like a person/artist/song → YouTube
        # Otherwise → Chrome Google search
        YOUTUBE_HINTS = ['song','music','video','singer','rapper','artist','band',
                         'punjabi','hindi','bollywood','movie','film','trailer','album']
        if any(h in q.lower() for h in YOUTUBE_HINTS):
            return {"action":"agent_task","platform":"youtube","task":"search","query":q}
        # Default: Chrome Google search (browser shows results visually)
        return {"action":"agent_task","platform":"chrome","task":"search","query":q}

    # ── WEB SEARCH (knowledge questions → typed answer) ───────────────────────
    for pattern in [
        r'who\s+is\s+', r'who\s+are\s+',
        r'what\s+is\s+', r'what\s+are\s+', r'what\s+was\s+',
        r'price\s+of\s+', r'cost\s+of\s+',
        r'how\s+(?:much|many|does|do|is|are|to)\s+',
        r'tell\s+me\s+about\s+',
        r'find\s+(?:me\s+)?',
        r'when\s+(?:is|was|did|does)\s+',
        r'where\s+(?:is|are|can|do)\s+',
        r'why\s+(?:is|are|does|do)\s+',
        r'define\s+', r'explain\s+', r'meaning\s+of\s+',
        r'what\s+happened\s+',
    ]:
        if _re.search(pattern, t):
            # If it ends with nothing (incomplete speech) → skip
            tail = _re.sub(pattern, '', t).strip()
            if len(tail) < 2:
                speak("Could you complete that question?")
                return {"action":"chat","message":"Incomplete question — please try again"}
            return {"action":"web_search","query":text}

    # Ends with ? → web search
    if text.strip().endswith("?"):
        tail = _re.sub(r'[?\s]+$', '', text).strip()
        if len(tail) < 3:
            speak("What would you like to know?")
            return {"action":"chat","message":"Incomplete question"}
        return {"action":"web_search","query":text}

    return None  # Nothing matched → falls through to AI

def run_command(text: str) -> str:
    """
    Main command runner.
    Priority order:
    1. Custom user-defined commands (instant, no AI)
    2. Smart Skip: very short dictation typed directly (no Groq, ~0ms)
    3. Local fast-path (regex patterns, no Groq)
    4. Groq AI parse with conversation context
    5. Verbatim fallback
    """
    text = text.strip()
    if not text:
        return ""

    with _exec_lock:

        # 1. Custom commands — user-defined shortcuts
        t_lower = text.lower().strip()
        for trigger, response in CUSTOM_COMMANDS.items():
            if t_lower == trigger.lower().strip():
                print(f"[CUSTOM CMD] '{trigger}' → '{response}'")
                add_to_history("user", text)
                result = run_command(response)  # run the mapped command
                add_to_history("assistant", result)
                _log("custom_cmd", text, result)
                return result

        # 2. Conversation commands — clear memory, etc.
        if t_lower in ("clear history", "clear memory", "forget everything", "reset context"):
            clear_history()
            speak("Memory cleared.")
            return "Conversation history cleared."

        if t_lower in ("show history", "what did i say"):
            if not CONV_HISTORY:
                return "No conversation history."
            summary = " | ".join([f"{m['role']}: {m['content'][:40]}" for m in CONV_HISTORY[-6:]])
            do_type(summary)
            return f"History: {len(CONV_HISTORY)} messages"

        # 3. Smart Skip — short, pure dictation, no command triggers
        if not is_command(text) or Recorder.is_smart_skip(text):
            do_type(text, False)
            add_to_history("user", text)
            _log("dictation", text, f"Typed: {text[:40]}")
            return f"✎ {text}"

        # 4. Local fast-path (no AI needed)
        local_obj = local_parse(text)
        if local_obj is not None:
            try:
                result = execute(local_obj)
                add_to_history("user", text)
                add_to_history("assistant", result)
                _log(local_obj.get("action","command"), text, result)
                return result
            except Exception as e:
                print(f"[ERROR] Local parse failed: {e}")

        # 5. Groq AI parse (with rolling conversation context)
        try:
            obj = ai_parse(text)
            if obj.get("action") == "type_text" and not obj.get("char_limit"):
                obj["text"] = text
            result = execute(obj)
            add_to_history("user", text)
            add_to_history("assistant", result)
            _log(obj.get("action","command"), text, result)
            return result
        except Exception as e:
            print(f"[ERROR] AI parse failed: {e}")
            do_type(text, False)
            _log("fallback", text, str(e))
            return f"✎ {text}"


# ═════════════════════════════════════════════════════════════════════════════
#  HTTP SERVER  (serves frontend + real-time API)
# ═════════════════════════════════════════════════════════════════════════════

class JarvisHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args): pass  # suppress all access logs

    def handle_one_request(self):
        """Override to silently swallow Windows socket abort errors (WinError 10053/10054)."""
        try:
            super().handle_one_request()
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass  # client disconnected — not an error
        except Exception as e:
            if hasattr(e, 'winerror') and e.winerror in (10053, 10054):
                pass  # Windows socket forcibly closed — ignore
            else:
                pass  # swallow all to keep server alive

    def handle(self):
        """Override to catch socket errors at the connection level."""
        try:
            super().handle()
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass
        except OSError as e:
            if hasattr(e, 'winerror') and e.winerror in (10053, 10054, 10061):
                pass
        except Exception:
            pass

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Connection', 'close')  # tell browser not to reuse socket

    def do_OPTIONS(self):
        try:
            self.send_response(200); self._cors(); self.end_headers()
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass

    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            path   = parsed.path
            params = parse_qs(parsed.query)

            if path in ('/', '/index.html'):
                self._serve_frontend()

            elif path == '/api/status':
                self._json({
                    "ok":True,"version":"3.0","os":OS,
                    "groq":HAS_GROQ,"nvidia":HAS_OPENAI,"tts":HAS_TTS,"sr":HAS_SR,
                    "selenium":HAS_SELENIUM,
                    "model":"nvidia/nemotron-3-nano-30b-a3b" if nvidia_client else "llama-3.3-70b-versatile",
                    "nvidia":HAS_OPENAI and nvidia_client is not None,
                    "uptime":(datetime.now()-datetime.fromisoformat(STATS["session_start"])).seconds,
                    "system":get_system_info(),
                    "timestamp":datetime.now().isoformat(),
                })

            elif path == '/api/stats':
                self._json(STATS)

            elif path == '/api/activity':
                self._json({"activity":ACTIVITY_LOG[:20]})

            elif path == '/api/search':
                q = params.get('q',[''])[0].strip()
                if not q:
                    self._json({"ok":False,"answer":"No query"}); return
                answer = web_search_text(q)
                if not answer or len(answer) < 8:
                    if nvidia_client:
                        try:
                            prompt = f"{JARVIS_PERSONA}\n\nAnswer this in 1-3 sentences: {q}"
                            ans_nv = _nvidia_stream_parse(prompt)
                            if ans_nv: answer = ans_nv
                        except Exception: pass
                    if (not answer or len(answer) < 8) and groq_client:
                        try:
                            r3 = groq_client.chat.completions.create(
                                model="llama-3.3-70b-versatile",
                                messages=[{"role":"system","content":JARVIS_PERSONA},
                                          {"role":"user","content":q}],
                                max_tokens=200, temperature=0.2)
                            answer = r3.choices[0].message.content.strip()
                        except Exception: pass
                _log("web_search", q, answer)
                self._json({"ok":True,"query":q,"answer":answer})

            elif path == '/api/news':
                topic = params.get('topic',['general'])[0]
                count = int(params.get('count',['5'])[0])
                self._json({"ok":True,"topic":topic,"items":fetch_news(topic,count)})

            elif path == '/api/sysinfo':
                self._json({"ok":True,"data":get_system_info()})

            elif path == '/api/reminders':
                rem = [{"fire_time":r[0].isoformat(),"message":r[1]} for r in CTX["reminders"]]
                self._json({"ok":True,"reminders":rem})

            elif path == '/api/microphones':
                mics = list_microphones()
                self._json({"ok":True,"microphones":mics,
                            "current":get_pref("mic_device_index",None)})

            elif path == '/api/prefs':
                self._json({"ok":True,"prefs":PREFS})

            elif path == '/api/custom_commands':
                self._json({"ok":True,"commands":CUSTOM_COMMANDS})

            elif path == '/api/history':
                self._json({"ok":True,"history":CONV_HISTORY[-20:]})

            else:
                self._send_404()

        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass  # client closed connection mid-response — normal on Windows
        except OSError as e:
            if hasattr(e, 'winerror') and e.winerror in (10053, 10054):
                pass
        except Exception as e:
            print(f"[HTTP GET ERROR] {e}")

    def do_POST(self):
        try:
            path   = urlparse(self.path).path
            length = int(self.headers.get('Content-Length', 0))
            body   = self.rfile.read(length)
            data   = json.loads(body) if body else {}

            if path == '/api/command':
                cmd = data.get('command', '').strip()
                if cmd:
                    threading.Thread(target=run_command, args=(cmd,), daemon=True).start()
                    self._json({"ok": True, "message": f"Executing: {cmd}"})
                else:
                    self._json({"ok": False, "message": "Empty command"})

            elif path == '/api/prefs':
                # Save one preference: {"key": "...", "value": ...}
                key   = data.get('key', '')
                value = data.get('value')
                if key:
                    set_pref(key, value)
                    # Apply runtime changes immediately
                    global WAKE_WORD, WAKE_WORD_ENABLED, SMART_SKIP_ENABLED, STREAM_TTS, CUSTOM_AI_PROMPT
                    if key == "wake_word":         WAKE_WORD = value
                    if key == "wake_word_enabled": WAKE_WORD_ENABLED = bool(value)
                    if key == "smart_skip":        SMART_SKIP_ENABLED = bool(value)
                    if key == "stream_tts":        STREAM_TTS = bool(value)
                    if key == "custom_ai_prompt":  CUSTOM_AI_PROMPT = str(value)
                    self._json({"ok": True, "key": key, "value": value})
                else:
                    self._json({"ok": False, "message": "No key provided"})

            elif path == '/api/custom_commands':
                # Add: {"trigger": "good morning", "response": "open gmail"}
                # Del: {"delete": "good morning"}
                if "delete" in data:
                    CUSTOM_COMMANDS.pop(data["delete"], None)
                elif "trigger" in data and "response" in data:
                    CUSTOM_COMMANDS[data["trigger"].lower().strip()] = data["response"]
                _save_custom_commands(CUSTOM_COMMANDS)
                self._json({"ok": True, "commands": CUSTOM_COMMANDS})

            elif path == '/api/clear_history':
                clear_history()
                self._json({"ok": True, "message": "History cleared"})

            else:
                self._send_404()

        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass
        except OSError as e:
            if hasattr(e, 'winerror') and e.winerror in (10053, 10054):
                pass
        except Exception as e:
            try:
                self._json({"ok":False,"message":str(e)}, 500)
            except Exception:
                pass

    def _serve_frontend(self):
        fe_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), FRONTEND_FILE)
        try:
            if os.path.exists(fe_path):
                with open(fe_path, 'rb') as f:
                    content = f.read()
            else:
                content = (
                    b"<html><body style='background:#03080f;color:#00c8ff;"
                    b"font-family:monospace;padding:40px'>"
                    b"<h2>JARVIS Backend Running</h2>"
                    b"<p>Put <strong>jarvis_frontend.html</strong> in the same folder.</p>"
                    b"<p>Endpoints: /api/status &nbsp; /api/stats &nbsp; /api/activity"
                    b" &nbsp; /api/search?q=... &nbsp; /api/news?topic=ai"
                    b" &nbsp; /api/sysinfo</p>"
                    b"</body></html>"
                )
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(content)))
            self._cors()
            self.end_headers()
            self.wfile.write(content)
            self.wfile.flush()
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass

    def _json(self, data, code=200):
        try:
            body = json.dumps(data, ensure_ascii=False).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self._cors()
            self.end_headers()
            self.wfile.write(body)
            self.wfile.flush()
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass  # client closed — not an error
        except OSError as e:
            if hasattr(e, 'winerror') and e.winerror in (10053, 10054):
                pass  # WinError 10053 / 10054 — socket aborted by Windows
            # else silently ignore

    def _send_404(self):
        try:
            self.send_response(404)
            self._cors()
            self.end_headers()
        except Exception:
            pass


class _SilentHTTPServer(HTTPServer):
    """HTTPServer subclass that silently swallows Windows socket errors."""

    def handle_error(self, request, client_address):
        """Override to suppress WinError 10053/10054 from filling the console."""
        import sys
        exc_type, exc_val, _ = sys.exc_info()
        if exc_type in (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            return  # normal Windows client disconnect — do nothing
        if isinstance(exc_val, OSError) and hasattr(exc_val, 'winerror'):
            if exc_val.winerror in (10053, 10054, 10061):
                return  # WinError: connection aborted / reset — do nothing
        # For anything else, log it (but don't crash)
        print(f"[HTTP ERROR] {exc_type.__name__}: {exc_val}")


def start_dashboard_server():
    try:
        server = _SilentHTTPServer(('localhost', DASHBOARD_PORT), JarvisHandler)
        print(f"  🌐 Dashboard: http://localhost:{DASHBOARD_PORT}")
        threading.Thread(target=server.serve_forever, daemon=True).start()
        def _open():
            time.sleep(1.5)
            webbrowser.open(f'http://localhost:{DASHBOARD_PORT}')
        threading.Thread(target=_open, daemon=True).start()
    except OSError as e:
        print(f"  [WARN] Port {DASHBOARD_PORT} busy: {e}")


# ═════════════════════════════════════════════════════════════════════════════
#  SPEECH RECOGNITION
# ═════════════════════════════════════════════════════════════════════════════

class Recorder:
    """
    Enhanced recorder with:
    - Audio device selection (mic_device_index)
    - Smart Skip — very short recordings typed verbatim without Groq
    - Wake word detection ("hey jarvis") always-listening mode
    - Real-time audio level callback
    """

    def __init__(self):
        if HAS_SR:
            self.rec = sr.Recognizer()
            self.rec.energy_threshold        = get_pref("energy_threshold", 200)
            self.rec.dynamic_energy_threshold = True
            self.rec.pause_threshold         = 0.6
            self.rec.non_speaking_duration   = 0.3
        self._wake_thread   = None
        self._wake_stop     = threading.Event()
        self._wake_active   = False

    # ── Core recording ─────────────────────────────────────────────────────────
    def record_until_stop(self, stop_event: threading.Event,
                          on_audio_level=None) -> str:
        if not HAS_SR:
            return ""
        frames = []; sample_rate = 16000; chunk = 1024
        device_index = get_pref("mic_device_index", None)
        try:
            import pyaudio
            pa = pyaudio.PyAudio()
            stream_kwargs = dict(
                format=pyaudio.paInt16, channels=1,
                rate=sample_rate, input=True, frames_per_buffer=chunk
            )
            if device_index is not None:
                stream_kwargs["input_device_index"] = device_index
            stream = pa.open(**stream_kwargs)
            while not stop_event.is_set():
                data = stream.read(chunk, exception_on_overflow=False)
                frames.append(data)
                if on_audio_level:
                    samples = struct.unpack(f"{chunk}h", data)
                    on_audio_level(max(abs(s) for s in samples) / 32768.0)
            stream.stop_stream(); stream.close(); pa.terminate()

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmp = f.name
            wf = wave.open(tmp, "wb")
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sample_rate)
            wf.writeframes(b"".join(frames)); wf.close()

            with sr.AudioFile(tmp) as src_:
                audio = self.rec.record(src_)
            os.unlink(tmp)
            lang = get_pref("speech_lang", "en-IN")
            return self.rec.recognize_google(audio, language=lang).strip()

        except ImportError:
            return self._fallback_record()
        except sr.UnknownValueError:
            return ""
        except Exception as e:
            return f"[error: {e}]"

    def _fallback_record(self) -> str:
        """Fallback when pyaudio not available."""
        try:
            mic = sr.Microphone()
            with mic as s:
                self.rec.adjust_for_ambient_noise(s, duration=0.3)
                audio = self.rec.listen(s, timeout=15, phrase_time_limit=60)
            lang = get_pref("speech_lang", "en-IN")
            return self.rec.recognize_google(audio, language=lang).strip()
        except Exception as e:
            return f"[error: {e}]"

    # ── Smart Skip ─────────────────────────────────────────────────────────────
    @staticmethod
    def is_smart_skip(text: str) -> bool:
        """
        Smart Skip: if text is very short / clearly dictation, bypass Groq.
        Saves ~500ms latency for simple dictation.
        """
        if not SMART_SKIP_ENABLED:
            return False
        t = text.strip().lower()
        # Skip if clearly a command keyword
        if any(t.startswith(kw) for kw in [
            "open ", "play ", "search ", "click", "type ", "write ",
            "scroll", "volume", "mute", "screenshot", "youtube", "whatsapp",
            "telegram", "instagram", "spotify", "tweet", "remind", "weather",
            "calculate", "who is", "what is", "how ", "news", "chrome",
        ]):
            return False
        # Skip (just type it) if very short dictation with no command keywords
        word_count = len(t.split())
        return word_count <= 3 and not any(c in t for c in ["?","open","play","search"])

    # ── Wake word (always-listening) ───────────────────────────────────────────
    def start_wake_word(self, on_triggered_callback):
        """Start always-listening wake word thread."""
        if not WAKE_WORD_ENABLED or not HAS_SR:
            return
        if self._wake_active:
            return
        self._wake_active = True
        self._wake_stop.clear()
        self._wake_thread = threading.Thread(
            target=self._wake_loop,
            args=(on_triggered_callback,),
            daemon=True
        )
        self._wake_thread.start()
        print(f"[WAKE WORD] Listening for: '{WAKE_WORD}'")

    def stop_wake_word(self):
        """Stop the wake word listener."""
        self._wake_active = False
        self._wake_stop.set()

    def _wake_loop(self, callback):
        """Background thread: listen for wake word continuously."""
        try:
            device_index = get_pref("mic_device_index", None)
            mic_kwargs = {}
            if device_index is not None:
                mic_kwargs["device_index"] = device_index
            mic = sr.Microphone(**mic_kwargs)
            while self._wake_active and not self._wake_stop.is_set():
                try:
                    with mic as s:
                        self.rec.adjust_for_ambient_noise(s, duration=0.1)
                        audio = self.rec.listen(s, timeout=3, phrase_time_limit=4)
                    lang = get_pref("speech_lang", "en-IN")
                    text = self.rec.recognize_google(audio, language=lang).lower().strip()
                    if WAKE_WORD.lower() in text:
                        print(f"[WAKE WORD] Triggered: '{text}'")
                        # Remove wake word, keep the rest as command
                        command = text.replace(WAKE_WORD.lower(), "").strip()
                        callback(command or "")
                except (sr.WaitTimeoutError, sr.UnknownValueError):
                    pass
                except Exception:
                    time.sleep(0.5)
        except Exception as e:
            print(f"[WAKE WORD] Loop error: {e}")


class HotkeyController:
    def __init__(self, overlay):
        self.overlay=overlay; self.recorder=Recorder(); self.recording=False
        self.stop_evt=threading.Event(); self._last_press=0.0
        self._DEBOUNCE=0.08; self._processing=False

    def start(self):
        if not HAS_PYNPUT: print("[ERROR] pip install pynput"); return
        listener = pynput_kb.Listener(on_press=self._on_press, on_release=self._on_release)
        listener.daemon = True
        listener.start()
        # Start wake word listener if enabled
        if WAKE_WORD_ENABLED:
            self.recorder.start_wake_word(self._on_wake_word)

    def _on_press(self,key):
        if key!=HOLD_KEY: return
        now=time.time()
        if now-self._last_press<self._DEBOUNCE: return
        self._last_press=now
        if not self.recording and not self._processing:
            self.recording=True; self.stop_evt.clear()
            threading.Thread(target=self._record_thread,daemon=True).start()

    def _on_release(self,key):
        if key==HOLD_KEY and self.recording:
            self.recording=False; self.stop_evt.set()

    def _record_thread(self):
        self.overlay.root.after(0, self.overlay.show_recording)
        text = self.recorder.record_until_stop(
            self.stop_evt,
            on_audio_level=lambda lvl: self.overlay.set_audio_level(lvl))

        if not text or text.startswith("[error"):
            self.overlay.root.after(0, self.overlay.hide)
            return

        # Smart Skip check — show transcription instantly, skip Groq
        if not is_command(text) or Recorder.is_smart_skip(text):
            self.overlay.root.after(0, lambda: self.overlay.show_result(f"✎ {text[:55]}"))
            threading.Thread(target=lambda: run_command(text), daemon=True).start()
            return

        self.overlay.root.after(0, self.overlay.show_processing)

        def _process():
            if self._processing: return
            self._processing = True
            try:
                result = run_command(text)
            finally:
                self._processing = False
            self.overlay.root.after(0, lambda: self.overlay.show_result(result))

        threading.Thread(target=_process, daemon=True).start()

    def _on_wake_word(self, command: str):
        """Called when wake word is detected. Records a follow-up command if empty."""
        if self._processing or self.recording:
            return
        if command:
            # Wake word + command in same utterance: e.g. "hey jarvis open youtube"
            speak("Yes?", blocking=False)
            threading.Thread(target=lambda: run_command(command), daemon=True).start()
        else:
            # Just wake word — start recording next sentence
            speak("Listening.", blocking=False)
            self.recording = True
            self.stop_evt.clear()
            # Auto-stop after 6 seconds of silence
            def _auto_stop():
                time.sleep(6)
                if self.recording:
                    self.recording = False
                    self.stop_evt.set()
            threading.Thread(target=_auto_stop, daemon=True).start()
            threading.Thread(target=self._record_thread, daemon=True).start()


# ═════════════════════════════════════════════════════════════════════════════
#  WAVEFORM OVERLAY  (tkinter bottom-of-screen indicator)
# ═════════════════════════════════════════════════════════════════════════════

class WaveformOverlay:
    WIN_W = 520; WIN_H = 120; PAD_Y = 60

    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.0)
        self.root.configure(bg=BG)
        self._position(); self._build()
        self.audio_level  = 0.0
        self.wave_phase   = 0.0
        self.state        = 'hidden'
        self._fade_target = 0.0
        self._cur_alpha   = 0.0
        self._result_text = ""
        self.root.after(33, self._tick)

    def _position(self):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x  = (sw - self.WIN_W) // 2
        y  = sh - self.WIN_H - self.PAD_Y
        self.root.geometry(f"{self.WIN_W}x{self.WIN_H}+{x}+{y}")

    def _build(self):
        self.canvas = tk.Canvas(
            self.root, width=self.WIN_W, height=self.WIN_H,
            bg=BG, highlightthickness=0)
        self.canvas.pack()

    def show_recording(self):
        self.state = 'recording'
        self.root.deiconify()
        self._fade_target = 0.96

    def show_processing(self): self.state = 'processing'

    def show_result(self, text: str):
        self.state = 'done'
        self._result_text = text[:60]
        self.root.after(2200, self.hide)

    def hide(self):
        self._fade_target = 0.0
        self.state = 'hidden'
        self.root.after(350, self.root.withdraw)

    def set_audio_level(self, level: float):
        self.audio_level = min(1.0, level * 3.5)

    def _tick(self):
        try:
            diff            = self._fade_target - self._cur_alpha
            self._cur_alpha += diff * 0.18
            self._cur_alpha  = max(0.0, min(0.96, self._cur_alpha))
            self.root.attributes('-alpha', self._cur_alpha)
            self._draw()
            self.wave_phase += 0.10 if self.state == 'recording' else 0.04
        except Exception:
            pass
        self.root.after(33, self._tick)

    def _draw(self):
        c = self.canvas
        W, H = self.WIN_W, self.WIN_H
        c.delete('all')

        # Rounded pill background
        r = 24
        for coords in [
            (0,       0,       2*r,   2*r,   90,  90),
            (W-2*r,   0,       W,     2*r,   0,   90),
            (0,       H-2*r,   2*r,   H,     180, 90),
            (W-2*r,   H-2*r,   W,     H,     270, 90),
        ]:
            c.create_arc(*coords[:4], start=coords[4], extent=coords[5],
                         fill=BG, outline=BG)
        c.create_rectangle(r, 0, W-r, H, fill=BG, outline=BG)
        c.create_rectangle(0, r, W, H-r, fill=BG, outline=BG)

        # Border colour by state
        bc = {'recording': RED, 'processing': AMBER,
              'done': GREEN, 'hidden': BLUE}.get(self.state, BLUE)
        c.create_rectangle(2, 2, W-2, H-2, outline=bc, width=1)

        mid = H // 2

        if self.state == 'recording':
            num_bars = 64; bar_w = 4
            spacing  = (W - 40) / num_bars
            amp      = self.audio_level
            for i in range(num_bars):
                x  = 20 + i * spacing
                t  = i / num_bars
                h1 = math.sin(t * math.pi * 6  + self.wave_phase)       * amp * 30
                h2 = math.sin(t * math.pi * 13 + self.wave_phase * 1.7) * amp * 13
                h3 = math.sin(t * math.pi * 3  + self.wave_phase * 0.5) * amp * 8
                bar_h = max(2, abs(h1 + h2 + h3))
                inten = max(0.3, min(1.0, 1 - abs(t - 0.5) * 1.5))
                g_v   = int(212 * inten)
                b_v   = int(255 * inten)
                c.create_rectangle(
                    x - bar_w/2, mid - bar_h,
                    x + bar_w/2, mid + bar_h,
                    fill=f'#00{g_v:02x}{b_v:02x}', outline='')
            c.create_oval(14, 12, 24, 22, fill=RED, outline='')
            c.create_text(32, 17, text="LISTENING", fill=RED,
                          font=("Courier New", 7, "bold"), anchor='w')

        elif self.state == 'processing':
            for i in range(12):
                angle = self.wave_phase * 2.5 + i * (math.pi / 6)
                x  = W/2 + math.cos(angle) * 26
                y  = mid + math.sin(angle) * 12
                a  = (i + 1) / 12
                rv = int(255 * a); gv = int(190 * a)
                c.create_oval(x-3, y-3, x+3, y+3,
                              fill=f'#{rv:02x}{gv:02x}00', outline='')
            c.create_text(W/2, mid + 30, text="AI PROCESSING...",
                          fill=AMBER, font=("Courier New", 8), anchor='center')

        elif self.state == 'done':
            c.create_text(W/2, mid - 12, text="✓ DONE", fill=GREEN,
                          font=("Courier New", 13, "bold"), anchor='center')
            c.create_text(W/2, mid + 14, text=self._result_text,
                          fill=GREEN, font=("Courier New", 8), anchor='center')

        if self.state != 'hidden':
            c.create_text(W/2, H - 9,
                          text="Hold RIGHT CTRL to speak  •  Release to execute",
                          fill='#1a3a50', font=("Courier New", 7), anchor='center')


# ═════════════════════════════════════════════════════════════════════════════
#  SYSTEM TRAY
# ═════════════════════════════════════════════════════════════════════════════

def start_tray(overlay):
    try:
        import pystray
        from PIL import Image, ImageDraw
        img=Image.new('RGB',(64,64),color=(5,14,24)); draw=ImageDraw.Draw(img)
        draw.ellipse([4,4,60,60],outline=(0,212,255),width=3)
        draw.text((20,18),"J3",fill=(0,212,255))
        def on_quit(icon,item): icon.stop(); overlay.root.quit()
        def open_dash(*a): webbrowser.open(f'http://localhost:{DASHBOARD_PORT}')
        icon=pystray.Icon("JARVIS v3",img,"JARVIS v3",
            menu=pystray.Menu(
                pystray.MenuItem("JARVIS v3 Agent — Hold RIGHT CTRL",lambda *a:None,enabled=False),
                pystray.MenuItem("Open Dashboard",open_dash),
                pystray.MenuItem("Quit",on_quit),
            ))
        threading.Thread(target=icon.run,daemon=True).start()
    except Exception: pass


# ═════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═════════════════════════════════════════════════════════════════════════════

def main():
    global _overlay_ref

    # Suppress Chrome/GPU stderr noise from Python process level
    import sys as _sys, os as _os
    if OS == "Windows":
        # Redirect stderr to nul for chrome subprocess noise
        _os.environ["PYTHONIOENCODING"] = "utf-8"
        _os.environ["CHROME_LOG_FILE"]  = "nul"
        # Suppress TensorFlow Lite XNNPACK delegate messages
        _os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
        _os.environ["GLOG_minloglevel"]     = "3"

    print()
    print("  ╔══════════════════════════════════════════════════════════════╗")
    print("  ║  J.A.R.V.I.S  v3  AGENT  —  AI Desktop + Browser Assistant  ║")
    print("  ╠══════════════════════════════════════════════════════════════╣")
    print("  ║  Hold  RIGHT CTRL  to speak, release to execute              ║")
    print(f"  ║  Dashboard  →  http://localhost:{DASHBOARD_PORT}                     ║")
    print("  ║                                                              ║")
    print("  ║  AGENT VOICE COMMANDS:                                       ║")
    print('  ║  🎬 "open youtube search karan aujla"  → search + play       ║')
    print('  ║  💬 "whatsapp message tarun hello"      → send WA message     ║')
    print('  ║  📱 "telegram message mom coming home"  → send TG message     ║')
    print('  ║  📸 "instagram search karan aujla"      → IG search           ║')
    print('  ║  🐦 "tweet hello everyone"              → compose tweet       ║')
    print('  ║  🎵 "play karan aujla on spotify"       → Spotify play        ║')
    print('  ║  🌐 "open chrome go to github.com"      → navigate browser    ║')
    print('  ║  📁 "open downloads folder"             → open folder         ║')
    print("  ╚══════════════════════════════════════════════════════════════╝")
    print()
    print(f"  NVIDIA:   {'✅ READY — nemotron-3-nano-30b (reasoning, PRIMARY)' if nvidia_client else '❌ pip install openai'}")
    print(f"  Groq:     {'✅ READY — llama-3.3-70b-versatile (FALLBACK)' if HAS_GROQ else '❌ pip install groq'}")
    print(f"  Selenium: {'✅ READY' if HAS_SELENIUM else '❌ pip install selenium webdriver-manager'}")
    print(f"  Speech:   {'✅ READY' if HAS_SR       else '❌ pip install SpeechRecognition pyaudio'}")
    print(f"  TTS:      {'✅ READY' if HAS_TTS      else '❌ pip install pyttsx3'}")
    print()
    print(f"  NEW FEATURES:")
    print(f"  💾 Prefs saved to:  {PREFS_FILE}")
    _ww_msg  = ("ENABLED — say '" + WAKE_WORD + "'") if WAKE_WORD_ENABLED else "disabled"
    _skip_msg = "ENABLED" if SMART_SKIP_ENABLED else "disabled"
    _tts_msg  = "ENABLED" if STREAM_TTS else "disabled"
    print(f"  🎯 Custom cmds:     {len(CUSTOM_COMMANDS)} loaded from {CUSTOM_CMDS_FILE}")
    print(f"  🧠 Conv history:    {len(CONV_HISTORY)} messages in memory")
    print(f"  🎙️  Wake word:       {_ww_msg}")
    print(f"  ⚡ Smart Skip:      {_skip_msg}")
    print(f"  📢 Stream TTS:      {_tts_msg}")
    if CUSTOM_AI_PROMPT:
        print("  🤖 Custom prompt:  ", CUSTOM_AI_PROMPT[:60])
    print()
    print("  VOICE SETTINGS COMMANDS:")
    print('  🎙️  "enable wake word"              → always-listening mode')
    print('  🤖  "set custom prompt be concise"  → change AI personality')
    print('  ➕  "add command X means do Y"       → create shortcut')
    print('  🧠  "show conversation history"     → see context memory')
    print('  🗑️   "clear history"                 → forget everything')
    print()

    if not HAS_GROQ:
        print("  [ERROR] pip install groq"); sys.exit(1)

    start_dashboard_server()

    overlay      = WaveformOverlay()
    _overlay_ref = overlay

    hotkey = HotkeyController(overlay)
    hotkey.start()
    start_tray(overlay)

    speak("JARVIS Agent ready. Hold right control to speak.", blocking=False)
    print(f"  ✅ All systems online. Dashboard: http://localhost:{DASHBOARD_PORT}\n")
    overlay.root.mainloop()


if __name__ == "__main__":
    main()