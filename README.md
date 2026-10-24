Markdown
# ⚡ NEXUS-X // QUANTUM TRADING AGENT (XAUUSD)

An institutional-grade, cyberpunk-styled quantitative terminal and autonomous trading engine for **XAUUSD (Gold)**. Powered by Python, FastAPI WebSockets, and MetaTrader 5 (MT5), featuring Smart Money Concepts (SMC) order flow detection and zero-lag hardware-accelerated telemetry.

---

## 🚀 Key Features

* **Zero-Lag Telemetry Charting:** 60 FPS hardware-accelerated candlestick engine powered by TradingView Lightweight Charts with multi-timeframe switching (1M, 5M, 15M, 1H).
* **Smart Money Concepts (SMC) Engine:** Automated detection of Fair Value Gaps (FVG), Break of Structure (BOS / CHoCH), and dynamic 200 EMA trend filtering.
* **Level 2 Depth of Market (DOM):** Real-time bid/ask order book depth matrix and volume imbalance telemetry.
* **Capital & Risk Diagnostics:** Hard stop 2.0% daily circuit breakers, dynamic ATR trailing stops, and spread expansion guards.
* **SQLite Attribution Memory:** Heuristic ledger that self-tags closed trades (Clean Win, Wicked Out SL, News Spikes) to adjust algorithmic execution weights.

---

## 🛠️ Architecture & Tech Stack

* **Trading Engine & Backend:** Python 3.11, MetaTrader 5 API, FastAPI, Uvicorn WebSockets, SQLite3
* **Frontend Cockpit:** Single-page responsive Obsidian UI, Tailwind CSS, TradingView Lightweight Charts, Lucide Icons, Tone.js

---

## 📦 Setup & Installation

### 1. Clone the Repository
```bash
git clone [https://github.com/sonisainisaini64-arch/xauusd-smc-quantum-desk.git](https://github.com/sonisainisaini64-arch/xauusd-smc-quantum-desk.git)
cd xauusd-smc-quantum-desk
2. Install Dependencies
Bash
pip install -r requirements.txt
3. Configure MetaTrader 5
Ensure MetaTrader 5 desktop client is installed, logged into your demo/live account, and Algo Trading is enabled in Tools -> Options -> Expert Advisors.

4. Launch Web Terminal
Bash
python -m uvicorn server:app --reload --port 8000
Open your browser at http://localhost:8000 and press F11 for trading desk mode.

5. Launch Trading Agent (Background Execution)
In a separate terminal tab:

Bash
python main.py
⚖️ Disclaimer
This software is developed for research and educational purposes in quantitative finance and algorithmic design. Use risk management protocols when deploying capital on live brokerage accounts.


Paste karne ke baad upar green button **`Commit changes...`** par click karein aur popup me confirm kar dein[cite: 5, 6].
