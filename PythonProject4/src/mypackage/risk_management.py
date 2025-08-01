"""
Risk management module for the Korean Stock Analysis System.

This module contains classes for managing risk in trading operations.
"""

import logging
from typing import Dict, Tuple

from .config import TradingSystemConfig, TradingPosition, MarketRegime, logger


class AdvancedRiskManager:
    """Enterprise-grade risk management system.
    
    This class provides methods for managing risk in trading operations,
    including position sizing, stop loss/take profit levels, and risk limits.
    """

    def __init__(self):
        """Initialize the AdvancedRiskManager."""
        self.positions: Dict[str, TradingPosition] = {}
        self.daily_pnl = 0.0
        self.portfolio_value = 1000000.0  # $1M starting capital
        self.risk_limits = TradingSystemConfig.RISK_LIMITS
        self.kill_switch_active = False
        logger.info("🛡️ Advanced Risk Manager initialized")

    def calculate_kelly_position_size(self, win_prob: float, avg_win: float, avg_loss: float,
                                      current_capital: float) -> float:
        """Calculate optimal position size using Kelly Criterion.
        
        Args:
            win_prob (float): Probability of winning (0-1).
            avg_win (float): Average win amount.
            avg_loss (float): Average loss amount.
            current_capital (float): Current capital.
            
        Returns:
            float: Optimal position size.
        """
        try:
            if win_prob <= 0 or win_prob >= 1 or avg_win <= 0 or avg_loss <= 0:
                return 0.0

            # Kelly Formula: f = (bp - q) / b
            b = avg_win / avg_loss
            p = win_prob
            q = 1 - win_prob

            kelly_fraction = (b * p - q) / b

            # Apply Kelly fraction limit
            kelly_fraction = min(kelly_fraction, self.risk_limits['kelly_fraction_limit'])
            kelly_fraction = max(kelly_fraction, 0)

            position_size = kelly_fraction * current_capital

            logger.info(f"📊 Kelly Position Size: {position_size:.2f} (fraction: {kelly_fraction:.4f})")
            return position_size

        except Exception as e:
            logger.error(f"Error calculating Kelly position size: {e}")
            return 0.0

    def dynamic_stop_loss_take_profit(self, current_price: float, entry_price: float,
                                      volatility: float, regime: MarketRegime) -> Tuple[float, float]:
        """Calculate dynamic stop loss and take profit levels based on market conditions.
        
        Args:
            current_price (float): Current price.
            entry_price (float): Entry price.
            volatility (float): Volatility.
            regime (MarketRegime): Market regime.
            
        Returns:
            Tuple[float, float]: Stop loss and take profit levels.
        """
        base_stop_loss_pct = self.risk_limits['stop_loss_pct']
        base_take_profit_pct = self.risk_limits['take_profit_pct']

        # Volatility adjustment
        vol_multiplier = 1 + (volatility - 0.2)

        # Regime-based adjustment
        regime_adjustments = {
            MarketRegime.HIGH_VOLATILITY: {'stop': 1.5, 'profit': 0.8},
            MarketRegime.LOW_VOLATILITY: {'stop': 0.7, 'profit': 1.2},
            MarketRegime.BULL: {'stop': 0.8, 'profit': 1.3},
            MarketRegime.BEAR: {'stop': 1.2, 'profit': 0.9},
            MarketRegime.SIDEWAYS: {'stop': 1.0, 'profit': 1.0}
        }

        adjustments = regime_adjustments.get(regime, {'stop': 1.0, 'profit': 1.0})

        # Calculate dynamic levels
        stop_loss_pct = base_stop_loss_pct * vol_multiplier * adjustments['stop']
        take_profit_pct = base_take_profit_pct * vol_multiplier * adjustments['profit']

        # For long positions
        stop_loss = entry_price * (1 - stop_loss_pct)
        take_profit = entry_price * (1 + take_profit_pct)

        return stop_loss, take_profit

    def check_risk_limits(self) -> Dict[str, bool]:
        """Check comprehensive risk limits.
        
        Returns:
            Dict[str, bool]: Risk status dictionary.
        """
        risk_status = {
            'daily_loss_limit': abs(self.daily_pnl) < (self.portfolio_value * self.risk_limits['max_daily_loss_pct']),
            'position_concentration': self._check_position_concentration(),
            'portfolio_risk': self._calculate_portfolio_risk() < self.risk_limits['max_portfolio_risk_pct'],
            'overall_status': True
        }

        risk_status['overall_status'] = all([
            risk_status['daily_loss_limit'],
            risk_status['position_concentration'],
            risk_status['portfolio_risk']
        ])

        return risk_status

    def _check_position_concentration(self) -> bool:
        """Check position concentration.
        
        Returns:
            bool: True if position concentration is within limits, False otherwise.
        """
        if not self.positions:
            return True

        max_position_value = max([pos.position_value for pos in self.positions.values()])
        concentration = max_position_value / self.portfolio_value

        return concentration <= self.risk_limits['max_position_size_pct']

    def _calculate_portfolio_risk(self) -> float:
        """Calculate overall portfolio risk.
        
        Returns:
            float: Portfolio risk as a fraction of portfolio value.
        """
        if not self.positions:
            return 0.0

        total_risk = sum([abs(pos.unrealized_pnl) for pos in self.positions.values()])
        return total_risk / self.portfolio_value