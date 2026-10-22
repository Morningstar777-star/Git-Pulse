import math
import numpy as np
from typing import List, Dict, Any, Tuple
from datetime import datetime, timezone
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance

class GBDTMomentumEngine:
    def __init__(self):
        self.model = HistGradientBoostingRegressor(
            max_iter=100,
            learning_rate=0.08,
            max_leaf_nodes=15,
            min_samples_leaf=4,
            random_state=42
        )
        self.is_trained = False
        self.feature_names = [
            "log_stars",
            "log_forks",
            "fork_ratio",
            "age_days",
            "v_24h",
            "v_7d",
            "rel_velocity_7d",
            "acceleration",
            "snapshot_coverage"
        ]
        self.feature_importances: Dict[str, float] = {}

    def extract_features(self, repo_dict: Dict[str, Any]) -> np.ndarray:
        stars = max(1.0, float(repo_dict.get("stars", 0)))
        forks = max(0.0, float(repo_dict.get("forks", 0)))
        v_24h = max(0.0, float(repo_dict.get("recent_growth_24h", 0)))
        v_7d = max(0.0, float(repo_dict.get("recent_growth_7d", 0)) / 7.0)
        
        # Age in days
        created_at_str = repo_dict.get("created_at", "")
        try:
            if created_at_str.endswith("Z"):
                created_at_str = created_at_str[:-1] + "+00:00"
            created_at = datetime.fromisoformat(created_at_str)
            age_days = max(1.0, (datetime.now(timezone.utc) - created_at).total_seconds() / 86400.0)
        except Exception:
            age_days = 180.0

        prior_stars = max(10.0, stars - (v_7d * 7.0))
        rel_v_7d = (v_7d * 7.0) / prior_stars
        acceleration = max(-1.0, min(3.0, (v_24h / max(1.0, v_7d)) - 1.0))
        fork_ratio = min(1.0, forks / stars)
        log_stars = math.log10(stars)
        log_forks = math.log10(max(1.0, forks))
        snapshots = float(repo_dict.get("snapshot_count", 3))

        return np.array([
            log_stars,
            log_forks,
            fork_ratio,
            age_days,
            v_24h,
            v_7d,
            rel_v_7d,
            acceleration,
            snapshots
        ], dtype=np.float32)

    def train_and_evaluate(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_test: np.ndarray,
        y_test: np.ndarray
    ) -> Dict[str, Any]:
        """Fit the GBDT regressor and calculate feature importances."""
        self.model.fit(X_train, y_train)
        self.is_trained = True

        # Permutation feature importances
        result = permutation_importance(self.model, X_test, y_test, n_repeats=5, random_state=42)
        total = sum(max(0.0, imp) for imp in result.importances_mean) or 1.0
        self.feature_importances = {
            name: round(float(max(0.0, imp) / total), 3)
            for name, imp in zip(self.feature_names, result.importances_mean)
        }

        # Predict test
        preds = self.model.predict(X_test)
        mae = float(np.mean(np.abs(preds - y_test)))
        
        return {
            "mae": round(mae, 4),
            "feature_importances": self.feature_importances
        }

    def predict_momentum(self, repo_dict: Dict[str, Any]) -> float:
        """Predict forward relative growth index and map to 0-100 scale."""
        feats = self.extract_features(repo_dict).reshape(1, -1)
        if not self.is_trained:
            # Fallback heuristic if not yet trained
            return 50.0
        raw_pred = float(self.model.predict(feats)[0])
        # Soft-saturate to 0-100
        score = 100.0 * (1.0 - math.exp(-max(0.0, raw_pred) / 0.18))
        return round(max(1.0, min(99.9, score)), 1)
