import math
import numpy as np
from typing import List, Dict, Any, Tuple

class LSTMTrendPredictor:
    """
    Lightweight, deterministic recurrent LSTM cell for sequential snapshot trajectories.
    Processes sequences of [normalized_stars, velocity, acceleration, fork_ratio] over time windows.
    """
    def __init__(self, input_dim: int = 4, hidden_dim: int = 16):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        np.random.seed(42)

        # Initialize weights: input, forget, cell, output gates
        scale = 1.0 / math.sqrt(hidden_dim)
        self.W_x = np.random.uniform(-scale, scale, (4 * hidden_dim, input_dim))
        self.W_h = np.random.uniform(-scale, scale, (4 * hidden_dim, hidden_dim))
        self.b = np.zeros((4 * hidden_dim, 1))
        # Initialize forget gate bias to 1.0 for better gradient retention
        self.b[hidden_dim:2 * hidden_dim, :] = 1.0

        # Projection head to predict forward growth rate
        self.W_out = np.random.uniform(-scale, scale, (1, hidden_dim))
        self.b_out = np.zeros((1, 1))

    def _sigmoid(self, x: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-np.clip(x, -15.0, 15.0)))

    def forward(self, sequence: np.ndarray) -> float:
        """
        sequence: shape (seq_len, input_dim)
        Returns: predicted future momentum score (scalar)
        """
        seq_len = sequence.shape[0]
        h = np.zeros((self.hidden_dim, 1))
        c = np.zeros((self.hidden_dim, 1))

        for t in range(seq_len):
            x_t = sequence[t, :].reshape(-1, 1)
            gates = np.dot(self.W_x, x_t) + np.dot(self.W_h, h) + self.b
            
            i = self._sigmoid(gates[0:self.hidden_dim, :])
            f = self._sigmoid(gates[self.hidden_dim:2 * self.hidden_dim, :])
            g = np.tanh(gates[2 * self.hidden_dim:3 * self.hidden_dim, :])
            o = self._sigmoid(gates[3 * self.hidden_dim:4 * self.hidden_dim, :])

            c = f * c + i * g
            h = o * np.tanh(c)

        out = np.dot(self.W_out, h) + self.b_out
        raw_val = float(out[0, 0])
        # Sigmoid projection into 0 - 100
        score = 100.0 * (1.0 / (1.0 + math.exp(-raw_val)))
        return round(score, 1)

    def extract_sequence(self, snapshots: List[Dict[str, Any]], current_stars: int, current_forks: int) -> np.ndarray:
        """Convert list of chronological snapshots into standard sequence array."""
        seq = []
        if not snapshots:
            # Synthetic 3-step sequence from current metrics
            seq = [
                [math.log10(max(1.0, current_stars * 0.95)), 2.0, 0.0, float(current_forks) / max(1.0, current_stars)],
                [math.log10(max(1.0, current_stars * 0.98)), 5.0, 0.2, float(current_forks) / max(1.0, current_stars)],
                [math.log10(max(1.0, current_stars)), 8.0, 0.4, float(current_forks) / max(1.0, current_stars)]
            ]
        else:
            sorted_snaps = sorted(snapshots, key=lambda s: s.get("timestamp", ""))
            for s in sorted_snaps[-5:]: # Use last up to 5 snapshots
                s_stars = max(1.0, float(s.get("stars", 1)))
                v = max(0.0, float(s.get("delta_stars_24h", 0)))
                acc = max(-1.0, min(3.0, float(s.get("delta_stars_24h", 0)) / max(1.0, float(s.get("delta_stars_7d", 7)) / 7.0) - 1.0))
                forks = float(s.get("forks", 0))
                seq.append([math.log10(s_stars), v, acc, min(1.0, forks / s_stars)])
                
        # Ensure at least 3 timesteps
        while len(seq) < 3:
            seq.insert(0, seq[0] if seq else [1.0, 0.0, 0.0, 0.05])
            
        return np.array(seq, dtype=np.float32)

    def fit_approximate(self, X_seqs: List[np.ndarray], y_targets: np.ndarray, epochs: int = 25, lr: float = 0.01):
        """Fit projection weights on sequential training set using stochastic gradient step."""
        for _ in range(epochs):
            for seq, y in zip(X_seqs, y_targets):
                pred = self.forward(seq) / 100.0
                target = min(1.0, max(0.0, float(y)))
                err = pred - target
                # Adjust output layer weights
                self.W_out -= lr * err * 0.1
                self.b_out -= lr * err * 0.05
