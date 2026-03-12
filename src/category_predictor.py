"""
AI Expense Categorization (rule-based)

Predicts transaction category from description / merchant using keywords.
"""

from __future__ import annotations

from typing import Optional


KEYWORDS = {
    "food": ["pizza", "dominos", "swiggy", "zomato", "kfc", "mcd", "restaurant", "cafe", "food", "burger"],
    "transport": ["uber", "ola", "metro", "bus", "train", "fuel", "petrol", "diesel", "rapido", "auto"],
    "shopping": ["amazon", "flipkart", "myntra", "shopping", "store", "mall"],
    "bills": ["electricity", "water", "gas", "recharge", "internet", "wifi", "broadband", "bill", "rent"],
    "education": ["tuition", "course", "udemy", "coursera", "school", "college", "university", "books", "fee", "education", "training", "certification"],
    "entertainment": ["netflix", "movie", "spotify", "prime video", "hotstar", "cinema", "gaming"],
}


def predict_category(description: Optional[str], merchant: Optional[str]) -> str:
    text = f"{description or ''} {merchant or ''}".strip().lower()
    if not text:
        return "other"

    for category, words in KEYWORDS.items():
        for w in words:
            if w in text:
                return category

    return "other"

