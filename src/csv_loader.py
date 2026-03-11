"""
CSV DataLoader Implementation

Loads transactions and user profiles from CSV files.
"""

import pandas as pd
from typing import List, Optional
from datetime import datetime

from .data_models import Transaction, UserProfile, DataLoader


class CSVDataLoader(DataLoader):
    """
    DataLoader implementation that reads from CSV files.
    
    Expected CSV format for transactions:
    - transaction_id, user_id, amount, description, category, merchant, timestamp
    
    Expected CSV format for users:
    - user_id, email, monthly_income, savings_goal
    """
    
    def __init__(
        self,
        transactions_file: str = "data/sample_transactions.csv",
        users_file: Optional[str] = "data/sample_users.csv"
    ):
        """
        Initialize CSV data loader.
        
        Args:
            transactions_file: Path to transactions CSV file
            users_file: Path to users CSV file (optional)
        """
        self.transactions_file = transactions_file
        self.users_file = users_file
        self._transactions_cache = None
        self._users_cache = None
    
    def _load_transactions_from_csv(self) -> List[Transaction]:
        """Load transactions from CSV file."""
        if self._transactions_cache is not None:
            return self._transactions_cache
        
        try:
            df = pd.read_csv(self.transactions_file)
            
            transactions = []
            for _, row in df.iterrows():
                # Parse timestamp
                timestamp = pd.to_datetime(row.get('timestamp', datetime.now()))
                
                transaction = Transaction(
                    amount=float(row['amount']),
                    description=str(row['description']),
                    timestamp=timestamp,
                    category=row.get('category') if pd.notna(row.get('category')) else None,
                    merchant=row.get('merchant') if pd.notna(row.get('merchant')) else None,
                    user_id=row.get('user_id') if pd.notna(row.get('user_id')) else None,
                    metadata={'transaction_id': row.get('transaction_id')}
                )
                transactions.append(transaction)
            
            self._transactions_cache = transactions
            return transactions
        
        except FileNotFoundError:
            print(f"Warning: Transactions file not found: {self.transactions_file}")
            return []
        except Exception as e:
            print(f"Error loading transactions: {e}")
            return []
    
    def _load_users_from_csv(self) -> dict:
        """Load users from CSV file."""
        if self._users_cache is not None:
            return self._users_cache
        
        if self.users_file is None:
            return {}
        
        try:
            df = pd.read_csv(self.users_file)
            
            users = {}
            for _, row in df.iterrows():
                user_id = str(row['user_id'])
                user_profile = UserProfile(
                    user_id=user_id,
                    monthly_income=float(row['monthly_income']) if pd.notna(row.get('monthly_income')) else None,
                    savings_goal=float(row['savings_goal']) if pd.notna(row.get('savings_goal')) else None,
                    preferences={'email': row.get('email')} if pd.notna(row.get('email')) else None
                )
                users[user_id] = user_profile
            
            self._users_cache = users
            return users
        
        except FileNotFoundError:
            print(f"Warning: Users file not found: {self.users_file}")
            return {}
        except Exception as e:
            print(f"Error loading users: {e}")
            return {}
    
    def load_transactions(self, user_id: Optional[str] = None) -> List[Transaction]:
        """
        Load transactions from CSV file.
        Includes both CSV-loaded transactions and any dynamically added ones.
        
        Args:
            user_id: Optional user ID to filter transactions
            
        Returns:
            List of Transaction objects
        """
        # Load from CSV first (if not already cached)
        csv_transactions = self._load_transactions_from_csv()
        
        # Combine with any dynamically added transactions
        all_transactions = csv_transactions.copy() if csv_transactions else []
        
        if user_id:
            all_transactions = [t for t in all_transactions if t.user_id == user_id]
        
        return all_transactions
    
    def load_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """
        Load user profile from CSV file.
        
        Args:
            user_id: User identifier
            
        Returns:
            UserProfile object or None if not found
        """
        users = self._load_users_from_csv()
        return users.get(user_id)
    
    def add_transaction(self, transaction: Transaction) -> None:
        """
        Add a transaction to the in-memory cache.
        This allows adding new transactions without modifying the CSV file.
        
        Args:
            transaction: Transaction object to add
        """
        if self._transactions_cache is None:
            self._transactions_cache = []
        self._transactions_cache.append(transaction)
    
    def add_user_profile(self, user_profile: UserProfile) -> None:
        """
        Add a user profile to the in-memory cache.
        
        Args:
            user_profile: UserProfile object to add
        """
        if self._users_cache is None:
            self._users_cache = {}
        self._users_cache[user_profile.user_id] = user_profile
