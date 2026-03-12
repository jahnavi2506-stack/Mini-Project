# IntelliBank Mini Project — Complete Guide


## 1. What This Project Is

**IntelliBank** is a personal finance mini app built with **Flask** (backend) and **HTML/CSS/JS** (frontend). It uses **Machine Learning** and **rule-based logic** to:

- Categorize expenses, detect anomalies, suggest savings, and score financial health  
- Show **charts** (Chart.js) and **budgets** (CSV-backed)  
- Send **smart notifications** (high spending, budget exceeded, anomalies)

**Tech stack:** Python 3, Flask, Jinja2, Chart.js, vanilla JavaScript (no React/Vue).

---

## 2. All Features (Summary)

| Feature | What it does | Where you see it |
|--------|---------------|------------------|
| **Sample dataset** | Loads CSV transactions and a demo user | Home → "Try Sample Dataset" |
| **Dashboard** | Main view: charts, budgets, score, notifications | `/dashboard/<user_id>` |
| **Financial Insights charts** | 4 charts: monthly bar, category pie, income vs expense line, weekly bar | Dashboard section "Financial Insights" |
| **Quick Add transaction** | Add expense/income; category auto-predicted if empty | "+ Quick Add" on dashboard; charts update without refresh |
| **Budget Summary** | Category-wise budget vs spent this month | Dashboard card "Budget Summary (This Month)" |
| **Manage Budgets** | Edit category limits in a modal; save to CSV; card updates instantly | "Manage Budgets" in Budget Summary card |
| **Smart Notifications** | Rule-based: high category %, budget exceeded, anomaly, high-spend day | "Notifications" button; list in dashboard |
| **Finance Health Score** | 0–100 score + short insights | Dashboard card "Finance Health Score" |
| **ML pipeline** | Anomaly detection, categorization, savings/expense suggestions | Backend; results feed dashboard and APIs |

---

## 3. How to Present to Your Guide (Step-by-Step)

### Before you start

1. Install: `pip install -r requirements.txt`  
2. Run: `python app.py`  
3. Open: `http://127.0.0.1:5000`

### Demo script (5–7 minutes)

**Step 1 — Home (30 sec)**  
- Say: "This is a personal finance app with ML and dashboards."  
- Click **"Try Sample Dataset"**.  
- Say: "We load sample transactions and a demo user so we can show the dashboard."

**Step 2 — Dashboard and charts (1–2 min)**  
- You land on the dashboard.  
- Say: "The main view has four charts: **Monthly Spending** (bar), **Expense Distribution** (pie), **Income vs Expense** (line), **Weekly Spending** (bar). They all read from the same transaction data."  
- Point out: **Budget Summary** (limits vs spent), **Finance Health Score** (0–100 and insights), and the **Notifications** area.

**Step 3 — Quick Add + live update (1 min)**  
- Click **"+ Quick Add"**.  
- Add: Type = Expense, Description = "Dominos Pizza", Merchant = "Dominos", **Category = leave empty**.  
- Submit.  
- Say: "Category is auto-filled by our rule-based predictor. After save, charts and the recent transactions list update **without refreshing the page** — we use the REST API and JavaScript."

**Step 4 — Manage Budgets (1 min)**  
- Click **"Manage Budgets"** in the Budget Summary card.  
- Change a value (e.g. Food 8000 → 6000).  
- Click **Save Changes**.  
- Say: "Budgets are stored in CSV. Only the Budget Summary card updates instantly via JavaScript; the rest of the page doesn’t reload."

**Step 5 — Notifications and score (30 sec)**  
- Click **Notifications**.  
- Say: "Alerts are rule-based: high category spending, budget exceeded, anomaly transactions, high-spend day. The Finance Health Score combines savings rate, budget adherence, spending spread, and anomalies."

**Step 6 — Backend in one sentence**  
- Say: "Flask serves HTML and JSON APIs. A single ML pipeline runs anomaly detection, categorization, and suggestions. We use CSV for transactions and budgets; the pipeline and rules run in Python."

---

## 4. Backend (Clear Picture)

### 4.1 Entry point

- **`app.py`** — Flask app: routes, JSON APIs, calls to pipeline and helpers.

### 4.2 Data

- **Transactions:** In-memory list (from sample CSV or added via UI). Each has: user_id, amount, type (income/expense), category, description, merchant, timestamp.  
- **Budgets:** `data/budgets.csv` — `user_id`, `category`, `budget_limit`.  
- **Users:** From sample loader or registration; stored in memory in `WebDataLoader`.

### 4.3 Main modules

| Module | Role |
|--------|------|
| `src/pipeline.py` | Runs the full ML pipeline: anomaly, categorization, savings/expense suggestions. |
| `src/anomaly_detection.py` | Anomaly detection (e.g. Isolation Forest + Z-score). |
| `src/transaction_categorization.py` | ML-based category from description/merchant (needs some training data). |
| `src/category_predictor.py` | **Rule-based** category prediction (keywords, e.g. "pizza" → food). Used when user leaves category empty. |
| `src/notifications_engine.py` | Builds list of notifications (high spending, budget exceeded, anomaly, high-spend day). |
| `src/budget_manager.py` | Reads/writes `budgets.csv`, computes spending per category, checks exceeded. |
| `src/finance_score.py` | Computes 0–100 score and insights (savings rate, budget adherence, distribution, anomalies). |
| `src/savings_suggestions.py` / `src/expense_suggestions.py` | Used by pipeline for suggestions. |

### 4.4 Important routes and APIs

- **GET /** — Home.  
- **GET /dashboard/&lt;user_id&gt;** — Renders dashboard (charts data passed to template; Chart.js draws on frontend).  
- **GET /api/financial_insights/&lt;user_id&gt;** — JSON for charts (monthly, category, income/expense, weekly).  
- **GET /api/dashboard_snapshot/&lt;user_id&gt;** — Charts + recent transactions (for Quick Add refresh).  
- **POST /api/transactions/&lt;user_id&gt;** — Add transaction (category predicted if empty); returns dashboard snapshot.  
- **GET /api/budgets/&lt;user_id&gt;** — Get budgets JSON.  
- **POST /api/budgets/&lt;user_id&gt;** or **POST /update-budgets** — Save budgets; response used to update Budget Summary card.

Flow in short: **Browser → Flask route or API → pipeline / budget_manager / notifications_engine / finance_score → CSV or in-memory data → HTML or JSON → browser.**

---

## 5. Frontend (Charts and UI)

- **Templates:** Jinja2 in `templates/` (e.g. `base.html`, `dashboard.html`).  
- **Charts:** Chart.js in `static/js/financial-charts.js`. The dashboard has four `<canvas>` elements; this script creates one chart per canvas from data passed by the server or from the snapshot API.  
- **Quick Add:** Form in modal; on submit, `fetch` POST to `/api/transactions/<user_id>`, then replace chart data and recent-transactions table from the response.  
- **Manage Budgets:** Modal form; on Save, `fetch` POST to `/update-budgets` (or `/api/budgets/<user_id>`), then JavaScript updates only the Budget Summary card (table or empty state) from the returned budgets and existing category spending.  
- **Toasts / modals:** `static/js/mini-app.js` (e.g. `MiniApp.showToast`, `MiniApp.showModal`).

---

## 6. Making Charts Look Great on Screen

- **Resolution:** Use a normal browser zoom (100%) and a decent window size so labels and legends are readable.  
- **Data:** Load sample dataset so all four charts have data (multiple months, categories, and recent days).  
- **Placement:** Keep the Financial Insights section in view when you present; scroll to it if the dashboard is long.  
- **Colors:** Already set in `financial-charts.js` (e.g. expenses red, income green, categories distinct). If you change them, keep contrast and consistency.  
- **Quick Add:** After adding a transaction, point at the chart that should change (e.g. monthly or category) and show it updated without refresh.

---

## 7. Algorithms (High Level)

- **Anomaly detection:** Model-based (e.g. Isolation Forest) plus Z-score on amount; transactions scoring as anomalies are flagged and used in notifications and health score.  
- **Categorization (ML):** Text (description/merchant) → TF-IDF (or similar) → classifier (e.g. Naive Bayes/Logistic Regression); used when enough training data exists.  
- **Category prediction (rules):** `category_predictor.py` uses keyword rules (e.g. "pizza", "restaurant" → food) to fill category when the user leaves it empty.  
- **Finance score:** Weighted combination of savings rate, budget adherence, spending distribution, and anomaly count, normalized to 0–100 and a few text insights.  
- **Notifications:** Rules: e.g. category &gt; X% of income, budget exceeded (from `budget_manager`), anomaly flag, single-day spending &gt; Y% of income.

---

## 8. Project Need and Use

- **Need:** People don’t track spending well; budgets are hard to follow; unusual transactions are missed.  
- **Use:** One place to see spending (charts), set category budgets, get alerts (notifications), and a simple health score — with minimal setup (CSV + in-memory, no DB). Good for a **mini project** to show full-stack (Flask + JS), ML pipeline, and clean UI (charts, modals, instant updates).

---

## 9. One-Page Cheat Sheet for You

1. **Run:** `python app.py` → open `http://127.0.0.1:5000`.  
2. **Demo:** Try Sample Dataset → Dashboard → Quick Add (no category) → Manage Budgets → Notifications.  
3. **Backend:** Flask + pipeline (anomaly, categorization, suggestions) + budget_manager + notifications_engine + finance_score; data in memory + budgets.csv.  
4. **Frontend:** Jinja2 + Chart.js (financial-charts.js) + mini-app.js (modals/toasts); APIs for add-transaction and budgets so the dashboard and Budget Summary update without full reload.  
5. **Charts:** Ensure sample data is loaded and Financial Insights section is visible at 100% zoom for a clear, professional look.

If you follow this file, you have one place that explains all features, how to present, what the backend does, and how to make the visualization look great for your guide.
