"""
Run the ML Pipeline demo and save output to file
"""

import sys
from datetime import datetime, timedelta
from src.data_models import Transaction, UserProfile
from src.pipeline import FinanceMLPipeline
from src.example_loader import ExampleDataLoader


def create_sample_transactions(user_id: str = "user123"):
    """Create sample transactions for demonstration."""
    base_date = datetime.now() - timedelta(days=60)
    
    transactions = [
        Transaction(amount=-5000.0, description="Rent payment", timestamp=base_date + timedelta(days=0), category="housing", merchant="Landlord", user_id=user_id),
        Transaction(amount=-1500.0, description="Grocery shopping at BigBasket", timestamp=base_date + timedelta(days=2), category="food", merchant="BigBasket", user_id=user_id),
        Transaction(amount=-800.0, description="Uber ride to office", timestamp=base_date + timedelta(days=3), category="transport", merchant="Uber", user_id=user_id),
        Transaction(amount=-2000.0, description="Zomato food delivery", timestamp=base_date + timedelta(days=5), category="food", merchant="Zomato", user_id=user_id),
        Transaction(amount=-5000.0, description="Rent payment", timestamp=base_date + timedelta(days=30), category="housing", merchant="Landlord", user_id=user_id),
        Transaction(amount=-1500.0, description="Grocery shopping", timestamp=base_date + timedelta(days=32), category="food", merchant="BigBasket", user_id=user_id),
        Transaction(amount=-50000.0, description="Electronics purchase", timestamp=base_date + timedelta(days=40), category="shopping", merchant="Electronics Store", user_id=user_id),
        Transaction(amount=-1200.0, description="Coffee and snacks", timestamp=datetime.now() - timedelta(days=1), category="food", merchant="Cafe", user_id=user_id),
        Transaction(amount=-300.0, description="Metro card recharge", timestamp=datetime.now() - timedelta(days=2), category="transport", merchant="Metro", user_id=user_id),
        Transaction(amount=-2500.0, description="Restaurant dinner with friends", timestamp=base_date + timedelta(days=7), category="food", merchant="Restaurant", user_id=user_id),
        Transaction(amount=-1200.0, description="Netflix subscription", timestamp=base_date + timedelta(days=10), category="entertainment", merchant="Netflix", user_id=user_id),
        Transaction(amount=-800.0, description="Uber ride home", timestamp=base_date + timedelta(days=12), category="transport", merchant="Uber", user_id=user_id),
        Transaction(amount=-3000.0, description="Shopping at mall", timestamp=base_date + timedelta(days=15), category="shopping", merchant="Mall", user_id=user_id),
        Transaction(amount=-1500.0, description="Grocery shopping at BigBasket", timestamp=base_date + timedelta(days=18), category="food", merchant="BigBasket", user_id=user_id),
        Transaction(amount=-2000.0, description="Zomato food delivery", timestamp=base_date + timedelta(days=20), category="food", merchant="Zomato", user_id=user_id),
        Transaction(amount=-500.0, description="Coffee shop", timestamp=base_date + timedelta(days=22), category="food", merchant="Cafe", user_id=user_id),
    ]
    return transactions


class SampleDataLoader(ExampleDataLoader):
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
    """Run the demo and print detailed output."""
    output_lines = []
    
    def print_and_save(msg):
        print(msg)
        output_lines.append(msg)
    
    print_and_save("=" * 70)
    print_and_save("FINANCE ML PIPELINE - DEMONSTRATION OUTPUT")
    print_and_save("=" * 70)
    print_and_save("")
    
    # 1. Setup
    user_id = "user123"
    sample_transactions = create_sample_transactions(user_id)
    user_profile = UserProfile(user_id=user_id, monthly_income=50000.0, savings_goal=100000.0)
    data_loader = SampleDataLoader(transactions=sample_transactions, user_profile=user_profile)
    
    print_and_save("[STEP 1] Initializing ML Pipeline...")
    pipeline = FinanceMLPipeline(
        data_loader=data_loader,
        anomaly_contamination=0.05,
        z_score_threshold=3.0,
        expense_n_clusters=3,
        categorization_classifier='naive_bayes',
        random_state=42
    )
    print_and_save("[OK] Pipeline initialized successfully")
    print_and_save("")
    
    # 2. Train
    print_and_save("[STEP 2] Training ML Models on Historical Data...")
    print_and_save(f"  - Training on {len(sample_transactions)} historical transactions")
    training_status = pipeline.train(user_id=user_id, min_transactions=10)
    print_and_save("  Training Results:")
    for component, status in training_status.items():
        # Skip non-status fields
        if component in ['total_transactions', 'trained_components']:
            continue
        # Check if status is a string and contains "success"
        if isinstance(status, str) and "success" in status:
            status_icon = "[OK]"
        else:
            status_icon = "[X]"
        print_and_save(f"    {status_icon} {component}: {status}")
    print_and_save("")
    
    # 3. Process new transactions
    print_and_save("[STEP 3] Processing New Transactions...")
    new_transactions = [
        Transaction(amount=-2500.0, description="Restaurant dinner", timestamp=datetime.now(), user_id=user_id),
        Transaction(amount=-100000.0, description="Large purchase", timestamp=datetime.now(), user_id=user_id)
    ]
    print_and_save(f"  - Processing {len(new_transactions)} new transactions")
    
    results = pipeline.process_transactions(new_transactions, user_id=user_id)
    
    print_and_save("")
    print_and_save("  ANOMALY DETECTION RESULTS:")
    print_and_save(f"    Found {len(results['anomaly_alerts'])} anomaly alerts")
    for i, alert in enumerate(results['anomaly_alerts'], 1):
        print_and_save(f"    Alert #{i}:")
        print_and_save(f"      Description: {alert['description']}")
        print_and_save(f"      Amount: Rs {abs(alert['amount']):,.2f}")
        print_and_save(f"      Method: {alert['method']}")
        print_and_save(f"      Score: {alert['score']:.4f}")
        print_and_save(f"      Reason: {alert['reason']}")
    
    print_and_save("")
    print_and_save("  TRANSACTION CATEGORIZATION RESULTS:")
    print_and_save(f"    Categorized {len(results['categorized_transactions'])} transactions")
    for i, cat in enumerate(results['categorized_transactions'], 1):
        print_and_save(f"    Transaction #{i}:")
        print_and_save(f"      Description: {cat['description']}")
        print_and_save(f"      Predicted Category: {cat['predicted_category']}")
        print_and_save(f"      Confidence: {cat['confidence']:.2%}")
        if cat['alternatives']:
            print_and_save(f"      Alternatives: {', '.join([f'{a['category']} ({a['confidence']:.2%})' for a in cat['alternatives']])}")
    
    print_and_save("")
    print_and_save("  NOTIFICATIONS:")
    print_and_save(f"    Generated {len(results['notifications'])} notifications")
    for i, notif in enumerate(results['notifications'], 1):
        print_and_save(f"    Notification #{i}: [{notif['priority'].upper()}] {notif['title']}")
        print_and_save(f"      {notif['message']}")
        if notif['action_suggestion']:
            print_and_save(f"      Action: {notif['action_suggestion']}")
    print_and_save("")
    
    # 4. Insights
    print_and_save("[STEP 4] Generating Personalized Insights...")
    insights = pipeline.get_personalized_insights(user_id=user_id)
    
    print_and_save("")
    print_and_save("  EXPENSE SUGGESTIONS:")
    if isinstance(insights.get('expense_suggestions'), list):
        for i, suggestion in enumerate(insights['expense_suggestions'], 1):
            print_and_save(f"    Suggestion #{i} - {suggestion['category'].upper()}:")
            print_and_save(f"      Current Monthly Spend: Rs {suggestion['current_monthly_spend']:,.2f}")
            print_and_save(f"      Suggested Reduction: Rs {suggestion['suggested_reduction']:,.2f}")
            print_and_save(f"      Potential Savings: Rs {suggestion['potential_savings']:,.2f}")
            print_and_save(f"      Priority: {suggestion['priority'].upper()}")
            print_and_save(f"      {suggestion['reason']}")
    else:
        print_and_save(f"    {insights.get('expense_suggestions', 'N/A')}")
    
    print_and_save("")
    print_and_save("  SAVINGS SUGGESTIONS:")
    if insights.get('savings_suggestion') and isinstance(insights['savings_suggestion'], dict):
        savings = insights['savings_suggestion']
        print_and_save(f"    Current Savings Rate: {savings['current_savings_rate']:.1%}")
        print_and_save(f"    Suggested Savings Rate: {savings['savings_percentage']:.1%}")
        print_and_save(f"    Suggested Monthly Savings: Rs {savings['suggested_monthly_savings']:,.2f}")
        print_and_save(f"    Projected Yearly Savings: Rs {savings['projected_yearly_savings']:,.2f}")
        print_and_save(f"    Recommended Range: Rs {savings['recommended_range']['min']:,.2f} - Rs {savings['recommended_range']['max']:,.2f}")
        print_and_save(f"    Priority: {savings['priority'].upper()}")
        print_and_save(f"    {savings['reason']}")
    else:
        print_and_save(f"    {insights.get('savings_suggestion', 'N/A')}")
    
    print_and_save("")
    print_and_save("  FINANCIAL SUMMARY:")
    if isinstance(insights.get('financial_summary'), dict):
        summary = insights['financial_summary']
        print_and_save(f"    Monthly Income: Rs {summary.get('monthly_income', 'N/A'):,.2f}" if summary.get('monthly_income') else "    Monthly Income: N/A")
        print_and_save(f"    Monthly Spending: Rs {summary.get('monthly_spending', 0):,.2f}")
        if summary.get('current_savings_rate'):
            print_and_save(f"    Current Savings Rate: {summary['current_savings_rate']:.1%}")
    print_and_save("")
    
    # 5. Statistics
    print_and_save("[STEP 5] Model Statistics:")
    stats = pipeline.get_model_statistics()
    print_and_save(f"    Overall Status: {stats['training_status']}")
    print_and_save(f"    Anomaly Detector: {stats['anomaly_detector']['status']}")
    print_and_save(f"    Expense Analyzer: {stats['expense_analyzer']['status']}")
    print_and_save(f"    Transaction Categorizer: {stats['transaction_categorizer']['status']}")
    print_and_save("")
    
    print_and_save("=" * 70)
    print_and_save("DEMONSTRATION COMPLETED SUCCESSFULLY!")
    print_and_save("=" * 70)
    
    # Save to file
    output_file = "demo_output.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))
    
    print_and_save(f"\nOutput also saved to: {output_file}")
    return output_file


if __name__ == "__main__":
    try:
        output_file = main()
        print(f"\n[OK] Demo completed! Check '{output_file}' for detailed output.")
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
