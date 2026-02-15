"""
HMM Regime Detector
===================
Hidden Markov Model for market regime detection.

Extends the existing regime_detection.py stub with full HMM
implementation using hmmlearn.

Reference: LSEG Market Regime Detection
https://github.com/LSEG-API-Samples/Article.RD.Python.MarketRegimeDetectionUsingStatisticalAndMLBasedApproaches
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional, Dict, List
from dataclasses import dataclass
from enum import Enum
import warnings

warnings.filterwarnings('ignore')

try:
    from hmmlearn.hmm import GaussianHMM
    HAS_HMMLEARN = True
except ImportError:
    HAS_HMMLEARN = False
    print("Warning: hmmlearn not installed. Install with: pip install hmmlearn")


class MarketRegime(Enum):
    """Market regime classifications."""
    BULL = 0
    BEAR = 1
    CHOP = 2


@dataclass
class RegimeDetectionResult:
    """
    Result container for regime detection.
    
    Attributes:
        regimes: Series of regime labels
        probabilities: DataFrame of regime probabilities
        transitions: Transition probability matrix
        regime_stats: Statistics per regime
        metadata: Additional information
    """
    regimes: pd.Series
    probabilities: pd.DataFrame
    transitions: np.ndarray
    regime_stats: Dict
    metadata: dict


class HMMRegimeDetector:
    """
    Hidden Markov Model for regime detection.
    
    Uses a Gaussian HMM to identify latent market states from
    observable features (returns, volatility).
    
    The HMM assumes:
    - Market has N hidden states (regimes)
    - Each state has Gaussian emission distribution
    - Transitions between states follow Markov property
    
    Decision: HMM is PRIMARY, volatility threshold is FALLBACK.
    
    Attributes:
        n_regimes: Number of hidden states (default: 3)
        features: List of features to use
        lookback_vol: Window for volatility calculation
    """
    
    def __init__(
        self,
        n_regimes: int = 3,
        covariance_type: str = 'full',
        n_iter: int = 100,
        lookback_vol: int = 21,
        use_volume: bool = False,
        random_state: int = 42
    ):
        """
        Initialize HMM Regime Detector.
        
        Args:
            n_regimes: Number of hidden regimes (2 or 3 recommended)
            covariance_type: HMM covariance type ('full', 'diag', 'tied')
            n_iter: Max EM iterations
            lookback_vol: Rolling window for volatility feature
            use_volume: Include volume as a feature
            random_state: Random seed for reproducibility
        """
        self.n_regimes = n_regimes
        self.covariance_type = covariance_type
        self.n_iter = n_iter
        self.lookback_vol = lookback_vol
        self.use_volume = use_volume
        self.random_state = random_state
        
        self.model = None
        self.is_fitted = False
        self._regime_mapping = {}  # Maps HMM states to semantic labels
    
    def _prepare_features(
        self,
        returns: pd.Series,
        volume: Optional[pd.Series] = None
    ) -> np.ndarray:
        """
        Prepare feature matrix for HMM.
        
        Features:
        1. Returns
        2. Rolling volatility
        3. Rolling volume (optional)
        
        Args:
            returns: Series of returns
            volume: Optional volume series
            
        Returns:
            Feature matrix (n_samples, n_features)
        """
        features = pd.DataFrame(index=returns.index)
        
        # Feature 1: Returns
        features['return'] = returns
        
        # Feature 2: Rolling volatility
        features['volatility'] = returns.rolling(self.lookback_vol).std() * np.sqrt(252)
        
        # Feature 3: Volume (optional)
        if self.use_volume and volume is not None:
            features['volume'] = np.log1p(volume)
        
        # Drop NaN
        features = features.dropna()
        
        return features.values, features.index
    
    def _map_regimes_to_labels(
        self,
        means: np.ndarray,
        variances: np.ndarray
    ) -> Dict[int, MarketRegime]:
        """
        Map HMM state indices to semantic regime labels.
        
        Uses mean return and variance to classify:
        - Highest mean return -> BULL
        - Lowest mean return -> BEAR
        - Middle / highest variance -> CHOP
        
        Args:
            means: Mean return per state
            variances: Variance per state
            
        Returns:
            Dict mapping state index to MarketRegime
        """
        n = len(means)
        
        # Sort states by mean return
        sorted_states = np.argsort(means.flatten())
        
        mapping = {}
        
        if n == 2:
            mapping[sorted_states[0]] = MarketRegime.BEAR
            mapping[sorted_states[1]] = MarketRegime.BULL
        elif n >= 3:
            mapping[sorted_states[0]] = MarketRegime.BEAR
            mapping[sorted_states[-1]] = MarketRegime.BULL
            
            # Middle states are CHOP (or check variance)
            for i in range(1, n-1):
                mapping[sorted_states[i]] = MarketRegime.CHOP
        
        return mapping
    
    def fit(
        self,
        returns: pd.Series,
        volume: Optional[pd.Series] = None
    ) -> 'HMMRegimeDetector':
        """
        Fit HMM on historical data.
        
        Args:
            returns: Series of returns (e.g., SPY daily returns)
            volume: Optional volume series
            
        Returns:
            self (fitted detector)
        """
        if not HAS_HMMLEARN:
            raise ImportError(
                "hmmlearn is required for HMM regime detection. "
                "Install with: pip install hmmlearn"
            )
        
        # Prepare features
        X, idx = self._prepare_features(returns, volume)
        
        if len(X) < 100:
            raise ValueError("Insufficient data for HMM training")
        
        # Initialize and fit HMM
        self.model = GaussianHMM(
            n_components=self.n_regimes,
            covariance_type=self.covariance_type,
            n_iter=self.n_iter,
            random_state=self.random_state
        )
        
        self.model.fit(X)
        
        # Map states to semantic labels
        means = self.model.means_[:, 0]  # Return means
        variances = np.array([self.model.covars_[i][0, 0] for i in range(self.n_regimes)])
        self._regime_mapping = self._map_regimes_to_labels(means, variances)
        
        self.is_fitted = True
        return self
    
    def detect(
        self,
        returns: pd.Series,
        volume: Optional[pd.Series] = None,
        use_fallback: bool = True
    ) -> RegimeDetectionResult:
        """
        Detect regimes in returns series.
        
        Args:
            returns: Series of returns
            volume: Optional volume series
            use_fallback: Use volatility threshold as fallback if HMM fails
            
        Returns:
            RegimeDetectionResult with regimes and probabilities
        """
        # Prepare features
        X, idx = self._prepare_features(returns, volume)
        
        # Try HMM-based detection
        try:
            if not self.is_fitted:
                self.fit(returns, volume)
            
            # Predict states
            hidden_states = self.model.predict(X)
            
            # Get probabilities
            posteriors = self.model.predict_proba(X)
            
            # Map to semantic labels
            regime_labels = pd.Series(
                [self._regime_mapping[s].name for s in hidden_states],
                index=idx,
                name='regime'
            )
            
            # Create probability DataFrame
            prob_df = pd.DataFrame(
                posteriors,
                index=idx,
                columns=[self._regime_mapping[i].name for i in range(self.n_regimes)]
            )
            
            # Regime statistics
            regime_stats = {}
            for state_idx in range(self.n_regimes):
                regime_name = self._regime_mapping[state_idx].name
                regime_stats[regime_name] = {
                    'mean_return': float(self.model.means_[state_idx, 0]),
                    'volatility': float(np.sqrt(self.model.covars_[state_idx][0, 0])),
                    'frequency': float((hidden_states == state_idx).mean()),
                }
            
            metadata = {
                'method': 'HMM',
                'n_regimes': self.n_regimes,
                'log_likelihood': self.model.score(X),
                'n_observations': len(X),
                'current_regime': regime_labels.iloc[-1],
                'current_probabilities': prob_df.iloc[-1].to_dict(),
            }
            
            return RegimeDetectionResult(
                regimes=regime_labels,
                probabilities=prob_df,
                transitions=self.model.transmat_,
                regime_stats=regime_stats,
                metadata=metadata
            )
            
        except Exception as e:
            if use_fallback:
                return self._volatility_fallback(returns, idx, str(e))
            else:
                raise
    
    def _volatility_fallback(
        self,
        returns: pd.Series,
        idx: pd.DatetimeIndex,
        error_msg: str
    ) -> RegimeDetectionResult:
        """
        Fallback to volatility-threshold regime detection.
        
        Used when HMM fails or is not available.
        
        Args:
            returns: Series of returns
            idx: DatetimeIndex for output
            error_msg: Error message from HMM failure
            
        Returns:
            RegimeDetectionResult using volatility thresholds
        """
        # Calculate rolling volatility
        vol = returns.rolling(self.lookback_vol).std() * np.sqrt(252)
        vol = vol.reindex(idx)
        
        # Threshold-based classification
        low_vol_threshold = 0.12
        high_vol_threshold = 0.20
        
        regimes = pd.Series(index=idx, dtype=str)
        regimes[vol < low_vol_threshold] = 'BULL'
        regimes[(vol >= low_vol_threshold) & (vol < high_vol_threshold)] = 'CHOP'
        regimes[vol >= high_vol_threshold] = 'BEAR'
        regimes = regimes.fillna('CHOP')
        
        # Create simple probabilities (1.0 for detected regime)
        prob_df = pd.DataFrame(0.0, index=idx, columns=['BULL', 'BEAR', 'CHOP'])
        for i, regime in enumerate(regimes):
            if regime in prob_df.columns:
                prob_df.iloc[i, prob_df.columns.get_loc(regime)] = 1.0
        
        metadata = {
            'method': 'VOLATILITY_FALLBACK',
            'n_regimes': 3,
            'hmm_error': error_msg,
            'n_observations': len(idx),
            'current_regime': regimes.iloc[-1] if len(regimes) > 0 else 'UNKNOWN',
        }
        
        return RegimeDetectionResult(
            regimes=regimes,
            probabilities=prob_df,
            transitions=np.eye(3) / 3,  # Uniform transitions
            regime_stats={},
            metadata=metadata
        )
    
    def get_current_regime(
        self,
        returns: pd.Series,
        volume: Optional[pd.Series] = None
    ) -> Dict:
        """
        Get current regime and probabilities.
        
        Convenience method for real-time regime checking.
        
        Args:
            returns: Recent returns series
            volume: Optional volume series
            
        Returns:
            Dict with current regime and probabilities
        """
        result = self.detect(returns, volume)
        
        return {
            'regime': result.metadata['current_regime'],
            'probabilities': result.metadata.get('current_probabilities', {}),
            'method': result.metadata['method'],
        }


def demo():
    """Demonstrate HMM regime detection."""
    print("=" * 60)
    print("HMM Regime Detector Demo")
    print("=" * 60)
    
    # Create sample returns with regime structure
    np.random.seed(42)
    n = 500
    dates = pd.date_range('2022-01-01', periods=n, freq='D')
    
    # Simulate regime-switching returns
    returns = pd.Series(index=dates, dtype=float)
    
    # Bull regime (low vol, positive drift)
    returns.iloc[:150] = np.random.randn(150) * 0.01 + 0.001
    
    # Bear regime (high vol, negative drift)
    returns.iloc[150:250] = np.random.randn(100) * 0.025 - 0.002
    
    # Chop regime (medium vol, no drift)
    returns.iloc[250:400] = np.random.randn(150) * 0.015
    
    # Bull again
    returns.iloc[400:] = np.random.randn(100) * 0.01 + 0.001
    
    print(f"Sample data: {n} days of returns")
    
    # Run HMM detection
    detector = HMMRegimeDetector(n_regimes=3)
    
    try:
        result = detector.detect(returns)
        
        print(f"\nMethod: {result.metadata['method']}")
        print(f"Current regime: {result.metadata['current_regime']}")
        print(f"Log-likelihood: {result.metadata.get('log_likelihood', 'N/A')}")
        
        print("\nRegime statistics:")
        for regime, stats in result.regime_stats.items():
            print(f"  {regime}:")
            print(f"    Mean return: {stats['mean_return']:.4f}")
            print(f"    Volatility: {stats['volatility']:.4f}")
            print(f"    Frequency: {stats['frequency']:.2%}")
        
        print("\nTransition matrix:")
        print(result.transitions.round(3))
        
        print("\nRegime distribution:")
        print(result.regimes.value_counts())
        
    except Exception as e:
        print(f"Demo error: {e}")


if __name__ == "__main__":
    demo()
