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
import smtplib
from email.message import EmailMessage

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

# Data files for persistence (enter by email, saved data)
DATA_TRANSACTIONS_CSV = os.path.join("data", "transactions.csv")
DATA_USERS_CSV = os.path.join("data", "users.csv")
SAMPLE_TRANSACTIONS = os.path.join("data", "sample_transactions.csv")
SAMPLE_USERS = os.path.join("data", "sample_users.csv")
TRANSACTIONS_DISPLAY_LIMIT = 50  # Mini project: show up to 50 in dashboard list

# Simple mail settings (configure via environment variables for real usage)
SMTP_HOST = os.environ.get("SMTP_HOST")  # e.g. smtp.gmail.com
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER")  # your email / SMTP username
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")  # app password / SMTP password
FROM_EMAIL = os.environ.get("FROM_EMAIL") or SMTP_USER

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


def ensure_data_files():
    """Ensure data/transactions.csv and data/users.csv exist; seed from sample files if missing."""
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(DATA_TRANSACTIONS_CSV) and os.path.exists(SAMPLE_TRANSACTIONS):
        import shutil
        shutil.copy(SAMPLE_TRANSACTIONS, DATA_TRANSACTIONS_CSV)
    if not os.path.exists(DATA_USERS_CSV) and os.path.exists(SAMPLE_USERS):
        import shutil
        shutil.copy(SAMPLE_USERS, DATA_USERS_CSV)


def get_user_by_email(email):
    """Look up user by email in data/users.csv. Returns dict with user_id, email, monthly_income, savings_goal or None."""
    if not email or not os.path.exists(DATA_USERS_CSV):
        return None
    email = (email or "").strip().lower()
    with open(DATA_USERS_CSV, "r", newline="", encoding="utf-8") as f:
        reader = __import__("csv").DictReader(f)
        for row in reader:
            if (row.get("email") or "").strip().lower() == email:
                return {
                    "user_id": (row.get("user_id") or "").strip(),
                    "email": (row.get("email") or "").strip(),
                    "monthly_income": _safe_float(row.get("monthly_income"), 0.0),
                    "savings_goal": _safe_float(row.get("savings_goal"), 0.0),
                }
    return None


def switch_to_csv_loader():
    """Switch global data_loader and pipeline to use CSV data files (persisted)."""
    global pipeline, data_loader
    ensure_data_files()
    data_loader = CSVDataLoader(
        transactions_file=DATA_TRANSACTIONS_CSV,
        users_file=DATA_USERS_CSV,
    )
    # CSVDataLoader caches; start fresh from disk
    try:
        data_loader._transactions_cache = None
        data_loader._users_cache = None
    except Exception:
        pass
    pipeline = FinanceMLPipeline(
        data_loader=data_loader,
        anomaly_contamination=0.05,
        z_score_threshold=3.0,
        expense_n_clusters=3,
        categorization_classifier='naive_bayes',
        random_state=42,
    )
    return pipeline, data_loader


def send_registration_email(to_email: str, user_id: str) -> None:
    """
    Send a simple \"you have registered\" email.
    Uses SMTP_* env vars; fails silently if not configured.
    """
    if not to_email or not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD or not FROM_EMAIL:
        return
    msg = EmailMessage()
    msg["Subject"] = "Registration successful - Finance ML Mini App"
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email
    body = (
        f"Hi {user_id},\n\n"
        "Your registration on the Finance ML mini project app was successful.\n"
        "You can log in again with this email to see your dashboard, charts and past transactions.\n\n"
        "Best regards,\n"
        "Finance ML App"
    )
    msg.set_content(body)
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
    except Exception:
        # For a mini project we don't hard-fail on email issues.
        pass


def append_user_to_csv(user_id, email, monthly_income, savings_goal=0.0):
    """Append a new user to data/users.csv."""
    ensure_data_files()
    with open(DATA_USERS_CSV, "a", newline="", encoding="utf-8") as f:
        w = __import__("csv").writer(f)
        w.writerow([str(user_id), str(email), float(monthly_income), float(savings_goal)])


def _next_transaction_id():
    """Get next transaction ID from data/transactions.csv."""
    if not os.path.exists(DATA_TRANSACTIONS_CSV):
        return 1
    max_id = 0
    with open(DATA_TRANSACTIONS_CSV, "r", newline="", encoding="utf-8") as f:
        reader = __import__("csv").DictReader(f)
        for row in reader:
            try:
                max_id = max(max_id, int(float(row.get("transaction_id", 0))))
            except (ValueError, TypeError):
                pass
    return max_id + 1


def append_transaction_to_csv(transaction):
    """Append a transaction to data/transactions.csv (for persistence)."""
    ensure_data_files()
    next_id = _next_transaction_id()
    ts = transaction.timestamp.strftime("%Y-%m-%d %H:%M:%S") if hasattr(transaction.timestamp, "strftime") else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = [next_id, transaction.user_id or "", transaction.amount, transaction.description or "", transaction.category or "", transaction.merchant or "", ts]
    with open(DATA_TRANSACTIONS_CSV, "a", newline="", encoding="utf-8") as f:
        w = __import__("csv").writer(f)
        w.writerow(row)
    # Invalidate CSV loader cache so dashboard/charts reflect saved rows after refresh.
    try:
        if data_loader and getattr(data_loader, "transactions_file", None) == DATA_TRANSACTIONS_CSV:
            data_loader._transactions_cache = None
    except Exception:
        pass


def _count_user_transactions_in_csv(user_id: str) -> int:
    """Count transactions for a user in the persisted CSV (fast, no pandas)."""
    if not user_id or not os.path.exists(DATA_TRANSACTIONS_CSV):
        return 0
    n = 0
    with open(DATA_TRANSACTIONS_CSV, "r", newline="", encoding="utf-8") as f:
        reader = __import__("csv").DictReader(f)
        for row in reader:
            if (row.get("user_id") or "").strip() == user_id:
                n += 1
    return n


def seed_user_with_sample_transactions(user_id: str, *, limit: int = None) -> int:
    """
    Seed a user with sample transactions if they have none.
    This makes the mini-project dashboard/charts useful immediately after login/registration.
    Returns number of rows inserted.
    """
    limit = int(limit or TRANSACTIONS_DISPLAY_LIMIT)
    ensure_data_files()
    if not user_id:
        return 0
    if _count_user_transactions_in_csv(user_id) > 0:
        return 0
    if not os.path.exists(SAMPLE_TRANSACTIONS):
        return 0

    inserted = 0
    with open(SAMPLE_TRANSACTIONS, "r", newline="", encoding="utf-8") as f:
        reader = __import__("csv").DictReader(f)
        for row in reader:
            if inserted >= limit:
                break
            try:
                amount = float(row.get("amount") or 0.0)
            except Exception:
                amount = 0.0
            desc = (row.get("description") or "").strip()
            cat = (row.get("category") or "").strip()
            merch = (row.get("merchant") or "").strip()
            ts = (row.get("timestamp") or "").strip() or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            next_id = _next_transaction_id()
            out_row = [next_id, user_id, amount, desc, cat, merch, ts]
            with open(DATA_TRANSACTIONS_CSV, "a", newline="", encoding="utf-8") as out:
                w = __import__("csv").writer(out)
                w.writerow(out_row)
            inserted += 1

    # Clear loader cache if we're currently using CSV loader
    try:
        if data_loader and getattr(data_loader, "transactions_file", None) == DATA_TRANSACTIONS_CSV:
            data_loader._transactions_cache = None
    except Exception:
        pass
    return inserted


def initialize_pipeline():
    """
    Initialize the ML pipeline.

    IMPORTANT: Prefer persisted CSV storage (data/users.csv + data/transactions.csv) when available.
    This prevents "data lost after refresh/restart" for same-email users.
    """
    global pipeline, data_loader
    if pipeline is None:
        ensure_data_files()

        # If persisted files exist, use them by default (app-like behavior).
        if os.path.exists(DATA_USERS_CSV) and os.path.exists(DATA_TRANSACTIONS_CSV):
            return switch_to_csv_loader()

        # Fallback: in-memory only (mainly for dev / minimal mode)
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


def _chart_data_for_user(user_id: str, focus_month: date = None, scope: str = "6months") -> dict:
    """
    Build chart-ready aggregates from stored transactions for a user.
    focus_month: first day of the month to focus on (for budget and filtering); default = current month.
    scope: 'this_month' | '3months' | '6months' | 'all' — range of data to include in charts.
    """
    pipeline, data_loader = initialize_pipeline()
    # CSVDataLoader caches file contents; clear cache so charts reflect saved transactions for existing email.
    try:
        if data_loader and getattr(data_loader, "transactions_file", None) == DATA_TRANSACTIONS_CSV:
            data_loader._transactions_cache = None
    except Exception:
        pass
    transactions = data_loader.load_transactions(user_id=user_id) or []

    def tx_date(t):
        try:
            return t.timestamp.date()
        except Exception:
            return datetime.now().date()

    today = datetime.now().date()
    focus = _month_start(focus_month) if focus_month else _month_start(today)

    # Number of months for monthly bar from scope
    if scope == "this_month":
        n_months = 1
    elif scope == "3months":
        n_months = 3
    elif scope == "all":
        n_months = 12
    else:
        n_months = 6

    # ---- Monthly Spending ----
    end_month = focus
    months = [_add_months(end_month, -i) for i in reversed(range(n_months))]
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

    # Date range for scope (for pie and trend)
    range_start = months[0] if months else focus
    range_end = _add_months(end_month, 1) if scope != "all" else today + timedelta(days=1)
    if scope == "all" and transactions:
        range_start = _month_start(min(tx_date(t) for t in transactions))
    elif scope == "all":
        range_start = focus

    def in_range(t):
        d = tx_date(t)
        return range_start <= d < range_end

    txs_in_scope = [t for t in transactions if in_range(t)]

    # ---- Expense Category Pie (scoped) ----
    category_order = ["Food", "Transport", "Shopping", "Bills", "Education", "Other"]
    category_keys = {"food": "Food", "transport": "Transport", "shopping": "Shopping", "bills": "Bills", "education": "Education"}
    category_totals = defaultdict(float)
    for t in txs_in_scope:
        amt = t.amount or 0
        if amt >= 0:
            continue
        key = (t.category or "").strip().lower()
        mapped = category_keys.get(key, "Other")
        category_totals[mapped] += abs(amt)
    category_data = [round(category_totals.get(k, 0.0), 2) for k in category_order]

    # ---- Income vs Expense Trend (30 days ending at focus month end or today) ----
    trend_days = 30
    end_day = min(today, range_end - timedelta(days=1)) if range_end else today
    start_day = end_day - timedelta(days=trend_days - 1)
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

    # ---- Weekly Spending (7 days ending at focus month or today) ----
    week_days = 7
    w_end = min(today, range_end - timedelta(days=1)) if range_end else today
    w_start = w_end - timedelta(days=week_days - 1)
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


def _available_months(user_id: str, last_n: int = 12) -> list:
    """
    Return list of (value_YYYY_MM, label) for month dropdown, most recent first.

    IMPORTANT: derive from the user's actual transactions so charts don't default
    to an empty future month (e.g. 2026) when data exists in earlier months.
    """
    pipeline, data_loader = initialize_pipeline()
    try:
        if data_loader and getattr(data_loader, "transactions_file", None) == DATA_TRANSACTIONS_CSV:
            data_loader._transactions_cache = None
    except Exception:
        pass
    txs = data_loader.load_transactions(user_id=user_id) or []

    months = set()
    for t in txs:
        try:
            d = t.timestamp.date()
        except Exception:
            continue
        months.add((d.year, d.month))

    # If we have real months, show them (latest first), capped.
    if months:
        sorted_months = sorted(months, key=lambda ym: (ym[0], ym[1]), reverse=True)[: int(last_n or 12)]
        return [(f"{y:04d}-{m:02d}", f"{calendar.month_abbr[m]} {y}") for (y, m) in sorted_months]

    # Fallback: last N months from today
    today = datetime.now().date()
    focus = _month_start(today)
    out = []
    for i in range(int(last_n or 12)):
        m = _add_months(focus, -i)
        out.append((m.strftime("%Y-%m"), f"{calendar.month_abbr[m.month]} {m.year}"))
    return out


def _latest_transaction_month(user_id: str):
    """Return first day of latest month that has transactions for this user, else None."""
    pipeline, data_loader = initialize_pipeline()
    try:
        if data_loader and getattr(data_loader, "transactions_file", None) == DATA_TRANSACTIONS_CSV:
            data_loader._transactions_cache = None
    except Exception:
        pass
    txs = data_loader.load_transactions(user_id=user_id) or []
    latest = None
    for t in txs:
        try:
            d = t.timestamp.date()
        except Exception:
            continue
        md = date(d.year, d.month, 1)
        if latest is None or md > latest:
            latest = md
    return latest


def _parse_month(month_str):
    """Parse YYYY-MM to first day of month, or None if invalid."""
    if not month_str or not isinstance(month_str, str):
        return None
    parts = month_str.strip().split("-")
    if len(parts) != 2:
        return None
    try:
        y, m = int(parts[0]), int(parts[1])
        if 1 <= m <= 12:
            return date(y, m, 1)
    except (ValueError, TypeError):
        pass
    return None


def _parse_transaction_date(date_str):
    """Parse YYYY-MM-DD to datetime at start of day (local), or None to use now."""
    if not date_str or not isinstance(date_str, str):
        return None
    s = date_str.strip()
    if not s:
        return None
    try:
        parts = s.split("-")
        if len(parts) != 3:
            return None
        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
        dt = date(y, m, d)
        return datetime.combine(dt, datetime.min.time())
    except (ValueError, TypeError):
        return None


def _recent_transactions_payload(user_id: str, limit: int = None) -> list:
    limit = limit if limit is not None else TRANSACTIONS_DISPLAY_LIMIT
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


@app.route('/enter', methods=['GET', 'POST'])
def enter():
    """Enter with email: existing user → dashboard with data; new user → register."""
    if request.method == 'GET':
        return render_template('enter_email.html')
    email = (request.form.get('email') or '').strip()
    if not email:
        flash('Please enter your email.', 'warning')
        return redirect(url_for('enter'))
    user = get_user_by_email(email)
    if user:
        switch_to_csv_loader()
        # If user has no saved transactions yet, seed them once so charts are not empty.
        try:
            added = seed_user_with_sample_transactions(user["user_id"])
            if added:
                flash(f"Loaded {added} sample transactions to get you started.", "info")
        except Exception:
            pass
        if pipeline and getattr(pipeline, '_is_trained', None) is False:
            txs = data_loader.load_transactions(user_id=user['user_id']) or []
            if len(txs) >= 2:
                try:
                    pipeline.train(user_id=user['user_id'])
                except Exception:
                    pass
        flash('Welcome back! Continue to your dashboard.', 'success')
        return redirect(url_for('dashboard', user_id=user['user_id']))
    return redirect(url_for('register', email=email))


@app.route('/load_sample_data')
def load_sample_data():
    """Load sample data into data/transactions.csv so same-email users see it in charts (single source of truth)."""
    global pipeline, data_loader
    try:
        ensure_data_files()
        # If persisted file is missing/empty, seed from sample so "enter with email" sees data in charts
        if not os.path.exists(DATA_TRANSACTIONS_CSV) and os.path.exists(SAMPLE_TRANSACTIONS):
            import shutil
            shutil.copy(SAMPLE_TRANSACTIONS, DATA_TRANSACTIONS_CSV)
        # Single source of truth: always use data/ so same-email users see past data in charts
        switch_to_csv_loader()
        sample_user = "user123"
        transactions = data_loader.load_transactions(user_id=sample_user)
        user_profile = data_loader.load_user_profile(sample_user)
        if not user_profile and os.path.exists(SAMPLE_USERS):
            import shutil
            if not os.path.exists(DATA_USERS_CSV):
                shutil.copy(SAMPLE_USERS, DATA_USERS_CSV)
            data_loader._users_cache = None
            user_profile = data_loader.load_user_profile(sample_user)
        if len(transactions) >= 2:
            try:
                pipeline.train(user_id=sample_user)
            except Exception:
                pass
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
    """User registration page. New users saved to data/users.csv; existing email → dashboard with past data."""
    if request.method == 'POST':
        user_id = (request.form.get('user_id') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        monthly_income = _safe_float(request.form.get('monthly_income'), 0.0)
        savings_goal = _safe_float(request.form.get('savings_goal'), 0.0)
        if not email:
            flash('Email is required.', 'warning')
            return redirect(url_for('register', email=request.form.get('email', '')))
        existing = get_user_by_email(email)
        if existing:
            # Same email → load their data and go to dashboard (no data lost)
            switch_to_csv_loader()
            existing_id = existing["user_id"]
            # If they never added transactions before, seed once so charts + list are populated.
            try:
                added = seed_user_with_sample_transactions(existing_id)
                if added:
                    flash(f"Loaded {added} sample transactions to get you started.", "info")
            except Exception:
                pass
            if pipeline and getattr(pipeline, '_is_trained', None) is False:
                txs = data_loader.load_transactions(user_id=existing_id) or []
                if len(txs) >= 2:
                    try:
                        pipeline.train(user_id=existing_id)
                    except Exception:
                        pass
            flash('This email is already registered. Your previous data is loaded below.', 'success')
            return redirect(url_for('dashboard', user_id=existing_id))
        if not user_id:
            flash('User ID is required for new registration.', 'warning')
            return redirect(url_for('register', email=email))
        append_user_to_csv(user_id, email, monthly_income, savings_goal)
        # Send a simple registration email (best-effort, no hard failure if SMTP not configured)
        try:
            send_registration_email(email, user_id)
        except Exception:
            pass
        switch_to_csv_loader()
        user_profile = UserProfile(
            user_id=user_id,
            monthly_income=monthly_income,
            savings_goal=savings_goal,
            preferences={'email': email},
        )
        data_loader.add_user_profile(user_profile)
        # New users: seed with sample transactions so dashboard is not empty in demos.
        try:
            seed_user_with_sample_transactions(user_id)
        except Exception:
            pass
        flash('Registration successful. Continue to your dashboard.', 'success')
        return redirect(url_for('dashboard', user_id=user_id))
    prefill_email = request.args.get('email', '')
    return render_template('register.html', prefill_email=prefill_email)


SCOPE_OPTIONS = [
    ("this_month", "This month only"),
    ("3months", "Last 3 months"),
    ("6months", "Last 6 months"),
    ("all", "All time"),
]


@app.route('/dashboard/<user_id>')
def dashboard(user_id):
    """User dashboard. Supports ?month=YYYY-MM&scope=this_month|3months|6months|all for dynamic view."""
    pipeline, data_loader = initialize_pipeline()
    month_param = request.args.get("month", "").strip()
    scope_param = request.args.get("scope", "6months").strip().lower()
    if scope_param not in [s[0] for s in SCOPE_OPTIONS]:
        scope_param = "6months"
    focus_month = _parse_month(month_param)
    today = datetime.now().date()
    if not focus_month:
        # Default to latest month that actually has data for this user (so charts aren't empty)
        focus_month = _latest_transaction_month(user_id) or _month_start(today)
    available_months = _available_months(user_id, 12)
    # If query month was missing, align focus month to the first dropdown option (latest data month)
    if not month_param and available_months:
        focus_month = _parse_month(available_months[0][0]) or focus_month
    selected_month = focus_month.strftime("%Y-%m")
    selected_scope = scope_param

    # Load user transactions (CSV loader caches; force reload so saved file data shows after refresh)
    try:
        if data_loader and getattr(data_loader, "transactions_file", None) == DATA_TRANSACTIONS_CSV:
            data_loader._transactions_cache = None
    except Exception:
        pass
    transactions = data_loader.load_transactions(user_id=user_id) or []
    user_profile = data_loader.load_user_profile(user_id)
    monthly_income = getattr(user_profile, "monthly_income", None) if user_profile else None

    # Budget tracking for selected month
    budgets = BudgetManager.get_user_budgets(user_id)
    category_spending = BudgetManager.calculate_category_spending(transactions, month=focus_month)
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
    
    chart_data = _chart_data_for_user(user_id, focus_month=focus_month, scope=scope_param)
    focus_month_label = f"{calendar.month_abbr[focus_month.month]} {focus_month.year}"
    # Sorted list for dashboard (latest first, cap at 50 so charts and list use same data)
    transactions_sorted = sorted(transactions or [], key=lambda t: getattr(t, 'timestamp', datetime.min), reverse=True)
    transactions_display = transactions_sorted[:TRANSACTIONS_DISPLAY_LIMIT]
    return render_template('dashboard.html', 
                         user_id=user_id,
                         transactions=transactions,
                         transactions_display=transactions_display,
                         user_profile=user_profile,
                         is_trained=is_trained,
                         insights=insights,
                         notifications=notifications,
                         upcoming_predictions=upcoming_predictions,
                         transaction_count=len(transactions),
                         budgets=budgets,
                         category_spending=category_spending,
                         budget_summary=budget_summary,
                         finance_score=finance_score,
                         available_months=available_months,
                         selected_month=selected_month,
                         selected_scope=selected_scope,
                         scope_options=SCOPE_OPTIONS,
                         chart_data=chart_data,
                         focus_month_label=focus_month_label)


@app.route('/add_transaction/<user_id>', methods=['GET', 'POST'])
def add_transaction(user_id):
    """Add transaction page."""
    pipeline, data_loader = initialize_pipeline()
    
    if request.method == 'POST':
        amount = float(request.form.get('amount', 0))
        description = request.form.get('description', '')
        category = request.form.get('category', '')
        merchant = request.form.get('merchant', '')
        tx_timestamp = _parse_transaction_date(request.form.get('transaction_date')) or datetime.now()

        # Auto-predict category if user didn't choose one
        predicted = None
        if not category:
            predicted = predict_category(description, merchant)
            category = predicted

        transaction = Transaction(
            amount=-abs(amount),
            description=description,
            timestamp=tx_timestamp,
            category=category if category else None,
            merchant=merchant if merchant else None,
            user_id=user_id
        )
        data_loader.add_transaction(transaction)
        # Persist so past data is shown when user re-enters or registers again
        if getattr(data_loader, "transactions_file", None) == DATA_TRANSACTIONS_CSV:
            append_transaction_to_csv(transaction)
        
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
    """Return chart-ready aggregates for Chart.js. Optional: ?month=YYYY-MM&scope=6months."""
    try:
        month_param = request.args.get("month", "").strip()
        scope_param = request.args.get("scope", "6months").strip().lower()
        if scope_param not in [s[0] for s in SCOPE_OPTIONS]:
            scope_param = "6months"
        focus_month = _parse_month(month_param)
        if not focus_month:
            focus_month = _latest_transaction_month(user_id) or _month_start(datetime.now().date())
        charts = _chart_data_for_user(user_id, focus_month=focus_month, scope=scope_param)
        return jsonify({"ok": True, "user_id": user_id, "charts": charts})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route('/api/dashboard_snapshot/<user_id>')
def api_dashboard_snapshot(user_id):
    """Return charts + latest transactions. Optional: ?month=YYYY-MM&scope=6months."""
    try:
        pipeline, data_loader = initialize_pipeline()
        txs = data_loader.load_transactions(user_id=user_id) or []
        month_param = request.args.get("month", "").strip()
        scope_param = request.args.get("scope", "6months").strip().lower()
        if scope_param not in [s[0] for s in SCOPE_OPTIONS]:
            scope_param = "6months"
        focus_month = _parse_month(month_param)
        if not focus_month:
            focus_month = _latest_transaction_month(user_id) or _month_start(datetime.now().date())
        charts = _chart_data_for_user(user_id, focus_month=focus_month, scope=scope_param)
        return jsonify(
            {
                "ok": True,
                "user_id": user_id,
                "transaction_count": len(txs),
                "is_trained": bool(getattr(pipeline, "_is_trained", False)),
                "charts": charts,
                "recent_transactions": _recent_transactions_payload(user_id, limit=TRANSACTIONS_DISPLAY_LIMIT),
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
        tx_timestamp = _parse_transaction_date(
            payload.get("transaction_date") or payload.get("date") or ""
        ) or datetime.now()

        if not description:
            return jsonify({"ok": False, "error": "Description is required"}), 400
        if amount <= 0:
            return jsonify({"ok": False, "error": "Amount must be greater than 0"}), 400

        if not category:
            category = predict_category(description, merchant)

        signed_amount = abs(amount) if kind == "income" else -abs(amount)
        transaction = Transaction(
            amount=signed_amount,
            description=description,
            timestamp=tx_timestamp,
            category=category if category else None,
            merchant=merchant if merchant else None,
            user_id=user_id,
        )
        data_loader.add_transaction(transaction)
        # Persist so past data is shown when user re-enters or registers again
        if getattr(data_loader, "transactions_file", None) == DATA_TRANSACTIONS_CSV:
            append_transaction_to_csv(transaction)

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
    ensure_data_files()
    initialize_pipeline()
    print("\n" + "="*70)
    print("Finance ML Pipeline Web Application")
    print("="*70)
    print("\nStarting server...")
    print("Open your browser and go to: http://127.0.0.1:5000")
    print("\nPress Ctrl+C to stop the server")
    print("="*70 + "\n")
    app.run(debug=True, host='127.0.0.1', port=5000)
