"""
Transaction Categorization Module

Implements:
- NLP preprocessing (cleaning, tokenization, stopword removal)
- Text classification using Naive Bayes or Logistic Regression
- Automatic category assignment for transactions
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import Counter
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder

from .data_models import Transaction

@dataclass
class CategoryPrediction:
    """Represents a category prediction for a transaction."""
    transaction: Transaction
    predicted_category: str
    confidence: float
    alternative_categories: List[Tuple[str, float]]  # (category, confidence)

class TextPreprocessor:    
    def __init__(self, custom_stopwords: Optional[List[str]] = None):
        """
        Initialize text preprocessor.
        
        Args:
            custom_stopwords: Additional stopwords to remove
        """
        # Common stopwords for transaction text
        self.stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
            'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are',
            'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do',
            'does', 'did', 'will', 'would', 'should', 'could', 'may',
            'might', 'must', 'can', 'this', 'that', 'these', 'those'
        }
        
        if custom_stopwords:
            self.stopwords.update(custom_stopwords)
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text.
        
        Args:
            text: Raw transaction description
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters but keep alphanumeric and spaces
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into words.
        
        Args:
            text: Cleaned text
            
        Returns:
            List of tokens
        """
        return text.split()
    
    def remove_stopwords(self, tokens: List[str]) -> List[str]:
        """
        Remove stopwords from tokens.
        
        Args:
            tokens: List of word tokens
            
        Returns:
            List of tokens without stopwords
        """
        return [token for token in tokens if token not in self.stopwords]
    
    def preprocess(self, text: str) -> str:
        """
        Complete preprocessing pipeline.
        
        Args:
            text: Raw transaction description
            
        Returns:
            Preprocessed text ready for feature extraction
        """
        cleaned = self.clean_text(text)
        tokens = self.tokenize(cleaned)
        filtered_tokens = self.remove_stopwords(tokens)
        return ' '.join(filtered_tokens)


class TransactionCategorizer:
    """
    Automatically categorizes transactions using NLP and ML.
    
    Assumptions:
    - Transaction descriptions contain enough information for categorization
    - Training data has labeled categories
    - Categories are consistent across transactions
    - Text features (TF-IDF) are sufficient for classification
    """
    
    def __init__(
        self,
        classifier_type: str = 'naive_bayes',
        max_features: int = 1000,
        min_df: int = 2,
        random_state: int = 42
    ):
        """
        Initialize transaction categorizer.
        
        Args:
            classifier_type: 'naive_bayes' or 'logistic_regression'
            max_features: Maximum number of features for TF-IDF
            min_df: Minimum document frequency for features
            random_state: Random seed for reproducibility
        """
        assert classifier_type in ['naive_bayes', 'logistic_regression'], \
            "Classifier type must be 'naive_bayes' or 'logistic_regression'"
        assert max_features > 0, "Max features must be positive"
        assert min_df > 0, "Min document frequency must be positive"
        
        self.classifier_type = classifier_type
        self.max_features = max_features
        self.min_df = min_df
        self.random_state = random_state
        
        self.preprocessor = TextPreprocessor()
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            min_df=min_df,
            lowercase=True,
            token_pattern=r'\b[a-z]+\b'
        )
        
        # Choose classifier
        if classifier_type == 'naive_bayes':
            self.classifier = MultinomialNB()
        else:
            self.classifier = LogisticRegression(
                random_state=random_state,
                max_iter=1000
            )
        
        self.label_encoder = LabelEncoder()
        self._is_fitted = False
    
    def fit(
        self,
        transactions: List[Transaction],
        min_samples_per_category: int = 2
    ) -> None:
        """
        Fit the categorizer on labeled transaction data.
        
        Args:
            transactions: List of transactions with category labels
            min_samples_per_category: Minimum samples needed per category
            
        Raises:
            ValueError: If insufficient or unlabeled data
        """
        # Filter transactions with categories
        labeled_transactions = [
            t for t in transactions
            if t.category is not None and t.category.strip()
        ]
        
        if len(labeled_transactions) < min_samples_per_category * 2:
            raise ValueError(
                f"Insufficient labeled data for training. "
                f"Need at least {min_samples_per_category * 2} labeled transactions."
            )
        
        # Check category distribution
        category_counts = Counter(t.category for t in labeled_transactions)
        
        # Filter categories with enough samples
        valid_categories = {
            cat for cat, count in category_counts.items()
            if count >= min_samples_per_category
        }
        
        if len(valid_categories) < 2:
            raise ValueError(
                f"Need at least 2 categories with {min_samples_per_category} samples each."
            )
        
        # Filter to valid categories
        training_transactions = [
            t for t in labeled_transactions
            if t.category in valid_categories
        ]
        
        # Preprocess descriptions
        descriptions = [
            self.preprocessor.preprocess(t.description)
            for t in training_transactions
        ]
        
        # Extract categories
        categories = [t.category for t in training_transactions]
        
        # Encode labels
        encoded_categories = self.label_encoder.fit_transform(categories)
        
        # Vectorize text
        X = self.vectorizer.fit_transform(descriptions)
        
        # Train classifier
        self.classifier.fit(X, encoded_categories)
        
        self._is_fitted = True
    
    def predict(
        self,
        transaction: Transaction,
        top_k: int = 3
    ) -> CategoryPrediction:
        """
        Predict category for a transaction.
        
        Args:
            transaction: Transaction to categorize
            top_k: Number of top predictions to return
            
        Returns:
            CategoryPrediction object
        """
        if not self._is_fitted:
            raise ValueError("Model must be fitted before prediction")
        
        # Preprocess description
        preprocessed = self.preprocessor.preprocess(transaction.description)
        
        if not preprocessed:
            # Fallback: use 'uncategorized' if no text
            return CategoryPrediction(
                transaction=transaction,
                predicted_category='uncategorized',
                confidence=0.0,
                alternative_categories=[]
            )
        
        # Vectorize
        X = self.vectorizer.transform([preprocessed])
        
        # Predict
        if self.classifier_type == 'naive_bayes':
            # Naive Bayes provides probability estimates
            probabilities = self.classifier.predict_proba(X)[0]
            predicted_idx = np.argmax(probabilities)
            confidence = probabilities[predicted_idx]
            
            # Get top K alternatives
            top_indices = np.argsort(probabilities)[-top_k:][::-1]
            alternative_categories = [
                (
                    self.label_encoder.inverse_transform([idx])[0],
                    float(probabilities[idx])
                )
                for idx in top_indices
                if idx != predicted_idx
            ]
        else:
            # Logistic Regression
            probabilities = self.classifier.predict_proba(X)[0]
            predicted_idx = np.argmax(probabilities)
            confidence = probabilities[predicted_idx]
            
            # Get top K alternatives
            top_indices = np.argsort(probabilities)[-top_k:][::-1]
            alternative_categories = [
                (
                    self.label_encoder.inverse_transform([idx])[0],
                    float(probabilities[idx])
                )
                for idx in top_indices
                if idx != predicted_idx
            ]
        
        predicted_category = self.label_encoder.inverse_transform([predicted_idx])[0]
        
        return CategoryPrediction(
            transaction=transaction,
            predicted_category=predicted_category,
            confidence=float(confidence),
            alternative_categories=alternative_categories[:top_k-1]
        )
    
    def predict_batch(
        self,
        transactions: List[Transaction]
    ) -> List[CategoryPrediction]:
        """
        Predict categories for multiple transactions.
        
        Args:
            transactions: List of transactions to categorize
            
        Returns:
            List of CategoryPrediction objects
        """
        return [self.predict(t) for t in transactions]
    
    def get_category_mapping(self) -> Dict[str, int]:
        """
        Get mapping of category names to encoded labels.
        
        Returns:
            Dictionary mapping category names to label indices
        """
        if not self._is_fitted:
            return {}
        
        return {
            category: int(idx)
            for idx, category in enumerate(self.label_encoder.classes_)
        }
