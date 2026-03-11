"""
Example: Load data from CSV files and run the ML pipeline

This demonstrates how to use the CSVDataLoader to load sample data.
"""

import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.pipeline import FinanceMLPipeline
from src.csv_loader import CSVDataLoader


def main():
    """Load data from CSV and demonstrate the pipeline."""
    print("=" * 70)
    print("Loading Data from CSV Files")
    print("=" * 70)
    
    # Initialize CSV data loader
    print("\n[1] Initializing CSV Data Loader...")
    data_loader = CSVDataLoader(
        transactions_file="data/sample_transactions.csv",
        users_file="data/sample_users.csv"
    )
    
    # Load transactions
    print("\n[2] Loading transactions from CSV...")
    all_transactions = data_loader.load_transactions()
    print(f"   Loaded {len(all_transactions)} transactions")
    
    # Load user profiles
    print("\n[3] Loading user profiles from CSV...")
    user_ids = set(t.user_id for t in all_transactions if t.user_id)
    print(f"   Found {len(user_ids)} users: {', '.join(user_ids)}")
    
    # Process each user
    for user_id in user_ids:
        print(f"\n{'='*70}")
        print(f"Processing User: {user_id}")
        print(f"{'='*70}")
        
        # Load user transactions
        user_transactions = data_loader.load_transactions(user_id=user_id)
        user_profile = data_loader.load_user_profile(user_id)
        
        print(f"\n   Transactions: {len(user_transactions)}")
        if user_profile:
            print(f"   Monthly Income: Rs {user_profile.monthly_income:,.2f}" if user_profile.monthly_income else "   Monthly Income: Not set")
        
        # Initialize pipeline
        print("\n[4] Initializing ML Pipeline...")
        pipeline = FinanceMLPipeline(
            data_loader=data_loader,
            anomaly_contamination=0.05,
            z_score_threshold=3.0,
            expense_n_clusters=3,
            categorization_classifier='naive_bayes',
            random_state=42
        )
        
        # Train models
        if len(user_transactions) >= 10:
            print("\n[5] Training ML Models...")
            try:
                training_status = pipeline.train(user_id=user_id, min_transactions=10)
                print("   Training Results:")
                for component, status in training_status.items():
                    status_icon = "[OK]" if "success" in status else "[X]"
                    print(f"     {status_icon} {component}: {status}")
                
                # Get insights
                print("\n[6] Generating Personalized Insights...")
                insights = pipeline.get_personalized_insights(user_id=user_id)
                
                if insights.get('expense_suggestions'):
                    print("\n   Expense Suggestions:")
                    for suggestion in insights['expense_suggestions'][:3]:  # Show top 3
                        print(f"     - {suggestion['category']}: {suggestion['reason']}")
                
                if insights.get('savings_suggestion'):
                    savings = insights['savings_suggestion']
                    print(f"\n   Savings Suggestion:")
                    print(f"     - {savings['reason']}")
                    print(f"     - Suggested monthly savings: Rs {savings['suggested_monthly_savings']:,.2f}")
                
            except Exception as e:
                print(f"   Error: {e}")
        else:
            print(f"\n   Need at least 10 transactions. Current: {len(user_transactions)}")
    
    print("\n" + "=" * 70)
    print("CSV Data Loading Complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
