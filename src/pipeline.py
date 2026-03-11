"""
Main Pipeline Orchestrator

Coordinates all ML features and provides a unified interface.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from .data_models import Transaction, UserProfile, DataLoader
from .anomaly_detection import AnomalyDetector
from .expense_suggestions import ExpenseAnalyzer
from .transaction_categorization import TransactionCategorizer
from .savings_suggestions import SavingsAnalyzer
from .notifications import NotificationEngine


class FinanceMLPipeline:
    """
    Main pipeline that orchestrates all ML features.
    
    This class provides a unified interface to:
    - Smart Spending Alerts (Anomaly Detection)
    - Personalized Expense Suggestions
    - Transaction Categorization
    - Smart Savings Suggestions
    - Smart Notifications System
    """
    
    def __init__(
        self,
        data_loader: DataLoader,
        anomaly_contamination: float = 0.05,
        z_score_threshold: float = 3.0,
        expense_n_clusters: int = 3,
        categorization_classifier: str = 'naive_bayes',
        random_state: int = 42
    ):
        """
        Initialize the ML pipeline.
        
        Args:
            data_loader: DataLoader instance for loading transactions
            anomaly_contamination: Contamination rate for anomaly detection
            z_score_threshold: Z-score threshold for anomaly detection
            expense_n_clusters: Number of clusters for expense analysis
            categorization_classifier: 'naive_bayes' or 'logistic_regression'
            random_state: Random seed for reproducibility
        """
        self.data_loader = data_loader
        
        # Initialize all components
        self.anomaly_detector = AnomalyDetector(
            contamination=anomaly_contamination,
            z_score_threshold=z_score_threshold,
            random_state=random_state
        )
        
        self.expense_analyzer = ExpenseAnalyzer(
            n_clusters=expense_n_clusters,
            random_state=random_state
        )
        
        self.transaction_categorizer = TransactionCategorizer(
            classifier_type=categorization_classifier,
            random_state=random_state
        )
        
        self.savings_analyzer = SavingsAnalyzer()
        
        self.notification_engine = NotificationEngine()
        
        self._is_trained = False
    
    def train(
        self,
        user_id: Optional[str] = None,
        min_transactions: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Train all ML models on historical data.
        Adapts to available data - trains with whatever transactions are available.
        
        Args:
            user_id: Optional user ID to filter transactions
            min_transactions: Optional minimum (if None, trains with any available data)
            
        Returns:
            Dictionary with training status for each component
        """
        # Load historical transactions
        transactions = self.data_loader.load_transactions(user_id=user_id)
        
        training_status = {
            'total_transactions': len(transactions),
            'trained_components': []
        }
        
        # Train anomaly detector (needs at least 2 transactions)
        if len(transactions) >= 2:
            try:
                self.anomaly_detector.fit(transactions)
                training_status['anomaly_detector'] = 'success'
                training_status['trained_components'].append('anomaly_detector')
            except Exception as e:
                training_status['anomaly_detector'] = f'failed: {str(e)}'
        else:
            training_status['anomaly_detector'] = f'skipped: need at least 2 transactions (have {len(transactions)})'
        
        # Train expense analyzer (needs at least 2 transactions)
        if len(transactions) >= 2:
            try:
                self.expense_analyzer.fit(transactions)
                training_status['expense_analyzer'] = 'success'
                training_status['trained_components'].append('expense_analyzer')
            except Exception as e:
                training_status['expense_analyzer'] = f'failed: {str(e)}'
        else:
            training_status['expense_analyzer'] = f'skipped: need at least 2 transactions (have {len(transactions)})'
        
        # Train transaction categorizer (needs labeled data)
        labeled_transactions = [
            t for t in transactions
            if t.category is not None and t.category.strip()
        ]
        
        if len(labeled_transactions) >= 2:
            try:
                # Use flexible minimum - at least 1 per category if possible
                min_samples = max(1, len(labeled_transactions) // 4)  # Adaptive minimum
                self.transaction_categorizer.fit(labeled_transactions, min_samples_per_category=min_samples)
                training_status['transaction_categorizer'] = 'success'
                training_status['trained_components'].append('transaction_categorizer')
            except Exception as e:
                training_status['transaction_categorizer'] = f'failed: {str(e)}'
        else:
            training_status['transaction_categorizer'] = f'skipped: need at least 2 labeled transactions (have {len(labeled_transactions)})'
        
        # Mark as trained if at least one component trained
        if training_status['trained_components']:
            self._is_trained = True
        
        return training_status
    
    def process_transactions(
        self,
        transactions: List[Transaction],
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process new transactions through the entire pipeline.
        
        Args:
            transactions: List of new transactions to process
            user_id: Optional user ID
            
        Returns:
            Dictionary with all pipeline outputs
        """
        if not self._is_trained:
            raise ValueError("Pipeline must be trained before processing transactions")
        
        if not transactions:
            return {
                'anomaly_alerts': [],
                'categorized_transactions': [],
                'notifications': []
            }
        
        results = {}
        
        # 1. Anomaly Detection (if model is trained)
        anomaly_alerts_objects = []
        if self.anomaly_detector._is_fitted:
            anomaly_alerts_objects = self.anomaly_detector.detect_anomalies(transactions)
        
        # Convert to dict format for results
        anomaly_alerts_dict = [
            {
                'transaction_id': getattr(t.transaction, 'id', None),
                'amount': t.transaction.amount,
                'description': t.transaction.description,
                'method': t.method,
                'score': t.anomaly_score,
                'reason': t.reason,
                'timestamp': t.transaction.timestamp.isoformat()
            }
            for t in anomaly_alerts_objects
        ]
        
        results['anomaly_alerts'] = anomaly_alerts_dict
        
        # 2. Transaction Categorization (if model is trained)
        categorized = []
        if self.transaction_categorizer._is_fitted:
            # Only categorize transactions without categories
            uncategorized = [
                t for t in transactions
                if not t.category or not t.category.strip()
            ]
            
            if uncategorized:
                predictions = self.transaction_categorizer.predict_batch(uncategorized)
                categorized = [
                    {
                        'transaction_id': getattr(p.transaction, 'id', None),
                        'description': p.transaction.description,
                        'predicted_category': p.predicted_category,
                        'confidence': p.confidence,
                        'alternatives': [
                            {'category': cat, 'confidence': conf}
                            for cat, conf in p.alternative_categories
                        ]
                    }
                    for p in predictions
                ]
        
        results['categorized_transactions'] = categorized
        
        # 3. Generate notifications
        # Load all user transactions for pattern analysis
        all_transactions = self.data_loader.load_transactions(user_id=user_id)
        user_profile = None
        if user_id:
            user_profile = self.data_loader.load_user_profile(user_id)
        
        # Pass anomaly alerts to notification engine for high expenditure notifications
        # Pass both objects (for internal processing) and dicts (for display)
        notifications = self.notification_engine.generate_contextual_notifications(
            all_transactions,
            user_profile,
            anomaly_alerts=anomaly_alerts_dict  # Pass anomaly alerts for notification generation
        )
        
        results['notifications'] = [
            {
                'type': n.notification_type,
                'title': n.title,
                'message': n.message,
                'priority': n.priority,
                'actionable': n.actionable,
                'action_suggestion': n.action_suggestion,
                'timestamp': n.timestamp.isoformat()
            }
            for n in notifications
        ]
        
        return results
    
    def get_personalized_insights(
        self,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get personalized insights and suggestions for a user.
        
        Args:
            user_id: User ID to generate insights for
            
        Returns:
            Dictionary with personalized insights
        """
        if not self._is_trained:
            raise ValueError("Pipeline must be trained before generating insights")
        
        # Load user data
        transactions = self.data_loader.load_transactions(user_id=user_id)
        user_profile = None
        if user_id:
            user_profile = self.data_loader.load_user_profile(user_id)
        
        insights = {}
        
        # 1. Expense Suggestions
        try:
            expense_suggestions = self.expense_analyzer.generate_suggestions(
                transactions,
                top_n=5
            )
            insights['expense_suggestions'] = [
                {
                    'category': s.category,
                    'current_monthly_spend': s.current_monthly_spend,
                    'suggested_reduction': s.suggested_reduction,
                    'potential_savings': s.potential_savings,
                    'reason': s.reason,
                    'priority': s.priority
                }
                for s in expense_suggestions
            ]
        except Exception as e:
            insights['expense_suggestions'] = f'error: {str(e)}'
        
        # 2. Savings Suggestions
        try:
            savings_suggestion = self.savings_analyzer.generate_suggestion(
                transactions,
                user_profile
            )
            if savings_suggestion:
                insights['savings_suggestion'] = {
                    'suggested_monthly_savings': savings_suggestion.suggested_monthly_savings,
                    'savings_percentage': savings_suggestion.savings_percentage,
                    'current_savings_rate': savings_suggestion.current_savings_rate,
                    'recommended_range': {
                        'min': savings_suggestion.recommended_savings_range[0],
                        'max': savings_suggestion.recommended_savings_range[1]
                    },
                    'projected_yearly_savings': savings_suggestion.projected_yearly_savings,
                    'reason': savings_suggestion.reason,
                    'priority': savings_suggestion.priority
                }
            else:
                insights['savings_suggestion'] = None
        except Exception as e:
            insights['savings_suggestion'] = f'error: {str(e)}'
        
        # 3. Financial Summary
        try:
            financial_summary = self.savings_analyzer.get_financial_summary(
                transactions,
                user_profile
            )
            insights['financial_summary'] = financial_summary
        except Exception as e:
            insights['financial_summary'] = f'error: {str(e)}'
        
        return insights
    
    def get_model_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about all trained models.
        
        Returns:
            Dictionary with model statistics
        """
        stats = {
            'training_status': 'trained' if self._is_trained else 'not_trained',
            'anomaly_detector': self.anomaly_detector.get_statistics(),
            'expense_analyzer': self.expense_analyzer.get_spending_patterns(),
            'transaction_categorizer': {
                'status': 'fitted' if self.transaction_categorizer._is_fitted else 'not_fitted',
                'classifier_type': self.transaction_categorizer.classifier_type,
                'categories': self.transaction_categorizer.get_category_mapping()
            }
        }
        
        return stats
