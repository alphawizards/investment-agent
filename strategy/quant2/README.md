# Quant 2.0 Strategy Framework

This directory contains the modernized "Quant 2.0" trading strategies implementing regime-adaptive, probability-based systems.

## Architecture

```
quant2/
├── momentum/          # Residual Momentum (Fama-French factor-neutral)
├── stat_arb/          # Statistical Arbitrage (DBSCAN + Kalman)
├── volatility/        # Short Volatility (VIX proxy signals)
├── regime/            # HMM Regime Detection & Allocation
├── meta_labeling/     # ML-filtered Quallamaggie signals
├── optimization/      # NCO Portfolio Optimization
└── data_generators/   # Dashboard JSON data generators
```

## Key Differences from Quant 1.0

| Feature | Quant 1.0 | Quant 2.0 |
|---------|-----------|-----------|
| Momentum | Total Return (12M ROC) | Residual Score (Fama-French neutralized) |
| Mean Reversion | OLMAR (single-period) | Stat Arb (DBSCAN clusters + Kalman) |
| Allocation | Static HRP | HMM regime-adaptive |
| Signal Filter | None | Meta-Labeling (Random Forest) |
| Optimization | HRP only | NCO (Nested Clustered) |

## Dependencies

- `hmmlearn` - Hidden Markov Models
- `filterpy` - Kalman Filter
- `pandas-datareader` - Fama-French data
- `scikit-learn` - DBSCAN, PCA, Random Forest

## Usage

```python
from strategy.quant2 import ResidualMomentum, HMMRegimeDetector

# Residual Momentum scoring
rm = ResidualMomentum(lookback_months=36)
scores = rm.calculate_scores(prices)

# Regime detection
hmm = HMMRegimeDetector(n_regimes=3)
regime_probs = hmm.detect(returns)
```
