"""
Configuration module for the Korean Stock Analysis System.

This module contains configuration classes and data structures used throughout the system.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Enhanced logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataSource(Enum):
    """Data source enumeration."""
    PYKRX = "pykrx"
    FDR = "financedatareader" 
    KRX_WEB = "krx_web"
    YFINANCE = "yfinance"
    CSV_FILE = "csv_file"


@dataclass
class StockInfo:
    """Stock information data class."""
    code: str
    name: str
    market: str = ""
    sector: str = ""
    listing_date: str = ""


@dataclass
class AnalysisConfig:
    """Analysis configuration."""
    analysis_period: str = "1y"
    risk_free_rate: float = 0.03
    max_workers: int = 10
    contamination: float = 0.1
    save_results: bool = True


class TradingSystemConfig:
    """Production system configuration"""

    # Korean Market Configuration
    KRX_TRADING_HOURS = {
        'market_open': '09:00',
        'market_close': '15:30',
        'night_session_start': '18:00',
        'night_session_end': '06:00'
    }

    # Transaction Costs (Korean Market 2025)
    TRANSACTION_COSTS = {
        'commission_rate': 0.00015,  # 0.015%
        'securities_tax_rate': 0.0015,  # 0.15% on sales
        'stamp_duty_rate': 0.0005,  # 0.05%
        'exchange_fee_rate': 0.000004,  # 0.0004%
        'total_cost_estimate': 0.0035  # 35 basis points total
    }

    # Risk Management Parameters
    RISK_LIMITS = {
        'max_daily_loss_pct': 0.02,  # 2% daily loss limit
        'max_position_size_pct': 0.10,  # 10% max position concentration
        'max_portfolio_risk_pct': 0.15,  # 15% portfolio risk cap
        'kelly_fraction_limit': 0.25,  # Maximum Kelly fraction
        'stop_loss_pct': 0.05,  # 5% stop loss
        'take_profit_pct': 0.15  # 15% take profit
    }


@dataclass
class TradingPosition:
    """Trading position data class"""
    symbol: str
    quantity: int
    entry_price: float
    current_price: float
    entry_time: datetime
    stop_loss: float
    take_profit: float
    unrealized_pnl: float
    position_value: float


@dataclass
class RiskMetrics:
    """Risk management metrics"""
    portfolio_value: float
    daily_pnl: float
    var_95: float  # Value at Risk 95%
    max_drawdown: float
    sharpe_ratio: float
    kelly_fraction: float
    position_concentration: Dict[str, float]


class MarketRegime(Enum):
    """Market regime classification"""
    BULL = "bull"
    BEAR = "bear"
    HIGH_VOLATILITY = "high_vol"
    LOW_VOLATILITY = "low_vol"
    SIDEWAYS = "sideways"
