# codex7.ai — The Viral Shorts Engine 🚀

![codex7.ai Banner](frontend/logo.png)

> **"Turn raw video into viral gold in seconds."**

**codex7.ai** is a production-grade AI SaaS platform engineered for content creators. It automates the complex workflow of captioning, styling, and formatting short-form content (YouTube Shorts, TikTok, Reels), delivering professional, high-engagement results with zero manual effort.

---

## 🌟 Why codex7?

### For Creators
*   **Zero-Edit Workflow**: Upload a video, get a viral-ready result.
*   **Locally Powered**: No recurring cloud API costs for transcription.
*   **Brand Consistency**: Save your signature fonts, colors, and animation styles.

### For Developers & Investors
*   **Architecture**: Built on a modern, decoupled **FastAPI** + **Vanilla JS** stack for maximum performance and easy scalability.
*   **Cost Efficiency**: Utilizes efficient on-device inference (`faster-whisper`), drastically reducing operating costs compared to API-wrapper SaaS products.
*   **Data Privacy**: Processing happens locally/on-server without sending audio to third-party black boxes.

---

## ✨ Key Features

| Feature | Description | Tech Stack |
| :--- | :--- | :--- |
| **🎙️ AI Transcription** | Ultra-accurate, offline speech-to-text with word-level timestamps. | `faster-whisper` (OpenAI Large-v3) |
| **🌍 Smart Translation** | Auto-detects input language (Hindi, Tamil, Spanish) and translates to high-impact English. | `Transform Logic` |
| **🎨 "Viral" Styling** | Dynamic rendering engine mimicking top creators (hormozi-style). | `CSS3 Glassmorphism` |
| **⚡ Instant Render** | High-speed video processing and subtitle burning. | `FFmpeg`, `MoviePy` |
| **📊 Analytics Engine** | Tracks user engagement, feature usage, and errors locally + Google Sheets. | `gspread`, `Pandas` |
| **🛡️ Enterprise Ready** | Modular codebase, environment config, and robust error handling. | `Python 3.10+`, `DotEnv` |

---

## 🏗️ Architecture

The system follows a clean **Service-Oriented Architecture (SOA)**:

```mermaid
graph TD
    User[User / Browser] <-->|HTTP/JSON| Frontend[Frontend (Vanilla JS + HTML5)]
    Frontend <-->|REST API| Backend[FastAPI Backend]
    Backend -->|Inference| AI[AI Service (Whisper)]
    Backend -->|Processing| Video[Video Engine (FFmpeg)]
    Backend -->|Persistence| DB[(Google Sheets / JSON DB)]
    AI -->|Model Weights| LocalStorage[Local Cache]
```

---

## 🚀 Quick Start Guide

### Prerequisites
*   **Python 3.10+** installed.
*   **FFmpeg** added to system PATH.
*   **Node.js** (Optional, for dependency management if needed).

### 1. Clone & Setup
```bash
git clone https://github.com/codex7-ai/platform.git
cd codex7.ai

# Create Virtual Environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### 3. Configure Environment
Create a `.env` file in the root directory (copied from `.env.example`):
```ini
PORT=8000
WHISPER_MODEL=small   # Use 'large-v3' for production
GOOGLE_SHEET_ID=your_sheet_id  # Optional for analytics
```

### 4. Run the Engine
```bash
# Start the Backend Server
python backend/main.py
```
> The API will launch at `http://localhost:8000`.

### 5. Launch Frontend
Simply open `frontend/index.html` in your browser.
*   *Recommended:* Use VS Code "Live Server" extension for the best experience.

---

## 🛠️ Project Structure

```text
codex7.ai/
├── backend/               # Core Logic
│   ├── main.py            # API Gateway & Routes
│   ├── ai_service.py      # AI Inference Module
│   ├── sheets_service.py  # Data Persistence Layer
│   └── services/          # Business Logic (Analytics, etc.)
├── frontend/              # User Interface
│   ├── editor.html        # Main Studio App
│   ├── script.js          # Client-side Controller
│   └── style.css          # Design System
├── datastore/             # Local Database Fallback
├── .env                   # Secrets (GitIgnored)
└── README.md              # Documentation
```

---

## � Analytics & Data

**codex7.ai** includes a dual-layer data strategy:
1.  **Google Sheets (Primary)**: Real-time dashboard for user feedback, errors, and usage stats.
2.  **JSON Fallback (Local)**: Ensures zero data loss if internet connectivity drops.

To enable full analytics, provide your `GOOGLE_SHEET_ID` and `credentials.json` (Service Account) in the `backend/` folder.

---

## � License & Credits

*   **License**: MIT
*   **Core AI**: Powered by [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper).
*   **Video Processing**: Powered by [MoviePy](https://zulko.github.io/moviepy/) and [FFmpeg](https://ffmpeg.org/).

---

**Ready to create?** [Launch Editor](http://localhost:8000) (Requires Server Running)
