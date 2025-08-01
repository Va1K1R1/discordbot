"""
Feature engineering module for the Korean Stock Analysis System.

This module contains classes for creating advanced features from stock data.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional

from .config import MarketRegime, logger


class SmartFeatureEngineering:
    """Smart feature engineering for stock data.
    
    This class provides methods for creating advanced features from stock data,
    including market regime detection and interaction features.
    """

    @staticmethod
    def detect_market_regimes(data):
        """Detect market regimes.
        
        Args:
            data (pd.DataFrame): Stock price data.
            
        Returns:
            pd.DataFrame: DataFrame with market regime indicators.
        """
        df = data.copy()

        # Volatility regime
        returns = df['Close'].pct_change().fillna(0)
        volatility = returns.rolling(20).std()

        # High/low volatility regime
        vol_threshold = volatility.rolling(252).quantile(0.7)  # 1-year basis, 70th percentile
        df['High_Vol_Regime'] = (volatility > vol_threshold).astype(int)

        # Trend regime (based on 20-day/50-day moving averages)
        if 'EMA_20' in df.columns and 'EMA_50' in df.columns:
            df['Bull_Regime'] = (df['EMA_20'] > df['EMA_50']).astype(int)
            df['Bear_Regime'] = (df['EMA_20'] < df['EMA_50']).astype(int)

        # Price position (relative to 52-week high/low)
        high_52w = df['High'].rolling(252).max()
        low_52w = df['Low'].rolling(252).min()
        df['Price_Position_52W'] = (df['Close'] - low_52w) / (high_52w - low_52w + 1e-10)

        # Volume regime
        volume_ma = df['Volume'].rolling(50).mean()
        df['High_Volume_Regime'] = (df['Volume'] > volume_ma * 1.5).astype(int)

        return df

    @staticmethod
    def create_interaction_features(data):
        """Create interaction features.
        
        Args:
            data (pd.DataFrame): Stock price data with technical indicators.
            
        Returns:
            pd.DataFrame: DataFrame with interaction features.
        """
        df = data.copy()

        # Price-volume interaction
        if 'Volume' in df.columns:
            # Rolling correlation between price and volume
            for period in [10, 20]:
                price_vol_corr = df['Close'].rolling(period).corr(df['Volume'])
                df[f'Price_Volume_Corr_{period}'] = price_vol_corr.fillna(0)

        # RSI and Bollinger Bands combination
        if 'RSI_14' in df.columns and 'BB_Position' in df.columns:
            df['RSI_BB_Combined'] = df['RSI_14'] * df['BB_Position']

        # MACD and price momentum combination
        if 'MACD' in df.columns and 'Price_Momentum_10' in df.columns:
            df['MACD_Momentum_Combined'] = df['MACD'] * df['Price_Momentum_10']

        # EMA slope combination
        ema_slopes = [col for col in df.columns if 'EMA' in col and 'slope' in col]
        if len(ema_slopes) >= 2:
            df['EMA_Slope_Convergence'] = df[ema_slopes[0]] - df[ema_slopes[-1]]

        return df

    @staticmethod
    def create_regime_dependent_features(data):
        """Create regime-dependent features.
        
        Args:
            data (pd.DataFrame): Stock price data with regime indicators.
            
        Returns:
            pd.DataFrame: DataFrame with regime-dependent features.
        """
        df = data.copy()

        # Regime-dependent RSI adjustment
        if 'RSI_14' in df.columns and 'High_Vol_Regime' in df.columns:
            # Adjust RSI thresholds in high volatility regime
            df['Adaptive_RSI_Signal'] = np.where(
                df['High_Vol_Regime'] == 1,
                np.where(df['RSI_14'] > 85, 1, np.where(df['RSI_14'] < 15, -1, 0)),
                np.where(df['RSI_14'] > 70, 1, np.where(df['RSI_14'] < 30, -1, 0))
            )

        # Regime-dependent momentum adjustment
        if 'Price_Momentum_10' in df.columns and 'High_Vol_Regime' in df.columns:
            df['Adaptive_Momentum'] = np.where(
                df['High_Vol_Regime'] == 1,
                df['Price_Momentum_10'] * 0.5,  # Weaken momentum signals in high volatility
                df['Price_Momentum_10'] * 1.2   # Strengthen momentum signals in low volatility
            )

        return df