"""
TradeView — ML Inference API (pete.local)
Serves GradientBoosting predictions via FastAPI.
Endpoint: POST /predict, POST /train/{symbol}, GET /models

Phase 2 service — extracted from monolithic backend/api/main.py.
"""

import logging
import os
import pickle
from pathlib import Path

import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from training import train as train_model

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_DIR = Path(os.environ.get("TV_MODEL_DIR", "/data/models"))
MODEL_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="TradeView ML Inference API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
Instrumentator().instrument(app).expose(app)


def load_model(symbol: str) -> dict | None:
    path = MODEL_DIR / f"{symbol}_latest.pkl"
    if not path.exists():
        return None
    with open(path, "rb") as f:
        return pickle.load(f)


@app.get("/")
def root():
    return {"name": "TradeView ML Inference API", "version": "0.1.0"}


@app.get("/models")
def list_models():
    models = []
    for p in MODEL_DIR.glob("*_latest.pkl"):
        symbol = p.stem.replace("_latest", "")
        try:
            data = pickle.load(open(p, "rb"))
            models.append({"symbol": symbol, "accuracy": data.get("accuracy")})
        except Exception:
            pass
    return {"models": models}


@app.post("/predict")
def predict(features: dict):
    """
    Accepts: {"symbol": "SPY", "features": {"RSI_14": 55.3, ...}}
    Returns: {"signal": "bullish", "confidence": 0.72}
    """
    symbol = features.get("symbol", "")
    feat_values = features.get("features", {})
    artifact = load_model(symbol)
    if artifact is None:
        return {"signal": "neutral", "confidence": 0.0, "reason": "no_model"}

    model = artifact["model"]
    scaler = artifact["scaler"]
    feature_cols = artifact["features"]

    try:
        X = np.array([[feat_values.get(c, 0.0) for c in feature_cols]])
        X_s = scaler.transform(X)
        proba = model.predict_proba(X_s)[0]
        pred = model.predict(X_s)[0]
        signal = "bullish" if pred == 1 else "bearish"
        confidence = round(float(max(proba)), 4)
        return {"signal": signal, "confidence": confidence}
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        return {"signal": "neutral", "confidence": 0.0}


@app.post("/train/{symbol}")
def train_endpoint(symbol: str):
    result = train_model(symbol)
    return result


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("TV_ML_PORT", 8766))
    uvicorn.run(app, host="0.0.0.0", port=port)
