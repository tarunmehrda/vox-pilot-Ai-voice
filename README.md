<div align="center">

# 🤖 J.A.R.V.I.S — v3 Advanced Agent

### *Your AI-Powered Desktop Voice Assistant*

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![NVIDIA](https://img.shields.io/badge/NVIDIA-Nemotron_30B-76B900?style=for-the-badge&logo=nvidia&logoColor=white)](https://build.nvidia.com)
[![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3_70B-F55036?style=for-the-badge&logo=meta&logoColor=white)](https://groq.com)
[![Selenium](https://img.shields.io/badge/Selenium-Browser_Agent-43B02A?style=for-the-badge&logo=selenium&logoColor=white)](https://selenium.dev)
[![License](https://img.shields.io/badge/License-MIT-00E5FF?style=for-the-badge)](LICENSE)

<br>

> **A fully local, voice-controlled AI assistant that automates your entire desktop.**
> **Talk to your PC like Tony Stark talks to JARVIS.**

<br>

[🚀 Quick Start](#-quick-start) · [✨ Features](#-features) · [🎤 Voice Commands](#-voice-commands) · [🛠️ Tech Stack](#️-tech-stack) · [⚙️ Configuration](#️-configuration)

---

</div>

<br>

## 🎯 What is JARVIS?

**JARVIS** is an advanced AI desktop assistant that transforms your voice into action. Hold **Right Ctrl**, speak your command, and watch JARVIS execute it — from opening apps and searching YouTube to sending WhatsApp messages, composing emails, controlling volume, managing files, and answering real-time questions.

> 💡 **No cloud dependency** — runs entirely on your machine with free API keys from NVIDIA & Groq.

<br>

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    🎤 Voice Input (Right Ctrl)                   │
│                          ↓                                       │
│   ┌──────────────────────────────────────────────────────────┐   │
│   │              🧠 AI Command Parser                        │   │
│   │                                                          │   │
│   │   1. Local Fast-Path (regex, 0ms)  ← 200+ patterns      │   │
│   │   2. NVIDIA Nemotron 30B (reasoning, streaming)          │   │
│   │   3. Groq LLaMA 3.3 70B (fallback)                      │   │
│   │   4. Smart Skip (dictation bypass)                       │   │
│   └────────────┬─────────────────────────────────┬───────────┘   │
│                ↓                                 ↓               │
│   ┌────────────────────┐            ┌────────────────────────┐   │
│   │  🖥️ Desktop Agent   │            │  🌐 Browser Agent      │   │
│   │  PyAutoGUI          │            │  Selenium Chrome       │   │
│   │  • Type/Click/Scroll│            │  • YouTube, WhatsApp   │   │
│   │  • Volume (pycaw)   │            │  • Instagram, Twitter  │   │
│   │  • Screenshot       │            │  • Gmail, LinkedIn     │   │
│   │  • File Operations  │            │  • Reddit, Facebook    │   │
│   └────────────────────┘            └────────────────────────┘   │
│                                                                  │
│   ┌──────────────────────────────────────────────────────────┐   │
│   │  📊 Web Dashboard — http://localhost:7798                │   │
│   │  Command Center · AI Search · Analytics · Settings       │   │
│   └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

<br>

## ✨ Features

### 🎤 Voice Control
| Feature | Description |
|---------|-------------|
| **Push-to-Talk** | Hold `Right Ctrl` to record, release to execute |
| **Wake Word** | Say *"Hey Jarvis"* for hands-free always-on mode |
| **Smart Skip** | Short dictation bypasses AI for 0ms latency |
| **Conversation Memory** | 20-message rolling context for follow-up commands |

### 🤖 Dual AI Engine
| Model | Role | Speed |
|-------|------|-------|
| **NVIDIA Nemotron-3 Nano 30B** | Primary (reasoning + streaming) | ~1-2s |
| **Groq LLaMA 3.3 70B** | Fallback (fast, reliable) | ~0.5s |
| **Local Regex Parser** | 200+ command patterns | **0ms** |

### 🌐 Browser Automation (Selenium)
| Platform | Capabilities |
|----------|-------------|
| 🎬 **YouTube** | Open, search, play videos, scroll feed |
| 💬 **WhatsApp** | Find contact, type & send messages |
| 📸 **Instagram** | Open, search, scroll, send DMs |
| 🐦 **Twitter/X** | Open, search, compose & post tweets |
| 📧 **Gmail** | Compose, fill fields, send emails |
| 🎵 **Spotify** | Search & play songs/artists |
| 💼 **LinkedIn** | Search people & job listings |
| 🟠 **Reddit** | Browse subreddits, search posts |
| 🔵 **Facebook** | Open, search, post |
| 🌐 **Chrome** | Navigate URLs, Google search, scroll |

### 🖥️ Desktop Automation (PyAutoGUI)
| Feature | Details |
|---------|---------|
| 📁 **File Manager** | Create/delete/rename/open files & folders |
| 🔊 **Volume Control** | Exact % via pycaw Windows Core Audio API |
| 📷 **Screenshot** | Capture & auto-save to Desktop |
| ⌨️ **Keyboard** | Type, press keys, hotkey combos |
| 🖱️ **Mouse** | Click, double-click, drag, scroll, auto-click |
| 🪟 **Window Management** | Minimize, maximize, snap, switch, close |
| 🔌 **System Power** | Lock, sleep, restart, shutdown |
| ⏰ **Reminders** | Timed voice alerts |
| 📝 **AI Text Editing** | Rewrite text to exact character/word limits |

### 🧠 AI Intelligence
| Feature | Details |
|---------|---------|
| 🔍 **Web Search** | Real-time answers via DuckDuckGo + AI extraction |
| 📰 **Live News** | Headlines by topic (AI, tech, sports, etc.) |
| 🌤️ **Weather** | Live weather for any city |
| 🧮 **Calculator** | Natural language math & percentages |
| 📋 **Clipboard AI** | Summarize, fix grammar, translate clipboard |
| ✏️ **Text Editor** | Rewrite selected text to exact character/word count |
| 💬 **Chat** | Conversational AI with memory |

<br>

## 🚀 Quick Start

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/your-username/vox-pilot.git
cd vox-pilot
```

### 2️⃣ Install Dependencies

```bash
pip install groq openai SpeechRecognition pyaudio pyautogui pyperclip psutil
pip install pynput pillow pyttsx3 requests feedparser
pip install selenium webdriver-manager
pip install pycaw comtypes
```

### 3️⃣ Get Free API Keys

| Service | Link | Purpose |
|---------|------|---------|
| 🟢 **NVIDIA** | [build.nvidia.com](https://build.nvidia.com) | Primary AI (Nemotron reasoning) |
| 🔴 **Groq** | [console.groq.com](https://console.groq.com) | Fallback AI (LLaMA 3.3 70B) |

### 4️⃣ Set Environment Variables

```powershell
# Windows PowerShell
$env:GROQ_API_KEY   = "gsk_your_key_here"
$env:NVIDIA_API_KEY = "nvapi-your_key_here"
```

### 5️⃣ Launch JARVIS

```bash
python jarvis_backend.py
```

✅ Dashboard opens automatically at **http://localhost:7798**  
✅ Hold **Right Ctrl** to speak commands  
✅ A floating overlay appears showing status  

<br>

## 🎤 Voice Commands

<details>
<summary><b>🗣️ App Control</b></summary>

```
"open youtube"        → Opens YouTube
"open chrome"         → Opens Chrome browser
"open notepad"        → Opens Notepad
"open spotify"        → Opens Spotify
"close chrome"        → Kills Chrome process
"open vs code"        → Opens Visual Studio Code
```
</details>

<details>
<summary><b>🔍 AI Search & Knowledge</b></summary>

```
"who is the CEO of Google"       → AI-powered web search
"price of Bitcoin today"         → Real-time price lookup
"what is machine learning"       → AI explanation
"latest AI news"                 → Top headlines
"weather in Mumbai"              → Live weather
"calculate 18 percent of 5000"   → Instant math
```
</details>

<details>
<summary><b>🌐 Browser Agent</b></summary>

```
"open youtube search karan aujla"      → YouTube search
"play lofi beats on spotify"           → Spotify play
"whatsapp message tarun hello"         → WhatsApp send
"tweet hello world"                    → Post on Twitter
"open gmail compose leave application" → Gmail compose
"chrome go to github.com"              → Navigate URL
```
</details>

<details>
<summary><b>📁 File Management</b></summary>

```
"make folder Projects"     → Creates folder on Desktop
"open downloads folder"    → Opens Downloads in Explorer
"create file notes.txt"    → Creates new file
"delete folder OldStuff"   → Deletes folder
"list desktop"             → Shows Desktop files
```
</details>

<details>
<summary><b>✏️ AI Text Editing</b></summary>

```
"make this in 300 characters"   → Rewrites to 300 chars
"make it shorter"               → Shortens text
"make it longer"                → Expands text
"fix grammar"                   → Fixes grammar errors
"summarize clipboard"           → Summarizes copied text
"translate clipboard to Hindi"  → Translates clipboard
```
</details>

<details>
<summary><b>🔊 Volume & System Control</b></summary>

```
"set volume to 50"    → Exact 50%
"increase volume 20"  → +20%
"mute"                → Toggle mute
"take screenshot"     → Capture & save
"lock screen"         → Lock PC
"shutdown"            → Shutdown PC
```
</details>

<br>

## 📊 Dashboard

The web dashboard at `http://localhost:7798` provides a premium Iron Man-inspired command center:

| Page | Features |
|------|----------|
| **📊 Dashboard** | Stats, quick commands, activity log, system status |
| **🔍 AI Search** | Web-powered AI search with history |
| **🎮 Agent Control** | Volume sliders, file ops, browser agents, screenshot |
| **📈 Analytics** | Usage charts, command categories, insights |
| **💻 System Info** | Live CPU/RAM/Disk/Battery monitor |
| **🧠 AI Memory** | View & manage conversation history |
| **⚙️ Settings** | API keys, model selection, wake word, themes |

<br>

## ⚙️ Configuration

### 🔑 API Keys

```bash
GROQ_API_KEY=gsk_xxxxx        # Groq console
NVIDIA_API_KEY=nvapi-xxxxx    # NVIDIA Build
```

### 🧠 AI Models Available

| Model | Provider | Best For |
|-------|----------|----------|
| **Nemotron-3 Nano 30B** | NVIDIA | Reasoning (primary) |
| **LLaMA 3.3 70B** | Meta/Groq | Complex commands (fallback) |
| **LLaMA 3.1 8B** | Meta/Groq | Ultra-fast responses |
| **Mixtral 8×7B** | Mistral/Groq | Balanced reasoning |
| **Gemma 2 9B** | Google/Groq | Efficient instructions |

### 🎨 Customization

- **Custom AI Personality** — *"set custom prompt respond like Tony Stark"*
- **Wake Word** — Change from "hey jarvis" to anything
- **Accent Colors** — Cyan, Green, Purple, Amber, Red
- **TTS Speed** — 100–250 WPM
- **Mic Selection** — Choose from available devices

<br>

## 📁 Project Structure

```
vox-pilot/
├── jarvis_backend.py       # 🧠 Main backend (4300+ lines)
│   ├── AI Parser           #    NVIDIA + Groq command parsing
│   ├── Local Fast-Path     #    200+ regex patterns (0ms)
│   ├── Desktop Agent       #    PyAutoGUI automation
│   ├── Browser Agent       #    Selenium Chrome automation
│   ├── Voice Engine        #    SpeechRecognition + pyttsx3
│   ├── Web Dashboard API   #    HTTP server on :7798
│   └── AI Text Editor      #    Rewrite text with AI
├── jarvis_frontend.html    # 🎨 Dashboard UI (Iron Man theme)
├── assets/
│   └── jarvis_banner.png   # 🖼️ README banner
└── README.md               # 📖 This file
```

<br>

## 🛠️ Tech Stack

<div align="center">

| Layer | Technology |
|-------|-----------|
| **Language** | Python 3.10+ |
| **Primary AI** | NVIDIA Nemotron-3 Nano 30B |
| **Fallback AI** | Groq LLaMA 3.3 70B Versatile |
| **Voice Input** | Google Speech Recognition |
| **Voice Output** | pyttsx3 (offline TTS) |
| **Browser Automation** | Selenium + ChromeDriver |
| **Desktop Automation** | PyAutoGUI + pynput |
| **Volume Control** | pycaw (Windows Core Audio API) |
| **Clipboard** | pyperclip |
| **System Monitor** | psutil |
| **News Feed** | feedparser (Google News RSS) |
| **Web Search** | DuckDuckGo API + HTML scraping |
| **Dashboard** | Vanilla HTML/CSS/JS |
| **Server** | Python HTTPServer |

</div>

<br>

## 🔧 Troubleshooting

<details>
<summary><b>❌ "No module named pyaudio"</b></summary>

```bash
pip install pipwin
pipwin install pyaudio
```
</details>

<details>
<summary><b>❌ Chrome driver not found</b></summary>

```bash
pip install webdriver-manager
# JARVIS auto-downloads the correct ChromeDriver version
```
</details>

<details>
<summary><b>❌ Volume control not working</b></summary>

```bash
pip install pycaw comtypes
# Requires Windows with audio devices
```
</details>

<details>
<summary><b>❌ Speech recognition not working</b></summary>

- Check microphone permissions in Windows Settings
- Run `python -c "import speech_recognition as sr; print(sr.Microphone.list_microphone_names())"` to list mics
- Select correct mic in Dashboard → Settings → Microphone Selection
</details>

<details>
<summary><b>❌ API key errors</b></summary>

- Verify keys at [console.groq.com](https://console.groq.com) and [build.nvidia.com](https://build.nvidia.com)
- Check Dashboard → Settings → Test Connection
- Ensure environment variables are set correctly
</details>

<br>

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

<br>

## 📜 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

<br>

---

<div align="center">

### ⭐ Star this repo if JARVIS made your life easier!

<br>

*"Sometimes you gotta run before you can walk." — Tony Stark*

<br>

[![Made with Python](https://img.shields.io/badge/Made_with-Python-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Powered by NVIDIA](https://img.shields.io/badge/Powered_by-NVIDIA_AI-76B900?style=flat-square&logo=nvidia&logoColor=white)](https://nvidia.com)
[![Uses Groq](https://img.shields.io/badge/Uses-Groq_Cloud-F55036?style=flat-square)](https://groq.com)

**Built with 💙 by Tarun**

</div>
