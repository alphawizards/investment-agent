"""
Meta-Labeling Model
===================
Random Forest classifier for filtering Quallamaggie signals.

The meta-model predicts the probability of trade success given
the market context (features), filtering out low-probability trades.

Input: Primary signal + context features
Output: Probability of profit (0.0 to 1.0)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import warnings
import pickle
from pathlib import Path

warnings.filterwarnings('ignore')

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import cross_val_score, train_test_split
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import (
        classification_report, 
        confusion_matrix,
        roc_auc_score,
        precision_recall_curve
    )
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    print("Warning: scikit-learn not installed. Install with: pip install scikit-learn")


@dataclass
class MetaModelResult:
    """Result from meta-model prediction."""
    probabilities: pd.Series
    predictions: pd.Series
    feature_importance: pd.Series
    metadata: dict


@dataclass
class TrainingResult:
    """Result from model training."""
    accuracy: float
    precision: float
    recall: float
    auc: float
    feature_importance: pd.Series
    cv_scores: np.ndarray
    metadata: dict


class MetaLabelModel:
    """
    Meta-labeling model for trade signal filtering.
    
    Uses Random Forest to predict probability of trade success
    based on market context features extracted at signal time.
    
    Workflow:
    1. Train on historical signals + outcomes (triple barrier labels)
    2. Predict probability for new signals
    3. Filter: Only take trades where P > threshold
    
    Attributes:
        n_estimators: Number of trees in Random Forest
        max_depth: Maximum tree depth
        min_samples_leaf: Minimum samples per leaf
        threshold: Probability threshold for trade filtering
    """
    
    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int = 10,
        min_samples_leaf: int = 20,
        threshold: float = 0.65,
        random_state: int = 42
    ):
        """
        Initialize Meta-Label Model.
        
        Args:
            n_estimators: Number of RF trees
            max_depth: Max depth per tree
            min_samples_leaf: Min samples per leaf (prevents overfitting)
            threshold: Probability threshold for trade acceptance
            random_state: Random seed
        """
        if not HAS_SKLEARN:
            raise ImportError(
                "scikit-learn is required for meta-labeling. "
                "Install with: pip install scikit-learn"
            )
        
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_leaf = min_samples_leaf
        self.threshold = threshold
        self.random_state = random_state
        
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = []
        self.is_fitted = False
    
    def _prepare_features(
        self,
        X: pd.DataFrame,
        fit_scaler: bool = False
    ) -> np.ndarray:
        """
        Prepare features for model training/prediction.
        
        Args:
            X: Feature DataFrame
            fit_scaler: Whether to fit the scaler (training only)
            
        Returns:
            Scaled feature array
        """
        # Handle missing values
        X = X.fillna(0)
        
        if fit_scaler:
            return self.scaler.fit_transform(X)
        else:
            return self.scaler.transform(X)
    
    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        cv_folds: int = 5
    ) -> TrainingResult:
        """
        Train the meta-labeling model.
        
        Args:
            X: Feature DataFrame (n_samples, n_features)
            y: Binary labels (1 = profit, 0 = not profit)
            cv_folds: Number of cross-validation folds
            
        Returns:
            TrainingResult with performance metrics
        """
        # Store feature names
        self.feature_names = X.columns.tolist()
        
        # Prepare features
        X_scaled = self._prepare_features(X, fit_scaler=True)
        y_array = y.values
        
        # Initialize model
        self.model = RandomForestClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            min_samples_leaf=self.min_samples_leaf,
            random_state=self.random_state,
            n_jobs=-1,
            class_weight='balanced'  # Handle class imbalance
        )
        
        # Cross-validation
        cv_scores = cross_val_score(
            self.model, X_scaled, y_array,
            cv=cv_folds, scoring='roc_auc'
        )
        
        # Fit on full data
        self.model.fit(X_scaled, y_array)
        self.is_fitted = True
        
        # Calculate metrics on training data
        y_pred = self.model.predict(X_scaled)
        y_proba = self.model.predict_proba(X_scaled)[:, 1]
        
        # Feature importance
        importance = pd.Series(
            self.model.feature_importances_,
            index=self.feature_names
        ).sort_values(ascending=False)
        
        # Metrics
        from sklearn.metrics import precision_score, recall_score, accuracy_score
        
        metadata = {
            'n_samples': len(y),
            'n_features': len(self.feature_names),
            'n_positive': int(y.sum()),
            'n_negative': int((1 - y).sum()),
            'cv_folds': cv_folds,
        }
        
        return TrainingResult(
            accuracy=accuracy_score(y_array, y_pred),
            precision=precision_score(y_array, y_pred),
            recall=recall_score(y_array, y_pred),
            auc=roc_auc_score(y_array, y_proba),
            feature_importance=importance,
            cv_scores=cv_scores,
            metadata=metadata
        )
    
    def predict_proba(
        self,
        X: pd.DataFrame
    ) -> pd.Series:
        """
        Predict probability of profit for each signal.
        
        Args:
            X: Feature DataFrame
            
        Returns:
            Series of probabilities (0.0 to 1.0)
        """
        if not self.is_fitted:
            raise ValueError("Model not fitted. Call fit() first.")
        
        # Prepare features
        X_scaled = self._prepare_features(X, fit_scaler=False)
        
        # Predict probabilities
        probas = self.model.predict_proba(X_scaled)[:, 1]
        
        return pd.Series(probas, index=X.index, name='probability')
    
    def predict(
        self,
        X: pd.DataFrame
    ) -> MetaModelResult:
        """
        Predict with full result details.
        
        Args:
            X: Feature DataFrame
            
        Returns:
            MetaModelResult with probabilities and predictions
        """
        probabilities = self.predict_proba(X)
        predictions = (probabilities >= self.threshold).astype(int)
        
        importance = pd.Series(
            self.model.feature_importances_,
            index=self.feature_names
        ).sort_values(ascending=False)
        
        metadata = {
            'n_signals': len(X),
            'n_accepted': int(predictions.sum()),
            'n_rejected': int((1 - predictions).sum()),
            'threshold': self.threshold,
            'avg_probability': probabilities.mean(),
        }
        
        return MetaModelResult(
            probabilities=probabilities,
            predictions=predictions,
            feature_importance=importance,
            metadata=metadata
        )
    
    def filter_signals(
        self,
        signal_dates: List[pd.Timestamp],
        features: pd.DataFrame,
        threshold: Optional[float] = None
    ) -> Tuple[List[pd.Timestamp], pd.Series]:
        """
        Filter signals based on predicted probability.
        
        Args:
            signal_dates: Original signal dates
            features: Feature DataFrame at signal dates
            threshold: Override default threshold
            
        Returns:
            Tuple of (accepted_dates, probabilities)
        """
        thresh = threshold or self.threshold
        
        # Align features with signal dates
        valid_dates = [d for d in signal_dates if d in features.index]
        X = features.loc[valid_dates]
        
        # Predict probabilities
        probabilities = self.predict_proba(X)
        
        # Filter
        accepted = probabilities[probabilities >= thresh].index.tolist()
        
        return accepted, probabilities
    
    def save(self, filepath: str) -> None:
        """
        Save trained model to disk.
        
        Args:
            filepath: Path to save model
        """
        if not self.is_fitted:
            raise ValueError("Model not fitted. Call fit() first.")
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'threshold': self.threshold,
            'params': {
                'n_estimators': self.n_estimators,
                'max_depth': self.max_depth,
                'min_samples_leaf': self.min_samples_leaf,
            }
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f"Model saved to {filepath}")
    
    def load(self, filepath: str) -> 'MetaLabelModel':
        """
        Load trained model from disk.
        
        Args:
            filepath: Path to model file
            
        Returns:
            self (loaded model)
        """
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)  # nosec B301
        
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.feature_names = model_data['feature_names']
        self.threshold = model_data['threshold']
        self.is_fitted = True
        
        return self
    
    def get_calibration_data(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        n_bins: int = 10
    ) -> pd.DataFrame:
        """
        Get calibration data (predicted vs actual probabilities).
        
        Useful for assessing model calibration.
        
        Args:
            X: Feature DataFrame
            y: True labels
            n_bins: Number of probability bins
            
        Returns:
            DataFrame with calibration data
        """
        probas = self.predict_proba(X)
        
        # Create bins
        bins = np.linspace(0, 1, n_bins + 1)
        bin_labels = [f"{bins[i]:.1f}-{bins[i+1]:.1f}" for i in range(n_bins)]
        
        calibration = []
        
        for i in range(n_bins):
            mask = (probas >= bins[i]) & (probas < bins[i+1])
            if mask.sum() > 0:
                calibration.append({
                    'bin': bin_labels[i],
                    'predicted_prob': probas[mask].mean(),
                    'actual_rate': y[mask].mean(),
                    'count': mask.sum()
                })
        
        return pd.DataFrame(calibration)


def demo():
    """Demonstrate meta-labeling model."""
    print("=" * 60)
    print("Meta-Labeling Model Demo")
    print("=" * 60)
    
    # Create sample data
    np.random.seed(42)
    n = 500
    n_features = 15
    
    dates = pd.date_range('2020-01-01', periods=n, freq='D')
    
    # Generate features
    feature_names = [f'feature_{i}' for i in range(n_features)]
    X = pd.DataFrame(
        np.random.randn(n, n_features),
        index=dates,
        columns=feature_names
    )
    
    # Generate labels (some relationship with features)
    y = (X['feature_0'] + X['feature_1'] + np.random.randn(n) * 0.5 > 0).astype(int)
    y = pd.Series(y, index=dates)
    
    print(f"Sample: {n} signals, {n_features} features")
    print(f"Label distribution: {y.value_counts().to_dict()}")
    
    # Train model
    model = MetaLabelModel(n_estimators=50, max_depth=5)
    training_result = model.fit(X, y)
    
    print(f"\nTraining Results:")
    print(f"  Accuracy: {training_result.accuracy:.3f}")
    print(f"  Precision: {training_result.precision:.3f}")
    print(f"  Recall: {training_result.recall:.3f}")
    print(f"  AUC: {training_result.auc:.3f}")
    print(f"  CV Scores: {training_result.cv_scores.mean():.3f} ± {training_result.cv_scores.std():.3f}")
    
    print("\nTop 5 Feature Importance:")
    print(training_result.feature_importance.head())
    
    # Predict on new data
    X_new = pd.DataFrame(
        np.random.randn(20, n_features),
        index=pd.date_range('2022-01-01', periods=20, freq='D'),
        columns=feature_names
    )
    
    result = model.predict(X_new)
    print(f"\nPrediction Results:")
    print(f"  Signals accepted: {result.metadata['n_accepted']}")
    print(f"  Signals rejected: {result.metadata['n_rejected']}")
    print(f"  Avg probability: {result.metadata['avg_probability']:.3f}")


if __name__ == "__main__":
    demo()
