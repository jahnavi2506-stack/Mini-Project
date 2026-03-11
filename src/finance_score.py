"""
Personal Finance Health Score (0–100)

Score factors:
- Savings rate (30%)
- Budget adherence (30%)
- Spending distribution (20%)
- Anomalies detected (20%)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, date

from .data_models import Transaction
from .budget_manager import BudgetManager


@dataclass(frozen=True)
class FinanceScoreResult:
    score: int
    insights: List[str]


class FinanceScoreCalculator:
    @staticmethod
    def _tx_date(t: Transaction) -> date:
        try:
            return t.timestamp.date()
        except Exception:
            return datetime.now().date()

    @staticmethod
    def _month_range(today: date) -> Tuple[date, date]:
        start = date(today.year, today.month, 1)
        if today.month == 12:
            end = date(today.year + 1, 1, 1)
        else:
            end = date(today.year, today.month + 1, 1)
        return start, end

    @staticmethod
    def calculate_score(
        transactions: List[Transaction],
        monthly_income: Optional[float],
        budgets: Optional[Dict[str, float]],
        *,
        anomaly_count: int = 0,
    ) -> Dict[str, Any]:
        txs = transactions or []
        income = float(monthly_income or 0.0)
        budgets = budgets or {}

        today = datetime.now().date()
        start, end = FinanceScoreCalculator._month_range(today)

        month_expenses = 0.0
        month_income = 0.0
        for t in txs:
            d = FinanceScoreCalculator._tx_date(t)
            if not (start <= d < end):
                continue
            amt = float(t.amount or 0.0)
            if amt >= 0:
                month_income += amt
            else:
                month_expenses += abs(amt)

        # Prefer profile income; otherwise use transactions income this month
        effective_income = income if income > 0 else month_income

        insights: List[str] = []

        # ---- Savings rate score (0..30) ----
        if effective_income > 0:
            savings = max(0.0, effective_income - month_expenses)
            savings_rate = savings / effective_income  # 0..1
            # target: >=20% is good
            savings_component = min(1.0, savings_rate / 0.20)
            savings_points = 30.0 * savings_component
            if savings_rate >= 0.20:
                insights.append("Good savings rate")
            elif savings_rate >= 0.10:
                insights.append("Savings rate is moderate — try reducing discretionary spending")
            else:
                insights.append("Low savings rate — review monthly expenses and budgets")
        else:
            savings_points = 15.0  # neutral when income unknown
            insights.append("Income not available — score uses neutral savings estimate")

        # ---- Budget adherence score (0..30) ----
        if budgets:
            spending_by_cat = BudgetManager.calculate_category_spending(txs)
            total_budget = 0.0
            total_over = 0.0
            for cat, limit in budgets.items():
                total_budget += float(limit)
                spent = float(spending_by_cat.get(cat, 0.0))
                if spent > float(limit):
                    total_over += (spent - float(limit))

            if total_budget > 0:
                adherence = max(0.0, 1.0 - (total_over / total_budget))
                budget_points = 30.0 * adherence
                if total_over <= 0:
                    insights.append("Budgets are on track this month")
                else:
                    insights.append(f"Budgets exceeded by ₹{total_over:.0f} total")
            else:
                budget_points = 15.0
        else:
            budget_points = 15.0
            insights.append("No budgets set — add budgets to improve tracking")

        # ---- Spending distribution score (0..20) ----
        # Penalize if one category dominates expenses (>45% of expenses).
        if month_expenses > 0:
            spending_by_cat = BudgetManager.calculate_category_spending(txs)
            top_cat = None
            top_val = 0.0
            for cat, val in spending_by_cat.items():
                if val > top_val:
                    top_val = val
                    top_cat = cat
            top_share = top_val / month_expenses if month_expenses else 0.0
            if top_share <= 0.35:
                dist_points = 20.0
            elif top_share <= 0.45:
                dist_points = 14.0
                insights.append("Spending is somewhat concentrated — diversify categories if possible")
            else:
                dist_points = 8.0
                if top_cat:
                    insights.append(f"High {top_cat.title()} spending concentration")
        else:
            dist_points = 16.0

        # ---- Anomalies score (0..20) ----
        if anomaly_count <= 0:
            anomaly_points = 20.0
        elif anomaly_count == 1:
            anomaly_points = 14.0
            insights.append("1 unusual transaction detected")
        elif anomaly_count <= 3:
            anomaly_points = 10.0
            insights.append(f"{anomaly_count} unusual transactions detected")
        else:
            anomaly_points = 6.0
            insights.append(f"{anomaly_count} unusual transactions detected — review immediately")

        total = savings_points + budget_points + dist_points + anomaly_points
        score = int(round(max(0.0, min(100.0, total))))

        # Keep insights concise (max 4)
        insights = insights[:4]

        return {"score": score, "insights": insights}

