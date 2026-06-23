"""Shared label definitions and the NEPSE seed symbol universe."""

# Trend classes (integer-encoded for the classifier).
TREND_LABELS = ["DOWNTREND", "SIDEWAYS", "UPTREND"]  # 0, 1, 2
# Volatility classes.
VOL_LABELS = ["LOW", "MEDIUM", "HIGH"]  # 0, 1, 2

# Model registry names.
PRICE_MODEL = "price_model"
TREND_MODEL = "trend_model"
VOLATILITY_MODEL = "volatility_model"

# Symbols used to train the global models / drive the synthetic generator.
SEED_SYMBOLS = [
    "NABIL", "NICA", "NRIC", "UPPER", "NTC",
    "CHCL", "GBIME", "ADBL", "HDL", "NLIC",
]

# Approx reference prices (NPR) for the synthetic generator.
BASE_PRICES = {
    "NABIL": 520.0, "NICA": 410.0, "NRIC": 780.0, "UPPER": 290.0, "NTC": 980.0,
    "CHCL": 470.0, "GBIME": 215.0, "ADBL": 305.0, "HDL": 1180.0, "NLIC": 640.0,
}
