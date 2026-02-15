"""
Meta-Strategy Orchestrator
==========================
Coordinates the entire Meta-Labeling pipeline:
1. Signal Generation (Quallamaggie)
2. Labeling (Triple Barrier)
3. Feature Engineering (FFD, VIX, etc.)
4. Model Training (Random Forest)
5. Signal Filtering (Inference)

Acts as the "Glue" between the isolated components.
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import pickle

# Import components
from strategy.pipeline.signal_layer import SignalResult, BaseStrategy
from strategy.quant2.meta_labeling.triple_barrier import TripleBarrierLabeler, TripleBarrierResult
from strategy.quant2.meta_labeling.feature_engineering import FeatureEngineer, FeatureSet
from strategy.quant2.meta_labeling.meta_model import MetaLabelModel, TrainingResult, MetaModelResult

@dataclass
class MetaStrategyConfig:
    """Configuration for the Meta-Strategy pipeline."""
    model_path: str = "models/meta_model.pkl"
    labeling_lookback: int = 126  # How far back to label trades for training
    training_min_samples: int = 50 # Minimum samples to train a model
    probability_threshold: float = 0.60

    # Labeling params
    profit_take: float = 0.05
    stop_loss: float = 0.03
    max_holding: int = 10

    # Feature params
    use_vix: bool = True
    vix_ticker: str = "^VIX"

class MetaStrategyOrchestrator:
    """
    Orchestrates the Meta-Labeling workflow.
    """

    def __init__(self, config: MetaStrategyConfig = None):
        self.config = config or MetaStrategyConfig()
        self.labeler = TripleBarrierLabeler(
            profit_take=self.config.profit_take,
            stop_loss=self.config.stop_loss,
            max_holding_days=self.config.max_holding
        )
        self.feature_engineer = FeatureEngineer(
            vix_ticker=self.config.vix_ticker
        )
        self.model = MetaLabelModel(
            threshold=self.config.probability_threshold
        )

        # Load model if exists
        if os.path.exists(self.config.model_path):
            try:
                self.model.load(self.config.model_path)
                print(f"   ✓ Loaded meta-model from {self.config.model_path}")
            except Exception as e:
                print(f"   ⚠️ Failed to load model: {e}")

    def run_training_pipeline(
        self,
        strategy: BaseStrategy,
        prices: pd.DataFrame,
        volume: Optional[pd.DataFrame] = None,
        vix: Optional[pd.Series] = None
    ) -> TrainingResult:
        """
        Run the full training pipeline:
        Generate Signals -> Label Trades -> Extract Features -> Train Model
        """
        print(f"\n🧠 Starting Meta-Model Training Pipeline for {strategy.name}...")

        # 1. Generate Raw Signals
        print("   1. Generating raw signals...")
        signal_result = strategy.generate_signals(prices, volume)

        # Get signal dates (where signal == 1)
        # Flatten signals to list of (date, ticker) or just process dates if model is asset-agnostic
        # For this implementation, we treat all signals as independent samples

        # We need to reconstruct the "trade" events
        # A trade is (Entry Date, Ticker)
        trade_events = []
        signals_df = signal_result.signals

        for date in signals_df.index:
            row = signals_df.loc[date]
            tickers = row[row == 1].index.tolist()
            for ticker in tickers:
                trade_events.append({'date': date, 'ticker': ticker})

        print(f"   ✓ Found {len(trade_events)} historical signals")

        if len(trade_events) < self.config.training_min_samples:
            print(f"   ⚠️ Insufficient samples ({len(trade_events)} < {self.config.training_min_samples}). Skipping training.")
            return None

        # 2. Label Trades (Triple Barrier)
        print("   2. Labeling trades (Triple Barrier)...")
        # We need to label each trade individually since prices differ by ticker
        # Optimization: Group by ticker to minimize series access

        labeled_samples = []

        # Group events by ticker
        events_by_ticker = {}
        for event in trade_events:
            events_by_ticker.setdefault(event['ticker'], []).append(event['date'])

        for ticker, dates in events_by_ticker.items():
            if ticker not in prices.columns: continue

            ticker_prices = prices[ticker]
            # Mock high/low if not available (using close)
            # ideally we'd pass full OHLCV, but pipeline standard is prices=Close
            # If we had High/Low in 'prices' dataframe (MultiIndex), we'd use it.
            # For now, assume prices is Close only.

            # Label
            tb_result = self.labeler.label_signals(
                dates,
                ticker_prices,
                high=ticker_prices, # Approximation
                low=ticker_prices   # Approximation
            )

            # Binary labels (1=Profit)
            binary_labels = self.labeler.get_binary_labels(tb_result)

            for i, event in enumerate(tb_result.events):
                labeled_samples.append({
                    'date': event.entry_date,
                    'ticker': ticker,
                    'label': binary_labels.loc[event.entry_date],
                    'return': event.return_pct
                })

        print(f"   ✓ Labeled {len(labeled_samples)} trades")

        # 3. Extract Features
        print("   3. Extracting features...")
        # We need features at the specific Date+Ticker
        # FeatureEngineer expects a DataFrame of OHLCV
        # We will iterate tickers again

        X_list = []
        y_list = []

        for ticker, dates in events_by_ticker.items():
            # Filter labeled samples for this ticker
            ticker_samples = [s for s in labeled_samples if s['ticker'] == ticker]
            if not ticker_samples: continue

            sample_dates = [s['date'] for s in ticker_samples]
            sample_labels = [s['label'] for s in ticker_samples]

            # Construct OHLCV for this ticker
            ohlcv = pd.DataFrame({
                'Close': prices[ticker],
                'Open': prices[ticker], # Approximation
                'High': prices[ticker], # Approximation
                'Low': prices[ticker],  # Approximation
            })
            if volume is not None and ticker in volume.columns:
                ohlcv['Volume'] = volume[ticker]

            # Extract
            # Note: extract_at_signals returns features for ALL dates in sample_dates
            # provided they have enough history.
            feature_set = self.feature_engineer.extract_at_signals(ohlcv, sample_dates, vix)

            # Align features with labels
            # FeatureSet features index is Date.
            # We need to make sure we match the label for that date.

            feat_df = feature_set.features

            for date, label in zip(sample_dates, sample_labels):
                if date in feat_df.index:
                    X_list.append(feat_df.loc[date])
                    y_list.append(label)

        if not X_list:
            print("   ⚠️ No features extracted (check data history length).")
            # Return empty training result instead of None to prevent attribute errors
            return TrainingResult(
                accuracy=0.0,
                precision=0.0,
                recall=0.0,
                auc=0.0,
                feature_importance=pd.Series(),
                cv_scores=np.array([]),
                metadata={'error': 'No features extracted'}
            )

        X = pd.DataFrame(X_list)
        y = pd.Series(y_list)

        # 4. Train Model
        print(f"   4. Training Random Forest on {len(X)} samples...")
        train_result = self.model.fit(X, y)

        print(f"     Accuracy: {train_result.accuracy:.2%}")
        print(f"     Precision: {train_result.precision:.2%}")
        print(f"     AUC: {train_result.auc:.3f}")

        # Save model
        os.makedirs(os.path.dirname(self.config.model_path), exist_ok=True)
        self.model.save(self.config.model_path)

        return train_result

    def apply_filtering(
        self,
        signal_result: SignalResult,
        prices: pd.DataFrame,
        volume: Optional[pd.DataFrame] = None,
        vix: Optional[pd.Series] = None
    ) -> SignalResult:
        """
        Apply meta-model filtering to existing signals.

        Returns:
            New SignalResult with filtered signals and updated strength.
        """
        if not self.model.is_fitted:
            print("   ⚠️ Meta-model not trained. Returning raw signals.")
            return signal_result

        print(f"\n🔍 Applying Meta-Labeling Filter to {signal_result.strategy_name}...")

        original_signals = signal_result.signals
        filtered_signals = pd.DataFrame(0, index=original_signals.index, columns=original_signals.columns)
        new_strength = pd.DataFrame(0.0, index=original_signals.index, columns=original_signals.columns)

        # Identify all signals
        trade_events = []
        for date in original_signals.index:
            row = original_signals.loc[date]
            tickers = row[row == 1].index.tolist()
            for ticker in tickers:
                trade_events.append({'date': date, 'ticker': ticker})

        if not trade_events:
            return signal_result

        # Group by ticker for efficient feature extraction
        events_by_ticker = {}
        for event in trade_events:
            events_by_ticker.setdefault(event['ticker'], []).append(event['date'])

        accepted_count = 0
        rejected_count = 0

        for ticker, dates in events_by_ticker.items():
            if ticker not in prices.columns: continue

            # Construct OHLCV
            ohlcv = pd.DataFrame({
                'Close': prices[ticker],
                'Open': prices[ticker],
                'High': prices[ticker],
                'Low': prices[ticker],
            })
            if volume is not None and ticker in volume.columns:
                ohlcv['Volume'] = volume[ticker]

            # Extract features
            # This returns a DataFrame indexed by Date
            feature_set = self.feature_engineer.extract_at_signals(ohlcv, dates, vix)

            if feature_set.features.empty:
                continue

            # Predict
            # Returns MetaModelResult
            try:
                model_result = self.model.predict(feature_set.features)

                # Apply filter
                # model_result.predictions is Series indexed by Date, 1=Accept, 0=Reject
                # model_result.probabilities is Series of probs

                for date in feature_set.features.index:
                    is_accepted = model_result.predictions.loc[date]
                    prob = model_result.probabilities.loc[date]

                    if is_accepted == 1:
                        filtered_signals.loc[date, ticker] = 1
                        # Update strength to be the model probability
                        new_strength.loc[date, ticker] = prob
                        accepted_count += 1
                    else:
                        rejected_count += 1

            except Exception as e:
                print(f"   ⚠️ Error predicting for {ticker}: {e}")
                continue

        print(f"   ✓ Filtered Signals: {accepted_count} accepted, {rejected_count} rejected")
        print(f"   ✓ Filter Rate: {rejected_count / (accepted_count + rejected_count + 1e-6):.1%}")

        return SignalResult(
            strategy_name=f"{signal_result.strategy_name}_Meta",
            signals=filtered_signals,
            strength=new_strength,
            metadata={
                **signal_result.metadata,
                'meta_labeling_enabled': True,
                'accepted_signals': accepted_count,
                'rejected_signals': rejected_count
            }
        )

# ==========================================
# Demo / Integration Test
# ==========================================
def demo():
    print("Meta-Strategy Orchestrator Demo")
    # This would require real data to run meaningfully
    pass

if __name__ == "__main__":
    demo()
