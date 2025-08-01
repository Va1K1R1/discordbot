"""
Tests for the config module.
"""

import unittest
from datetime import datetime

from src.mypackage.config import TradingSystemConfig, TradingPosition, RiskMetrics, MarketRegime


class TestTradingSystemConfig(unittest.TestCase):
    """Tests for the TradingSystemConfig class."""

    def test_krx_trading_hours(self):
        """Test KRX trading hours configuration."""
        self.assertEqual(TradingSystemConfig.KRX_TRADING_HOURS['market_open'], '09:00')
        self.assertEqual(TradingSystemConfig.KRX_TRADING_HOURS['market_close'], '15:30')
        self.assertEqual(TradingSystemConfig.KRX_TRADING_HOURS['night_session_start'], '18:00')
        self.assertEqual(TradingSystemConfig.KRX_TRADING_HOURS['night_session_end'], '06:00')

    def test_transaction_costs(self):
        """Test transaction costs configuration."""
        self.assertEqual(TradingSystemConfig.TRANSACTION_COSTS['commission_rate'], 0.00015)
        self.assertEqual(TradingSystemConfig.TRANSACTION_COSTS['securities_tax_rate'], 0.0015)
        self.assertEqual(TradingSystemConfig.TRANSACTION_COSTS['stamp_duty_rate'], 0.0005)
        self.assertEqual(TradingSystemConfig.TRANSACTION_COSTS['exchange_fee_rate'], 0.000004)
        self.assertEqual(TradingSystemConfig.TRANSACTION_COSTS['total_cost_estimate'], 0.0035)

    def test_risk_limits(self):
        """Test risk limits configuration."""
        self.assertEqual(TradingSystemConfig.RISK_LIMITS['max_daily_loss_pct'], 0.02)
        self.assertEqual(TradingSystemConfig.RISK_LIMITS['max_position_size_pct'], 0.10)
        self.assertEqual(TradingSystemConfig.RISK_LIMITS['max_portfolio_risk_pct'], 0.15)
        self.assertEqual(TradingSystemConfig.RISK_LIMITS['kelly_fraction_limit'], 0.25)
        self.assertEqual(TradingSystemConfig.RISK_LIMITS['stop_loss_pct'], 0.05)
        self.assertEqual(TradingSystemConfig.RISK_LIMITS['take_profit_pct'], 0.15)


class TestTradingPosition(unittest.TestCase):
    """Tests for the TradingPosition class."""

    def test_trading_position_creation(self):
        """Test creating a TradingPosition instance."""
        position = TradingPosition(
            symbol="005930.KS",
            quantity=100,
            entry_price=70000.0,
            current_price=72000.0,
            entry_time=datetime.now(),
            stop_loss=65000.0,
            take_profit=80000.0,
            unrealized_pnl=200000.0,
            position_value=7200000.0
        )
        
        self.assertEqual(position.symbol, "005930.KS")
        self.assertEqual(position.quantity, 100)
        self.assertEqual(position.entry_price, 70000.0)
        self.assertEqual(position.current_price, 72000.0)
        self.assertEqual(position.stop_loss, 65000.0)
        self.assertEqual(position.take_profit, 80000.0)
        self.assertEqual(position.unrealized_pnl, 200000.0)
        self.assertEqual(position.position_value, 7200000.0)


class TestMarketRegime(unittest.TestCase):
    """Tests for the MarketRegime enum."""

    def test_market_regime_values(self):
        """Test MarketRegime enum values."""
        self.assertEqual(MarketRegime.BULL.value, "bull")
        self.assertEqual(MarketRegime.BEAR.value, "bear")
        self.assertEqual(MarketRegime.HIGH_VOLATILITY.value, "high_vol")
        self.assertEqual(MarketRegime.LOW_VOLATILITY.value, "low_vol")
        self.assertEqual(MarketRegime.SIDEWAYS.value, "sideways")


if __name__ == '__main__':
    unittest.main()