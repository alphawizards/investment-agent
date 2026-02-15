"""
Residual Momentum Strategy
==========================
Factor-neutral momentum using Fama-French regression residuals.

This module implements Residual Momentum as described in:
Blitz, Huij, and Martens (2011) - "Residual Momentum"

Key Concept:
    Instead of ranking stocks by total returns (which includes market beta,
    size, and value exposures), we rank by the RESIDUAL returns after
    regressing out these systematic factors. This isolates the pure
    behavioral momentum anomaly.

Formula:
    R_i,t = α_i + β_MKT * MKT_t + β_SMB * SMB_t + β_HML * HML_t + ε_i,t
    
    Residual Score = Σ(ε_i) / σ(ε_i)  over formation period

Usage:
    rm = ResidualMomentum(lookback_months=36)
    scores = rm.calculate_scores(returns, factors)
    top_stocks = rm.get_top_n(scores, n=10)
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass
import warnings

warnings.filterwarnings('ignore')

try:
    from statsmodels.regression.linear_model import OLS
    from statsmodels.tools import add_constant
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False
    print("Warning: statsmodels not installed. Install with: pip install statsmodels")

from .fama_french_loader import FamaFrenchLoader


@dataclass
class ResidualMomentumResult:
    """
    Result container for Residual Momentum calculations.
    
    Attributes:
        scores: DataFrame of residual momentum scores (tickers x dates)
        rankings: DataFrame of rankings (1 = highest score)
        factor_exposures: Dict of factor beta estimates per ticker
        residuals: DataFrame of regression residuals
        metadata: Additional calculation metadata
    """
    scores: pd.DataFrame
    rankings: pd.DataFrame
    factor_exposures: Dict[str, Dict[str, float]]
    residuals: pd.DataFrame
    metadata: Dict


class ResidualMomentum:
    """
    Residual Momentum strategy implementation.
    
    This strategy ranks stocks by their idiosyncratic (residual) momentum
    after controlling for Fama-French factors. It provides "purer" momentum
    exposure without the beta contamination of traditional momentum.
    
    Key advantages over total return momentum:
    1. Higher Sharpe ratio (cleaner signal)
    2. No momentum crashes (not structurally long high-beta stocks)
    3. More consistent across market environments
    
    Attributes:
        lookback_months: Formation period for regression (default: 36)
        scoring_months: Period for residual scoring (default: 12)
        min_observations: Minimum observations required for regression
    """
    
    def __init__(
        self,
        lookback_months: int = 36,
        scoring_months: int = 12,
        min_observations: int = 24,
        skip_recent_month: bool = True
    ):
        """
        Initialize Residual Momentum calculator.
        
        Args:
            lookback_months: Months of data for factor regression (default: 36)
            scoring_months: Months of residuals for scoring (default: 12)
            min_observations: Minimum observations for valid regression
            skip_recent_month: Skip most recent month (momentum reversal effect)
        """
        if not HAS_STATSMODELS:
            raise ImportError(
                "statsmodels is required for Residual Momentum. "
                "Install with: pip install statsmodels"
            )
        
        self.lookback_months = lookback_months
        self.scoring_months = scoring_months
        self.min_observations = min_observations
        self.skip_recent_month = skip_recent_month
        
        # Fama-French loader for factor data
        self.ff_loader = FamaFrenchLoader()
    
    def _align_data(
        self,
        stock_returns: pd.DataFrame,
        factors: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Align stock returns with factor data on common dates.
        
        Args:
            stock_returns: DataFrame of stock returns (dates x tickers)
            factors: DataFrame of factor returns
            
        Returns:
            Tuple of aligned (stock_returns, factors)
        """
        # Get common dates
        common_dates = stock_returns.index.intersection(factors.index)
        
        if len(common_dates) < self.min_observations:
            raise ValueError(
                f"Insufficient overlapping dates: {len(common_dates)} < {self.min_observations}"
            )
        
        stock_returns = stock_returns.loc[common_dates]
        factors = factors.loc[common_dates]
        
        return stock_returns, factors
    
    def _run_factor_regression(
        self,
        stock_returns: pd.Series,
        factors: pd.DataFrame
    ) -> Tuple[pd.Series, Dict[str, float], Dict]:
        """
        Run Fama-French 3-factor regression for a single stock.
        
        Model: R_i - RF = α + β_MKT * (MKT-RF) + β_SMB * SMB + β_HML * HML + ε
        
        Args:
            stock_returns: Series of stock returns
            factors: DataFrame with Mkt-RF, SMB, HML, RF columns
            
        Returns:
            Tuple of (residuals, factor_betas, regression_stats)
        """
        # Calculate excess returns
        if 'RF' in factors.columns:
            excess_returns = stock_returns - factors['RF']
        else:
            excess_returns = stock_returns
        
        # Prepare factor matrix
        factor_cols = ['Mkt-RF', 'SMB', 'HML']
        available_cols = [c for c in factor_cols if c in factors.columns]
        X = factors[available_cols]
        X = add_constant(X)
        
        # Drop NaN values
        valid_mask = ~(excess_returns.isna() | X.isna().any(axis=1))
        X_clean = X[valid_mask]
        y_clean = excess_returns[valid_mask]
        
        if len(y_clean) < self.min_observations:
            # Not enough data - return NaN
            return pd.Series(dtype=float), {}, {'valid': False}
        
        # Run OLS regression
        model = OLS(y_clean, X_clean)
        results = model.fit()
        
        # Extract residuals
        residuals = pd.Series(results.resid, index=y_clean.index)
        
        # Extract factor betas
        betas = {
            'alpha': results.params.get('const', np.nan),
            'beta_mkt': results.params.get('Mkt-RF', np.nan),
            'beta_smb': results.params.get('SMB', np.nan),
            'beta_hml': results.params.get('HML', np.nan),
        }
        
        # Regression statistics
        stats = {
            'valid': True,
            'r_squared': results.rsquared,
            'adj_r_squared': results.rsquared_adj,
            'n_observations': len(y_clean),
            'residual_std': residuals.std(),
        }
        
        return residuals, betas, stats
    
    def _calculate_residual_score(
        self,
        residuals: pd.Series,
        scoring_periods: int
    ) -> float:
        """
        Calculate residual momentum score.
        
        Score = Cumulative Residual Returns / Residual Volatility
        
        This standardizes the residual returns by their volatility,
        preventing high-volatility stocks from dominating the rankings.
        
        Args:
            residuals: Series of regression residuals
            scoring_periods: Number of periods to use for scoring
            
        Returns:
            Residual momentum score (higher = stronger momentum)
        """
        if len(residuals) < scoring_periods:
            return np.nan
        
        # Use most recent scoring_periods (skip last if configured)
        if self.skip_recent_month:
            recent_residuals = residuals.iloc[-(scoring_periods + 1):-1]
        else:
            recent_residuals = residuals.iloc[-scoring_periods:]
        
        # Cumulative residual return
        cumulative_return = recent_residuals.sum()
        
        # Residual volatility (use full period for stability)
        volatility = residuals.std()
        
        if volatility == 0 or np.isnan(volatility):
            return np.nan
        
        # Residual score = cumulative / volatility
        score = cumulative_return / volatility
        
        return score
    
    def calculate_scores(
        self,
        stock_returns: pd.DataFrame,
        factors: Optional[pd.DataFrame] = None,
        as_of_date: Optional[str] = None
    ) -> ResidualMomentumResult:
        """
        Calculate residual momentum scores for all stocks.
        
        Args:
            stock_returns: Monthly returns (dates x tickers)
            factors: Optional pre-loaded factor data
            as_of_date: Calculate scores as of this date (default: latest)
            
        Returns:
            ResidualMomentumResult with scores, rankings, and metadata
        """
        # Load factor data if not provided
        if factors is None:
            start_date = stock_returns.index[0] - pd.DateOffset(months=1)
            end_date = stock_returns.index[-1] + pd.DateOffset(months=1)
            factors = self.ff_loader.get_monthly_factors(
                start_date=str(start_date.date()),
                end_date=str(end_date.date())
            )
        
        # Align data
        stock_returns, factors = self._align_data(stock_returns, factors)
        
        # Determine as_of_date
        if as_of_date:
            as_of = pd.to_datetime(as_of_date)
        else:
            as_of = stock_returns.index[-1]
        
        # Filter to lookback period
        start_lookback = as_of - pd.DateOffset(months=self.lookback_months)
        stock_returns_period = stock_returns[(stock_returns.index >= start_lookback) & 
                                              (stock_returns.index <= as_of)]
        factors_period = factors[(factors.index >= start_lookback) & 
                                  (factors.index <= as_of)]
        
        # Calculate scores for each stock
        scores = {}
        factor_exposures = {}
        all_residuals = {}
        
        for ticker in stock_returns_period.columns:
            returns = stock_returns_period[ticker].dropna()
            
            if len(returns) < self.min_observations:
                scores[ticker] = np.nan
                continue
            
            # Align with factors
            common = returns.index.intersection(factors_period.index)
            if len(common) < self.min_observations:
                scores[ticker] = np.nan
                continue
            
            # Run regression
            residuals, betas, stats = self._run_factor_regression(
                returns.loc[common],
                factors_period.loc[common]
            )
            
            if not stats.get('valid', False):
                scores[ticker] = np.nan
                continue
            
            # Calculate score
            score = self._calculate_residual_score(residuals, self.scoring_months)
            
            scores[ticker] = score
            factor_exposures[ticker] = betas
            all_residuals[ticker] = residuals
        
        # Convert to DataFrames
        scores_df = pd.DataFrame({as_of: scores}).T
        rankings_df = scores_df.rank(axis=1, ascending=False)
        residuals_df = pd.DataFrame(all_residuals)
        
        # Metadata
        metadata = {
            'as_of_date': as_of,
            'lookback_months': self.lookback_months,
            'scoring_months': self.scoring_months,
            'n_stocks_scored': (~scores_df.iloc[0].isna()).sum(),
            'n_stocks_total': len(scores_df.columns),
        }
        
        return ResidualMomentumResult(
            scores=scores_df,
            rankings=rankings_df,
            factor_exposures=factor_exposures,
            residuals=residuals_df,
            metadata=metadata
        )
    
    def calculate_rolling_scores(
        self,
        stock_returns: pd.DataFrame,
        factors: Optional[pd.DataFrame] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        frequency: str = 'M'
    ) -> pd.DataFrame:
        """
        Calculate rolling residual momentum scores over time.
        
        Args:
            stock_returns: Monthly returns (dates x tickers)
            factors: Optional pre-loaded factor data
            start_date: Start date for rolling window
            end_date: End date for rolling window
            frequency: Rebalancing frequency ('M' for monthly, 'Q' for quarterly)
            
        Returns:
            DataFrame of rolling scores (dates x tickers)
        """
        # Load factors if needed
        if factors is None:
            factors = self.ff_loader.get_monthly_factors()
        
        # Align data
        stock_returns, factors = self._align_data(stock_returns, factors)
        
        # Determine date range
        if start_date:
            start = pd.to_datetime(start_date)
        else:
            start = stock_returns.index[self.lookback_months]
        
        if end_date:
            end = pd.to_datetime(end_date)
        else:
            end = stock_returns.index[-1]
        
        # Generate rebalance dates
        rebalance_dates = pd.date_range(start, end, freq=frequency)
        rebalance_dates = [d for d in rebalance_dates if d in stock_returns.index]
        
        # Calculate scores at each rebalance date
        all_scores = {}
        
        for date in rebalance_dates:
            result = self.calculate_scores(stock_returns, factors, str(date.date()))
            all_scores[date] = result.scores.iloc[0]
        
        return pd.DataFrame(all_scores).T
    
    def get_top_n(
        self,
        result: ResidualMomentumResult,
        n: int = 10
    ) -> List[str]:
        """
        Get top N stocks by residual momentum score.
        
        Args:
            result: ResidualMomentumResult from calculate_scores
            n: Number of top stocks to return
            
        Returns:
            List of ticker symbols
        """
        scores = result.scores.iloc[0].dropna()
        return scores.nlargest(n).index.tolist()
    
    def get_bottom_n(
        self,
        result: ResidualMomentumResult,
        n: int = 10
    ) -> List[str]:
        """
        Get bottom N stocks by residual momentum score.
        
        Useful for short leg of long/short momentum strategy.
        
        Args:
            result: ResidualMomentumResult from calculate_scores
            n: Number of bottom stocks to return
            
        Returns:
            List of ticker symbols
        """
        scores = result.scores.iloc[0].dropna()
        return scores.nsmallest(n).index.tolist()
    
    def get_factor_exposure_summary(
        self,
        result: ResidualMomentumResult
    ) -> pd.DataFrame:
        """
        Get summary of factor exposures across all stocks.
        
        Args:
            result: ResidualMomentumResult from calculate_scores
            
        Returns:
            DataFrame with factor exposure statistics
        """
        exposures = pd.DataFrame(result.factor_exposures).T
        
        summary = pd.DataFrame({
            'Mean': exposures.mean(),
            'Std': exposures.std(),
            'Min': exposures.min(),
            'Max': exposures.max(),
            'Median': exposures.median(),
        })
        
        return summary


def demo():
    """Demonstrate Residual Momentum calculation."""
    print("=" * 60)
    print("Residual Momentum Demo")
    print("=" * 60)
    
    # Create sample data (in practice, use real stock returns)
    np.random.seed(42)
    dates = pd.date_range('2020-01-01', periods=48, freq='M')
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'AMD']
    
    # Simulate returns with some factor exposure + idiosyncratic component
    returns = pd.DataFrame(
        np.random.randn(len(dates), len(tickers)) * 0.05 + 0.01,
        index=dates,
        columns=tickers
    )
    
    print("\nSample stock returns:")
    print(returns.tail())
    
    # Calculate residual momentum
    rm = ResidualMomentum(lookback_months=36, scoring_months=12)
    
    try:
        result = rm.calculate_scores(returns)
        
        print(f"\nResidual Momentum Scores (as of {result.metadata['as_of_date']}):")
        print(result.scores.T.sort_values(by=result.scores.index[0], ascending=False))
        
        print(f"\nTop 3 stocks: {rm.get_top_n(result, 3)}")
        print(f"Bottom 3 stocks: {rm.get_bottom_n(result, 3)}")
        
        print("\nFactor exposure summary:")
        print(rm.get_factor_exposure_summary(result))
        
    except Exception as e:
        print(f"Demo error (expected if no network): {e}")
        print("In production, ensure pandas-datareader can access Ken French data.")


if __name__ == "__main__":
    demo()
