"""
TradeView — Data Ingestion Service (otto.local)
Fetches OHLCV data from yfinance, persists to TimescaleDB,
and publishes price updates to Valkey pub/sub.

Phase 2 service — extracted from monolithic backend/api/main.py.
"""

import asyncio
import logging
import os
from datetime import datetime

import pandas as pd
import yfinance as yf

from publisher import ValkeyPublisher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_HOST = os.environ.get("TV_DB_HOST", "localhost")
DB_PORT = int(os.environ.get("TV_DB_PORT", 5432))
DB_USER = os.environ.get("TV_DB_USER", "tradeview")
DB_PASSWORD = os.environ.get("TV_DB_PASSWORD", "")
DB_NAME = os.environ.get("TV_DB_NAME", "tradeview")
FETCH_INTERVAL = int(os.environ.get("TV_FETCH_INTERVAL", 300))  # seconds

WATCHLIST = [
    "SPY", "QQQ", "AAPL", "MSFT", "GOOGL",
    "AMZN", "TSLA", "BTC-USD", "ETH-USD", "GC=F", "CL=F",
]


def get_db_conn():
    import psycopg2
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_USER, password=DB_PASSWORD, dbname=DB_NAME,
    )


def fetch_and_store(symbol: str, publisher: ValkeyPublisher) -> None:
    logger.info(f"Fetching {symbol}")
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="5d", interval="1d")
    if df.empty:
        logger.warning(f"No data for {symbol}")
        return

    df.index = pd.to_datetime(df.index, utc=True)
    df = df.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]]

    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            for ts, row in df.iterrows():
                cur.execute(
                    """
                    INSERT INTO ohlcv (time, symbol, open, high, low, close, volume)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (ts, symbol, row.open, row.high, row.low, row.close, int(row.volume)),
                )
        conn.commit()
        logger.info(f"Stored {len(df)} rows for {symbol}")

        # Publish latest close to Valkey
        latest = df.iloc[-1]
        publisher.publish(symbol, {
            "symbol": symbol,
            "time": df.index[-1].isoformat(),
            "open": float(latest.open),
            "high": float(latest.high),
            "low": float(latest.low),
            "close": float(latest.close),
            "volume": int(latest.volume),
        })
    finally:
        conn.close()


async def run_loop() -> None:
    publisher = ValkeyPublisher()
    while True:
        for symbol in WATCHLIST:
            try:
                fetch_and_store(symbol, publisher)
            except Exception as e:
                logger.error(f"Error fetching {symbol}: {e}")
        logger.info(f"Cycle complete. Sleeping {FETCH_INTERVAL}s.")
        await asyncio.sleep(FETCH_INTERVAL)


if __name__ == "__main__":
    asyncio.run(run_loop())
