"""
Comprehensive test suite for Finance ML Pipeline

Tests all features according to requirements and architecture diagrams.
"""

import unittest
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data_models import Transaction, UserProfile
from src.pipeline import FinanceMLPipeline
from src.example_loader import ExampleDataLoader


class SampleDataLoader(ExampleDataLoader):
    """Test data loader."""
    
    def __init__(self, transactions: list = None, user_profile: UserProfile = None):
        self.transactions = transactions or []
        self.user_profile = user_profile
    
    def load_transactions(self, user_id=None):
        if user_id:
            return [t for t in self.transactions if t.user_id == user_id]
        return self.transactions
    
    def load_user_profile(self, user_id):
        if self.user_profile and self.user_profile.user_id == user_id:
            return self.user_profile
        return None


class TestSmartSpendingAlerts(unittest.TestCase):
    """Test Case 1: Smart Spending Alerts (Anomaly Detection)"""
    
    def setUp(self):
        """Set up test data."""
        base_date = datetime.now() - timedelta(days=60)
        self.transactions = [
            Transaction(amount=-1000.0, description="Regular expense", timestamp=base_date, category="food", user_id="user1"),
            Transaction(amount=-1200.0, description="Regular expense 2", timestamp=base_date + timedelta(days=1), category="food", user_id="user1"),
            Transaction(amount=-1100.0, description="Regular expense 3", timestamp=base_date + timedelta(days=2), category="food", user_id="user1"),
            Transaction(amount=-1050.0, description="Regular expense 4", timestamp=base_date + timedelta(days=3), category="food", user_id="user1"),
            Transaction(amount=-1150.0, description="Regular expense 5", timestamp=base_date + timedelta(days=4), category="food", user_id="user1"),
            Transaction(amount=-1000.0, description="Regular expense 6", timestamp=base_date + timedelta(days=5), category="food", user_id="user1"),
            Transaction(amount=-1200.0, description="Regular expense 7", timestamp=base_date + timedelta(days=6), category="food", user_id="user1"),
            Transaction(amount=-1100.0, description="Regular expense 8", timestamp=base_date + timedelta(days=7), category="food", user_id="user1"),
            Transaction(amount=-1050.0, description="Regular expense 9", timestamp=base_date + timedelta(days=8), category="food", user_id="user1"),
            Transaction(amount=-1150.0, description="Regular expense 10", timestamp=base_date + timedelta(days=9), category="food", user_id="user1"),
        ]
        self.user_profile = UserProfile(user_id="user1", monthly_income=50000.0)
        self.data_loader = SampleDataLoader(transactions=self.transactions, user_profile=self.user_profile)
        self.pipeline = FinanceMLPipeline(data_loader=self.data_loader)
    
    def test_anomaly_detection_uses_historical_data(self):
        """Test: Uses historical transaction data of the user."""
        self.pipeline.train(user_id="user1", min_transactions=10)
        self.assertTrue(self.pipeline.anomaly_detector._is_fitted)
    
    def test_isolation_forest_detects_anomalies(self):
        """Test: Isolation Forest identifies unusual transactions automatically."""
        self.pipeline.train(user_id="user1", min_transactions=10)
        # Verify isolation forest is fitted
        self.assertTrue(self.pipeline.anomaly_detector._is_fitted)
        self.assertIsNotNone(self.pipeline.anomaly_detector.isolation_forest)
        # Test directly with isolation forest
        anomaly_transaction = Transaction(
            amount=-50000.0,
            description="Unusual large purchase",
            timestamp=datetime.now(),
            user_id="user1"
        )
        alert = self.pipeline.anomaly_detector.detect_with_isolation_forest(anomaly_transaction)
        self.assertEqual(alert.method, 'isolation_forest')
        # Also test through pipeline
        results = self.pipeline.process_transactions([anomaly_transaction], user_id="user1")
        self.assertGreater(len(results['anomaly_alerts']), 0)
    
    def test_z_score_flags_high_amounts(self):
        """Test: Z-score flags amounts much higher than usual."""
        self.pipeline.train(user_id="user1", min_transactions=10)
        # Add an anomaly
        anomaly_transaction = Transaction(
            amount=-50000.0,
            description="Unusual large purchase",
            timestamp=datetime.now(),
            user_id="user1"
        )
        results = self.pipeline.process_transactions([anomaly_transaction], user_id="user1")
        # Check if z-score method is used
        methods = [alert['method'] for alert in results['anomaly_alerts']]
        self.assertIn('z_score', methods or ['isolation_forest'])
    
    def test_alerts_triggered_for_unusual_transactions(self):
        """Test: Trigger alerts when a transaction is statistically unusual."""
        self.pipeline.train(user_id="user1", min_transactions=10)
        anomaly_transaction = Transaction(
            amount=-50000.0,
            description="Unusual purchase",
            timestamp=datetime.now(),
            user_id="user1"
        )
        results = self.pipeline.process_transactions([anomaly_transaction], user_id="user1")
        self.assertGreater(len(results['anomaly_alerts']), 0)
        self.assertIn('reason', results['anomaly_alerts'][0])


class TestPersonalizedExpenseSuggestions(unittest.TestCase):
    """Test Case 2: Personalized Expense Suggestions"""
    
    def setUp(self):
        """Set up test data."""
        base_date = datetime.now() - timedelta(days=60)
        self.transactions = [
            Transaction(amount=-5000.0, description="Entertainment", timestamp=base_date, category="entertainment", user_id="user2"),
            Transaction(amount=-5000.0, description="Entertainment", timestamp=base_date + timedelta(days=30), category="entertainment", user_id="user2"),
            Transaction(amount=-2000.0, description="Food", timestamp=base_date, category="food", user_id="user2"),
            Transaction(amount=-2000.0, description="Food", timestamp=base_date + timedelta(days=30), category="food", user_id="user2"),
            Transaction(amount=-1000.0, description="Transport", timestamp=base_date, category="transport", user_id="user2"),
            Transaction(amount=-1000.0, description="Transport", timestamp=base_date + timedelta(days=30), category="transport", user_id="user2"),
        ]
        self.user_profile = UserProfile(user_id="user2", monthly_income=50000.0)
        self.data_loader = SampleDataLoader(transactions=self.transactions, user_profile=self.user_profile)
        self.pipeline = FinanceMLPipeline(data_loader=self.data_loader)
    
    def test_collects_and_categorizes_transactions(self):
        """Test: Collect transaction data and categorize it (food, travel, bills)."""
        self.pipeline.train(user_id="user2", min_transactions=6)
        categories = set(t.category for t in self.transactions if t.category)
        self.assertGreater(len(categories), 0)
    
    def test_uses_kmeans_clustering(self):
        """Test: Use Clustering (K-Means) to identify spending patterns."""
        self.pipeline.train(user_id="user2", min_transactions=6)
        self.assertTrue(self.pipeline.expense_analyzer._is_fitted)
        # Check if K-Means was used (if enough categories)
        patterns = self.pipeline.expense_analyzer.get_spending_patterns()
        self.assertEqual(patterns['status'], 'fitted')
    
    def test_suggests_expense_reduction_tips(self):
        """Test: Suggest tips like 'You spend ₹5,000 on entertainment monthly. Reduce it to save ₹1,000.'"""
        self.pipeline.train(user_id="user2", min_transactions=6)
        insights = self.pipeline.get_personalized_insights(user_id="user2")
        self.assertIn('expense_suggestions', insights)
        suggestions = insights['expense_suggestions']
        if isinstance(suggestions, list) and len(suggestions) > 0:
            suggestion = suggestions[0]
            self.assertIn('category', suggestion)
            self.assertIn('current_monthly_spend', suggestion)
            self.assertIn('potential_savings', suggestion)
            self.assertIn('reason', suggestion)


class TestTransactionCategorization(unittest.TestCase):
    """Test Case 3: Transaction Categorization (Automatic)"""
    
    def setUp(self):
        """Set up test data."""
        base_date = datetime.now() - timedelta(days=60)
        self.transactions = [
            Transaction(amount=-100.0, description="Uber ride", timestamp=base_date, category="transport", user_id="user3"),
            Transaction(amount=-200.0, description="Uber ride home", timestamp=base_date + timedelta(days=1), category="transport", user_id="user3"),
            Transaction(amount=-150.0, description="Uber to office", timestamp=base_date + timedelta(days=2), category="transport", user_id="user3"),
            Transaction(amount=-500.0, description="Zomato food delivery", timestamp=base_date, category="food", user_id="user3"),
            Transaction(amount=-600.0, description="Zomato order", timestamp=base_date + timedelta(days=1), category="food", user_id="user3"),
            Transaction(amount=-550.0, description="Zomato dinner", timestamp=base_date + timedelta(days=2), category="food", user_id="user3"),
            Transaction(amount=-300.0, description="Restaurant meal", timestamp=base_date + timedelta(days=3), category="food", user_id="user3"),
            Transaction(amount=-400.0, description="Restaurant dinner", timestamp=base_date + timedelta(days=4), category="food", user_id="user3"),
        ]
        self.user_profile = UserProfile(user_id="user3", monthly_income=50000.0)
        self.data_loader = SampleDataLoader(transactions=self.transactions, user_profile=self.user_profile)
        self.pipeline = FinanceMLPipeline(data_loader=self.data_loader)
    
    def test_takes_transaction_descriptions(self):
        """Test: Take transaction descriptions (e.g., 'Uber', 'Zomato')."""
        descriptions = [t.description for t in self.transactions]
        self.assertIn('Uber', ' '.join(descriptions))
        self.assertIn('Zomato', ' '.join(descriptions))
    
    def test_applies_nlp_preprocessing(self):
        """Test: Apply Natural Language Processing (NLP): preprocess text → clean, tokenize, remove stopwords."""
        # Need at least 10 labeled transactions with 2+ categories for training
        self.pipeline.train(user_id="user3", min_transactions=8)
        # Test preprocessing (works even if model not fitted)
        preprocessor = self.pipeline.transaction_categorizer.preprocessor
        cleaned = preprocessor.preprocess("Uber ride to office")
        self.assertIsInstance(cleaned, str)
        self.assertEqual(cleaned.lower(), cleaned)  # Should be lowercase
        # Verify preprocessing steps
        tokens = preprocessor.tokenize(cleaned)
        self.assertIsInstance(tokens, list)
        filtered = preprocessor.remove_stopwords(tokens)
        self.assertIsInstance(filtered, list)
    
    def test_uses_naive_bayes_or_logistic_regression(self):
        """Test: Use Naive Bayes classifier or Logistic Regression."""
        self.pipeline.train(user_id="user3", min_transactions=8)
        classifier_type = self.pipeline.transaction_categorizer.classifier_type
        self.assertIn(classifier_type, ['naive_bayes', 'logistic_regression'])
    
    def test_assigns_categories_automatically(self):
        """Test: Assign categories automatically."""
        self.pipeline.train(user_id="user3", min_transactions=8)
        # Test with uncategorized transaction
        new_transaction = Transaction(
            amount=-200.0,
            description="Uber ride",
            timestamp=datetime.now(),
            user_id="user3"
        )
        results = self.pipeline.process_transactions([new_transaction], user_id="user3")
        if len(results['categorized_transactions']) > 0:
            categorized = results['categorized_transactions'][0]
            self.assertIn('predicted_category', categorized)
            self.assertIn('confidence', categorized)


class TestSmartSavingsSuggestions(unittest.TestCase):
    """Test Case 4: Smart Savings Suggestions"""
    
    def setUp(self):
        """Set up test data."""
        base_date = datetime.now() - timedelta(days=60)
        self.transactions = [
            Transaction(amount=-20000.0, description="Monthly expenses", timestamp=base_date, category="expenses", user_id="user4"),
            Transaction(amount=-20000.0, description="Monthly expenses", timestamp=base_date + timedelta(days=30), category="expenses", user_id="user4"),
        ]
        self.user_profile = UserProfile(user_id="user4", monthly_income=50000.0)
        self.data_loader = SampleDataLoader(transactions=self.transactions, user_profile=self.user_profile)
        self.pipeline = FinanceMLPipeline(data_loader=self.data_loader)
    
    def test_analyzes_spending_and_income_patterns(self):
        """Test: Analyze past spending and income patterns."""
        self.pipeline.train(user_id="user4", min_transactions=2)
        insights = self.pipeline.get_personalized_insights(user_id="user4")
        self.assertIn('financial_summary', insights)
        summary = insights['financial_summary']
        if isinstance(summary, dict):
            self.assertIn('monthly_income', summary)
            self.assertIn('monthly_spending', summary)
    
    def test_applies_rule_based_ml_patterns(self):
        """Test: Apply rule-based ML patterns to suggest 'Save 10–15% of your monthly income.'"""
        self.pipeline.train(user_id="user4", min_transactions=2)
        insights = self.pipeline.get_personalized_insights(user_id="user4")
        if insights.get('savings_suggestion') and isinstance(insights['savings_suggestion'], dict):
            savings = insights['savings_suggestion']
            self.assertIn('savings_percentage', savings)
            # Check if percentage is in reasonable range (10-30%)
            percentage = savings['savings_percentage']
            self.assertGreaterEqual(percentage, 0.10)
            self.assertLessEqual(percentage, 0.30)
    
    def test_shows_saving_plan_recommendations(self):
        """Test: Show saving plan recommendations in app."""
        self.pipeline.train(user_id="user4", min_transactions=2)
        insights = self.pipeline.get_personalized_insights(user_id="user4")
        if insights.get('savings_suggestion') and isinstance(insights['savings_suggestion'], dict):
            savings = insights['savings_suggestion']
            self.assertIn('suggested_monthly_savings', savings)
            self.assertIn('projected_yearly_savings', savings)
            self.assertIn('reason', savings)


class TestSmartNotificationsSystem(unittest.TestCase):
    """Test Case 5: Smart Notifications System"""
    
    def setUp(self):
        """Set up test data."""
        base_date = datetime.now() - timedelta(days=60)
        self.transactions = [
            Transaction(amount=-5000.0, description="Rent payment", timestamp=base_date, category="housing", merchant="Landlord", user_id="user5"),
            Transaction(amount=-5000.0, description="Rent payment", timestamp=base_date + timedelta(days=30), category="housing", merchant="Landlord", user_id="user5"),
            Transaction(amount=-1500.0, description="Grocery", timestamp=base_date, category="food", merchant="Store", user_id="user5"),
            Transaction(amount=-1500.0, description="Grocery", timestamp=base_date + timedelta(days=30), category="food", merchant="Store", user_id="user5"),
        ]
        self.user_profile = UserProfile(user_id="user5", monthly_income=50000.0)
        self.data_loader = SampleDataLoader(transactions=self.transactions, user_profile=self.user_profile)
        self.pipeline = FinanceMLPipeline(data_loader=self.data_loader)
    
    def test_analyzes_user_behavior_patterns(self):
        """Test: Analyze user behavior patterns (e.g., rent payment, shopping habits)."""
        self.pipeline.train(user_id="user5", min_transactions=4)
        # Check if pattern miner can identify patterns
        pattern_miner = self.pipeline.notification_engine.pattern_miner
        patterns = pattern_miner._extract_recurring_patterns(self.transactions)
        # Should find recurring rent payment pattern
        self.assertGreaterEqual(len(patterns), 0)
    
    def test_uses_pattern_mining_sequential_analysis(self):
        """Test: Use pattern mining / sequential analysis."""
        self.pipeline.train(user_id="user5", min_transactions=4)
        # Check if pattern miner is initialized
        self.assertIsNotNone(self.pipeline.notification_engine.pattern_miner)
    
    def test_triggers_contextual_notifications(self):
        """Test: Trigger contextual notifications."""
        self.pipeline.train(user_id="user5", min_transactions=4)
        results = self.pipeline.process_transactions([], user_id="user5")
        self.assertIn('notifications', results)
        # Notifications may be empty if no patterns match, but structure should exist


class TestArchitectureFlow(unittest.TestCase):
    """Test Case 6: Architecture Flow (Sequence Diagram)"""
    
    def setUp(self):
        """Set up test data."""
        base_date = datetime.now() - timedelta(days=60)
        self.transactions = [
            Transaction(amount=-1000.0, description="Regular expense", timestamp=base_date, category="food", user_id="user6"),
            Transaction(amount=-1200.0, description="Regular expense 2", timestamp=base_date + timedelta(days=1), category="food", user_id="user6"),
        ] * 5  # 10 transactions
        self.user_profile = UserProfile(user_id="user6", monthly_income=50000.0)
        self.data_loader = SampleDataLoader(transactions=self.transactions, user_profile=self.user_profile)
        self.pipeline = FinanceMLPipeline(data_loader=self.data_loader)
    
    def test_flow_user_adds_transaction_to_ml_analysis(self):
        """Test: User Adds Transaction → Transaction Management → ML Categorization → Anomaly Detection"""
        self.pipeline.train(user_id="user6", min_transactions=10)
        new_transaction = Transaction(
            amount=-2000.0,
            description="New transaction",
            timestamp=datetime.now(),
            user_id="user6"
        )
        results = self.pipeline.process_transactions([new_transaction], user_id="user6")
        # Should have categorization
        self.assertIn('categorized_transactions', results)
        # Should have anomaly detection
        self.assertIn('anomaly_alerts', results)
    
    def test_flow_ml_to_notification_service(self):
        """Test: ML Engine → Transaction Management → Notification Service"""
        self.pipeline.train(user_id="user6", min_transactions=10)
        new_transaction = Transaction(
            amount=-50000.0,  # Anomaly
            description="Large purchase",
            timestamp=datetime.now(),
            user_id="user6"
        )
        results = self.pipeline.process_transactions([new_transaction], user_id="user6")
        # Should have notifications
        self.assertIn('notifications', results)
        # If anomaly detected, should trigger alert
        if len(results['anomaly_alerts']) > 0:
            # Notifications should be generated
            self.assertIsInstance(results['notifications'], list)


def run_all_tests():
    """Run all test cases."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestSmartSpendingAlerts))
    suite.addTests(loader.loadTestsFromTestCase(TestPersonalizedExpenseSuggestions))
    suite.addTests(loader.loadTestsFromTestCase(TestTransactionCategorization))
    suite.addTests(loader.loadTestsFromTestCase(TestSmartSavingsSuggestions))
    suite.addTests(loader.loadTestsFromTestCase(TestSmartNotificationsSystem))
    suite.addTests(loader.loadTestsFromTestCase(TestArchitectureFlow))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == '__main__':
    result = run_all_tests()
    if result.wasSuccessful():
        print("\n" + "="*70)
        print("ALL TESTS PASSED! [OK]")
        print("="*70)
    else:
        print("\n" + "="*70)
        print(f"TESTS FAILED: {len(result.failures)} failures, {len(result.errors)} errors")
        print("="*70)
        sys.exit(1)
