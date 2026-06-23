"""Rule-based fusion of model outputs into a BUY / SELL / HOLD signal."""


def generate_signal(price: dict, trend: dict, volatility: dict) -> dict:
    """Combine price, trend and volatility predictions into one trading signal."""
    reasons: list[str] = []
    score = 0

    trend_label = trend["label"]
    if trend_label == "UPTREND":
        score += 1
        reasons.append("Uptrend detected")
    elif trend_label == "DOWNTREND":
        score -= 1
        reasons.append("Downtrend detected")

    exp_ret = price.get("predicted_return", 0.0)
    if exp_ret > 0.005:
        score += 1
        reasons.append(f"Positive predicted move (+{exp_ret * 100:.2f}%)")
    elif exp_ret < -0.005:
        score -= 1
        reasons.append(f"Negative predicted move ({exp_ret * 100:.2f}%)")

    vol_label = volatility["label"]
    if vol_label == "LOW":
        reasons.append("Low volatility")
    elif vol_label == "HIGH":
        reasons.append("High volatility — elevated risk")

    if score >= 2:
        signal = "BUY"
    elif score <= -2:
        signal = "SELL"
    else:
        signal = "HOLD"

    # Strength is dampened under high volatility.
    magnitude = abs(score)
    if signal == "HOLD":
        strength = "NEUTRAL"
    elif magnitude >= 2 and vol_label != "HIGH":
        strength = "STRONG"
    elif vol_label == "HIGH":
        strength = "WEAK"
    else:
        strength = "MODERATE"

    # Confidence: blend of the contributing models.
    confidence = round(
        (price.get("confidence", 0.5) + trend.get("confidence", 0.5)) / 2, 3
    )

    if not reasons:
        reasons.append("No strong directional signal")

    return {
        "signal": signal,
        "strength": strength,
        "confidence": confidence,
        "reason": reasons,
        "score": score,
    }
