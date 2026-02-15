"""
Strategy Parameter Schemas
==========================
Pydantic models for validating strategy and backtest parameters.
"""

from datetime import date
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator, model_validator
import re


class BacktestParams(BaseModel):
    """Parameters for running a backtest."""
    
    initial_capital: float = Field(
        default=100000.0,
        ge=1000,
        le=100_000_000,
        description="Starting capital in USD/AUD"
    )
    start_date: str = Field(
        description="Backtest start date (YYYY-MM-DD)"
    )
    end_date: Optional[str] = Field(
        default=None,
        description="Backtest end date (YYYY-MM-DD), defaults to today"
    )
    rebalance_frequency: Literal["daily", "weekly", "monthly"] = Field(
        default="monthly",
        description="Portfolio rebalancing frequency"
    )
    
    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', v):
            raise ValueError('Date must be in YYYY-MM-DD format')
        return v
    
    @model_validator(mode='after')
    def validate_date_range(self):
        if self.end_date and self.start_date > self.end_date:
            raise ValueError('start_date must be before end_date')
        return self


class ScannerParams(BaseModel):
    """Parameters for stock scanning/screening."""
    
    lookback_days: int = Field(
        default=252,
        ge=20,
        le=1260,
        description="Number of trading days to analyze (20-1260)"
    )
    min_volume: int = Field(
        default=100000,
        ge=0,
        le=1_000_000_000,
        description="Minimum average daily volume"
    )
    max_results: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of results to return"
    )
    include_etfs: bool = Field(
        default=True,
        description="Include ETFs in scan results"
    )


class MomentumStrategyParams(BaseModel):
    """Parameters for momentum-based strategies."""
    
    lookback_period: int = Field(
        default=12,
        ge=1,
        le=36,
        description="Momentum lookback in months"
    )
    top_n: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of top assets to select"
    )
    skip_recent: int = Field(
        default=1,
        ge=0,
        le=6,
        description="Months to skip for momentum calculation (e.g., skip=1 uses 12-1 month return)"
    )


class RiskParityParams(BaseModel):
    """Parameters for risk parity / inverse volatility strategies."""
    
    lookback_days: int = Field(
        default=60,
        ge=20,
        le=252,
        description="Volatility calculation window"
    )
    max_weight: float = Field(
        default=0.25,
        ge=0.01,
        le=1.0,
        description="Maximum weight per asset (1.0 = no limit)"
    )
    min_weight: float = Field(
        default=0.0,
        ge=0.0,
        le=0.5,
        description="Minimum weight per asset"
    )
    
    @model_validator(mode='after')
    def validate_weights(self):
        if self.min_weight > self.max_weight:
            raise ValueError('min_weight must be <= max_weight')
        return self


class RegimeDetectionParams(BaseModel):
    """Parameters for regime detection strategies."""
    
    n_regimes: int = Field(
        default=2,
        ge=2,
        le=5,
        description="Number of market regimes to detect"
    )
    lookback_days: int = Field(
        default=252,
        ge=60,
        le=1260,
        description="Historical window for regime estimation"
    )
    transition_buffer: int = Field(
        default=5,
        ge=0,
        le=20,
        description="Days to wait before confirming regime change"
    )


class OLMARParams(BaseModel):
    """Parameters for OLMAR mean-reversion strategy."""
    
    window: int = Field(
        default=5,
        ge=2,
        le=30,
        description="Price prediction window"
    )
    epsilon: float = Field(
        default=10.0,
        ge=1.0,
        le=100.0,
        description="Reversion threshold parameter"
    )


class ComparisonRequest(BaseModel):
    """Request model for strategy comparison."""
    
    strategy_ids: List[str] = Field(
        min_length=1,
        max_length=10,
        description="List of strategy IDs to compare"
    )
    start_date: str = Field(
        description="Comparison start date (YYYY-MM-DD)"
    )
    end_date: Optional[str] = Field(
        default=None,
        description="Comparison end date (YYYY-MM-DD)"
    )
    initial_capital: float = Field(
        default=100000.0,
        ge=1000,
        le=100_000_000
    )
    
    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', v):
            raise ValueError('Date must be in YYYY-MM-DD format')
        return v
