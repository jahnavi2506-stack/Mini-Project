"""
Smart Savings Suggestions Module

Implements:
- Analysis of income and spending patterns
- Rule-based ML patterns for savings recommendations
- Savings percentage suggestions based on financial health
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
from datetime import datetime, timedelta

from .data_models import Transaction, UserProfile


@dataclass
class SavingsSuggestion:
    """Represents a savings suggestion."""
    suggested_monthly_savings: float
    savings_percentage: float
    current_savings_rate: float
    recommended_savings_range: Tuple[float, float]  # (min, max)
    reason: str
    priority: str  # 'high', 'medium', 'low'
    projected_yearly_savings: float


class SavingsAnalyzer:
    """
    Analyzes spending and income to suggest savings goals.
    
    Assumptions:
    - User has consistent income (monthly or can be estimated)
    - Spending patterns are relatively stable
    - Savings goals are based on percentage of income
    - Historical data reflects current financial situation
    """
    
    def __init__(
        self,
        min_savings_percentage: float = 0.10,
        ideal_savings_percentage: float = 0.15,
        max_savings_percentage: float = 0.30,
        lookback_months: int = 3
    ):
        """
        Initialize savings analyzer.
        
        Args:
            min_savings_percentage: Minimum recommended savings (10%)
            ideal_savings_percentage: Ideal savings target (15%)
            max_savings_percentage: Maximum realistic savings (30%)
            lookback_months: Number of months to analyze for patterns
        """
        assert 0 < min_savings_percentage < 1, "Min savings must be between 0 and 1"
        assert 0 < ideal_savings_percentage < 1, "Ideal savings must be between 0 and 1"
        assert 0 < max_savings_percentage < 1, "Max savings must be between 0 and 1"
        assert min_savings_percentage <= ideal_savings_percentage <= max_savings_percentage, \
            "Savings percentages must be in ascending order"
        assert lookback_months > 0, "Lookback months must be positive"
        
        self.min_savings_percentage = min_savings_percentage
        self.ideal_savings_percentage = ideal_savings_percentage
        self.max_savings_percentage = max_savings_percentage
        self.lookback_months = lookback_months
    
    def _calculate_monthly_income(
        self,
        transactions: List[Transaction],
        user_profile: Optional[UserProfile] = None
    ) -> Optional[float]:
        """
        Calculate or estimate monthly income.
        
        Args:
            transactions: List of transactions (may include income)
            user_profile: User profile with income information
            
        Returns:
            Estimated monthly income or None
        """
        # First, try to get from user profile
        if user_profile and user_profile.monthly_income:
            return user_profile.monthly_income
        
        # Otherwise, try to infer from transactions
        # Look for positive amounts that might be income
        # This is a placeholder - actual implementation depends on dataset structure
        income_transactions = [
            t for t in transactions
            if t.amount > 0  # Income is typically positive
        ]
        
        if not income_transactions:
            return None
        
        # Group by month
        monthly_income = defaultdict(float)
        for transaction in income_transactions:
            month_key = transaction.timestamp.strftime('%Y-%m')
            monthly_income[month_key] += transaction.amount
        
        if not monthly_income:
            return None
        
        # Return average monthly income
        return sum(monthly_income.values()) / len(monthly_income)
    
    def _calculate_monthly_spending(
        self,
        transactions: List[Transaction],
        lookback_months: Optional[int] = None
    ) -> float:
        """
        Calculate average monthly spending.
        
        Args:
            transactions: List of transactions
            lookback_months: Number of months to look back (uses self.lookback_months if None)
            
        Returns:
            Average monthly spending
        """
        if lookback_months is None:
            lookback_months = self.lookback_months
        
        if not transactions:
            return 0.0
        
        # Filter to expenses (negative amounts or positive if dataset uses different convention)
        # This assumes expenses are negative or we take absolute value
        expense_transactions = [
            t for t in transactions
            if t.amount < 0 or (t.category and t.category != 'income')
        ]
        
        if not expense_transactions:
            return 0.0
        
        # Calculate cutoff date
        if expense_transactions:
            latest_date = max(t.timestamp for t in expense_transactions)
            cutoff_date = latest_date - timedelta(days=lookback_months * 30)
            
            # Filter to recent transactions
            recent_transactions = [
                t for t in expense_transactions
                if t.timestamp >= cutoff_date
            ]
        else:
            recent_transactions = expense_transactions
        
        # Group by month
        monthly_spending = defaultdict(float)
        for transaction in recent_transactions:
            month_key = transaction.timestamp.strftime('%Y-%m')
            monthly_spending[month_key] += abs(transaction.amount)
        
        if not monthly_spending:
            return 0.0
        
        return sum(monthly_spending.values()) / len(monthly_spending)
    
    def _calculate_current_savings_rate(
        self,
        monthly_income: float,
        monthly_spending: float
    ) -> float:
        """
        Calculate current savings rate.
        
        Args:
            monthly_income: Monthly income
            monthly_spending: Monthly spending
            
        Returns:
            Current savings rate (0.0 to 1.0)
        """
        if monthly_income <= 0:
            return 0.0
        
        savings = monthly_income - monthly_spending
        return max(0.0, savings / monthly_income)
    
    def generate_suggestion(
        self,
        transactions: List[Transaction],
        user_profile: Optional[UserProfile] = None
    ) -> Optional[SavingsSuggestion]:
        """
        Generate savings suggestion based on income and spending patterns.
        
        Args:
            transactions: List of historical transactions
            user_profile: User profile with income information
            
        Returns:
            SavingsSuggestion object or None if insufficient data
        """
        if not transactions:
            return None
        
        # Calculate monthly income
        monthly_income = self._calculate_monthly_income(transactions, user_profile)
        
        if monthly_income is None or monthly_income <= 0:
            # Cannot generate suggestion without income data
            return None
        
        # Calculate monthly spending
        monthly_spending = self._calculate_monthly_spending(transactions)
        
        # Calculate current savings rate
        current_savings_rate = self._calculate_current_savings_rate(
            monthly_income,
            monthly_spending
        )
        
        # Determine suggested savings percentage based on current rate
        if current_savings_rate < self.min_savings_percentage:
            # User is saving less than minimum - suggest minimum
            suggested_percentage = self.min_savings_percentage
            priority = 'high'
            reason = (
                f"Your current savings rate is {current_savings_rate*100:.1f}%. "
                f"Start by saving at least {self.min_savings_percentage*100:.0f}% of your income."
            )
        elif current_savings_rate < self.ideal_savings_percentage:
            # User is below ideal - suggest ideal
            suggested_percentage = self.ideal_savings_percentage
            priority = 'medium'
            reason = (
                f"Your current savings rate is {current_savings_rate*100:.1f}%. "
                f"Aim to save {self.ideal_savings_percentage*100:.0f}% of your income "
                f"for better financial security."
            )
        else:
            # User is already saving well - suggest maintaining or slightly increasing
            suggested_percentage = min(
                current_savings_rate + 0.05,  # Suggest 5% increase
                self.max_savings_percentage
            )
            priority = 'low'
            reason = (
                f"Great job! You're saving {current_savings_rate*100:.1f}% of your income. "
                f"Consider increasing to {suggested_percentage*100:.0f}% for even better results."
            )
        
        # Calculate suggested monthly savings
        suggested_monthly_savings = monthly_income * suggested_percentage
        
        # Calculate recommended range
        recommended_min = monthly_income * self.min_savings_percentage
        recommended_max = monthly_income * self.max_savings_percentage
        
        # Project yearly savings
        projected_yearly_savings = suggested_monthly_savings * 12
        
        return SavingsSuggestion(
            suggested_monthly_savings=suggested_monthly_savings,
            savings_percentage=suggested_percentage,
            current_savings_rate=current_savings_rate,
            recommended_savings_range=(recommended_min, recommended_max),
            reason=reason,
            priority=priority,
            projected_yearly_savings=projected_yearly_savings
        )
    
    def get_financial_summary(
        self,
        transactions: List[Transaction],
        user_profile: Optional[UserProfile] = None
    ) -> Dict[str, Any]:
        """
        Get financial summary for analysis.
        
        Args:
            transactions: List of transactions
            user_profile: User profile
            
        Returns:
            Dictionary with financial summary
        """
        monthly_income = self._calculate_monthly_income(transactions, user_profile)
        monthly_spending = self._calculate_monthly_spending(transactions)
        
        if monthly_income and monthly_income > 0:
            current_savings_rate = self._calculate_current_savings_rate(
                monthly_income,
                monthly_spending
            )
        else:
            current_savings_rate = None
        
        return {
            "monthly_income": float(monthly_income) if monthly_income else None,
            "monthly_spending": float(monthly_spending),
            "current_savings_rate": float(current_savings_rate) if current_savings_rate else None,
            "lookback_months": self.lookback_months
        }
