## Finance ML Pipeline (IntelliBank) — One-File Guide

This file explains **all features**, **backend flow**, and **how to present the mini project**.
Read this like a senior developer coaching an intern before demo day.

---

## ### What this project is (in one line)
A **Flask mini web app** for personal finance that combines **ML-based insights** + **rule-based intelligence** + **interactive charts** in a clean dashboard.

---

## ### Features available (what to show your guide)

### 1) Web app screens (user flow)
- **Home**: entry point + “Try Sample Dataset” for quick demo
- **Register**: create a user profile (income stored in-memory for that session)
- **Dashboard**: the main “mini app” screen where everything comes together
- **Add Transaction**: classic form flow to add an expense (manual category optional)
- **Train**: trains ML components (anomaly detector, expense analyzer, categorizer if labeled data exists)
- **Insights**: shows savings + expense suggestions + summary

### 2) Financial Insights charts (Chart.js)
Dashboard section **Financial Insights** includes 4 charts:
- **Monthly Spending (Bar)**: total expenses by month (recent months)
- **Expense Distribution (Pie)**: share of spending by category (Food/Transport/Shopping/Bills/Other)
- **Income vs Expense Trend (Line)**: daily totals over recent days (2 lines: Income = green, Expense = red)
- **Weekly Spending Activity (Bar)**: expenses for last 7 days

Key demo point: charts update automatically from stored transactions.

### 3) Quick Add transaction (no refresh)
Dashboard has **＋ Quick Add**:
- Opens a modal
- Adds transaction via a JSON/form API
- Updates charts + recent transactions instantly (no page reload)

### 4) Budget tracking (CSV-backed)
- Budgets stored in **`data/budgets.csv`**
- Dashboard shows **Budget Summary (This Month)**: Spent vs Limit
- **Manage Budgets** button opens a modal
  - Saves budgets to CSV
  - **Updates Budget Summary instantly** (DOM update, no refresh)

### 5) Smart notifications (rule-based engine)
Notifications are generated dynamically from:
- **Budget exceeded** (from budgets)
- **High category spending** (>30% of monthly income)
- **Anomaly alerts** (when anomaly detector is fitted)
- Optional: **high spending day**

Displayed on dashboard and in the notifications popup.

### 6) AI expense categorization (rule-based)
When adding a transaction:
- If **category is empty**, the system predicts one using keywords:
  - “dominos, pizza, swiggy” → food
  - “uber, ola, metro” → transport
  - “amazon, flipkart” → shopping
  - “netflix, movie” → entertainment

Manual category selection always overrides prediction.

### 7) Finance Health Score (0–100)
Dashboard shows a score card + short insights.
Score factors (weighted):
- Savings rate (30%)
- Budget adherence (30%)
- Spending distribution (20%)
- Anomalies detected (20%)

---

## ### How the backend works (clear intern-level mental model)

### A) Storage model (simple + mini-project friendly)
This project uses a **hybrid storage approach**:

1) **CSV sample dataset** (persistent input)
- `data/sample_transactions.csv`
- `data/sample_users.csv`

2) **In-memory additions** (during the current server run)
- When you add a transaction in the web UI, it is stored in memory (DataLoader cache).
- This keeps the project simple and demo-friendly (no DB setup).

3) **Budgets CSV** (persistent configuration)
- `data/budgets.csv` stores category limits per user.

### B) Core “engine”: FinanceMLPipeline
`src/pipeline.py` is the orchestrator:
- anomaly detection
- expense suggestions
- categorization (if trained with labeled categories)
- savings suggestions
- existing notification utilities (pattern-based reminders still exist)

Important: your newer features **do not modify the ML logic**. They only consume outputs.

### C) Dashboard composition (what happens when you open /dashboard/<user>)
When you open the dashboard, the server:
1) Loads user transactions via DataLoader
2) Loads user profile (income)
3) Loads budgets from `data/budgets.csv`
4) Calculates:
   - category spending
   - budget summary
   - smart notifications (rule engine)
   - finance health score
5) Renders `templates/dashboard.html`

### D) JSON APIs (why they exist)
To support “mini app” interactions without refresh:
- **Charts API**: returns chart-ready aggregates
- **Quick Add API**: adds transaction and returns an updated snapshot
- **Budgets update API**: writes budgets CSV and returns updated budgets JSON

You can explain it as: *“We kept Flask templates for the UI, but we use small APIs to update specific parts of the dashboard live.”*

---

## ### How to run (what to do before you meet your guide)

### 1) Install
```bash
python -m pip install -r requirements.txt
```

### 2) Run server
```bash
python app.py
```

### 3) Open browser
`http://127.0.0.1:5000`

Tip: Keep one tab open to the dashboard during the demo.

---

## ### Presentation plan (5–7 minutes, very effective)

### Step 0 — Setup sentence (10 seconds)
“This is a personal finance mini application. It combines ML insights with budgeting and interactive charts to help users understand spending patterns and stay financially healthy.”

### Step 1 — Load sample data (30 seconds)
1. Home → Click **Try Sample Dataset**
2. Go to Dashboard for `user123`

Talking points:
- “The sample dataset is CSV-based, so it’s easy to test.”
- “The dashboard is the main screen.”

### Step 2 — Financial Insights charts (45 seconds)
Show the 4 charts and explain what each chart means:
- Monthly Spending → overall expense trend
- Expense Distribution → which categories dominate
- Income vs Expense Trend → daily pattern
- Weekly Spending → last 7 days behavior

### Step 3 — Quick Add (live update, no refresh) (60 seconds)
Click **＋ Quick Add**, add:
- Expense, amount: 599
- Description: “Dominos Pizza”
- Merchant: “Dominos”
- Leave category empty

Then say:
- “Category is auto predicted.”
- “Charts update immediately. This is important for an interactive dashboard.”

### Step 4 — Budgets (interactive UI but lightweight) (60 seconds)
1. Click **Manage Budgets**
2. Reduce Food limit (so it becomes exceeded)
3. Click **Save Changes**
4. Show Budget Summary changes **instantly**

Talking points:
- “Budgets are stored in CSV (no DB).”
- “Budget Summary updates using DOM manipulation (simple JS, no framework).”

### Step 5 — Smart notifications + health score (45 seconds)
1. Click **Notifications** popup
2. Show budget exceeded / high category spend messages
3. Show Finance Health Score and 2–4 insights

Talking points:
- “Rule-based engine makes the app feel intelligent even without heavy AI.”
- “Finance score gives a clear KPI for the user.”

### Step 6 — Insights page (45 seconds)
Open **Insights**:
- show savings/expense suggestions
Explain: “This is where ML outputs are presented.”

### Closing (15 seconds)
“In short, this project gives a complete mini finance product: ingestion → analysis → visualization → action (budgets + alerts).”

---

## ### Backend “questions your guide may ask” (and how to answer)

### Q1) Where is data stored?
- Sample: CSV files in `data/`
- New transactions: in-memory cache while server runs
- Budgets: CSV `data/budgets.csv`

### Q2) How are charts calculated?
- Aggregation from user transactions via API endpoints returning chart-ready series.

### Q3) What makes notifications “smart”?
- Rule engine uses income, budgets, spending distribution, and anomaly detector results.

### Q4) Where is the ML?
- `src/pipeline.py` orchestrates anomaly detection, categorization, and savings/expense suggestions.

---

## ### UI improvements for charts (what to add to screens to make it look great)

These are small, high-impact upgrades (no framework).

### 1) Use consistent chart card sizing
Keep each chart inside a fixed-height container (already used):
- Height ~ **260–320px**
- Avoid super tall charts that cause scrolling.

### 2) Add micro “stat tiles” above charts (very good for presentation)
Add 3–4 small cards above “Financial Insights”, like:
- “This month spent: ₹X”
- “Top category: Food”
- “Budget exceeded: 2 categories”
- “Health score: 72”

These help the viewer interpret charts instantly.

### 3) Improve chart readability
In `static/js/financial-charts.js` you can adjust:
- **tick formatting** (₹K / ₹L)
- **max tick count** on the line chart (so labels don’t overlap)
- **tooltips** to show exact values
- **colors**: Income green, Expense red, multiple category colors

### 4) Add “empty state” messages for charts
If no transactions exist:
- Show a small alert: “Add a transaction to see charts.”
This looks polished and avoids blank charts.

### 5) Use consistent category naming
Make sure your category values are consistent (food/transport/shopping/bills/other) so pie chart and budgets align.

### 6) Add a “last updated” small text
Example: “Updated: 2 minutes ago”
This makes the dashboard feel real and modern.

---

## ### File map (where features live)

### Backend
- `app.py` — Flask routes + APIs + dashboard composition
- `src/pipeline.py` — ML orchestrator
- `src/anomaly_detection.py` — anomaly model
- `src/transaction_categorization.py` — ML categorization (if trained)
- `src/budget_manager.py` — budgets CSV read/write + checks
- `src/notifications_engine.py` — smart rule-based notifications
- `src/category_predictor.py` — keyword-based category prediction
- `src/finance_score.py` — score + insights

### Frontend
- `templates/base.html` — design tokens, layout, modal/toast styles
- `templates/dashboard.html` — dashboard layout + cards + chart canvases
- `static/js/mini-app.js` — modal/toast utilities
- `static/js/financial-charts.js` — Chart.js rendering + live updates

---

## ### One last tip (presentation confidence booster)
Before meeting your guide:
- Run the app once
- Use sample data
- Do one Quick Add + one budget change
- Confirm: charts update + budget summary updates instantly

That’s the “wow moment” that makes the project look like a real mini product.

