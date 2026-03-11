"""
Example usage of the Finance ML Pipeline

This demonstrates how to use the pipeline with sample data.
Replace the ExampleDataLoader with your actual data loader implementation.
"""

from datetime import datetime, timedelta
from src.data_models import Transaction, UserProfile
from src.pipeline import FinanceMLPipeline
from src.example_loader import ExampleDataLoader


def create_sample_transactions(user_id: str = "user123") -> list:
    """
    Create sample transactions for demonstration.
    
    In production, these would come from your DataLoader.
    """
    base_date = datetime.now() - timedelta(days=60)
    
    transactions = [
        # Regular expenses
        Transaction(
            amount=-5000.0,
            description="Rent payment",
            timestamp=base_date + timedelta(days=0),
            category="housing",
            merchant="Landlord",
            user_id=user_id
        ),
        Transaction(
            amount=-1500.0,
            description="Grocery shopping at BigBasket",
            timestamp=base_date + timedelta(days=2),
            category="food",
            merchant="BigBasket",
            user_id=user_id
        ),
        Transaction(
            amount=-800.0,
            description="Uber ride to office",
            timestamp=base_date + timedelta(days=3),
            category="transport",
            merchant="Uber",
            user_id=user_id
        ),
        Transaction(
            amount=-2000.0,
            description="Zomato food delivery",
            timestamp=base_date + timedelta(days=5),
            category="food",
            merchant="Zomato",
            user_id=user_id
        ),
        # Recurring monthly expenses
        Transaction(
            amount=-5000.0,
            description="Rent payment",
            timestamp=base_date + timedelta(days=30),
            category="housing",
            merchant="Landlord",
            user_id=user_id
        ),
        Transaction(
            amount=-1500.0,
            description="Grocery shopping",
            timestamp=base_date + timedelta(days=32),
            category="food",
            merchant="BigBasket",
            user_id=user_id
        ),
        # Anomaly - unusually high expense
        Transaction(
            amount=-50000.0,
            description="Electronics purchase",
            timestamp=base_date + timedelta(days=40),
            category="shopping",
            merchant="Electronics Store",
            user_id=user_id
        ),
        # Recent transactions
        Transaction(
            amount=-1200.0,
            description="Coffee and snacks",
            timestamp=datetime.now() - timedelta(days=1),
            category="food",
            merchant="Cafe",
            user_id=user_id
        ),
        Transaction(
            amount=-300.0,
            description="Metro card recharge",
            timestamp=datetime.now() - timedelta(days=2),
            category="transport",
            merchant="Metro",
            user_id=user_id
        ),
        # Additional transactions for training
        Transaction(
            amount=-2500.0,
            description="Restaurant dinner with friends",
            timestamp=base_date + timedelta(days=7),
            category="food",
            merchant="Restaurant",
            user_id=user_id
        ),
        Transaction(
            amount=-1200.0,
            description="Netflix subscription",
            timestamp=base_date + timedelta(days=10),
            category="entertainment",
            merchant="Netflix",
            user_id=user_id
        ),
        Transaction(
            amount=-800.0,
            description="Uber ride home",
            timestamp=base_date + timedelta(days=12),
            category="transport",
            merchant="Uber",
            user_id=user_id
        ),
        Transaction(
            amount=-3000.0,
            description="Shopping at mall",
            timestamp=base_date + timedelta(days=15),
            category="shopping",
            merchant="Mall",
            user_id=user_id
        ),
        Transaction(
            amount=-1500.0,
            description="Grocery shopping at BigBasket",
            timestamp=base_date + timedelta(days=18),
            category="food",
            merchant="BigBasket",
            user_id=user_id
        ),
        Transaction(
            amount=-2000.0,
            description="Zomato food delivery",
            timestamp=base_date + timedelta(days=20),
            category="food",
            merchant="Zomato",
            user_id=user_id
        ),
        Transaction(
            amount=-500.0,
            description="Coffee shop",
            timestamp=base_date + timedelta(days=22),
            category="food",
            merchant="Cafe",
            user_id=user_id
        ),
    ]
    
    return transactions


class SampleDataLoader(ExampleDataLoader):
    """
    Sample implementation that uses in-memory data.
    Replace this with your actual data loading logic.
    """
    
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


def main():
    """
    Example workflow demonstrating the ML pipeline.
    """
    print("=" * 60)
    print("Finance ML Pipeline - Usage Example")
    print("=" * 60)
    
    # 1. Create sample data
    user_id = "user123"
    sample_transactions = create_sample_transactions(user_id)
    user_profile = UserProfile(
        user_id=user_id,
        monthly_income=50000.0,
        savings_goal=100000.0
    )
    
    # 2. Initialize data loader
    data_loader = SampleDataLoader(
        transactions=sample_transactions,
        user_profile=user_profile
    )
    
    # 3. Create pipeline
    print("\n[1] Initializing ML Pipeline...")
    pipeline = FinanceMLPipeline(
        data_loader=data_loader,
        anomaly_contamination=0.05,
        z_score_threshold=3.0,
        expense_n_clusters=3,
        categorization_classifier='naive_bayes',
        random_state=42
    )
    
    # 4. Train models
    print("\n[2] Training ML models on historical data...")
    try:
        training_status = pipeline.train(user_id=user_id, min_transactions=10)
        print("Training Status:")
        for component, status in training_status.items():
            print(f"  - {component}: {status}")
    except ValueError as e:
        print(f"Training failed: {e}")
        print("Note: This example may need more sample transactions.")
        return
    
    # 5. Process new transactions
    print("\n[3] Processing new transactions...")
    new_transactions = [
        Transaction(
            amount=-2500.0,
            description="Restaurant dinner",
            timestamp=datetime.now(),
            user_id=user_id
        ),
        Transaction(
            amount=-100000.0,  # Potential anomaly
            description="Large purchase",
            timestamp=datetime.now(),
            user_id=user_id
        )
    ]
    
    try:
        results = pipeline.process_transactions(new_transactions, user_id=user_id)
        
        print(f"\nAnomaly Alerts: {len(results['anomaly_alerts'])}")
        for alert in results['anomaly_alerts']:
            print(f"  - {alert['description']}: {alert['reason']}")
    except ValueError as e:
        print(f"Processing failed: {e}")
        print("Note: Some models may not be trained yet.")
        results = {'anomaly_alerts': [], 'categorized_transactions': [], 'notifications': []}
    
    print(f"\nCategorized Transactions: {len(results['categorized_transactions'])}")
    for cat in results['categorized_transactions']:
        print(f"  - {cat['description']} -> {cat['predicted_category']} "
              f"(confidence: {cat['confidence']:.2f})")
    
    print(f"\nNotifications: {len(results['notifications'])}")
    for notif in results['notifications']:
        print(f"  - [{notif['priority']}] {notif['title']}")
    
    # 6. Get personalized insights
    print("\n[4] Generating personalized insights...")
    insights = pipeline.get_personalized_insights(user_id=user_id)
    
    if 'expense_suggestions' in insights:
        print("\nExpense Suggestions:")
        for suggestion in insights['expense_suggestions']:
            print(f"  - {suggestion['category']}: {suggestion['reason']}")
    
    if insights.get('savings_suggestion'):
        savings = insights['savings_suggestion']
        print(f"\nSavings Suggestion:")
        print(f"  - {savings['reason']}")
        print(f"  - Suggested monthly savings: Rs {savings['suggested_monthly_savings']:.2f}")
        print(f"  - Projected yearly savings: Rs {savings['projected_yearly_savings']:.2f}")
    
    # 7. Get model statistics
    print("\n[5] Model Statistics:")
    stats = pipeline.get_model_statistics()
    print(f"  Training Status: {stats['training_status']}")
    print(f"  Anomaly Detector: {stats['anomaly_detector']['status']}")
    print(f"  Expense Analyzer: {stats['expense_analyzer']['status']}")
    print(f"  Transaction Categorizer: {stats['transaction_categorizer']['status']}")
    
    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
