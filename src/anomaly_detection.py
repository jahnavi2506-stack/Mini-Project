"""
Anomaly Detection Module

Detects unusual transactions using Isolation Forest and z-score on amounts.
"""

import numpy as np
from typing import List
from dataclasses import dataclass
from sklearn.ensemble import IsolationForest

from .data_models import Transaction


@dataclass
class AnomalyAlert:
    """Represents a detected anomalous transaction."""
    transaction: Transaction
    method: str
    anomaly_score: float
    reason: str


class AnomalyDetector:
    def __init__(
        self,
        contamination: float = 0.05,
        z_score_threshold: float = 3.0,
        random_state: int = 42
    ):
        self.contamination = contamination
        self.z_score_threshold = z_score_threshold
        self.random_state = random_state
        self._is_fitted = False
        self._amount_mean: float = 0.0
        self._amount_std: float = 1.0
        self._isolation_forest = None

    def fit(self, transactions: List[Transaction]) -> "AnomalyDetector":
        """Fit the detector on historical transactions."""
        if len(transactions) < 2:
            return self

        amounts = np.array([abs(t.amount) for t in transactions]).reshape(-1, 1)
        self._amount_mean = float(np.mean(amounts))
        self._amount_std = float(np.std(amounts))
        if self._amount_std == 0:
            self._amount_std = 1.0

        self._isolation_forest = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state
        )
        self._isolation_forest.fit(amounts)
        self._is_fitted = True
        return self

    def detect_anomalies(self, transactions: List[Transaction]) -> List[AnomalyAlert]:
        """Detect anomalies in the given transactions. Returns list of AnomalyAlert."""
        if not self._is_fitted or not transactions:
            return []

        amounts = np.array([abs(t.amount) for t in transactions]).reshape(-1, 1)
        alerts = []

        # Z-score based anomalies
        flagged_indices = set()
        if self._amount_std > 0:
            z_scores = np.abs((amounts.flatten() - self._amount_mean) / self._amount_std)
            for i, (t, z) in enumerate(zip(transactions, z_scores)):
                if z >= self.z_score_threshold:
                    flagged_indices.add(i)
                    alerts.append(AnomalyAlert(
                        transaction=t,
                        method='z_score',
                        anomaly_score=float(z),
                        reason=f'Amount {abs(t.amount):.2f} is {z:.1f} standard deviations from mean'
                    ))

        # Isolation Forest anomalies (for transactions not already flagged by z-score)
        if self._isolation_forest is not None and len(amounts) > 0:
            pred = self._isolation_forest.predict(amounts)
            scores = -self._isolation_forest.score_samples(amounts)
            for i, (t, is_anom, score) in enumerate(zip(transactions, pred, scores)):
                if is_anom == -1 and i not in flagged_indices:
                    alerts.append(AnomalyAlert(
                        transaction=t,
                        method='isolation_forest',
                        anomaly_score=float(score),
                        reason='Unusual spending pattern detected'
                    ))

        return alerts

    def get_statistics(self) -> dict:
        """Return detector statistics for pipeline."""
        return {
            'status': 'fitted' if self._is_fitted else 'not_fitted',
            'contamination': self.contamination,
            'z_score_threshold': self.z_score_threshold,
            'amount_mean': self._amount_mean,
            'amount_std': self._amount_std,
        }
