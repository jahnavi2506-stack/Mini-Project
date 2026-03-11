"""
Example DataLoader Implementation

This is a reference implementation showing how to create a DataLoader
for your specific dataset. Replace this with your actual data loading logic.
"""

from typing import List, Optional
from datetime import datetime

from .data_models import Transaction, UserProfile, DataLoader


class ExampleDataLoader(DataLoader):
    """
    Example implementation of DataLoader.
    
    TODO: Replace this with your actual data loading implementation.
    This example shows the expected interface and structure.
    """
    
    def __init__(self, data_path: Optional[str] = None):
        """
        Initialize data loader.
        
        Args:
            data_path: Path to your dataset (format depends on your data)
        """
        self.data_path = data_path
        # TODO: Initialize your data source here
        # Examples:
        # - Database connection
        # - CSV file path
        # - API client
        # - etc.
    
    def load_transactions(self, user_id: Optional[str] = None) -> List[Transaction]:
        """
        Load transactions from your data source.
        
        Args:
            user_id: Optional user ID to filter transactions
            
        Returns:
            List of Transaction objects
            
        TODO: Implement actual data loading logic here.
        Expected steps:
        1. Load raw data from your source (CSV, DB, API, etc.)
        2. Parse and validate data
        3. Convert to Transaction objects
        4. Filter by user_id if provided
        """
        # Example structure - replace with your actual implementation
        transactions = []
        
        # TODO: Load your data here
        # Example for CSV:
        # import pandas as pd
        # df = pd.read_csv(self.data_path)
        # for row in df.itertuples():
        #     transaction = Transaction(
        #         amount=row.amount,
        #         description=row.description,
        #         timestamp=pd.to_datetime(row.timestamp),
        #         category=row.category if hasattr(row, 'category') else None,
        #         merchant=row.merchant if hasattr(row, 'merchant') else None,
        #         user_id=row.user_id if hasattr(row, 'user_id') else None
        #     )
        #     transactions.append(transaction)
        
        # TODO: Filter by user_id if provided
        # if user_id:
        #     transactions = [t for t in transactions if t.user_id == user_id]
        
        return transactions
    
    def load_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """
        Load user profile information.
        
        Args:
            user_id: User identifier
            
        Returns:
            UserProfile object or None if not found
            
        TODO: Implement actual profile loading logic here.
        """
        # TODO: Load user profile from your data source
        # Example:
        # profile_data = load_from_database(user_id)
        # if profile_data:
        #     return UserProfile(
        #         user_id=user_id,
        #         monthly_income=profile_data.get('monthly_income'),
        #         savings_goal=profile_data.get('savings_goal'),
        #         preferences=profile_data.get('preferences')
        #     )
        
        return None
