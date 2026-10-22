import math
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

def parse_iso_date(date_str: str) -> datetime:
    """Safely parse ISO date strings."""
    try:
        # Handle trailing Z
        if date_str.endswith("Z"):
            date_str = date_str[:-1] + "+00:00"
        return datetime.fromisoformat(date_str)
    except Exception:
        return datetime.now(timezone.utc)

def calculate_baseline_momentum(
    stars: int,
    forks: int,
    open_issues: int,
    created_at_str: str,
    recent_growth_24h: int,
    recent_growth_7d: int,
    recent_growth_30d: int,
    snapshot_count: int = 1
) -> Dict[str, float]:
    """
    Computes an interpretable, defensible momentum score (0 to 100).
    
    Formula components:
    1. Velocity (V): Weighted blend of 24h and 7d star acquisition rate.
    2. Acceleration (A): Ratio of instantaneous velocity (24h) to smoothed baseline (7d / 7).
    3. Scale Dampener (S): Logarithmic transformation to prevent 100k+ star titans from
       monopolizing the momentum board while still crediting real mass adoption.
    4. Novelty Factor (N): Time-decay function giving sensible advantage to repositories
       created within the last 6 months that are climbing rapidly.
    5. Builder Intent (B): Fork conversion velocity (forks denote real development adoption).
    6. Data Confidence (C): Safeguard against 1-point observation anomalies.
    """
    now = datetime.now(timezone.utc)
    created_at = parse_iso_date(created_at_str)
    age_days = max(1.0, (now - created_at).total_seconds() / 86400.0)

    # 1. Velocity (Stars gained per day, smoothed)
    v_24h = max(0.0, float(recent_growth_24h))
    v_7d = max(0.0, float(recent_growth_7d) / 7.0)
    velocity = (0.65 * v_24h) + (0.35 * v_7d)
    
    # 2. Relative growth velocity against existing base
    prior_stars = max(10.0, float(stars - recent_growth_7d))
    relative_velocity = (v_7d * 7.0) / prior_stars

    # 3. Acceleration: Is velocity today higher than the 7-day average?
    expected_daily = max(1.0, v_7d)
    acceleration = (v_24h / expected_daily) - 1.0
    # Clamped to [-1.0, 3.0] to prevent viral single-hour spikes from breaking scale
    acceleration_clamped = max(-1.0, min(3.0, acceleration))

    # 4. Scale Dampener: Log10 curve
    # Log10(100) = 2, Log10(1,000) = 3, Log10(50,000) = 4.7
    log_scale = math.log10(max(10.0, float(stars)))

    # 5. Novelty / Recency Bonus
    # Repos under 90 days old get up to +40% boost if they have velocity > 5 stars/day
    novelty_bonus = 1.0
    if age_days < 180 and velocity > 3.0:
        decay = math.exp(-age_days / 90.0)
        novelty_bonus = 1.0 + (0.45 * decay)

    # 6. Builder Intent (Fork ratio)
    fork_ratio = min(1.0, max(0.05, float(forks) / max(1.0, float(stars))))
    fork_factor = 1.0 + (0.2 * fork_ratio)

    # 7. Confidence penalty if we only have 1 snapshot observation
    confidence = min(1.0, 0.65 + (0.07 * min(5, snapshot_count)))

    # Raw composite calculation
    # Core drive is daily velocity * relative velocity power * acceleration multiplier
    velocity_factor = math.log1p(velocity * 4.0) * (1.0 + min(2.0, relative_velocity * 1.5))
    acc_multiplier = 1.0 + (0.25 * acceleration_clamped)
    
    raw_score = (velocity_factor * acc_multiplier * novelty_bonus * fork_factor * confidence)

    # Map to 0-100 scale using sigmoid-like soft-clipping
    # Midpoint around raw_score = 12
    normalized_score = 100.0 * (1.0 - math.exp(-raw_score / 14.0))
    normalized_score = round(max(1.0, min(99.9, normalized_score)), 1)

    return {
        "velocity_score": round(velocity, 2),
        "acceleration_score": round(acceleration_clamped, 2),
        "novelty_bonus": round(novelty_bonus, 2),
        "scale_dampener": round(log_scale, 2),
        "confidence": round(confidence, 2),
        "composite_momentum": normalized_score
    }
