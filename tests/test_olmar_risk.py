
import pandas as pd
import numpy as np
from strategy.quant1.olmar.olmar_strategy import OLMARStrategy, OLMARConfig

def test_risk_controls():
    print("Testing OLMAR Risk Controls...")

    # Create dummy data
    dates = pd.date_range("2023-01-01", periods=100)
    assets = ["AssetA", "AssetB"]

    # Scenario:
    # AssetA: Flat then drops significantly (Stop Loss trigger)
    # AssetB: High volatility (Vol Guard trigger)

    prices_data = {
        "AssetA": np.ones(100) * 100,
        "AssetB": np.ones(100) * 100
    }

    # Trigger Stop Loss for A: Drop to 80 (0.8 of max 100) < 0.85
    prices_data["AssetA"][50:] = 80

    # Trigger Vol Guard for B: Alternating high returns
    # std(returns) > 0.05
    # alternating +/- 10% returns
    for i in range(50, 100):
        if i % 2 == 0:
            prices_data["AssetB"][i] = prices_data["AssetB"][i-1] * 1.10
        else:
            prices_data["AssetB"][i] = prices_data["AssetB"][i-1] * 0.90

    prices = pd.DataFrame(prices_data, index=dates)

    strategy = OLMARStrategy(OLMARConfig(rebalance_freq='daily'))

    # Run strategy
    # Note: We can't easily mock olmar_weights inner logic without mocking the function
    # but we can check if our risk logic applied "on top" of whatever it returned.
    # The default olmar_weights likely returns non-zero weights.

    result = strategy.generate_weights(prices, apply_cost_constraints=False)
    weights = result.weights

    # Check Stop Loss (AssetA)
    # At index > 50, price is 80, rolling max (since start) is 100. Ratio = 0.80 < 0.85.
    # Weight should be 0.

    # Allow some buffer for rolling window to pick up
    idx_check = 60
    w_a = weights.iloc[idx_check]["AssetA"]
    print(f"AssetA Weight at idx {idx_check} (Price=80, Max=100): {w_a}")

    # Check Vol Guard (AssetB)
    # Volatility should be high.
    # We expect weights to be halved compared to raw weights (if raw wasn't 0)

    raw_w_b = result.raw_weights.iloc[idx_check]["AssetB"]
    w_b = weights.iloc[idx_check]["AssetB"]

    print(f"AssetB Weight at idx {idx_check} (High Vol): {w_b} (Raw: {raw_w_b})")

    # Assertions
    if w_a == 0.0:
        print("✅ Stop Loss Passed (Weight is 0.0)")
    else:
        print(f"❌ Stop Loss Failed: Weight {w_a} != 0.0")

    # For Vol guard, we need to ensure it's reduced.
    # Since OLMAR might output 0 anyway, we check if logic held.
    # Or we can verify volatility calculation manually.

    returns = prices.pct_change()
    vol = returns["AssetB"].rolling(20).std().iloc[idx_check]
    print(f"AssetB Volatility: {vol:.4f}")
    if vol > 0.05:
        if w_b <= raw_w_b * 0.5 + 1e-9: # Float tolerance
             print("✅ Volatility Guard Passed (Weight Reduced)")
        else:
             print(f"❌ Volatility Guard Failed: {w_b} > {raw_w_b * 0.5}")
    else:
        print("⚠️ Volatility not high enough to test guard")

if __name__ == "__main__":
    test_risk_controls()
