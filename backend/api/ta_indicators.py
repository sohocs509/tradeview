"""
Technical analysis indicators to replace pandas-ta.
Implements the required TA methods as a DataFrame accessor.
"""
import pandas as pd
import numpy as np


class TAAccessor:
    """Pandas DataFrame accessor for technical indicators."""

    def __init__(self, pandas_obj):
        self._obj = pandas_obj

    def sma(self, length=20, append=True):
        """Simple Moving Average"""
        col_name = f'SMA_{length}'
        self._obj[col_name] = self._obj['close'].rolling(window=length).mean()
        return self._obj if append else None

    def ema(self, length=12, append=True):
        """Exponential Moving Average"""
        col_name = f'EMA_{length}'
        self._obj[col_name] = self._obj['close'].ewm(span=length, adjust=False).mean()
        return self._obj if append else None

    def rsi(self, length=14, append=True):
        """Relative Strength Index"""
        col_name = f'RSI_{length}'
        delta = self._obj['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=length).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=length).mean()
        rs = gain / loss
        self._obj[col_name] = 100 - (100 / (1 + rs))
        return self._obj if append else None

    def macd(self, fast=12, slow=26, signal=9, append=True):
        """MACD"""
        ema_fast = self._obj['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = self._obj['close'].ewm(span=slow, adjust=False).mean()
        self._obj['MACD'] = ema_fast - ema_slow
        self._obj['MACD_signal'] = self._obj['MACD'].ewm(span=signal, adjust=False).mean()
        self._obj['MACD_hist'] = self._obj['MACD'] - self._obj['MACD_signal']
        return self._obj if append else None

    def stoch(self, high_col='high', low_col='low', close_col='close', length=14, append=True, **kwargs):
        """Stochastic Oscillator"""
        lowest_low = self._obj[low_col].rolling(window=length).min()
        highest_high = self._obj[high_col].rolling(window=length).max()
        self._obj['STOCH_K'] = 100 * (self._obj[close_col] - lowest_low) / (highest_high - lowest_low)
        self._obj['STOCH_D'] = self._obj['STOCH_K'].rolling(window=3).mean()
        return self._obj if append else None

    def bbands(self, length=20, std=2, append=True):
        """Bollinger Bands"""
        sma = self._obj['close'].rolling(window=length).mean()
        std_dev = self._obj['close'].rolling(window=length).std()
        self._obj[f'BB_upper_{length}'] = sma + (std_dev * std)
        self._obj[f'BB_middle_{length}'] = sma
        self._obj[f'BB_lower_{length}'] = sma - (std_dev * std)
        return self._obj if append else None

    def atr(self, length=14, append=True):
        """Average True Range"""
        tr0 = abs(self._obj['high'] - self._obj['low'])
        tr1 = abs(self._obj['high'] - self._obj['close'].shift())
        tr2 = abs(self._obj['low'] - self._obj['close'].shift())
        tr = pd.concat([tr0, tr1, tr2], axis=1).max(axis=1)
        self._obj[f'ATR_{length}'] = tr.rolling(window=length).mean()
        return self._obj if append else None

    def obv(self, append=True):
        """On-Balance Volume"""
        obv = [0] * len(self._obj)
        for i in range(1, len(self._obj)):
            if self._obj['close'].iloc[i] > self._obj['close'].iloc[i-1]:
                obv[i] = obv[i-1] + self._obj['volume'].iloc[i]
            elif self._obj['close'].iloc[i] < self._obj['close'].iloc[i-1]:
                obv[i] = obv[i-1] - self._obj['volume'].iloc[i]
            else:
                obv[i] = obv[i-1]
        self._obj['OBV'] = obv
        return self._obj if append else None

    def vwap(self, append=True):
        """Volume-Weighted Average Price"""
        tp = (self._obj['high'] + self._obj['low'] + self._obj['close']) / 3
        self._obj['VWAP'] = (tp * self._obj['volume']).cumsum() / self._obj['volume'].cumsum()
        return self._obj if append else None


# Register the accessor with pandas
pd.api.extensions.register_dataframe_accessor('ta')(TAAccessor)
