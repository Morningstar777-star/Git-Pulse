# GitPulse Explorer — Local GitHub Trend Intelligence Dashboard

A locally hosted technology intelligence dashboard and momentum radar for discovering breakout GitHub repositories, emerging frameworks, and rising developer tools before they become mainstream.

---

## 1. Quick Launch (Windows 11)

### Double-Click Launch:
Simply double-click **`run.bat`** in the root directory.

The launcher will:
1. Verify that Python 3.10+ and Node.js are available.
2. Automatically initialize the Python virtual environment (`.venv`) and install dependencies if needed.
3. Automatically build the production frontend bundle if not already present.
4. Detect if GitPulse Explorer is already running on port 8000 (preventing port collisions and duplicate instances).
5. Open your default web browser directly to `http://localhost:8000`.

### Development Mode (with Live Hot-Reloading):
To edit the frontend code with instant Vite hot-module replacement, double-click **`dev.bat`** or run:
```bash
# Terminal 1: Backend
.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload

# Terminal 2: Frontend
cd frontend
npm run dev
```

---

## 2. Key Architecture & Features

### A. Persistent Momentum Radar (Left Sidebar)
- Tracks the fastest-accelerating repositories currently on the radar.
- Renders rank badges (`#1`, `#2`, `#3`), daily/weekly velocity indicators (`+740 today`), logarithmic scale dampening, and real-time SVG sparkline curves.
- Expandable / collapsible sidebar toggle.

### B. Explore by Topic (9 Curated Technology Hubs)
- **Artificial Intelligence & Machine Learning** (Diffusion models, PyTorch, Transformers)
- **LLMs, AI Agents & Developer Tools** (Ollama, Browser-Use, CrewAI, Cline)
- **Web Development & Frameworks** (Next.js, Tailwind, Shadcn, Astral UV)
- **Data Engineering & Databases** (DuckDB, Polars, ClickHouse, Qdrant)
- **Quantitative Finance & Data Science** (Freqtrade, CCXT, YFinance, Superlinked)
- **Cybersecurity & AppSec** (Nuclei, SecLists, TruffleHog, SQLMap)
- **Robotics, IoT & Embedded Hardware** (ESP-IDF, Klipper, ROS2, Taichi)
- **Open Source Infrastructure** (Kubernetes, Supabase, PocketBase, Tailscale)
- **Emerging & Unclassified Technologies** (Ladybird, Bubbletea, Smallchat)

### C. Two Distinct Repository Sorting Modes
- **Mode 1: Overall Popularity** — Rank repositories by absolute established adoption (Total Stars descending or Forks descending).
- **Mode 2: Momentum** — Rank repositories by their velocity, rate of acceleration, and breakout novelty rather than mere historical accumulation. Includes selectable time windows (`24h`, `7d`, `30d`).

### D. Repository Telemetry Details Modal
- Click any repository in the sidebar or main grid to inspect:
  - Historical star-growth trajectory chart based on recorded snapshots.
  - Granular momentum factor breakdown (Velocity, Acceleration, Novelty bonus, Scale dampener, Confidence).
  - Ecosystem tags and related repositories.
  - One-click Watchlist bookmarking.

---

## 3. The Momentum Intelligence Engine

Do not confuse momentum with simplistic star counts. GitPulse Explorer implements an interpretable mathematical baseline alongside gradient-boosted trees and time-series modeling:

$$\text{Score} = \text{Velocity} \times \left(1 + \beta \cdot \text{Acceleration}\right) \times \log_{10}(1 + \text{Stars}) \times \text{NoveltyMultiplier} \times \text{Confidence}$$

### Benchmarked Models:
1. **Calibrated Baseline Formula:** Monotonic physics formulation with logarithmic scale bounding and acceleration clamping. Zero cold-start latency, highly interpretable.
2. **Hist-GBDT Momentum Regressor:** Gradient-boosted decision trees trained on multi-factor interactions (fork-to-star ratio, velocity, repository age in days).
3. **Sequential LSTM Trend Recurrence:** Recurrent neural sequence model on sliding chronological snapshot windows.

### Running the Standalone Benchmark Suite:
Run the model evaluation directly in your terminal at any time:
```bash
.venv\Scripts\python.exe evaluate_momentum.py
```
Or view the live benchmark comparison and toggle the active ranking model directly from the **Engine Diagnostics** button in the dashboard header.

---

## 4. GitHub API Configuration

GitPulse Explorer works out of the box with **zero configuration** using pre-seeded multi-day snapshots and public endpoints.

To increase your hourly GitHub API limits from 60 to 5,000 requests/hour:
1. Copy `.env.example` to `.env`:
   ```bash
   copy .env.example .env
   ```
2. Generate a Personal Access Token on GitHub (`Settings` -> `Developer settings` -> `Personal access tokens` -> `Tokens (classic)` with no extra scopes needed for public repos).
3. Set your token:
   ```env
   GITHUB_TOKEN=ghp_yourPersonalAccessTokenHere
   ```
4. Restart the application or click **Sync Now** in the top right header.

---

## 5. Technology Stack

- **Backend:** Python 3.11, FastAPI, Uvicorn, Aiohttp, SQLite, Scikit-learn, NumPy.
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, Lucide React, Framer Motion.
- **Design Standard:** Adheres to the *135-Blueprint Premium Web Craft Standard* (Enterprise AI Cockpit, Liquid Glass 2.0 dual-mask refraction, 7-layer viewport stack, Instrument Serif editorial typography).
