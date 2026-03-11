-- TradeView TimescaleDB schema

CREATE TABLE IF NOT EXISTS ohlcv (
    time        TIMESTAMPTZ     NOT NULL,
    symbol      TEXT            NOT NULL,
    open        DOUBLE PRECISION,
    high        DOUBLE PRECISION,
    low         DOUBLE PRECISION,
    close       DOUBLE PRECISION,
    volume      BIGINT
);

SELECT create_hypertable('ohlcv', 'time', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol ON ohlcv (symbol, time DESC);

-- Continuous aggregate for daily OHLCV summary
CREATE MATERIALIZED VIEW IF NOT EXISTS ohlcv_daily
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', time) AS bucket,
    symbol,
    first(open, time)  AS open,
    max(high)          AS high,
    min(low)           AS low,
    last(close, time)  AS close,
    sum(volume)        AS volume
FROM ohlcv
GROUP BY bucket, symbol
WITH NO DATA;
