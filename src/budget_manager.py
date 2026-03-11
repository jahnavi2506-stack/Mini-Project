"""
Budget Tracking System

CSV-based category-wise budgets and monthly spending checks.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple

import csv
import os

from .data_models import Transaction


@dataclass(frozen=True)
class BudgetItem:
    user_id: str
    category: str
    budget_limit: float


class BudgetManager:
    """
    Manages per-user monthly category budgets stored in `data/budgets.csv`.
    """

    DEFAULT_BUDGETS_PATH = os.path.join("data", "budgets.csv")

    @staticmethod
    def get_user_budgets(user_id: str, budgets_file: Optional[str] = None) -> Dict[str, float]:
        budgets_file = budgets_file or BudgetManager.DEFAULT_BUDGETS_PATH
        budgets: Dict[str, float] = {}

        if not os.path.exists(budgets_file):
            return budgets

        with open(budgets_file, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row:
                    continue
                if (row.get("user_id") or "").strip() != user_id:
                    continue
                category = (row.get("category") or "").strip().lower()
                limit_str = (row.get("budget_limit") or "").strip()
                try:
                    limit_val = float(limit_str)
                except Exception:
                    continue
                if category:
                    budgets[category] = limit_val

        return budgets

    @staticmethod
    def _tx_date(t: Transaction) -> date:
        try:
            return t.timestamp.date()
        except Exception:
            return datetime.now().date()

    @staticmethod
    def calculate_category_spending(
        transactions: List[Transaction],
        *,
        month: Optional[date] = None,
        include_income: bool = False,
    ) -> Dict[str, float]:
        """
        Calculate spending by category for a given month (defaults to current month).

        Expenses are amounts < 0. Income (>=0) can be included if include_income=True.
        """
        if not transactions:
            return {}

        today = datetime.now().date()
        target = month or date(today.year, today.month, 1)
        start = date(target.year, target.month, 1)
        if target.month == 12:
            end = date(target.year + 1, 1, 1)
        else:
            end = date(target.year, target.month + 1, 1)

        totals: Dict[str, float] = {}
        for t in transactions:
            td = BudgetManager._tx_date(t)
            if not (start <= td < end):
                continue
            amt = t.amount or 0.0
            if not include_income and amt >= 0:
                continue

            category = (t.category or "other").strip().lower() or "other"
            value = abs(amt) if amt < 0 else amt
            totals[category] = totals.get(category, 0.0) + float(value)

        return totals

    @staticmethod
    def check_budget_exceeded(
        transactions: List[Transaction],
        budgets: Dict[str, float],
        *,
        month: Optional[date] = None,
    ) -> List[Dict[str, object]]:
        """
        Return structured warning notifications for any exceeded budgets.
        """
        if not budgets:
            return []

        spending = BudgetManager.calculate_category_spending(transactions, month=month)
        exceeded = []
        now_iso = datetime.now().isoformat()

        for cat, limit in budgets.items():
            spent = float(spending.get(cat, 0.0))
            if spent > float(limit):
                over = spent - float(limit)
                exceeded.append(
                    {
                        "type": "warning",
                        "message": f"You exceeded your {cat.title()} budget by ₹{over:.0f}",
                        "timestamp": now_iso,
                    }
                )

        return exceeded

    @staticmethod
    def set_user_budgets(
        user_id: str,
        budgets: Dict[str, float],
        budgets_file: Optional[str] = None,
    ) -> None:
        """
        Replace the budgets for a user in the CSV file (keeps other users unchanged).

        budgets: dict of {category: limit}. Categories are lowercased.
        """
        budgets_file = budgets_file or BudgetManager.DEFAULT_BUDGETS_PATH

        # Normalize and filter
        normalized: Dict[str, float] = {}
        for k, v in (budgets or {}).items():
            cat = (k or "").strip().lower()
            if not cat:
                continue
            try:
                limit = float(v)
            except Exception:
                continue
            if limit <= 0:
                continue
            normalized[cat] = limit

        rows: List[Dict[str, str]] = []

        # Read existing rows (if file exists)
        if os.path.exists(budgets_file):
            with open(budgets_file, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not row:
                        continue
                    if (row.get("user_id") or "").strip() == user_id:
                        # Drop old user rows (we will replace)
                        continue
                    rows.append(
                        {
                            "user_id": (row.get("user_id") or "").strip(),
                            "category": (row.get("category") or "").strip().lower(),
                            "budget_limit": (row.get("budget_limit") or "").strip(),
                        }
                    )

        # Append new rows for this user
        for cat, limit in sorted(normalized.items()):
            rows.append({"user_id": user_id, "category": cat, "budget_limit": str(limit)})

        # Ensure parent dir exists
        parent = os.path.dirname(budgets_file)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)

        # Write back with header
        with open(budgets_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["user_id", "category", "budget_limit"])
            writer.writeheader()
            for r in rows:
                # Skip incomplete
                if not r.get("user_id") or not r.get("category") or not r.get("budget_limit"):
                    continue
                writer.writerow(r)

