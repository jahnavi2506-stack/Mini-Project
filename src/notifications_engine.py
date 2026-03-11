"""
Smart Notifications Engine

Rule-based intelligent notifications based on transactions, budgets, and anomalies.
"""

from __future__ import annotations

from datetime import datetime, date
from typing import Any, Dict, List, Optional
from collections import defaultdict

from .data_models import Transaction
from .budget_manager import BudgetManager


class NotificationEngine:
    @staticmethod
    def _tx_date(t: Transaction) -> date:
        try:
            return t.timestamp.date()
        except Exception:
            return datetime.now().date()

    @staticmethod
    def generate_notifications(
        transactions: List[Transaction],
        monthly_income: Optional[float],
        *,
        budgets: Optional[Dict[str, float]] = None,
        anomaly_alerts: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, str]]:
        """
        Generate intelligent notifications.

        Returns list of:
        {
          "type": "info|warning|critical",
          "message": "...",
          "timestamp": "ISO..."
        }
        """
        now_iso = datetime.now().isoformat()
        txs = transactions or []
        income = float(monthly_income or 0.0)

        notifications: List[Dict[str, str]] = []

        # 1) Budget exceeded (from budgets feature)
        if budgets:
            notifications.extend(BudgetManager.check_budget_exceeded(txs, budgets))

        # 2) High category spending (>30% of income) for current month
        if income > 0:
            spending = BudgetManager.calculate_category_spending(txs)
            for cat, spent in sorted(spending.items(), key=lambda x: x[1], reverse=True):
                if spent > 0.30 * income:
                    notifications.append(
                        {
                            "type": "warning",
                            "message": f"{cat.title()} spending is ₹{spent:.0f} (over 30% of your monthly income).",
                            "timestamp": now_iso,
                        }
                    )

        # 3) Anomaly transaction (pipeline anomaly detector flags)
        if anomaly_alerts:
            count = len(anomaly_alerts)
            # If any anomaly amount is very high, escalate
            high_amount = False
            for a in anomaly_alerts:
                try:
                    amt = abs(float(a.get("amount", 0.0)))
                except Exception:
                    amt = 0.0
                if amt >= 20000:
                    high_amount = True
                    break
            notifications.append(
                {
                    "type": "critical" if high_amount else "warning",
                    "message": f"{count} unusual transaction(s) detected. Please review recent activity.",
                    "timestamp": now_iso,
                }
            )

        # 4) High spending day (optional)
        # If any single day spending is > 15% of income, alert (only if income known)
        if income > 0 and txs:
            daily = defaultdict(float)
            for t in txs:
                if (t.amount or 0) < 0:
                    daily[NotificationEngine._tx_date(t)] += abs(float(t.amount))
            if daily:
                day, max_spend = max(daily.items(), key=lambda x: x[1])
                if max_spend > 0.15 * income:
                    notifications.append(
                        {
                            "type": "info",
                            "message": f"High spending day: ₹{max_spend:.0f} spent on {day.strftime('%b %d')}.",
                            "timestamp": now_iso,
                        }
                    )

        # De-duplicate identical messages while preserving order
        seen = set()
        deduped = []
        for n in notifications:
            key = (n.get("type"), n.get("message"))
            if key in seen:
                continue
            seen.add(key)
            # Ensure required fields exist
            deduped.append(
                {
                    "type": n.get("type") or "info",
                    "message": n.get("message") or "",
                    "timestamp": n.get("timestamp") or now_iso,
                }
            )

        # Sort by severity: critical -> warning -> info
        order = {"critical": 0, "warning": 1, "info": 2}
        deduped.sort(key=lambda x: order.get(x.get("type", "info"), 3))
        return deduped

