# TradeView Platform — System Design Document

**Open Source Stock & Commodities Trading Platform**
**with Machine Learning & Technical Analysis**

| | |
|---|---|
| **Prepared by** | David Pruitt |
| **Organization** | Enthropic Data LLC |
| **Date** | March 11, 2026 |
| **Version** | 1.0 |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Infrastructure Overview](#2-infrastructure-overview)
3. [Technology Stack](#3-technology-stack)
4. [System Architecture](#4-system-architecture)
5. [Node Specifications](#5-node-specifications)
6. [Frontend Design (Godot 4)](#6-frontend-design-godot-4)
7. [Machine Learning Pipeline](#7-machine-learning-pipeline)
8. [API Specification](#8-api-specification)
9. [Deployment Strategy](#9-deployment-strategy)
10. [Phased Development Roadmap](#10-phased-development-roadmap)
11. [Security Considerations](#11-security-considerations)
12. [Appendix](#12-appendix)

---

## 1. Executive Summary

TradeView is a fully open-source trading visualization and analysis platform designed for real-time market data display, technical indicator computation, and machine learning signal generation. The system is architected as a distributed application running across a homelab infrastructure, with the Godot 4 game engine serving as the client-side rendering frontend and a Python-based backend distributed across a fleet of Raspberry Pi single-board computers.

The platform targets equities, ETFs, commodities, and cryptocurrency markets, ingesting data from free and open-source data providers. All technical indicators are computed server-side using the pandas-ta library, with a GradientBoosting ML model providing directional predictions streamed to the client in real time via WebSocket.

This document defines the system architecture, node responsibilities, communication protocols, technology selections, and deployment strategy for the initial prototype and subsequent phases of development.

---

## 2. Infrastructure Overview

### 2.1 Node Topology

The platform is deployed across four physical machines in a distributed architecture. The Minisforum mini PC (fw01) serves as the primary frontend host and API gateway, while three Raspberry Pi units handle specialized backend workloads. All nodes communicate over the local network with Twingate providing secure remote access via tavipali.twingate.com.

| Node | Hostname | Role | Services |
|------|----------|------|----------|
| **`fw01`** | `mini.local` | Frontend Host / Gateway | Godot 4 Client, Nginx reverse proxy, Twingate connector, Redis pub/sub broker |
| **`otto`** | `otto.local` | Data Ingestion & Storage | Market data fetchers (yfinance, CCXT), PostgreSQL + TimescaleDB, data normalization pipeline, MQTT publisher |
| **`pete`** | `pete.local` | ML Training & Inference | scikit-learn / XGBoost model training, inference API (FastAPI), model registry, feature engineering pipeline |
| **`milo`** | `milo.local` | API Server & Indicators | FastAPI WebSocket server, pandas-ta indicator computation, Redis cache client, API rate limiting |

### 2.2 Network Architecture

All nodes are connected via the local LAN. The Minisforum (fw01) acts as the ingress point for the Godot client, connecting to milo's FastAPI WebSocket endpoint. Inter-node communication uses a combination of Redis pub/sub for real-time event streaming and REST APIs for request/response patterns. MQTT (via the existing Mosquitto broker) is used for system health monitoring and telemetry, feeding into the existing Grafana dashboards.

| From | To | Protocol | Port | Purpose |
|------|----|----------|------|---------|
| fw01 (Godot) | milo | WebSocket | `8765` | Market stream |
| otto | Redis (milo) | TCP | `6379` | Price updates |
| milo | pete | HTTP/REST | `8766` | ML inference |
| otto | PostgreSQL (otto) | TCP | `5432` | Data persistence |
| All nodes | Mosquitto | MQTT | `1883` | Health/telemetry |

### 2.3 Remote Access

Remote access to the platform is provided via Twingate (tavipali.twingate.com), allowing the Godot client to connect to milo's WebSocket endpoint from outside the local network. This eliminates the need for port forwarding or VPN tunnels for client access, while the existing Linode VPN tunnel continues to handle CGNAT bypass for other services.

---

## 3. Technology Stack

Every component in the platform is open source, licensed under MIT, BSD, Apache 2.0, or LGPL. No proprietary dependencies are required at any layer.

### 3.1 Frontend Layer

| Component | Technology | License | Host |
|-----------|-----------|---------|------|
| Game Engine | Godot 4.2+ (GDScript) | MIT | `fw01` |
| Chart Renderer | Custom Control nodes (_draw API) | MIT | `fw01` |
| WebSocket Client | Godot built-in WebSocketPeer | MIT | `fw01` |
| UI Framework | Godot Control nodes (VBox, HBox, Panel) | MIT | `fw01` |

### 3.2 Backend Layer

| Component | Technology | License | Host |
|-----------|-----------|---------|------|
| API Server | FastAPI + Uvicorn | MIT / BSD | `milo` |
| Technical Indicators | pandas-ta (RSI, MACD, BB, SMA, EMA, ATR, OBV, VWAP, Stochastic) | MIT | `milo` |
| ML Framework | scikit-learn (GradientBoosting), XGBoost | BSD / Apache 2.0 | `pete` |
| Market Data | yfinance, CCXT (crypto exchanges) | Apache 2.0 / MIT | `otto` |
| Time-Series DB | PostgreSQL + TimescaleDB extension | PostgreSQL / Apache 2.0 | `otto` |
| Cache / Pub-Sub | Redis | BSD | `milo` |
| Monitoring | MQTT (Mosquitto) + Grafana | EPL / AGPL | existing |

### 3.3 Infrastructure & DevOps

| Tool | Purpose | License |
|------|---------|---------|
| Ansible | Fleet provisioning, service deployment, rolling updates | GPL 3.0 |
| Docker / Compose | Container orchestration for each service | Apache 2.0 |
| Twingate | Zero-trust remote access (tavipali.twingate.com) | Proprietary (free tier) |
| GitHub Actions | CI/CD pipeline for backend and Godot exports | N/A (hosted) |
| step-ca | Internal TLS certificate authority (YubiKey backed) | Apache 2.0 |

---

## 4. System Architecture

### 4.1 Data Flow

The system follows a pipeline architecture where data flows from external sources through ingestion, computation, and presentation layers. Each stage is owned by a dedicated node.

1. **otto** pulls OHLCV data from Yahoo Finance (equities/commodities) and CCXT (crypto) on configurable intervals. Raw data is normalized and persisted to TimescaleDB. Price update events are published to Redis.

2. **milo** subscribes to Redis price channels. On each update, pandas-ta computes the full indicator suite (SMA, EMA, RSI, MACD, Bollinger Bands, ATR, OBV, VWAP, Stochastic). Results are cached in Redis with a 5-minute TTL.

3. **milo** calls pete's inference API with the latest feature vector. pete runs the trained GradientBoosting model and returns a directional signal (bullish/bearish/neutral) with confidence score.

4. **milo** streams the complete payload (candle + indicators + ML signal) to all connected Godot clients via WebSocket.

5. **fw01** renders the data in real time using Godot's GPU-accelerated _draw API: candlestick chart with overlays, RSI sub-panel, MACD sub-panel, volume bars, and ML signal badge.

### 4.2 Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    fw01 (mini.local)                         │
│  ┌───────────────────┐  ┌─────────────┐  ┌──────────────┐  │
│  │ Candlestick Chart │  │  RSI Panel  │  │  MACD Panel  │  │
│  │ + SMA/EMA overlay │  │  (14)       │  │  (12,26,9)   │  │
│  │ + Bollinger Bands │  └─────────────┘  └──────────────┘  │
│  │ + Volume bars     │        ┌──────────────────┐         │
│  │ + ML signal badge │        │  Godot 4 Client  │         │
│  └────────┬──────────┘        └──────────────────┘         │
│           │ WebSocket (ws://milo:8765)                      │
└───────────┼─────────────────────────────────────────────────┘
            │
┌───────────┴─────────────────────────────────────────────────┐
│                     milo (milo.local)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ FastAPI       │  │ pandas-ta    │  │ Redis             │  │
│  │ WebSocket     │  │ Indicators   │  │ Cache + Pub/Sub   │  │
│  │ Server :8765  │  │ Engine       │  │ :6379             │  │
│  └──────┬───────┘  └──────────────┘  └─────────┬─────────┘  │
│         │ HTTP :8766                            │            │
└─────────┼───────────────────────────────────────┼────────────┘
          │                                       │
┌─────────┴──────────────┐  ┌─────────────────────┴───────────┐
│   pete (pete.local)    │  │      otto (otto.local)          │
│  ┌──────────────────┐  │  │  ┌──────────────────────────┐   │
│  │ ML Inference API │  │  │  │ yfinance / CCXT fetchers │   │
│  │ GradientBoosting │  │  │  │ Data normalization       │   │
│  │ XGBoost          │  │  │  └────────────┬─────────────┘   │
│  │ Model Registry   │  │  │  ┌────────────┴─────────────┐   │
│  │ Optuna Tuning    │  │  │  │ PostgreSQL + TimescaleDB  │   │
│  └──────────────────┘  │  │  │ :5432                     │   │
└────────────────────────┘  │  └───────────────────────────┘   │
                            └──────────────────────────────────┘
```

### 4.3 Logical Layer Mapping

| Layer | Components | Node(s) |
|-------|-----------|---------|
| Presentation | CandlestickChart, IndicatorPanel (RSI), IndicatorPanel (MACD), MarketClient (WebSocket), UI Controls | fw01 (Godot 4) |
| API Gateway | FastAPI WebSocket server, REST endpoints, Redis cache layer, rate limiter | milo |
| Computation | pandas-ta indicator engine (10+ indicators), feature engineering pipeline | milo |
| Intelligence | GradientBoosting classifier, model training pipeline, model versioning, Optuna hyperparameter tuning | pete |
| Data | yfinance / CCXT fetchers, TimescaleDB, data normalization, Redis pub/sub publisher | otto |

---

## 5. Node Specifications

### 5.1 fw01 — Frontend Host & Gateway

- **Hardware:** Minisforum mini PC (mini.local)
- **Primary role:** Runs the Godot 4 client natively, providing GPU-accelerated chart rendering at 60fps. Also runs Nginx as a reverse proxy to route API requests to milo.
- **Services:** Godot 4 application, Nginx reverse proxy, Twingate connector
- **Resource profile:** Moderate CPU, GPU required for chart rendering, 4GB+ RAM recommended

### 5.2 otto — Data Ingestion & Storage

- **Hardware:** Raspberry Pi (otto.local)
- **Primary role:** Pulls market data from external sources on scheduled intervals (Celery beat scheduler). Normalizes and stores all OHLCV data in TimescaleDB with continuous aggregates for multiple timeframes. Publishes price update events to Redis channels.
- **Services:** PostgreSQL 16 + TimescaleDB, Python data fetchers, Celery worker + beat scheduler, Redis publisher
- **Storage:** External USB SSD recommended for TimescaleDB data directory (microSD inadequate for write-heavy workloads)

### 5.3 pete — ML Training & Inference

- **Hardware:** Raspberry Pi (pete.local)
- **Primary role:** Hosts the ML model lifecycle. Trains GradientBoosting classifiers on historical indicator data, serves real-time inference via a dedicated FastAPI endpoint, and manages model versioning with pickle serialization.
- **Services:** FastAPI inference server (port 8766), model training pipeline, Optuna hyperparameter search (scheduled weekly), model artifact storage
- **Resource profile:** CPU-intensive during training windows. 4GB+ RAM recommended for XGBoost. Training can be scheduled during off-hours to avoid inference latency impact.

### 5.4 milo — API Server & Indicator Engine

- **Hardware:** Raspberry Pi (milo.local)
- **Primary role:** Central API gateway. Subscribes to otto's price updates via Redis, computes the full technical indicator suite using pandas-ta, requests ML predictions from pete, and streams the composite payload to Godot clients over WebSocket.
- **Services:** FastAPI + Uvicorn (port 8765), Redis server, pandas-ta computation engine, WebSocket connection manager
- **Scaling:** Uvicorn workers can be increased to handle multiple concurrent WebSocket clients. Redis provides natural decoupling from otto's ingestion rate.

---

## 6. Frontend Design (Godot 4)

### 6.1 Scene Architecture

The Godot client is composed of four primary scripts organized around a single main scene. The scene uses a VBoxContainer layout to stack the toolbar, candlestick chart, RSI panel, and MACD panel vertically, with flexible size ratios ensuring the chart receives the majority of screen real estate.

| Script | Node Type | Responsibility |
|--------|-----------|---------------|
| `main.gd` | Control | Controller: wires UI signals, manages symbol selection, routes data between client and chart components |
| `market_client.gd` | Node | WebSocket lifecycle: connect, poll, parse JSON messages, emit typed signals (candles_received, candle_updated, ml_signal_received) |
| `candlestick_chart.gd` | Control | Main chart renderer: OHLCV candles, SMA/EMA overlays, Bollinger Bands fill, volume bars, ML signal badge, price axis, hover tooltip, zoom/pan input handling |
| `indicator_panel.gd` | Control | Sub-chart renderer: RSI mode (with 30/70 zones) and MACD mode (histogram + signal line). Enum-selectable, two instances used in scene. |

### 6.2 Rendering Strategy

All chart rendering uses Godot's immediate-mode `_draw()` API on Control nodes, which provides hardware-accelerated 2D drawing without the overhead of persistent scene nodes for each data point. This approach allows rendering of thousands of candles at 60fps. The chart supports mouse-wheel zoom (10–300 visible candles), click-drag panning, and hover crosshair with OHLCV tooltip.

### 6.3 Technical Indicators Displayed

| Indicator | Location | Parameters | Visual |
|-----------|----------|-----------|--------|
| SMA | Main chart overlay | `20, 50` | Gold and blue lines |
| EMA | Main chart overlay | `12, 26` | Computed server-side |
| Bollinger Bands | Main chart overlay | `20, 2.0` | Gray band with fill |
| RSI | Sub-panel (RSI) | `14` | Purple line, 30/70 zones |
| MACD | Sub-panel (MACD) | `12, 26, 9` | Teal/orange lines + histogram |
| Stochastic | Server-side (future panel) | `14, 3, 3` | Planned |
| ATR | Server-side (tooltip) | `14` | Numeric in hover info |
| OBV | Server-side | N/A | Planned panel |
| Volume | Main chart (bottom) | N/A | Green/red bars |

---

## 7. Machine Learning Pipeline

### 7.1 Model Architecture

The initial model is a GradientBoosting classifier (scikit-learn) trained to predict next-bar direction. The binary target is defined as: 1 if the next close is greater than the current close, 0 otherwise. Feature engineering produces 11 input features from the technical indicator suite.

### 7.2 Feature Set

| Feature | Source Indicator | Category |
|---------|-----------------|----------|
| `RSI_14` | RSI(14) | Momentum |
| `MACD_12_26_9` | MACD line | Momentum |
| `MACDh_12_26_9` | MACD histogram | Momentum |
| `STOCHk_14_3_3` | Stochastic %K | Momentum |
| `STOCHd_14_3_3` | Stochastic %D | Momentum |
| `BBL_20_2.0` | Lower Bollinger Band | Volatility |
| `BBM_20_2.0` | Middle Bollinger Band | Volatility |
| `BBU_20_2.0` | Upper Bollinger Band | Volatility |
| `ATRr_14` | Average True Range | Volatility |
| `SMA_20` | Simple Moving Avg (20) | Trend |
| `SMA_50` | Simple Moving Avg (50) | Trend |

### 7.3 Training Pipeline

Training occurs on pete via a REST endpoint or scheduled Celery task. The pipeline fetches 2 years of historical data from otto's TimescaleDB, computes indicators, engineers features, applies StandardScaler normalization, splits 80/20 for train/test, and fits the GradientBoosting model. Trained models are serialized with pickle and versioned by symbol and timestamp. Optuna hyperparameter tuning runs weekly during off-peak hours.

### 7.4 Inference Flow

On each price update, milo constructs the latest feature vector from the indicator cache and sends it to pete's inference endpoint via HTTP. pete loads the latest model for the requested symbol, applies the scaler transform, runs `predict_proba`, and returns the signal (bullish/bearish/neutral) with confidence as a float between 0 and 1. Typical inference latency on the Pi is under 50ms.

### 7.5 Future ML Roadmap

- LSTM/GRU recurrent networks via PyTorch for sequence-aware predictions
- Ensemble voting across GradientBoosting, XGBoost, and LSTM models
- Reinforcement learning agent for position sizing and risk management
- NLP sentiment analysis from news feeds (RSS) for supplementary signals

---

## 8. API Specification

### 8.1 REST Endpoints (milo:8765)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check. Returns API name and version. |
| `GET` | `/api/symbols` | Returns default watchlist with ticker and display name. |
| `GET` | `/api/train/{symbol}?period=2y` | Triggers ML model training on pete for the given symbol. Returns accuracy and sample counts. |

### 8.2 WebSocket Protocol (milo:8765)

The WebSocket endpoint at `/ws/market/{symbol}` accepts optional query parameters: `period` (default: `6mo`) and `interval` (default: `1d`). On connection, the server sends an `init` message with the full historical candle array including all computed indicator values, the current ML signal, and a list of available indicator column names. Subsequently, an `update` message is pushed every 60 seconds with the latest candle and refreshed ML signal.

**`init` message:**

```json
{
  "type": "init",
  "symbol": "SPY",
  "candles": [
    {
      "timestamp": "2025-09-01T00:00:00",
      "open": 450.12,
      "high": 453.80,
      "low": 449.05,
      "close": 452.30,
      "volume": 45000000,
      "RSI_14": 55.3,
      "SMA_20": 448.50,
      "MACD_12_26_9": 1.25
    }
  ],
  "ml_signal": { "signal": "bullish", "confidence": 0.72 },
  "indicator_list": ["SMA_20", "SMA_50", "RSI_14", "MACD_12_26_9", "..."]
}
```

**`update` message:**

```json
{
  "type": "update",
  "candle": { "timestamp": "...", "open": 451.0, "..." : "..." },
  "ml_signal": { "signal": "bearish", "confidence": 0.61 }
}
```

### 8.3 ML Inference Endpoint (pete:8766)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/predict` | Accepts feature vector JSON, returns signal and confidence. |
| `POST` | `/train/{symbol}` | Trains model from TimescaleDB data. Returns metrics. |
| `GET` | `/models` | Lists all trained models with version and accuracy. |

---

## 9. Deployment Strategy

### 9.1 Ansible Playbook Structure

Deployment is managed via the existing Ansible infrastructure used for the Pi fleet. Each node has a dedicated role in the playbook. The trading platform adds four new roles: `tradeview-data` (otto), `tradeview-ml` (pete), `tradeview-api` (milo), and `tradeview-client` (fw01). Each role defines Docker Compose services, environment configuration, health checks, and monitoring integration.

### 9.2 Docker Compose Services

| Node | Container | Image | Ports |
|------|-----------|-------|-------|
| `otto` | `timescaledb` | `timescale/timescaledb:latest-pg16` | `5432:5432` |
| `otto` | `data-fetcher` | `python:3.11-slim` (custom) | N/A (internal) |
| `pete` | `ml-service` | `python:3.11-slim` (custom) | `8766:8766` |
| `milo` | `api-server` | `python:3.11-slim` (custom) | `8765:8765` |
| `milo` | `redis` | `redis:7-alpine` | `6379:6379` |

### 9.3 CI/CD Pipeline

GitHub Actions handles continuous integration with automated testing (pytest for backend, GDScript unit tests via GUT for Godot). On merge to main, the pipeline builds Docker images, pushes to the local registry, and triggers Ansible deployment. Godot client exports are built via the Godot headless export pipeline and distributed as a binary to fw01.

### 9.4 Monitoring & Alerting

Each service publishes health metrics to MQTT topics under `tradeview/health/{node}/{service}`. The existing Grafana dashboards are extended with a TradeView panel showing WebSocket connection count, data ingestion lag, indicator computation time, ML inference latency, and per-node CPU/memory utilization. Alerting thresholds trigger notifications via the existing MQTT alert pipeline.

---

## 10. Phased Development Roadmap

| Phase | Target | Deliverables |
|-------|--------|-------------|
| **Phase 1** | Weeks 1–3 | Monolithic prototype: single-node backend (milo) with FastAPI + pandas-ta + ML. Godot client on fw01 connecting via WebSocket. Basic candlestick chart with SMA overlay, RSI panel, and ML signal badge. |
| **Phase 2** | Weeks 4–6 | Distribute backend: split data ingestion to otto (TimescaleDB + fetchers), ML to pete (inference API + training pipeline). Add Redis pub/sub on milo. Deploy via Ansible with Docker Compose. |
| **Phase 3** | Weeks 7–9 | Full indicator suite: MACD panel, Bollinger Bands, Stochastic, ATR, OBV, VWAP. Watchlist sidebar with multi-symbol quick-switch. Timeframe selector (1m through 1w). Hover crosshair with full info panel. |
| **Phase 4** | Weeks 10–12 | Order execution: Alpaca API integration for paper trading, order panel in Godot, position tracking, P&L display. Backtesting engine with historical replay mode. |
| **Phase 5** | Weeks 13+ | Advanced ML: LSTM/GRU via PyTorch, ensemble model voting, reinforcement learning agent. 3D visualization mode (volumetric order book, correlation sphere). Alerts system with MQTT push notifications. |

---

## 11. Security Considerations

- All inter-node communication is secured with mTLS certificates issued by the existing step-ca certificate authority (YubiKey-backed root). Certificates are rotated automatically via ACME.
- API keys for external data providers (Alpaca, Alpha Vantage) are stored in environment variables managed by Ansible Vault, never committed to version control.
- Redis requires authentication (`requirepass`) and is bound to the local network interface only. No external exposure.
- Twingate provides zero-trust access control for remote client connections, replacing traditional VPN-based access. Access policies are scoped per-resource.
- TimescaleDB follows PostgreSQL security best practices: dedicated service account with minimal privileges, no superuser access from application code, encrypted connections.
- WebSocket connections from Godot clients are authenticated via a shared token passed as a query parameter, validated by milo's FastAPI middleware.

---

## 12. Appendix

### 12.1 Project Repository Structure

```
trading-platform/
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   └── ml/
│       ├── models/
│       ├── training.py
│       └── inference.py
├── godot_project/
│   ├── project.godot
│   ├── scenes/
│   │   └── main.tscn
│   └── scripts/
│       ├── main.gd
│       ├── market_client.gd
│       ├── candlestick_chart.gd
│       └── indicator_panel.gd
├── ansible/
│   ├── playbooks/
│   │   └── deploy.yml
│   └── roles/
│       ├── tradeview-data/
│       ├── tradeview-ml/
│       ├── tradeview-api/
│       └── tradeview-client/
├── docker/
│   ├── otto/
│   │   └── docker-compose.yml
│   ├── pete/
│   │   └── docker-compose.yml
│   └── milo/
│       └── docker-compose.yml
├── docs/
│   └── design-document.md
├── start_backend.sh
└── README.md
```

### 12.2 Supported Market Symbols (Default Watchlist)

| Ticker | Name | Type |
|--------|------|------|
| `SPY` | S&P 500 ETF | ETF |
| `QQQ` | Nasdaq 100 ETF | ETF |
| `AAPL` | Apple Inc. | Equity |
| `MSFT` | Microsoft Corp. | Equity |
| `GOOGL` | Alphabet Inc. | Equity |
| `AMZN` | Amazon.com Inc. | Equity |
| `TSLA` | Tesla Inc. | Equity |
| `BTC-USD` | Bitcoin USD | Crypto |
| `ETH-USD` | Ethereum USD | Crypto |
| `GC=F` | Gold Futures | Commodity |
| `CL=F` | Crude Oil Futures | Commodity |
