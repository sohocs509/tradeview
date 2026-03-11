# Trading Platform Prototype

Open-source stock & commodities trading platform built with **Godot 4** (frontend) and **FastAPI** (backend), featuring real-time candlestick charts, technical indicators, and machine learning signals.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Godot 4 Client                     │
│  ┌──────────────┐ ┌───────────┐ ┌────────────────┐  │
│  │ Candlestick  │ │ RSI Panel │ │  MACD Panel    │  │
│  │ Chart        │ │           │ │                │  │
│  │ + SMA/EMA    │ └───────────┘ └────────────────┘  │
│  │ + Bollinger  │         ┌───────────────┐         │
│  │ + Volume     │         │  ML Signal    │         │
│  └──────┬───────┘         │  Badge        │         │
│         │                 └───────────────┘         │
│         │ WebSocket                                  │
└─────────┼───────────────────────────────────────────┘
          │
┌─────────┴───────────────────────────────────────────┐
│              FastAPI Backend (Python)                 │
│  ┌──────────────┐ ┌───────────┐ ┌────────────────┐  │
│  │ MarketData   │ │ pandas-ta │ │ ML Signal Gen  │  │
│  │ Engine       │ │ Indicators│ │ (GradientBoost)│  │
│  │ (yfinance)   │ │           │ │                │  │
│  └──────────────┘ └───────────┘ └────────────────┘  │
└─────────────────────────────────────────────────────┘
```

## Stack (100% Open Source)

| Layer          | Technology         | License     |
|----------------|--------------------|-------------|
| Game Engine    | Godot 4            | MIT         |
| Backend API    | FastAPI + Uvicorn  | MIT / BSD   |
| Market Data    | yfinance           | Apache 2.0  |
| Indicators     | pandas-ta          | MIT         |
| ML Models      | scikit-learn       | BSD         |
| Data Analysis  | pandas / numpy     | BSD         |

## Features

### Chart
- OHLCV candlestick rendering with bull/bear coloring
- Mouse scroll to zoom, drag to pan
- Hover for OHLC + volume tooltip
- Price axis with auto-scaling

### Technical Indicators
- **Overlays**: SMA(20), SMA(50), EMA(12), EMA(26), Bollinger Bands(20,2)
- **RSI Panel**: RSI(14) with overbought/oversold zones
- **MACD Panel**: MACD(12,26,9) line, signal line, histogram
- **Volume**: Color-coded volume bars (bull=green, bear=red)
- Toggle overlays on/off via toolbar

### Machine Learning
- GradientBoosting classifier predicting next-bar direction
- Features: RSI, MACD, MACD histogram, Stochastic K/D, Bollinger Bands, ATR, SMA 20/50
- Auto-trains on first connection, displays signal + confidence badge
- Train endpoint: `GET /api/train/{symbol}?period=2y`

## Quick Start

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
python main.py
```

Or use the helper script:
```bash
chmod +x start_backend.sh
./start_backend.sh
```

The API starts on `http://localhost:8765`.

### 2. Godot Client

1. Install [Godot 4.2+](https://godotengine.org/download)
2. Open Godot → Import → select `godot_project/project.godot`
3. Press **F5** (or Play) to run
4. Type a symbol (e.g. `SPY`, `AAPL`, `BTC-USD`) and click **Connect**

## API Endpoints

| Endpoint                          | Method    | Description                    |
|-----------------------------------|-----------|--------------------------------|
| `GET /`                           | REST      | Health check                   |
| `GET /api/symbols`                | REST      | Default watchlist              |
| `GET /api/train/{symbol}`         | REST      | Train ML model on symbol       |
| `WS /ws/market/{symbol}`          | WebSocket | Stream candles + indicators    |

### WebSocket Message Types

**`init`** — Sent on connection:
```json
{
  "type": "init",
  "symbol": "SPY",
  "candles": [ { "timestamp": "...", "open": 450.0, ... "RSI_14": 55.3, ... } ],
  "ml_signal": { "signal": "bullish", "confidence": 0.72 },
  "indicator_list": ["SMA_20", "SMA_50", "RSI_14", ...]
}
```

**`update`** — Sent every 60s:
```json
{
  "type": "update",
  "candle": { "timestamp": "...", "open": 451.0, ... },
  "ml_signal": { "signal": "bearish", "confidence": 0.61 }
}
```

## Project Structure

```
trading-platform/
├── backend/
│   ├── main.py              # FastAPI server, indicators, ML
│   └── requirements.txt
├── godot_project/
│   ├── project.godot         # Godot project config
│   ├── scenes/
│   │   └── main.tscn         # Main scene layout
│   └── scripts/
│       ├── main.gd           # Controller (wires everything)
│       ├── market_client.gd  # WebSocket client
│       ├── candlestick_chart.gd  # Candle + overlay renderer
│       └── indicator_panel.gd    # RSI / MACD sub-panels
├── start_backend.sh
└── README.md
```

## Next Steps

Here are natural extensions once the prototype is working:

- [ ] **Order execution panel** — place simulated or live orders via Alpaca API
- [ ] **Watchlist sidebar** — multiple symbols with quick-switch
- [ ] **Timeframe selector** — 1m, 5m, 15m, 1h, 1d, 1w
- [ ] **More ML models** — LSTM via PyTorch, ensemble voting
- [ ] **Backtesting engine** — replay historical data with strategy rules
- [ ] **Alerts system** — push notifications on indicator crossovers
- [ ] **TimescaleDB** — persistent storage for tick data
- [ ] **Redis pub/sub** — scale to multiple Godot clients
- [ ] **3D mode** — volumetric order book, correlation sphere
- [ ] **Raspberry Pi deployment** — run backend across Pi fleet

## Distributed Deployment (Pi Fleet)

Since you already have otto, pete, and milo, a natural split:

| Pi     | Role                         |
|--------|------------------------------|
| otto   | Data ingestion + TimescaleDB |
| pete   | ML training + inference      |
| milo   | FastAPI server + Redis       |

Coordinate with Ansible, monitor with your existing Grafana/MQTT stack.

## License

MIT — all dependencies are open source (MIT, BSD, or Apache 2.0).
