"""
TradeView — ML Training Pipeline (pete.local)
Trains GradientBoosting classifier on historical indicator data from TimescaleDB.

Phase 2 service — extracted from monolithic backend/api/main.py.
"""

import logging
import os
import pickle
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pandas_ta as ta
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

MODEL_DIR = Path(os.environ.get("TV_MODEL_DIR", "/data/models"))
MODEL_DIR.mkdir(parents=True, exist_ok=True)

DB_HOST = os.environ.get("TV_DB_HOST", "otto.local")
DB_PORT = int(os.environ.get("TV_DB_PORT", 5433))
DB_USER = os.environ.get("TV_DB_USER", "tradeview")
DB_PASSWORD = os.environ.get("TV_DB_PASSWORD", "")
DB_NAME = os.environ.get("TV_DB_NAME", "tradeview")

FEATURE_COLS = [
    "RSI_14", "MACD_12_26_9", "MACDh_12_26_9",
    "STOCHk_14_3_3", "STOCHd_14_3_3",
    "BBL_20_2.0", "BBM_20_2.0", "BBU_20_2.0",
    "ATRr_14", "SMA_20", "SMA_50",
]


def fetch_from_db(symbol: str, period_days: int = 730) -> pd.DataFrame:
    import psycopg2
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_USER, password=DB_PASSWORD, dbname=DB_NAME,
    )
    try:
        query = """
            SELECT time, open, high, low, close, volume
            FROM ohlcv
            WHERE symbol = %s AND time >= NOW() - INTERVAL '%s days'
            ORDER BY time ASC
        """
        df = pd.read_sql(query, conn, params=(symbol, period_days), index_col="time")
        df.index = pd.to_datetime(df.index, utc=True)
        return df
    finally:
        conn.close()


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result.ta.sma(length=20, append=True)
    result.ta.sma(length=50, append=True)
    result.ta.ema(length=12, append=True)
    result.ta.ema(length=26, append=True)
    result.ta.rsi(length=14, append=True)
    result.ta.macd(fast=12, slow=26, signal=9, append=True)
    result.ta.stoch(append=True)
    result.ta.bbands(length=20, std=2, append=True)
    result.ta.atr(length=14, append=True)
    return result


def train(symbol: str) -> dict:
    df = fetch_from_db(symbol)
    if df.empty:
        return {"status": "no_data", "symbol": symbol}

    df = compute_indicators(df)
    available_cols = [c for c in FEATURE_COLS if c in df.columns]
    work = df[available_cols + ["close"]].dropna().copy()
    work["target"] = (work["close"].shift(-1) > work["close"]).astype(int)
    work = work.dropna()

    if len(work) < 30:
        return {"status": "insufficient_data", "samples": len(work)}

    X = work[available_cols].values
    y = work["target"].values
    split = int(len(X) * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    scaler = StandardScaler()
    scaler.fit(X_train)
    model = GradientBoostingClassifier(n_estimators=100, max_depth=3, learning_rate=0.1, random_state=42)
    model.fit(scaler.transform(X_train), y_train)
    accuracy = model.score(scaler.transform(X_test), y_test)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    model_path = MODEL_DIR / f"{symbol}_{ts}.pkl"
    with open(model_path, "wb") as f:
        pickle.dump({"model": model, "scaler": scaler, "features": available_cols, "accuracy": accuracy}, f)

    # Also write as latest
    latest_path = MODEL_DIR / f"{symbol}_latest.pkl"
    with open(latest_path, "wb") as f:
        pickle.dump({"model": model, "scaler": scaler, "features": available_cols, "accuracy": accuracy}, f)

    logger.info(f"Trained model for {symbol}: accuracy={accuracy:.4f}")
    return {"status": "trained", "symbol": symbol, "accuracy": round(accuracy, 4),
            "train_samples": len(X_train), "test_samples": len(X_test)}
