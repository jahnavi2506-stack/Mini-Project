"""
Data models and abstractions for transaction data.
These are dataset-agnostic interfaces that define the expected structure.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class Transaction:
    """
    Represents a single transaction.
    All fields are optional to accommodate different dataset structures.
    """
    amount: float
    description: str
    timestamp: datetime
    category: Optional[str] = None
    merchant: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate transaction data."""
        assert self.amount is not None, "Transaction amount is required"
        assert isinstance(self.amount, (int, float)), "Amount must be numeric"
        assert self.description is not None, "Transaction description is required"
        assert self.timestamp is not None, "Transaction timestamp is required"


@dataclass
class UserProfile:
    """
    Represents user financial profile.
    """
    user_id: str
    monthly_income: Optional[float] = None
    savings_goal: Optional[float] = None
    preferences: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate user profile."""
        assert self.user_id is not None, "User ID is required"


class DataLoader(ABC):
    """
    Abstract interface for loading transaction data.
    Implementations should handle dataset-specific loading logic.
    """
    
    @abstractmethod
    def load_transactions(self, user_id: Optional[str] = None) -> List[Transaction]:
        """
        Load transactions for a user or all users.
        
        Args:
            user_id: Optional user identifier to filter transactions
            
        Returns:
            List of Transaction objects
            
        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError("Subclass must implement load_transactions")
    
    @abstractmethod
    def load_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """
        Load user profile information.
        
        Args:
            user_id: User identifier
            
        Returns:
            UserProfile object or None if not found
        """
        raise NotImplementedError("Subclass must implement load_user_profile")
