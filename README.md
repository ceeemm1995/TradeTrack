READMEtradetrack.md
# 📊 TradeTrack

TradeTrack is a highly responsive, localized web-based trading journal application built with **FastAPI** and styled with a sharp, modern neo-brutalist UI layout. Specifically engineered for fast-paced financial market scalpers (Gold, Silver, Crude Oil), it leverages technical analysis tracking frameworks and features an integrated **Gemini AI Trading Assistant** to help review execution setups and protect psychological discipline.

---

## ✨ Features

* **🔒 Secure Local Authentication:** Fast, encrypted user registration and login using `passlib` (bcrypt) data structures.
* **📈 Scalper-Focused Journaling:** Track daily trading sessions, market symmetry patterns, win/loss metrics, and risk-to-reward dynamics.
* **🤖 Integrated Gemini AI Coach:** Send your journaled metrics or trading state straight to a dedicated AI model instance to receive rapid, objective system reviews and market structure analysis.
* **🎨 Neo-Brutalist Interface:** Designed for quick data scannability with a high-contrast theme, custom vector branding assets, and zero heavy asset latency.
* **📁 100% Local Data Privacy:** All user credentials and trading records are stored securely on your local hard drive via flat JSON file engines (`users.json`, `trade_track.json`). No external cloud database required.

---

## 🛠️ Tech Stack

* **Backend:** FastAPI (Python 3.11+)
* **Server Engine:** Uvicorn
* **Security:** Passlib (Bcrypt hashing)
* **AI Integration:** Google GenAI SDK (Gemini Core Engine)
* **Database:** Local JSON File Systems

---

## 🚀 Installation & Local Setup

Get your local instances running in less than 3 minutes:

### 1. Clone the Repository
```bash
git clone [https://github.com/ceeemm1995/TradeTrack.git](https://github.com/ceeemm1995/TradeTrack.git)
cd TradeTrack

