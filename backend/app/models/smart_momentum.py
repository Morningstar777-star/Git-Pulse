import math
from datetime import datetime, timezone
from typing import Dict, Any, Optional

def parse_iso_date(date_str: str) -> datetime:
    """Safely parse ISO date strings."""
    try:
        if date_str.endswith("Z"):
            date_str = date_str[:-1] + "+00:00"
        return datetime.fromisoformat(date_str)
    except Exception:
        return datetime.now(timezone.utc)

def calculate_smart_momentum(
    stars: int,
    forks: int,
    open_issues: int,
    created_at_str: str,
    recent_growth_24h: int,
    recent_growth_7d: int,
    recent_growth_30d: int,
    snapshot_count: int = 3
) -> Dict[str, float]:
    """
    Bayesian Kinetic Momentum (BKM) Engine:
    The single, definitive smart ranking algorithm for technology discovery.
    
    Synthesized across 5 distinct perspectives:
    1. Sub-linear Power-Law Normalization (stops 100k+ giants & 2-star micro-noise).
    2. Bounded Instantaneous Acceleration via tanh (catches surges, blocks 1-hr bot spikes).
    3. Builder Intent Multiplier (fork-to-star conversion verifies real developer usage).
    4. Exponential Half-Life Novelty Decay (rewards breakout velocity in young tools).
    5. Bayesian Observation Confidence (guards against single-observation noise).
    """
    now = datetime.now(timezone.utc)
    created_at = parse_iso_date(created_at_str)
    age_days = max(1.0, (now - created_at).total_seconds() / 86400.0)

    # Clean non-negative values
    stars_f = max(1.0, float(stars))
    forks_f = max(0.0, float(forks))
    v_24h = max(0.0, float(recent_growth_24h))
    v_7d = max(0.0, float(recent_growth_7d) / 7.0)
    v_30d = max(0.0, float(recent_growth_30d) / 30.0)

    # 1. Blended Velocity Density (60% 24h, 30% 7d, 10% 30d)
    blended_v = (0.60 * v_24h) + (0.30 * v_7d) + (0.10 * v_30d)

    # Power-law scale dampener with Dirichlet smoothing (+50 stars prior)
    # This prevents micro-repos (2 stars -> 4 stars) from blowing up,
    # while preventing 150k giants from dominating on baseline organic clicks alone.
    scale_dampener = math.log10(stars_f + 50.0) * math.pow(stars_f + 150.0, 0.20)
    velocity_density = blended_v / max(1.0, scale_dampener)

    # 2. Bounded Acceleration (Jerk / Second Derivative)
    # Compares instantaneous rate against smoothed 7d baseline
    expected_daily = max(1.0, v_7d)
    raw_acc = (v_24h / expected_daily) - 1.0
    # Hyperbolic tangent bounding: smooth, bounded in [-0.8, 1.8]
    acc_multiplier = 1.0 + (0.65 * math.tanh(raw_acc / 1.5))

    # 3. Builder Intent Factor (Fork Conversion Ratio)
    # Forking implies real development intent (cloning, building, contributing).
    # Normal repos have ~10% forks. Meme/hype repos have < 2% forks.
    fork_ratio = min(0.50, forks_f / stars_f)
    if fork_ratio >= 0.12:
        builder_intent = 1.0 + min(0.35, (fork_ratio - 0.12) * 1.8)
    elif fork_ratio < 0.03:
        builder_intent = 0.85 # Slight penalty for passive bookmarking / hype
    else:
        builder_intent = 1.0

    # 4. Novelty Booster (Exponential Half-Life of 120 Days)
    # Younger projects showing verified velocity get strong preference
    novelty_bonus = 1.0
    if age_days < 240 and blended_v >= 3.0:
        decay = math.exp(-age_days / 120.0)
        novelty_bonus = 1.0 + (0.50 * decay)

    # 5. Bayesian Observation Confidence Prior
    # Penalizes single snapshot observations until multiple time points confirm trajectory
    confidence = min(1.0, 0.70 + (0.06 * min(5, snapshot_count)))

    # Raw Kinetic Score
    # Log-smoothed dynamic range
    core_kinetic = math.log1p(velocity_density * 8.0)
    raw_score = core_kinetic * acc_multiplier * builder_intent * novelty_bonus * confidence

    # Map to calibrated 0 - 100 Index using soft-saturation curve (Tau = 1.85)
    normalized_score = 100.0 * (1.0 - math.exp(-raw_score / 1.85))
    final_score = round(max(1.0, min(99.9, normalized_score)), 1)

    return {
        "velocity_score": round(blended_v, 2),
        "acceleration_score": round(acc_multiplier - 1.0, 2),
        "novelty_bonus": round(novelty_bonus, 2),
        "scale_dampener": round(scale_dampener, 2),
        "confidence": round(confidence, 2),
        "composite_momentum": final_score
    }
