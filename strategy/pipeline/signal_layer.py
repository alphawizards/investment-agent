"""
Signal Layer
=============
VectorBT-powered signal generation with pluggable strategy system.
"""

import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Type
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

# Try to import vectorbt
try:
    import vectorbt as vbt
    HAS_VBT = True
except ImportError:
    HAS_VBT = False
    print("Warning: vectorbt not installed. Using fallback calculations.")

# Try to import hard asset signals
try:
    from ..hard_asset_signals import (
        HardAssetSignalManager,
        BTCVolatilityMomentum,
        GoldRegimeFilter,
        SilverGoldRatio
    )
    HAS_HARD_ASSETS = True
except ImportError:
    HAS_HARD_ASSETS = False


@dataclass
class SignalResult:
    """Result from signal generation."""
    strategy_name: str
    signals: pd.DataFrame  # columns: ticker, signal (1=buy, -1=sell, 0=hold)
    strength: pd.DataFrame  # signal strength 0-1
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class BaseStrategy(ABC):
    """
    Abstract base class for trading strategies.
    
    All strategies must implement generate_signals() method.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy name."""
        pass
    
    @property
    def description(self) -> str:
        """Strategy description."""
        return ""
    
    @abstractmethod
    def generate_signals(
        self,
        prices: pd.DataFrame,
        volume: pd.DataFrame = None,
        **kwargs
    ) -> SignalResult:
        """
        Generate trading signals.
        
        Args:
            prices: DataFrame with Close prices (columns=tickers, index=dates)
            volume: DataFrame with Volume (optional)
            **kwargs: Additional parameters
            
        Returns:
            SignalResult with signals and metadata
        """
        pass
    
    def get_parameters(self) -> Dict[str, Any]:
        """Return strategy parameters for logging."""
        return {}


class MomentumStrategy(BaseStrategy):
    """
    Momentum-based strategy (generic).
    
    Buys top N stocks by momentum over lookback period.
    """
    
    def __init__(
        self,
        lookback: int = 126,  # 6 months
        top_n: int = 5,
        min_momentum: float = 0.0
    ):
        self.lookback = lookback
        self.top_n = top_n
        self.min_momentum = min_momentum
    
    @property
    def name(self) -> str:
        return f"Momentum_{self.lookback}D"
    
    @property
    def description(self) -> str:
        return f"Top {self.top_n} stocks by {self.lookback}-day momentum"
    
    def generate_signals(
        self,
        prices: pd.DataFrame,
        volume: pd.DataFrame = None,
        **kwargs
    ) -> SignalResult:
        """Generate momentum signals."""
        
        # Calculate returns over lookback period
        returns = prices.pct_change(self.lookback)
        
        # Create signals DataFrame
        signals = pd.DataFrame(0, index=prices.index, columns=prices.columns)
        strength = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
        
        for date in prices.index[self.lookback:]:
            row_returns = returns.loc[date].dropna()
            
            if len(row_returns) == 0:
                continue
            
            # Filter by minimum momentum
            row_returns = row_returns[row_returns > self.min_momentum]
            
            # Rank and select top N
            top_tickers = row_returns.nlargest(min(self.top_n, len(row_returns))).index
            
            for ticker in top_tickers:
                signals.loc[date, ticker] = 1
                strength.loc[date, ticker] = row_returns[ticker] / row_returns.max()
        
        return SignalResult(
            strategy_name=self.name,
            signals=signals,
            strength=strength,
            metadata={
                'lookback': self.lookback,
                'top_n': self.top_n,
                'min_momentum': self.min_momentum
            }
        )
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            'lookback': self.lookback,
            'top_n': self.top_n,
            'min_momentum': self.min_momentum
        }


class DualMomentumStrategy(BaseStrategy):
    """
    Antonacci Dual Momentum Strategy.
    
    Combines absolute and relative momentum.
    """
    
    def __init__(
        self,
        lookback: int = 252,
        defensive_assets: List[str] = None,
        risk_free_rate: float = 0.04
    ):
        self.lookback = lookback
        self.defensive_assets = defensive_assets or ['TLT', 'IEF', 'BND']
        self.risk_free_rate = risk_free_rate
    
    @property
    def name(self) -> str:
        return "Dual_Momentum"
    
    @property
    def description(self) -> str:
        return "Antonacci Dual Momentum (absolute + relative)"
    
    def generate_signals(
        self,
        prices: pd.DataFrame,
        volume: pd.DataFrame = None,
        **kwargs
    ) -> SignalResult:
        """Generate dual momentum signals."""
        
        # Calculate 12-month returns
        returns = prices.pct_change(self.lookback)
        
        # Daily risk-free threshold
        rf_threshold = self.risk_free_rate * (self.lookback / 252)
        
        signals = pd.DataFrame(0, index=prices.index, columns=prices.columns)
        strength = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
        
        # Separate risky and defensive assets
        risky_assets = [c for c in prices.columns if c not in self.defensive_assets]
        
        for date in prices.index[self.lookback:]:
            row_returns = returns.loc[date].dropna()
            
            # Get best risky asset
            risky_returns = row_returns.reindex(risky_assets).dropna()
            if len(risky_returns) == 0:
                continue
            
            best_risky = risky_returns.idxmax()
            best_return = risky_returns[best_risky]
            
            # Absolute momentum check
            if best_return > rf_threshold:
                # Invest in best risky asset
                signals.loc[date, best_risky] = 1
                strength.loc[date, best_risky] = min(1.0, best_return / rf_threshold / 2)
            else:
                # Invest in best defensive asset
                defensive_returns = row_returns.reindex(self.defensive_assets).dropna()
                if len(defensive_returns) > 0:
                    best_defensive = defensive_returns.idxmax()
                    signals.loc[date, best_defensive] = 1
                    strength.loc[date, best_defensive] = 0.5
        
        return SignalResult(
            strategy_name=self.name,
            signals=signals,
            strength=strength,
            metadata={
                'lookback': self.lookback,
                'defensive_assets': self.defensive_assets,
                'risk_free_rate': self.risk_free_rate
            }
        )
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            'lookback': self.lookback,
            'defensive_assets': self.defensive_assets,
            'risk_free_rate': self.risk_free_rate
        }


class HRPStrategy(BaseStrategy):
    """
    Hierarchical Risk Parity signal strategy.
    
    Always invested (no timing), just provides allocation signals.
    """
    
    def __init__(self, rebalance_frequency: str = 'monthly'):
        self.rebalance_frequency = rebalance_frequency
    
    @property
    def name(self) -> str:
        return "HRP"
    
    @property
    def description(self) -> str:
        return "Hierarchical Risk Parity (always invested)"
    
    def generate_signals(
        self,
        prices: pd.DataFrame,
        volume: pd.DataFrame = None,
        **kwargs
    ) -> SignalResult:
        """Generate HRP signals (all assets always on)."""
        
        # For HRP, all assets are always "on"
        signals = pd.DataFrame(1, index=prices.index, columns=prices.columns)
        
        # Strength based on inverse volatility
        returns = prices.pct_change()
        rolling_vol = returns.rolling(63).std() * np.sqrt(252)
        
        # Inverse volatility as strength (higher = lower vol = stronger)
        inv_vol = 1 / rolling_vol.replace(0, np.nan)
        strength = inv_vol.div(inv_vol.sum(axis=1), axis=0).fillna(0)
        
        return SignalResult(
            strategy_name=self.name,
            signals=signals,
            strength=strength,
            metadata={
                'rebalance_frequency': self.rebalance_frequency
            }
        )
    
    def get_parameters(self) -> Dict[str, Any]:
        return {'rebalance_frequency': self.rebalance_frequency}


class SignalManager:
    """
    Manages strategy registration and signal generation.
    """
    
    def __init__(self):
        self._strategies: Dict[str, BaseStrategy] = {}
        self._results: Dict[str, SignalResult] = {}
        self._hard_asset_manager = None
        
        # Register default strategies
        self.register_strategy(MomentumStrategy(lookback=21, top_n=5))  # 1M
        self.register_strategy(MomentumStrategy(lookback=63, top_n=5))  # 3M
        self.register_strategy(MomentumStrategy(lookback=126, top_n=5))  # 6M
        self.register_strategy(DualMomentumStrategy())
        self.register_strategy(HRPStrategy())
        
        # Register hard asset signals if available
        if HAS_HARD_ASSETS:
            self._hard_asset_manager = HardAssetSignalManager()
            print("   ✓ Hard Asset Signal Manager initialized (BTC, GOLD, SILVER)")
    
    @property
    def hard_assets(self):
        """Access hard asset signal manager."""
        return self._hard_asset_manager
    
    def register_strategy(self, strategy: BaseStrategy):
        """Register a strategy."""
        self._strategies[strategy.name] = strategy
        print(f"   ✓ Registered strategy: {strategy.name}")
    
    def get_strategy(self, name: str) -> Optional[BaseStrategy]:
        """Get a strategy by name."""
        return self._strategies.get(name)
    
    def list_strategies(self) -> List[str]:
        """List all registered strategies."""
        return list(self._strategies.keys())
    
    def generate_signals(
        self,
        strategy_name: str,
        prices: pd.DataFrame,
        volume: pd.DataFrame = None,
        **kwargs
    ) -> SignalResult:
        """
        Generate signals for a specific strategy.
        """
        if strategy_name not in self._strategies:
            raise ValueError(f"Unknown strategy: {strategy_name}")
        
        strategy = self._strategies[strategy_name]
        result = strategy.generate_signals(prices, volume, **kwargs)
        
        self._results[strategy_name] = result
        return result
    
    def generate_all_signals(
        self,
        prices: pd.DataFrame,
        volume: pd.DataFrame = None,
        **kwargs
    ) -> Dict[str, SignalResult]:
        """
        Generate signals for all registered strategies.
        """
        results = {}
        
        for name, strategy in self._strategies.items():
            try:
                result = strategy.generate_signals(prices, volume, **kwargs)
                results[name] = result
                self._results[name] = result
            except Exception as e:
                print(f"   ⚠️ Error generating signals for {name}: {e}")
        
        return results
    
    def get_latest_signals(self, strategy_name: str) -> Optional[SignalResult]:
        """Get the most recently generated signals for a strategy."""
        return self._results.get(strategy_name)


# Factory function for common strategies
def create_quallamaggie_strategy(momentum_period: int = 126) -> MomentumStrategy:
    """Create a Quallamaggie-style momentum strategy."""
    return MomentumStrategy(
        lookback=momentum_period,
        top_n=10,
        min_momentum=0.0
    )
