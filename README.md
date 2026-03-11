# Finance ML Pipeline (IntelliBank) — Mini Project

A **Flask-based personal finance mini app** enhanced with **Machine Learning + interactive dashboard UI**.

You can:
- Load a sample dataset, or register your own user
- Add transactions (expense or income)
- Train ML models and get insights
- View **Financial Insights charts** (Chart.js)
- Set **category budgets** (CSV-backed) and track spending vs limits
- Get **smart rule-based notifications**
- See a **Finance Health Score (0–100)**

---

## Quick Start (Web App)

### 1) Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 2) Run the server

```bash
python app.py
```

Open in browser:
- `http://127.0.0.1:5000`

---

## Recommended Demo Flow (10/10 Presentation)

This is a clean flow for a **5–7 minute** mini-project presentation.

### Part A — Problem & solution (30–45 sec)
- **Problem**: People don’t track spending patterns; budgets are hard; unusual transactions go unnoticed.
- **Solution**: A mini finance app that combines **ML insights + dashboards + alerts + budgeting**.

### Part B — Live product walkthrough (4–5 min)

1) **Home → Try Sample Dataset**
   - Click **“Try Sample Dataset”**
   - Explain: loads CSV sample data and prepares a ready-to-demo user (`user123`)

2) **Dashboard (show the “mini app” UI)**
   - Highlight laptop-friendly UI (no zoom)
   - Show **Financial Insights** charts:
     - Monthly Spending (bar)
     - Expense Distribution (pie)
     - Income vs Expense Trend (line)
     - Weekly Spending Activity (bar)

3) **Quick Add → Live chart update (no refresh)**
   - Click **“＋ Quick Add”**
   - Add a transaction like:
     - Type: Expense
     - Description: `Dominos Pizza`
     - Merchant: `Dominos`
     - Category: leave empty (auto-predict)
   - Explain:
     - Category is auto-predicted (rule-based)
     - Charts + recent transactions update immediately

4) **Budgets → Manage Budgets (interactive UI)**
   - Open **Manage Budgets** modal
   - Change limits (e.g., lower Food budget)
   - Click **Save Changes**
   - Show:
     - **Budget Summary card updates instantly** (DOM update, no refresh)
     - Explain: budgets persist in `data/budgets.csv`

5) **Smart Notifications**
   - Click **Notifications**
   - Explain rules:
     - High category spending relative to income
     - Budget exceeded warnings
     - Anomaly alerts (when anomaly detector is fitted)

6) **Finance Health Score**
   - Show the score card (0–100)
   - Explain score factors:
     - Savings rate, budgets adherence, distribution, anomalies

7) **Insights page (ML outputs)**
   - Click **Insights**
   - Explain:
     - Expense suggestions
     - Savings suggestions
     - Financial summary

### Part C — Technical architecture (60–90 sec)

Explain the pipeline and integrations briefly:
- **Storage**: CSV sample data + in-memory additions; budgets in CSV
- **Backend**: Flask routes + lightweight JSON APIs
- **ML**: anomaly detection, categorization, savings & expense analyzers
- **Frontend**: template-based UI with reusable modal/toast utilities, Chart.js for visualization

### Part D — Wrap-up (30 sec)
- Summarize outcomes:
  - “A mini finance app with ML insights, interactive charts, budgets, smart notifications, and a health score.”
- Mention next steps:
  - authentication, persistence DB, export reports, dark mode, stronger ML category model, etc.

---

## Main Features

### 1) Machine Learning pipeline
- **Anomaly detection**: flags unusual transactions
- **Transaction categorization**: ML-based categorization (when trained with labeled data)
- **Expense + savings suggestions**: personalized guidance based on spend patterns

### 2) Financial Insights charts (Chart.js)
Dashboard section **Financial Insights**:
- Monthly Spending (bar)
- Expense Distribution (pie)
- Income vs Expense Trend (line)
- Weekly Spending Activity (bar)

Automatically aggregates from transactions and updates dynamically after **Quick Add**.

### 3) Budget tracking (CSV-backed)
- Budgets stored in: `data/budgets.csv`
- Dashboard shows **Budget Summary**
- Modal **Manage Budgets** writes to CSV
- Summary updates instantly after save (DOM update)

### 4) Smart notifications (rule-based)
Module: `src/notifications_engine.py`
- High category spend vs income
- Budget exceeded warnings
- Anomaly alerts (when detector fitted)
- Optional high-spending day tip

### 5) AI Expense categorization (rule-based)
Module: `src/category_predictor.py`
- If user doesn’t select category, predicts from description/merchant keywords
- Manual override always respected

### 6) Finance Health Score (0–100)
Module: `src/finance_score.py`
Weights:
- Savings rate 30%
- Budget adherence 30%
- Spending distribution 20%
- Anomalies 20%

---

## How It Works (Data Flow)

1) Transactions come from a **DataLoader**:
- `CSVDataLoader` reads `data/sample_transactions.csv`, `data/sample_users.csv`
- New transactions are added in-memory via web UI / APIs

2) The **FinanceMLPipeline** trains and generates outputs:
- anomaly detector
- expense analyzer
- transaction categorizer (if labeled data exists)
- savings analyzer

3) The dashboard composes:
- ML-driven insights (optional if trained)
- rule-based notifications (budgets + income + anomalies)
- finance score
- chart aggregates via APIs for Chart.js

---

## Key Endpoints (Web + APIs)

### Web pages
- `/` home
- `/load_sample_data` load sample user data (`user123`)
- `/register` register user
- `/dashboard/<user_id>` dashboard
- `/add_transaction/<user_id>` add transaction (classic flow)
- `/train/<user_id>` train models
- `/insights/<user_id>` insights

### JSON APIs (used by the dashboard)
- `GET /api/financial_insights/<user_id>` → chart aggregates
- `GET /api/dashboard_snapshot/<user_id>` → charts + recent tx (for quick refresh)
- `POST /api/transactions/<user_id>` → AJAX add transaction (Quick Add)
- `POST /update-budgets` → update budgets (Manage Budgets modal)
- `GET /api/budgets/<user_id>` / `POST /api/budgets/<user_id>` → budgets API (optional direct use)

---

## Data Files

- `data/sample_transactions.csv` — sample transactions (expenses are negative)
- `data/sample_users.csv` — sample user profiles
- `data/budgets.csv` — category budgets per user (CSV-backed)

---

## Troubleshooting

### ModuleNotFoundError / import issues

Run from the project root:

```bash
cd C:\Users\jahna\Downloads\MiniProject
python app.py
```

### Charts not showing
- Ensure you have internet (Chart.js loads via CDN).
- Open DevTools → Console for errors.

---

## Docs

- `UI_IMPROVEMENTS.md` — UI system & responsive design notes
- `data/ReadmeFiles/README.md` — dataset + mini-project notes (extended)

