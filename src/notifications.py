"""
Smart Notifications System Module

Implements:
- Pattern mining for user behavior analysis
- Sequential analysis for recurring patterns
- Contextual notification triggers
"""

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from collections import defaultdict, Counter
from datetime import datetime, timedelta

from .data_models import Transaction, UserProfile


@dataclass
class Notification:
    """Represents a smart notification."""
    notification_type: str
    title: str
    message: str
    priority: str  # 'high', 'medium', 'low'
    trigger_reason: str
    timestamp: datetime
    actionable: bool  # Whether user can take action
    action_suggestion: Optional[str] = None


class PatternMiner:
    """
    Mines patterns from transaction sequences.
    
    Assumptions:
    - Recurring transactions indicate patterns (rent, subscriptions, etc.)
    - Temporal patterns are meaningful (weekly, monthly, etc.)
    - Similar amounts at similar times indicate recurring expenses
    """
    
    def __init__(
        self,
        similarity_threshold: float = 0.15,  # 15% variance allowed
        min_pattern_occurrences: int = 2,
        pattern_window_days: int = 5
    ):
        """
        Initialize pattern miner.
        
        Args:
            similarity_threshold: Amount similarity threshold (0.15 = 15% variance)
            min_pattern_occurrences: Minimum occurrences to consider a pattern
            pattern_window_days: Days around expected date to look for pattern
        """
        assert 0 < similarity_threshold < 1, "Similarity threshold must be between 0 and 1"
        assert min_pattern_occurrences > 0, "Minimum occurrences must be positive"
        assert pattern_window_days > 0, "Pattern window must be positive"
        
        self.similarity_threshold = similarity_threshold
        self.min_pattern_occurrences = min_pattern_occurrences
        self.pattern_window_days = pattern_window_days
    
    def _amounts_similar(
        self,
        amount1: float,
        amount2: float
    ) -> bool:
        """
        Check if two amounts are similar within threshold.
        
        Args:
            amount1: First amount
            amount2: Second amount
            
        Returns:
            True if amounts are similar
        """
        if amount1 == 0 and amount2 == 0:
            return True
        
        max_amount = max(abs(amount1), abs(amount2))
        if max_amount == 0:
            return True
        
        difference = abs(amount1 - amount2)
        return (difference / max_amount) <= self.similarity_threshold
    
    def _extract_recurring_patterns(
        self,
        transactions: List[Transaction]
    ) -> List[Dict[str, Any]]:
        """
        Extract recurring transaction patterns.
        
        Args:
            transactions: List of transactions
            
        Returns:
            List of pattern dictionaries
        """
        if len(transactions) < self.min_pattern_occurrences:
            return []
        
        # Group by category and merchant
        patterns = defaultdict(list)
        
        for transaction in transactions:
            # Create pattern key from category and merchant
            key = (
                transaction.category or 'uncategorized',
                transaction.merchant or transaction.description[:20]
            )
            patterns[key].append(transaction)
        
        identified_patterns = []
        
        for (category, merchant), pattern_transactions in patterns.items():
            if len(pattern_transactions) < self.min_pattern_occurrences:
                continue
            
            # Check if amounts are similar
            amounts = [abs(t.amount) for t in pattern_transactions]
            avg_amount = sum(amounts) / len(amounts)
            
            # Check similarity
            all_similar = all(
                self._amounts_similar(amount, avg_amount)
                for amount in amounts
            )
            
            if not all_similar:
                continue
            
            # Analyze temporal pattern
            sorted_transactions = sorted(
                pattern_transactions,
                key=lambda t: t.timestamp
            )
            
            # Calculate intervals between transactions
            intervals = []
            for i in range(1, len(sorted_transactions)):
                delta = sorted_transactions[i].timestamp - sorted_transactions[i-1].timestamp
                intervals.append(delta.days)
            
            if intervals:
                avg_interval = sum(intervals) / len(intervals)
                
                # Determine pattern type
                if 25 <= avg_interval <= 35:
                    pattern_type = 'monthly'
                elif 6 <= avg_interval <= 8:
                    pattern_type = 'weekly'
                elif 85 <= avg_interval <= 95:
                    pattern_type = 'quarterly'
                else:
                    pattern_type = 'irregular'
                
                identified_patterns.append({
                    'category': category,
                    'merchant': merchant,
                    'amount': avg_amount,
                    'pattern_type': pattern_type,
                    'interval_days': avg_interval,
                    'occurrences': len(pattern_transactions),
                    'last_occurrence': sorted_transactions[-1].timestamp,
                    'transactions': sorted_transactions
                })
        
        return identified_patterns
    
    def find_upcoming_patterns(
        self,
        transactions: List[Transaction],
        lookahead_days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Find patterns that are expected to occur soon.
        
        Args:
            transactions: Historical transactions
            lookahead_days: Days ahead to look for expected patterns
            
        Returns:
            List of upcoming pattern predictions
        """
        patterns = self._extract_recurring_patterns(transactions)
        
        if not patterns:
            return []
        
        upcoming = []
        today = datetime.now()
        
        for pattern in patterns:
            last_occurrence = pattern['last_occurrence']
            interval_days = pattern['interval_days']
            
            # Calculate next expected occurrence
            next_expected = last_occurrence + timedelta(days=interval_days)
            
            # Check if it's within lookahead window
            days_until = (next_expected - today).days
            
            if 0 <= days_until <= lookahead_days:
                pattern['next_expected'] = next_expected
                pattern['days_until'] = days_until
                upcoming.append(pattern)
        
        return upcoming


class NotificationEngine:
    """
    Generates contextual notifications based on patterns and user behavior.
    
    Assumptions:
    - Users benefit from proactive notifications
    - Notifications should be timely and relevant
    - Too many notifications reduce engagement
    - Context matters (rent due, unusual spending, etc.)
    """
    
    def __init__(
        self,
        pattern_miner: Optional[PatternMiner] = None,
        notification_cooldown_hours: int = 24
    ):
        """
        Initialize notification engine.
        
        Args:
            pattern_miner: PatternMiner instance (creates new if None)
            notification_cooldown_hours: Minimum hours between similar notifications
        """
        self.pattern_miner = pattern_miner or PatternMiner()
        self.notification_cooldown_hours = notification_cooldown_hours
        self.last_notifications = defaultdict(datetime)  # Track last notification time by type
    
    def _should_send_notification(
        self,
        notification_type: str
    ) -> bool:
        """
        Check if notification should be sent (cooldown check).
        
        Args:
            notification_type: Type of notification
            
        Returns:
            True if notification should be sent
        """
        if notification_type not in self.last_notifications:
            return True
        
        last_sent = self.last_notifications[notification_type]
        hours_since = (datetime.now() - last_sent).total_seconds() / 3600
        
        return hours_since >= self.notification_cooldown_hours
    
    def generate_pattern_notifications(
        self,
        transactions: List[Transaction],
        lookahead_days: int = 7
    ) -> List[Notification]:
        """
        Generate notifications for upcoming recurring patterns.
        
        Args:
            transactions: Historical transactions
            lookahead_days: Days ahead to check for patterns
            
        Returns:
            List of Notification objects
        """
        if not self._should_send_notification('pattern_reminder'):
            return []
        
        upcoming_patterns = self.pattern_miner.find_upcoming_patterns(
            transactions,
            lookahead_days
        )
        
        notifications = []
        
        for pattern in upcoming_patterns:
            days_until = pattern['days_until']
            amount = pattern['amount']
            category = pattern['category']
            merchant = pattern['merchant']
            
            if days_until == 0:
                title = f"Payment Due Today: {merchant}"
                message = (
                    f"Your {category} payment of Rs {amount:.2f} to {merchant} "
                    f"is due today."
                )
                priority = 'high'
            elif days_until <= 2:
                title = f"Upcoming Payment: {merchant}"
                message = (
                    f"Your {category} payment of Rs {amount:.2f} to {merchant} "
                    f"is due in {days_until} day(s)."
                )
                priority = 'high'
            else:
                title = f"Reminder: {merchant} Payment"
                message = (
                    f"Your recurring {category} payment of Rs {amount:.2f} "
                    f"is expected in {days_until} days."
                )
                priority = 'medium'
            
            notification = Notification(
                notification_type='pattern_reminder',
                title=title,
                message=message,
                priority=priority,
                trigger_reason=f"Recurring pattern detected: {pattern['pattern_type']}",
                timestamp=datetime.now(),
                actionable=True,
                action_suggestion=f"Ensure sufficient funds for Rs {amount:.2f} payment"
            )
            
            notifications.append(notification)
        
        if notifications:
            self.last_notifications['pattern_reminder'] = datetime.now()
        
        return notifications
    
    def generate_spending_notifications(
        self,
        transactions: List[Transaction],
        monthly_budget: Optional[float] = None,
        current_month_spending: Optional[float] = None
    ) -> List[Notification]:
        """
        Generate notifications based on spending patterns.
        
        Args:
            transactions: Recent transactions
            monthly_budget: Monthly budget limit (if available)
            current_month_spending: Current month's spending (if available)
            
        Returns:
            List of Notification objects
        """
        if not transactions:
            return []
        
        notifications = []
        
        # Budget warning notification
        if monthly_budget and current_month_spending is not None:
            if not self._should_send_notification('budget_warning'):
                return notifications
            
            spending_percentage = (current_month_spending / monthly_budget) * 100
            
            if spending_percentage >= 90:
                title = "Budget Alert: Near Limit"
                message = (
                    f"You've spent {spending_percentage:.1f}% of your monthly budget. "
                    f"Only Rs {monthly_budget - current_month_spending:.2f} remaining."
                )
                priority = 'high'
                action_suggestion = "Review recent expenses and adjust spending"
            elif spending_percentage >= 75:
                title = "Budget Warning: 75% Spent"
                message = (
                    f"You've used {spending_percentage:.1f}% of your monthly budget. "
                    f"Rs {monthly_budget - current_month_spending:.2f} remaining."
                )
                priority = 'medium'
                action_suggestion = "Monitor spending for the rest of the month"
            else:
                return notifications  # No notification needed
            
            notification = Notification(
                notification_type='budget_warning',
                title=title,
                message=message,
                priority=priority,
                trigger_reason=f"Budget usage: {spending_percentage:.1f}%",
                timestamp=datetime.now(),
                actionable=True,
                action_suggestion=action_suggestion
            )
            
            notifications.append(notification)
            self.last_notifications['budget_warning'] = datetime.now()
        
        return notifications
    
    def generate_anomaly_notifications(
        self,
        anomaly_alerts: List[Any]  # List of AnomalyAlert objects or dicts
    ) -> List[Notification]:
        """
        Generate notifications for detected anomalies.
        
        Args:
            anomaly_alerts: List of AnomalyAlert objects
            
        Returns:
            List of Notification objects for anomalies
        """
        notifications = []
        
        if not anomaly_alerts:
            return notifications
        
        for alert in anomaly_alerts:
            # Check if we should send notification (cooldown)
            if not self._should_send_notification('anomaly_alert'):
                continue
            
            # Handle both AnomalyAlert objects and dicts
            if isinstance(alert, dict):
                # Already converted to dict in pipeline
                amount = abs(alert.get('amount', 0))
                description = alert.get('description', 'Unknown')
                reason = alert.get('reason', 'Unusual transaction detected')
                method = alert.get('method', 'unknown')
                score = alert.get('score', 0)
            else:
                # AnomalyAlert object
                amount = abs(alert.transaction.amount)
                description = alert.transaction.description
                reason = alert.reason
                method = alert.method
                score = alert.anomaly_score
            
            if amount > 50000:
                priority = 'high'
                title = "⚠️ High Expenditure Alert!"
                message = (
                    f"Unusual transaction detected: Rs {amount:,.2f} for '{description}'. "
                    f"This is significantly higher than your usual spending pattern. "
                    f"Please verify this transaction."
                )
            elif amount > 20000:
                priority = 'high'
                title = "⚠️ Unusual Spending Detected"
                message = (
                    f"Transaction of Rs {amount:,.2f} for '{description}' "
                    f"is unusual compared to your spending history. Please review."
                )
            else:
                priority = 'medium'
                title = "⚠️ Spending Alert"
                message = (
                    f"Transaction of Rs {amount:,.2f} for '{description}' "
                    f"is higher than usual. {reason}"
                )
            
            notification = Notification(
                notification_type='anomaly_alert',
                title=title,
                message=message,
                priority=priority,
                trigger_reason=f"Anomaly detected: {method} method, score: {score:.4f}",
                timestamp=datetime.now(),
                actionable=True,
                action_suggestion="Review this transaction and verify if it's legitimate"
            )
            
            notifications.append(notification)
        
        if notifications:
            self.last_notifications['anomaly_alert'] = datetime.now()
        
        return notifications
    
    def generate_contextual_notifications(
        self,
        transactions: List[Transaction],
        user_profile: Optional[UserProfile] = None,
        anomaly_alerts: Optional[List[Any]] = None
    ) -> List[Notification]:
        """
        Generate all contextual notifications.
        
        Args:
            transactions: Historical transactions
            user_profile: User profile information
            anomaly_alerts: Optional list of AnomalyAlert objects
            
        Returns:
            List of all Notification objects
        """
        all_notifications = []
        
        # Anomaly-based notifications (if provided)
        if anomaly_alerts:
            anomaly_notifications = self.generate_anomaly_notifications(anomaly_alerts)
            all_notifications.extend(anomaly_notifications)
        
        # Pattern-based notifications
        pattern_notifications = self.generate_pattern_notifications(transactions)
        all_notifications.extend(pattern_notifications)
        
        # Spending notifications (if budget data available)
        spending_notifications = self.generate_spending_notifications(transactions)
        all_notifications.extend(spending_notifications)
        
        # Sort by priority (high -> medium -> low)
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        all_notifications.sort(key=lambda n: priority_order.get(n.priority, 3))
        
        return all_notifications
