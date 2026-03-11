"""
Open Source Trading Platform - Backend
FastAPI + WebSocket + pandas-ta + scikit-learn/XGBoost

Streams candlestick data, technical indicators, and ML predictions
to a Godot 4 frontend over WebSocket.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
import pandas_ta as ta
import yfinance as yf
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware

# ML imports
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import GradientBoostingClassifier
import pickle
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Trading Platform API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
# Data & Indicator Engine
# ──────────────────────────────────────────────

class MarketDataEngine:
    """Fetches market data and computes technical indicators."""

    def __init__(self):
        self.cache: dict[str, pd.DataFrame] = {}
        self.cache_expiry: dict[str, datetime] = {}
        self.cache_ttl = timedelta(minutes=5)

    def fetch_ohlcv(
        self,
        symbol: str,
        period: str = "6mo",
        interval: str = "1d",
    ) -> pd.DataFrame:
        """Fetch OHLCV data from Yahoo Finance with caching."""
        cache_key = f"{symbol}_{period}_{interval}"
        now = datetime.now()

        if cache_key in self.cache and now < self.cache_expiry.get(cache_key, now):
            return self.cache[cache_key]

        logger.info(f"Fetching {symbol} | period={period} interval={interval}")
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)

        if df.empty:
            raise ValueError(f"No data returned for {symbol}")

        df.index = pd.to_datetime(df.index)
        df = df.rename(columns=str.lower)
        df = df[["open", "high", "low", "close", "volume"]]

        self.cache[cache_key] = df
        self.cache_expiry[cache_key] = now + self.cache_ttl
        return df

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute technical indicators using pandas-ta."""
        result = df.copy()

        # Trend
        result.ta.sma(length=20, append=True)
        result.ta.sma(length=50, append=True)
        result.ta.ema(length=12, append=True)
        result.ta.ema(length=26, append=True)

        # Momentum
        result.ta.rsi(length=14, append=True)
        result.ta.macd(fast=12, slow=26, signal=9, append=True)
        result.ta.stoch(append=True)

        # Volatility
        result.ta.bbands(length=20, std=2, append=True)
        result.ta.atr(length=14, append=True)

        # Volume
        result.ta.obv(append=True)
        result.ta.vwap(append=True)

        return result


# ──────────────────────────────────────────────
# ML Signal Generator
# ──────────────────────────────────────────────

class MLSignalGenerator:
    """
    Simple ML model that predicts next-bar direction.
    Uses GradientBoosting on technical indicator features.
    Retrains on the fly with available data.
    """

    FEATURE_COLS = [
        "RSI_14", "MACD_12_26_9", "MACDh_12_26_9",
        "STOCHk_14_3_3", "STOCHd_14_3_3",
        "BBL_20_2.0", "BBM_20_2.0", "BBU_20_2.0",
        "ATRr_14", "SMA_20", "SMA_50",
    ]

    def __init__(self):
        self.model = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=3,
            learning_rate=0.1,
            random_state=42,
        )
        self.scaler = StandardScaler()
        self.is_trained = False

    def prepare_features(self, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        """Extract features and labels from indicator DataFrame."""
        available_cols = [c for c in self.FEATURE_COLS if c in df.columns]
        if len(available_cols) < 5:
            raise ValueError("Not enough indicator columns for ML")

        work = df[available_cols + ["close"]].dropna().copy()

        # Label: 1 if next close > current close, else 0
        work["target"] = (work["close"].shift(-1) > work["close"]).astype(int)
        work = work.dropna()

        X = work[available_cols].values
        y = work["target"].values
        return X, y

    def train(self, df: pd.DataFrame) -> dict:
        """Train the model on historical indicator data."""
        X, y = self.prepare_features(df)

        if len(X) < 30:
            return {"status": "insufficient_data", "samples": len(X)}

        # Train/test split (last 20% as test)
        split = int(len(X) * 0.8)
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]

        self.scaler.fit(X_train)
        X_train_s = self.scaler.transform(X_train)
        X_test_s = self.scaler.transform(X_test)

        self.model.fit(X_train_s, y_train)
        accuracy = self.model.score(X_test_s, y_test)
        self.is_trained = True

        return {
            "status": "trained",
            "accuracy": round(accuracy, 4),
            "train_samples": len(X_train),
            "test_samples": len(X_test),
        }

    def predict(self, df: pd.DataFrame) -> dict:
        """Predict signal for the latest bar."""
        if not self.is_trained:
            return {"signal": "neutral", "confidence": 0.0}

        available_cols = [c for c in self.FEATURE_COLS if c in df.columns]
        latest = df[available_cols].dropna().iloc[-1:].values

        if latest.shape[0] == 0:
            return {"signal": "neutral", "confidence": 0.0}

        latest_s = self.scaler.transform(latest)
        proba = self.model.predict_proba(latest_s)[0]
        pred = self.model.predict(latest_s)[0]

        signal = "bullish" if pred == 1 else "bearish"
        confidence = round(float(max(proba)), 4)

        return {"signal": signal, "confidence": confidence}


# ──────────────────────────────────────────────
# Global instances
# ──────────────────────────────────────────────

engine = MarketDataEngine()
ml_gen = MLSignalGenerator()


# ──────────────────────────────────────────────
# REST Endpoints
# ──────────────────────────────────────────────

@app.get("/")
def root():
    return {"name": "Trading Platform API", "version": "0.1.0"}


@app.get("/api/symbols")
def get_symbols():
    """Return a list of default watchlist symbols."""
    return {
        "symbols": [
            {"ticker": "SPY", "name": "S&P 500 ETF"},
            {"ticker": "QQQ", "name": "Nasdaq 100 ETF"},
            {"ticker": "AAPL", "name": "Apple Inc."},
            {"ticker": "MSFT", "name": "Microsoft Corp."},
            {"ticker": "GOOGL", "name": "Alphabet Inc."},
            {"ticker": "AMZN", "name": "Amazon.com Inc."},
            {"ticker": "TSLA", "name": "Tesla Inc."},
            {"ticker": "BTC-USD", "name": "Bitcoin USD"},
            {"ticker": "ETH-USD", "name": "Ethereum USD"},
            {"ticker": "GC=F", "name": "Gold Futures"},
            {"ticker": "CL=F", "name": "Crude Oil Futures"},
        ]
    }


@app.get("/api/train/{symbol}")
def train_model(symbol: str, period: str = "2y"):
    """Train the ML model on a given symbol."""
    try:
        df = engine.fetch_ohlcv(symbol, period=period)
        df = engine.compute_indicators(df)
        result = ml_gen.train(df)
        return {"symbol": symbol, **result}
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────────
# WebSocket Streaming
# ──────────────────────────────────────────────

def dataframe_to_candles(df: pd.DataFrame) -> list[dict]:
    """Convert a DataFrame with indicators to a list of JSON-safe dicts."""
    records = []
    for idx, row in df.iterrows():
        candle = {
            "timestamp": idx.isoformat(),
            "open": round(float(row["open"]), 4),
            "high": round(float(row["high"]), 4),
            "low": round(float(row["low"]), 4),
            "close": round(float(row["close"]), 4),
            "volume": int(row["volume"]),
        }
        # Attach indicator values (skip NaN)
        for col in df.columns:
            if col not in ("open", "high", "low", "close", "volume"):
                val = row[col]
                if pd.notna(val):
                    candle[col] = round(float(val), 4)
        records.append(candle)
    return records


@app.websocket("/ws/market/{symbol}")
async def market_stream(
    websocket: WebSocket,
    symbol: str,
    period: str = "6mo",
    interval: str = "1d",
):
    """
    WebSocket endpoint for Godot client.
    Sends initial historical data + indicators, then streams updates.
    """
    await websocket.accept()
    logger.info(f"Client connected: {symbol}")

    try:
        # Fetch and compute
        df = engine.fetch_ohlcv(symbol, period=period, interval=interval)
        df_ind = engine.compute_indicators(df)

        # Train ML if not already trained
        if not ml_gen.is_trained:
            train_result = ml_gen.train(df_ind)
            logger.info(f"ML train result: {train_result}")

        candles = dataframe_to_candles(df_ind)
        ml_signal = ml_gen.predict(df_ind)

        # Send initial payload
        await websocket.send_json({
            "type": "init",
            "symbol": symbol,
            "candles": candles,
            "ml_signal": ml_signal,
            "indicator_list": [
                c for c in df_ind.columns
                if c not in ("open", "high", "low", "close", "volume")
            ],
        })

        # Streaming loop — poll for updates every 60s
        while True:
            await asyncio.sleep(60)
            try:
                df = engine.fetch_ohlcv(symbol, period="5d", interval=interval)
                df_ind = engine.compute_indicators(df)
                latest = dataframe_to_candles(df_ind.tail(1))
                ml_signal = ml_gen.predict(df_ind)

                await websocket.send_json({
                    "type": "update",
                    "candle": latest[0] if latest else None,
                    "ml_signal": ml_signal,
                })
            except Exception as e:
                logger.warning(f"Update error: {e}")

    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {symbol}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("TV_API_PORT", 8770))
    uvicorn.run(app, host="0.0.0.0", port=port)
