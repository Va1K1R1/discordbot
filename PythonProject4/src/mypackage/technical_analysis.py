"""
Technical analysis module for the Korean Stock Analysis System.

This module contains classes for performing technical analysis on stock data.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional

from .config import logger


class AdvancedTechnicalAnalyzer:
    """Advanced technical analyzer for stock data.
    
    This class provides methods for calculating various technical indicators
    and market structure indicators.
    """

    @staticmethod
    def calculate_market_structure_indicators(data):
        """Calculate market structure indicators.
        
        Args:
            data (pd.DataFrame): Stock price data.
            
        Returns:
            pd.DataFrame: DataFrame with market structure indicators.
        """
        df = data.copy()

        # Advanced moving average system
        periods = [5, 10, 20, 50, 100, 200]
        for period in periods:
            if len(df) > period:
                # EMA
                df[f'EMA_{period}'] = df['Close'].ewm(span=period, adjust=False).mean()

                # EMA slope (momentum)
                df[f'EMA_{period}_slope'] = df[f'EMA_{period}'].diff() / df[f'EMA_{period}']

                # Distance between price and EMA
                df[f'Price_EMA_{period}_dist'] = (df['Close'] - df[f'EMA_{period}']) / df[f'EMA_{period}']

        # Moving average alignment score
        ma_score = 0
        for i, period in enumerate(periods[:-1]):
            next_period = periods[i + 1]
            if f'EMA_{period}' in df.columns and f'EMA_{next_period}' in df.columns:
                ma_score += (df[f'EMA_{period}'] > df[f'EMA_{next_period}']).astype(int)

        df['MA_Alignment_Score'] = ma_score / (len(periods) - 1)

        # Advanced RSI variants
        for period in [14, 21]:
            if len(df) > period:
                delta = df['Close'].diff()
                gain = delta.where(delta > 0, 0).rolling(period, min_periods=1).mean()
                loss = -delta.where(delta < 0, 0).rolling(period, min_periods=1).mean()
                rs = gain / (loss + 1e-10)
                rsi = 100 - (100 / (1 + rs))
                df[f'RSI_{period}'] = rsi

                # RSI divergence detection
                df[f'RSI_{period}_divergence'] = (
                        (df['Close'].diff() > 0) & (rsi.diff() < 0) |
                        (df['Close'].diff() < 0) & (rsi.diff() > 0)
                ).astype(int)

        # Bollinger Bands advanced analysis
        if len(df) > 20:
            bb_period = 20
            bb_std = 2

            sma = df['Close'].rolling(bb_period).mean()
            std = df['Close'].rolling(bb_period).std()

            df['BB_Upper'] = sma + (std * bb_std)
            df['BB_Lower'] = sma - (std * bb_std)
            df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / sma
            df['BB_Position'] = (df['Close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])

            # Bollinger Bands compression/expansion
            df['BB_Squeeze'] = (df['BB_Width'] < df['BB_Width'].rolling(50).quantile(0.2)).astype(int)  
            df['BB_Expansion'] = (df['BB_Width'] > df['BB_Width'].rolling(50).quantile(0.8)).astype(int)

        # Advanced MACD
        if len(df) > 26:
            exp1 = df['Close'].ewm(span=12).mean()
            exp2 = df['Close'].ewm(span=26).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9).mean()
            histogram = macd - signal

            df['MACD'] = macd
            df['MACD_Signal'] = signal
            df['MACD_Histogram'] = histogram

            # MACD divergence
            df['MACD_Bullish_Divergence'] = (
                    (df['Close'].diff() < 0) & (macd.diff() > 0)
            ).astype(int)
            df['MACD_Bearish_Divergence'] = (
                    (df['Close'].diff() > 0) & (macd.diff() < 0)
            ).astype(int)

        # Stochastic Oscillator
        if len(df) > 14:
            low_14 = df['Low'].rolling(14).min()
            high_14 = df['High'].rolling(14).max()
            k_percent = 100 * ((df['Close'] - low_14) / (high_14 - low_14 + 1e-10))
            d_percent = k_percent.rolling(3).mean()

            df['Stoch_K'] = k_percent
            df['Stoch_D'] = d_percent
            df['Stoch_Overbought'] = (k_percent > 80).astype(int)
            df['Stoch_Oversold'] = (k_percent < 20).astype(int)

        return df.fillna(method='ffill').fillna(0)

    @staticmethod
    def calculate_momentum_indicators(data):
        """Calculate momentum indicators.
        
        Args:
            data (pd.DataFrame): Stock price data.
            
        Returns:
            pd.DataFrame: DataFrame with momentum indicators.
        """
        df = data.copy()

        # Various momentum periods
        for period in [1, 3, 5, 10, 20, 50]:
            if len(df) > period:
                # Price momentum
                df[f'Price_Momentum_{period}'] = df['Close'].pct_change(period)

                # Volume momentum
                df[f'Volume_Momentum_{period}'] = df['Volume'].pct_change(period)

                # Price-volume combined momentum
                df[f'PV_Momentum_{period}'] = (
                        df[f'Price_Momentum_{period}'] * df[f'Volume_Momentum_{period}']
                ).fillna(0)

        # ROC (Rate of Change)
        for period in [10, 20]:
            if len(df) > period:
                df[f'ROC_{period}'] = ((df['Close'] - df['Close'].shift(period)) /
                                       df['Close'].shift(period)) * 100

        # Volatility-adjusted momentum
        for period in [10, 20]:
            if len(df) > period:
                returns = df['Close'].pct_change()
                volatility = returns.rolling(period).std()
                df[f'Vol_Adj_Momentum_{period}'] = (
                        returns.rolling(period).mean() / (volatility + 1e-10)
                )

        return df.fillna(0)