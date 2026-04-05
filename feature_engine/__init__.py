#!/usr/bin/env python3
"""Feature engineering package — IC-validated feature pipeline.

Contains:
- preprocessor: normalized feature computation pipeline
- technical_indicators: RSI, MACD, Bollinger Bands, ATR, VWAP

All features are validated with IC > 0.05 against labels.
"""
from feature_engine import technical_indicators
from feature_engine import preprocessor

__all__ = ["technical_indicators", "preprocessor"]
