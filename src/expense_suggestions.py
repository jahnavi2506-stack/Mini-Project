"""
Personalized Expense Suggestions Module

Implements:
- K-Means clustering to identify spending patterns
- Analysis of spending by category
- Personalized suggestions for expense reduction
"""

import numpy as np
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict
from sklearn.cluster import KMeans

from .data_models import Transaction


@dataclass
class ExpenseSuggestion:
    """Represents a personalized expense suggestion."""
    category: str
    current_monthly_spend: float
    suggested_reduction: float
    potential_savings: float
    reason: str
    priority: str  # 'high', 'medium', 'low'


class ExpenseAnalyzer:
    def __init__(
        self,
        n_clusters: int = 3,
        reduction_percentage: float = 0.2,
        min_transactions_per_category: int = 3,
        random_state: int = 42
    ):
        assert n_clusters > 0, "Number of clusters must be positive"
        assert 0 < reduction_percentage < 1, "Reduction percentage must be between 0 and 1"
        assert min_transactions_per_category > 0, "Minimum transactions must be positive"
        
        self.n_clusters = n_clusters
        self.reduction_percentage = reduction_percentage
        self.min_transactions_per_category = min_transactions_per_category
        self.random_state = random_state
        self.kmeans_model = None
        self.category_patterns = None
        self._is_fitted = False
    
    def _group_by_category(
        self,
        transactions: List[Transaction]
    ) -> Dict[str, List[Transaction]]:
        """
        Group transactions by category.
        
        Args:
            transactions: List of transactions
            
        Returns:
            Dictionary mapping category to list of transactions
        """
        category_groups = defaultdict(list)
        
        for transaction in transactions:
            # Use category if available, otherwise use 'uncategorized'
            category = transaction.category or 'uncategorized'
            category_groups[category].append(transaction)
        
        return dict(category_groups)
    
    def _calculate_monthly_spending(
        self,
        transactions: List[Transaction]
    ) -> float:
        """
        Calculate average monthly spending from transactions.
        
        Args:
            transactions: List of transactions
            
        Returns:
            Average monthly spending amount
        """
        if not transactions:
            return 0.0
        
        # Group by month and calculate total per month
        monthly_totals = defaultdict(float)
        
        for transaction in transactions:
            # Extract year-month as key
            month_key = transaction.timestamp.strftime('%Y-%m')
            monthly_totals[month_key] += abs(transaction.amount)
        
        if not monthly_totals:
            return 0.0
        
        # Return average monthly spending
        return np.mean(list(monthly_totals.values()))
    
    def fit(self, transactions: List[Transaction]) -> None:
        """
        Fit the expense analyzer on historical data.
        
        Args:
            transactions: List of historical transactions
            
        Raises:
            ValueError: If insufficient data for analysis
        """
        if len(transactions) < self.min_transactions_per_category * 2:
            raise ValueError(
                f"Insufficient data for expense analysis. "
                f"Need at least {self.min_transactions_per_category * 2} transactions."
            )
        
        # Group transactions by category
        category_groups = self._group_by_category(transactions)
        
        # Calculate spending patterns per category
        self.category_patterns = {}
        
        for category, cat_transactions in category_groups.items():
            if len(cat_transactions) >= self.min_transactions_per_category:
                monthly_spend = self._calculate_monthly_spending(cat_transactions)
                avg_transaction = np.mean([abs(t.amount) for t in cat_transactions])
                
                self.category_patterns[category] = {
                    'monthly_spend': monthly_spend,
                    'avg_transaction': avg_transaction,
                    'transaction_count': len(cat_transactions),
                    'transactions': cat_transactions
                }
        
        # Fit K-Means on spending features (amount, frequency)
        if len(self.category_patterns) >= self.n_clusters:
            features = []
            categories = []
            
            for category, pattern in self.category_patterns.items():
                features.append([
                    pattern['monthly_spend'],
                    pattern['avg_transaction'],
                    pattern['transaction_count']
                ])
                categories.append(category)
            
            features = np.array(features)
            
            # Normalize features for clustering
            features_normalized = (
                (features - features.mean(axis=0)) / (features.std(axis=0) + 1e-6)
            )
            
            self.kmeans_model = KMeans(
                n_clusters=min(self.n_clusters, len(categories)),
                random_state=self.random_state,
                n_init=10
            )
            self.kmeans_model.fit(features_normalized)
        
        self._is_fitted = True
    
    def generate_suggestions(
        self,
        transactions: List[Transaction],
        top_n: int = 3
    ) -> List[ExpenseSuggestion]:
        """
        Generate personalized expense reduction suggestions.
        
        Args:
            transactions: Recent transactions to analyze
            top_n: Number of top suggestions to return
            
        Returns:
            List of ExpenseSuggestion objects, sorted by potential savings
        """
        if not self._is_fitted:
            raise ValueError("Model must be fitted before generating suggestions")
        
        if not transactions:
            return []
        
        # Calculate current spending by category
        category_groups = self._group_by_category(transactions)
        current_spending = {}
        
        for category, cat_transactions in category_groups.items():
            monthly_spend = self._calculate_monthly_spending(cat_transactions)
            current_spending[category] = monthly_spend
        
        suggestions = []
        
        # Generate suggestions for each category
        for category, monthly_spend in current_spending.items():
            if monthly_spend <= 0:
                continue
            
            # Compare with historical patterns if available
            historical_spend = (
                self.category_patterns.get(category, {}).get('monthly_spend', 0)
            )
            
            # Use current or historical, whichever is higher
            reference_spend = max(monthly_spend, historical_spend)
            
            # Calculate suggested reduction
            suggested_reduction = reference_spend * self.reduction_percentage
            potential_savings = suggested_reduction
            
            # Determine priority based on spending amount
            if reference_spend > 10000:  # High spending threshold
                priority = 'high'
            elif reference_spend > 5000:
                priority = 'medium'
            else:
                priority = 'low'
            
            # Format to match requirement: "You spend ₹X on Y monthly. Reduce it to save ₹Z."
            reason = (
                f"You spend ₹{reference_spend:.0f} on {category} monthly. "
                f"Reduce it to save ₹{potential_savings:.0f}."
            )
            
            suggestion = ExpenseSuggestion(
                category=category,
                current_monthly_spend=reference_spend,
                suggested_reduction=suggested_reduction,
                potential_savings=potential_savings,
                reason=reason,
                priority=priority
            )
            
            suggestions.append(suggestion)
        
        # Sort by potential savings (descending) and return top N
        suggestions.sort(key=lambda x: x.potential_savings, reverse=True)
        return suggestions[:top_n]
    
    def get_spending_patterns(self) -> Dict[str, Any]:
        """
        Get identified spending patterns.
        
        Returns:
            Dictionary with spending pattern information
        """
        if not self._is_fitted:
            return {"status": "not_fitted"}
        
        return {
            "status": "fitted",
            "category_patterns": {
                cat: {
                    "monthly_spend": float(pattern['monthly_spend']),
                    "avg_transaction": float(pattern['avg_transaction']),
                    "transaction_count": pattern['transaction_count']
                }
                for cat, pattern in self.category_patterns.items()
            },
            "n_clusters": self.n_clusters if self.kmeans_model else 0
        }
