"""
Web Application for Finance ML Pipeline

Simple Flask web interface to interact with the ML pipeline.
"""

from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from datetime import datetime, timedelta, date
import calendar
from collections import defaultdict
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.data_models import Transaction, UserProfile
from src.pipeline import FinanceMLPipeline
from src.example_loader import ExampleDataLoader
from src.csv_loader import CSVDataLoader
from src.budget_manager import BudgetManager
from src.notifications_engine import NotificationEngine as SmartNotificationEngine
from src.finance_score import FinanceScoreCalculator
from src.category_predictor import predict_category


app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Add built-in functions and types to Jinja2 template context
import builtins
app.jinja_env.globals['abs'] = builtins.abs
app.jinja_env.globals['isinstance'] = builtins.isinstance
app.jinja_env.globals['list'] = list
app.jinja_env.globals['dict'] = dict
app.jinja_env.globals['str'] = str

# Global pipeline instance
pipeline = None
data_loader = None


class WebDataLoader(ExampleDataLoader):
    """Data loader for web application."""
    
    def __init__(self):
        self.transactions = []
        self.user_profiles = {}
    
    def load_transactions(self, user_id=None):
        if user_id:
            return [t for t in self.transactions if t.user_id == user_id]
        return self.transactions
    
    def load_user_profile(self, user_id):
        return self.user_profiles.get(user_id)
    
    def add_transaction(self, transaction):
        """Add a transaction."""
        self.transactions.append(transaction)
    
    def add_user_profile(self, user_profile):
        """Add a user profile."""
        self.user_profiles[user_profile.user_id] = user_profile


def initialize_pipeline():
    """Initialize the ML pipeline."""
    global pipeline, data_loader
    if pipeline is None:
        data_loader = WebDataLoader()
        pipeline = FinanceMLPipeline(
            data_loader=data_loader,
            anomaly_contamination=0.05,
            z_score_threshold=3.0,
            expense_n_clusters=3,
            categorization_classifier='naive_bayes',
            random_state=42
        )
    return pipeline, data_loader


def _safe_float(value, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _month_start(d: date) -> date:
    return date(d.year, d.month, 1)


def _add_months(d: date, months: int) -> date:
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    return date(y, m, 1)


def _chart_data_for_user(user_id: str) -> dict:
    """
    Build chart-ready aggregates from stored transactions for a user.
    Returns a dict with monthly spending, category distribution, income vs expense trend,
    and last-7-days spending.
    """
    pipeline, data_loader = initialize_pipeline()
    transactions = data_loader.load_transactions(user_id=user_id) or []

    # Normalize transaction list
    def tx_date(t):
        try:
            return t.timestamp.date()
        except Exception:
            return datetime.now().date()

    today = datetime.now().date()

    # ---- Monthly Spending (last 6 months) ----
    end_month = _month_start(today)
    months = [_add_months(end_month, -i) for i in reversed(range(6))]
    month_labels = [f"{calendar.month_abbr[m.month]} {m.year}" for m in months]
    monthly_totals = []
    for m in months:
        m_next = _add_months(m, 1)
        total = 0.0
        for t in transactions:
            td = tx_date(t)
            if m <= td < m_next and (t.amount or 0) < 0:
                total += abs(t.amount)
        monthly_totals.append(round(total, 2))

    # ---- Expense Category Pie ----
    category_order = ["Food", "Transport", "Shopping", "Bills", "Other"]
    category_keys = {"food": "Food", "transport": "Transport", "shopping": "Shopping", "bills": "Bills"}
    category_totals = defaultdict(float)
    for t in transactions:
        amt = t.amount or 0
        if amt >= 0:
            continue
        key = (t.category or "").strip().lower()
        mapped = category_keys.get(key, "Other")
        category_totals[mapped] += abs(amt)
    category_data = [round(category_totals.get(k, 0.0), 2) for k in category_order]

    # ---- Income vs Expense Trend (last 30 days, daily) ----
    trend_days = 30
    start_day = today - timedelta(days=trend_days - 1)
    labels = [(start_day + timedelta(days=i)) for i in range(trend_days)]
    label_strs = [d.strftime("%b %d") for d in labels]
    income_series = []
    expense_series = []
    for d in labels:
        inc = 0.0
        exp = 0.0
        for t in transactions:
            if tx_date(t) != d:
                continue
            amt = t.amount or 0
            if amt >= 0:
                inc += amt
            else:
                exp += abs(amt)
        income_series.append(round(inc, 2))
        expense_series.append(round(exp, 2))

    # ---- Daily Spending (last 7 days) ----
    week_days = 7
    w_start = today - timedelta(days=week_days - 1)
    w_labels = [(w_start + timedelta(days=i)) for i in range(week_days)]
    w_label_strs = [d.strftime("%a") for d in w_labels]
    w_spend = []
    for d in w_labels:
        exp = 0.0
        for t in transactions:
            if tx_date(t) == d and (t.amount or 0) < 0:
                exp += abs(t.amount)
        w_spend.append(round(exp, 2))

    return {
        "monthly_spending": {"labels": month_labels, "data": monthly_totals},
        "expense_distribution": {"labels": category_order, "data": category_data},
        "income_vs_expense": {"labels": label_strs, "income": income_series, "expense": expense_series},
        "weekly_spending": {"labels": w_label_strs, "data": w_spend},
    }


def _recent_transactions_payload(user_id: str, limit: int = 10) -> list:
    pipeline, data_loader = initialize_pipeline()
    txs = data_loader.load_transactions(user_id=user_id) or []
    txs = sorted(txs, key=lambda t: t.timestamp, reverse=True)
    out = []
    for t in txs[:limit]:
        try:
            ts = t.timestamp.strftime("%Y-%m-%d %H:%M")
        except Exception:
            ts = ""
        out.append(
            {
                "timestamp": ts,
                "description": t.description,
                "amount": round(abs(t.amount or 0.0), 2),
                "is_income": (t.amount or 0) >= 0,
                "category": t.category or "",
                "merchant": t.merchant or "",
            }
        )
    return out

@app.route('/')
def index():
    """Home page."""
    return render_template('index.html')


@app.route('/load_sample_data')
def load_sample_data():
    """Load sample data from CSV files."""
    global pipeline, data_loader
    
    try:
        # Switch to CSV data loader
        data_loader = CSVDataLoader(
            transactions_file="data/sample_transactions.csv",
            users_file="data/sample_users.csv"
        )
        
        # Reinitialize pipeline with CSV loader
        pipeline = FinanceMLPipeline(
            data_loader=data_loader,
            anomaly_contamination=0.05,
            z_score_threshold=3.0,
            expense_n_clusters=3,
            categorization_classifier='naive_bayes',
            random_state=42
        )
        
        # Load sample user
        sample_user = "user123"
        transactions = data_loader.load_transactions(user_id=sample_user)
        user_profile = data_loader.load_user_profile(sample_user)
        
        # Auto-train with available data (works with any amount)
        if len(transactions) >= 2:
            pipeline.train(user_id=sample_user)  # Flexible - trains with available data
        
        return render_template('sample_data_loaded.html',
                             user_id=sample_user,
                             transaction_count=len(transactions),
                             user_profile=user_profile)
    except Exception as e:
        return render_template('error.html',
                             message=f"Error loading sample data: {str(e)}",
                             user_id="")


@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page."""
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        email = request.form.get('email')
        monthly_income = float(request.form.get('monthly_income', 0))
        
        pipeline, data_loader = initialize_pipeline()
        
        # Create user profile
        user_profile = UserProfile(
            user_id=user_id,
            monthly_income=monthly_income
        )
        data_loader.add_user_profile(user_profile)
        
        return render_template('register_success.html', user_id=user_id)
    
    return render_template('register.html')


@app.route('/dashboard/<user_id>')
def dashboard(user_id):
    """User dashboard."""
    pipeline, data_loader = initialize_pipeline()
    
    # Load user transactions
    transactions = data_loader.load_transactions(user_id=user_id)
    user_profile = data_loader.load_user_profile(user_id)
    monthly_income = getattr(user_profile, "monthly_income", None) if user_profile else None

    # Budget tracking
    budgets = BudgetManager.get_user_budgets(user_id)
    category_spending = BudgetManager.calculate_category_spending(transactions)
    budget_summary = []
    for cat, limit in budgets.items():
        spent = float(category_spending.get(cat, 0.0))
        budget_summary.append(
            {
                "category": cat,
                "spent": spent,
                "limit": float(limit),
                "remaining": float(limit) - spent,
                "exceeded": spent > float(limit),
            }
        )
    budget_summary.sort(key=lambda x: x["category"])
    
    # Check if pipeline is trained
    is_trained = pipeline._is_trained
    
    # Get insights if trained (works with any amount of data)
    insights = None
    if is_trained and len(transactions) >= 1:
        try:
            insights = pipeline.get_personalized_insights(user_id=user_id)
        except:
            pass
    
    # Get notifications and predictions (next 30 days for next month view)
    notifications = []
    upcoming_predictions = []
    if is_trained and len(transactions) >= 2:
        try:
            # Anomaly alerts from pipeline (if fitted)
            anomaly_alerts = []
            try:
                if getattr(pipeline.anomaly_detector, "_is_fitted", False):
                    alerts = pipeline.anomaly_detector.detect_anomalies(transactions[-20:])
                    anomaly_alerts = [
                        {
                            "amount": a.transaction.amount,
                            "description": a.transaction.description,
                            "score": a.anomaly_score,
                            "reason": a.reason,
                        }
                        for a in alerts
                    ]
            except Exception:
                anomaly_alerts = []

            notifications = SmartNotificationEngine.generate_notifications(
                transactions,
                monthly_income,
                budgets=budgets,
                anomaly_alerts=anomaly_alerts,
            )
            
            # Get upcoming patterns (next 30 days for next month predictions)
            upcoming_patterns = pipeline.notification_engine.pattern_miner.find_upcoming_patterns(
                transactions,
                lookahead_days=30  # Show next month predictions
            )
            
            # Format predictions for display
            for pattern in upcoming_patterns:
                next_expected = pattern.get('next_expected')
                days_until = pattern.get('days_until', 0)
                upcoming_predictions.append({
                    'category': pattern['category'],
                    'merchant': pattern['merchant'],
                    'amount': pattern['amount'],
                    'next_expected': next_expected.strftime('%Y-%m-%d') if next_expected else 'Unknown',
                    'days_until': days_until,
                    'pattern_type': pattern.get('pattern_type', 'recurring')
                })
        except Exception as e:
            # Silently fail - notifications are optional
            pass

    # Finance Health Score (0-100)
    finance_score = None
    try:
        anomaly_count = 0
        # Try to reuse anomaly detector state if fitted
        if getattr(pipeline.anomaly_detector, "_is_fitted", False):
            try:
                anomaly_count = len(pipeline.anomaly_detector.detect_anomalies(transactions[-30:]))
            except Exception:
                anomaly_count = 0
        finance_score = FinanceScoreCalculator.calculate_score(
            transactions,
            monthly_income,
            budgets,
            anomaly_count=anomaly_count,
        )
    except Exception:
        finance_score = None
    
    return render_template('dashboard.html', 
                         user_id=user_id,
                         transactions=transactions,
                         user_profile=user_profile,
                         is_trained=is_trained,
                         insights=insights,
                         notifications=notifications,
                         upcoming_predictions=upcoming_predictions,
                         transaction_count=len(transactions),
                         budgets=budgets,
                         category_spending=category_spending,
                         budget_summary=budget_summary,
                         finance_score=finance_score)


@app.route('/add_transaction/<user_id>', methods=['GET', 'POST'])
def add_transaction(user_id):
    """Add transaction page."""
    pipeline, data_loader = initialize_pipeline()
    
    if request.method == 'POST':
        amount = float(request.form.get('amount', 0))
        description = request.form.get('description', '')
        category = request.form.get('category', '')
        merchant = request.form.get('merchant', '')

        # Auto-predict category if user didn't choose one
        predicted = None
        if not category:
            predicted = predict_category(description, merchant)
            category = predicted
        
        # Create transaction
        transaction = Transaction(
            amount=-abs(amount),  # Make negative for expenses
            description=description,
            timestamp=datetime.now(),
            category=category if category else None,
            merchant=merchant if merchant else None,
            user_id=user_id
        )
        
        data_loader.add_transaction(transaction)
        
        # Auto-train pipeline with available data (flexible - works with any amount)
        user_transactions = data_loader.load_transactions(user_id=user_id)
        if len(user_transactions) >= 2 and not pipeline._is_trained:
            try:
                pipeline.train(user_id=user_id)  # No minimum - trains with available data
            except:
                pass
        
        # Process the new transaction
        results = {}
        if pipeline._is_trained:
            try:
                results = pipeline.process_transactions([transaction], user_id=user_id)
            except:
                pass
        
        return render_template('transaction_result.html',
                             user_id=user_id,
                             transaction=transaction,
                             results=results)
    
    return render_template('add_transaction.html', user_id=user_id)


@app.route('/train/<user_id>')
def train(user_id):
    """Train the ML models."""
    pipeline, data_loader = initialize_pipeline()
    
    transactions = data_loader.load_transactions(user_id=user_id)
    
    if len(transactions) < 1:
        return render_template('error.html',
                             message=f"Need at least 1 transaction to train. You have {len(transactions)}.",
                             user_id=user_id)
    
    try:
        # Train with available data (flexible - no hard minimum)
        training_status = pipeline.train(user_id=user_id)
        return render_template('train_success.html',
                             user_id=user_id,
                             training_status=training_status)
    except Exception as e:
        return render_template('error.html',
                             message=f"Training failed: {str(e)}",
                             user_id=user_id)


@app.route('/insights/<user_id>')
def insights(user_id):
    """View personalized insights."""
    pipeline, data_loader = initialize_pipeline()
    
    # Load user transactions
    transactions = data_loader.load_transactions(user_id=user_id)
    
    # Auto-train if not trained and have enough data
    if not pipeline._is_trained:
        if len(transactions) >= 2:
            try:
                pipeline.train(user_id=user_id)
            except Exception as e:
                return render_template('error.html',
                                     message=f"Error training models: {str(e)}. Need at least 2 transactions.",
                                     user_id=user_id)
        else:
            return render_template('error.html',
                                 message=f"Please train the models first. You have {len(transactions)} transaction(s). Need at least 2.",
                                 user_id=user_id)
    
    try:
        insights_data = pipeline.get_personalized_insights(user_id=user_id)
        return render_template('insights.html',
                             user_id=user_id,
                             insights=insights_data)
    except Exception as e:
        return render_template('error.html',
                             message=f"Error generating insights: {str(e)}",
                             user_id=user_id)


@app.route('/api/financial_insights/<user_id>')
def api_financial_insights(user_id):
    """Return chart-ready aggregates for Chart.js."""
    try:
        return jsonify({"ok": True, "user_id": user_id, "charts": _chart_data_for_user(user_id)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route('/api/dashboard_snapshot/<user_id>')
def api_dashboard_snapshot(user_id):
    """Return charts + latest transactions so dashboard can update without refresh."""
    try:
        pipeline, data_loader = initialize_pipeline()
        txs = data_loader.load_transactions(user_id=user_id) or []
        return jsonify(
            {
                "ok": True,
                "user_id": user_id,
                "transaction_count": len(txs),
                "is_trained": bool(getattr(pipeline, "_is_trained", False)),
                "charts": _chart_data_for_user(user_id),
                "recent_transactions": _recent_transactions_payload(user_id, limit=10),
            }
        )
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route('/api/transactions/<user_id>', methods=['POST'])
def api_add_transaction(user_id):
    """
    Add a transaction via AJAX and return updated dashboard snapshot.
    Body can be form-encoded or JSON with:
      amount, description, category, merchant, kind ('expense'|'income')
    """
    pipeline, data_loader = initialize_pipeline()
    try:
        payload = request.get_json(silent=True) or request.form or {}
        amount = _safe_float(payload.get("amount", 0))
        description = (payload.get("description") or "").strip()
        category = (payload.get("category") or "").strip()
        merchant = (payload.get("merchant") or "").strip()
        kind = (payload.get("kind") or "expense").strip().lower()

        if not description:
            return jsonify({"ok": False, "error": "Description is required"}), 400
        if amount <= 0:
            return jsonify({"ok": False, "error": "Amount must be greater than 0"}), 400

        # Auto-predict category if missing
        if not category:
            category = predict_category(description, merchant)

        signed_amount = abs(amount) if kind == "income" else -abs(amount)
        transaction = Transaction(
            amount=signed_amount,
            description=description,
            timestamp=datetime.now(),
            category=category if category else None,
            merchant=merchant if merchant else None,
            user_id=user_id,
        )
        data_loader.add_transaction(transaction)

        # Train if possible (keeps existing behavior)
        user_transactions = data_loader.load_transactions(user_id=user_id) or []
        if len(user_transactions) >= 2 and not getattr(pipeline, "_is_trained", False):
            try:
                pipeline.train(user_id=user_id)
            except Exception:
                pass

        return api_dashboard_snapshot(user_id)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route('/api/budgets/<user_id>')
def api_get_budgets(user_id):
    """Get user budgets from CSV."""
    try:
        budgets = BudgetManager.get_user_budgets(user_id)
        return jsonify({"ok": True, "user_id": user_id, "budgets": budgets})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route('/api/budgets/<user_id>', methods=['POST'])
def api_set_budgets(user_id):
    """Set/replace user budgets in CSV."""
    try:
        payload = request.get_json(silent=True) or {}
        budgets = payload.get("budgets")
        if not isinstance(budgets, dict):
            return jsonify({"ok": False, "error": "Expected JSON body: { budgets: {category: limit} }"}), 400

        BudgetManager.set_user_budgets(user_id, budgets)
        return jsonify({"ok": True, "user_id": user_id, "budgets": BudgetManager.get_user_budgets(user_id)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route('/update-budgets', methods=['POST'])
def update_budgets():
    """
    Lightweight alias endpoint for updating budgets (CSV-backed).
    Expected JSON:
      { "user_id": "...", "budgets": { "food": 8000, ... } }
    """
    try:
        payload = request.get_json(silent=True) or {}
        user_id = (payload.get("user_id") or "").strip()
        budgets = payload.get("budgets")
        if not user_id:
            return jsonify({"ok": False, "error": "user_id is required"}), 400
        if not isinstance(budgets, dict):
            return jsonify({"ok": False, "error": "Expected JSON body: { user_id, budgets: {category: limit} }"}), 400

        BudgetManager.set_user_budgets(user_id, budgets)
        return jsonify({"ok": True, "user_id": user_id, "budgets": BudgetManager.get_user_budgets(user_id)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == '__main__':
    initialize_pipeline()
    print("\n" + "="*70)
    print("Finance ML Pipeline Web Application")
    print("="*70)
    print("\nStarting server...")
    print("Open your browser and go to: http://127.0.0.1:5000")
    print("\nPress Ctrl+C to stop the server")
    print("="*70 + "\n")
    app.run(debug=True, host='127.0.0.1', port=5000)
