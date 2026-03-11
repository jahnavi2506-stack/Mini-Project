/* global Chart, MiniApp */
/**
 * IntelliBank Dashboard – Financial Insights Charts
 *
 * Modular Chart.js integration:
 * - fetch chart-ready aggregates from /api/financial_insights/:userId
 * - render 4 charts
 * - refresh charts + recent transactions after adding a transaction via AJAX
 */

(function () {
  'use strict';

  const COLORS = {
    income: '#16a34a',   // green
    expense: '#dc2626',  // red
    grid: 'rgba(148, 163, 184, 0.35)',
    text: '#0f172a',
    muted: '#64748b',
    categories: ['#0ea5e9', '#22c55e', '#a855f7', '#f59e0b', '#64748b']
  };

  function $(id) { return document.getElementById(id); }

  function moneyTick(value) {
    const v = Number(value || 0);
    if (Math.abs(v) >= 100000) return '₹' + (v / 100000).toFixed(1) + 'L';
    if (Math.abs(v) >= 1000) return '₹' + (v / 1000).toFixed(1) + 'K';
    return '₹' + v.toFixed(0);
  }

  function baseOptions() {
    return {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: COLORS.muted } },
        tooltip: {
          callbacks: {
            label: function (ctx) {
              const val = (ctx.parsed && typeof ctx.parsed === 'object') ? ctx.parsed.y : ctx.parsed;
              return (ctx.dataset.label ? ctx.dataset.label + ': ' : '') + '₹' + Number(val || 0).toFixed(2);
            }
          }
        }
      },
      scales: {
        x: { ticks: { color: COLORS.muted }, grid: { color: 'transparent' } },
        y: { ticks: { color: COLORS.muted, callback: moneyTick }, grid: { color: COLORS.grid } }
      }
    };
  }

  function createMonthlyBar(ctx, series) {
    return new Chart(ctx, {
      type: 'bar',
      data: {
        labels: series.labels,
        datasets: [{
          label: 'Expenses',
          data: series.data,
          backgroundColor: 'rgba(220, 38, 38, 0.85)',
          borderColor: COLORS.expense,
          borderWidth: 1,
          borderRadius: 8
        }]
      },
      options: baseOptions()
    });
  }

  function createCategoryPie(ctx, series) {
    return new Chart(ctx, {
      type: 'pie',
      data: {
        labels: series.labels,
        datasets: [{
          label: 'Expense Share',
          data: series.data,
          backgroundColor: COLORS.categories,
          borderColor: '#ffffff',
          borderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom', labels: { color: COLORS.muted } }
        }
      }
    });
  }

  function createIncomeVsExpense(ctx, series) {
    const opts = baseOptions();
    opts.scales.x.ticks.maxRotation = 0;
    opts.scales.x.ticks.autoSkip = true;
    opts.scales.x.ticks.maxTicksLimit = 8;
    return new Chart(ctx, {
      type: 'line',
      data: {
        labels: series.labels,
        datasets: [
          {
            label: 'Income',
            data: series.income,
            borderColor: COLORS.income,
            backgroundColor: 'rgba(22, 163, 74, 0.15)',
            tension: 0.35,
            fill: true,
            pointRadius: 2
          },
          {
            label: 'Expenses',
            data: series.expense,
            borderColor: COLORS.expense,
            backgroundColor: 'rgba(220, 38, 38, 0.10)',
            tension: 0.35,
            fill: true,
            pointRadius: 2
          }
        ]
      },
      options: opts
    });
  }

  function createWeeklyBar(ctx, series) {
    const opts = baseOptions();
    opts.scales.y.beginAtZero = true;
    return new Chart(ctx, {
      type: 'bar',
      data: {
        labels: series.labels,
        datasets: [{
          label: 'Expenses',
          data: series.data,
          backgroundColor: 'rgba(220, 38, 38, 0.75)',
          borderColor: COLORS.expense,
          borderWidth: 1,
          borderRadius: 8
        }]
      },
      options: opts
    });
  }

  function updateChart(chart, labels, datasetValues, datasetIndex) {
    chart.data.labels = labels;
    if (Array.isArray(datasetValues)) {
      if (typeof datasetIndex === 'number') {
        chart.data.datasets[datasetIndex].data = datasetValues;
      } else {
        chart.data.datasets[0].data = datasetValues;
      }
    }
    chart.update();
  }

  function updateLineChart(chart, labels, income, expense) {
    chart.data.labels = labels;
    chart.data.datasets[0].data = income;
    chart.data.datasets[1].data = expense;
    chart.update();
  }

  function setRecentTransactionsTable(rows) {
    const tbody = $('recent-transactions-body');
    if (!tbody) return;
    tbody.innerHTML = '';
    rows.forEach(function (r) {
      const tr = document.createElement('tr');
      const amt = (r.is_income ? r.amount : r.amount);
      tr.innerHTML =
        '<td>' + escapeHtml(r.timestamp || '') + '</td>' +
        '<td>' + escapeHtml(r.description || '') + '</td>' +
        '<td style=\"color:' + (r.is_income ? COLORS.income : COLORS.expense) + '; font-weight:600;\">₹ ' + Number(amt || 0).toFixed(2) + (r.is_income ? ' (Income)' : '') + '</td>' +
        '<td>' + escapeHtml(r.category || '—') + '</td>' +
        '<td>' + escapeHtml(r.merchant || '—') + '</td>';
      tbody.appendChild(tr);
    });
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = String(text ?? '');
    return div.innerHTML;
  }

  async function fetchJSON(url) {
    const res = await fetch(url, { headers: { 'Accept': 'application/json' } });
    const data = await res.json();
    if (!data || data.ok !== true) {
      throw new Error((data && data.error) ? data.error : 'Request failed');
    }
    return data;
  }

  function initFinancialInsights(userId) {
    const els = {
      monthly: $('chart-monthly-spending'),
      pie: $('chart-expense-pie'),
      trend: $('chart-income-expense'),
      weekly: $('chart-weekly-spending')
    };

    if (!els.monthly || !els.pie || !els.trend || !els.weekly) return;

    const charts = { monthly: null, pie: null, trend: null, weekly: null };

    async function loadAndRender() {
      const data = await fetchJSON('/api/financial_insights/' + encodeURIComponent(userId));
      const c = data.charts;
      if (!charts.monthly) {
        charts.monthly = createMonthlyBar(els.monthly.getContext('2d'), c.monthly_spending);
        charts.pie = createCategoryPie(els.pie.getContext('2d'), c.expense_distribution);
        charts.trend = createIncomeVsExpense(els.trend.getContext('2d'), c.income_vs_expense);
        charts.weekly = createWeeklyBar(els.weekly.getContext('2d'), c.weekly_spending);
      } else {
        updateChart(charts.monthly, c.monthly_spending.labels, c.monthly_spending.data);
        charts.pie.data.labels = c.expense_distribution.labels;
        charts.pie.data.datasets[0].data = c.expense_distribution.data;
        charts.pie.update();
        updateLineChart(charts.trend, c.income_vs_expense.labels, c.income_vs_expense.income, c.income_vs_expense.expense);
        updateChart(charts.weekly, c.weekly_spending.labels, c.weekly_spending.data);
      }
    }

    async function refreshSnapshot() {
      const snap = await fetchJSON('/api/dashboard_snapshot/' + encodeURIComponent(userId));
      const c = snap.charts;
      updateChart(charts.monthly, c.monthly_spending.labels, c.monthly_spending.data);
      charts.pie.data.labels = c.expense_distribution.labels;
      charts.pie.data.datasets[0].data = c.expense_distribution.data;
      charts.pie.update();
      updateLineChart(charts.trend, c.income_vs_expense.labels, c.income_vs_expense.income, c.income_vs_expense.expense);
      updateChart(charts.weekly, c.weekly_spending.labels, c.weekly_spending.data);
      setRecentTransactionsTable(snap.recent_transactions || []);
      const countEl = $('transaction-count');
      if (countEl) countEl.textContent = String(snap.transaction_count ?? '');
    }

    // Quick Add Transaction modal (AJAX)
    const quickAddBtn = $('btn-quick-add');
    if (quickAddBtn && window.MiniApp && MiniApp.showModal) {
      quickAddBtn.addEventListener('click', function () {
        const body = `
          <form id=\"quick-add-form\" class=\"grid-2\" style=\"margin-top: 12px;\">
            <div class=\"form-group\">
              <label for=\"qa-kind\">Type</label>
              <select id=\"qa-kind\" name=\"kind\">
                <option value=\"expense\" selected>Expense</option>
                <option value=\"income\">Income</option>
              </select>
            </div>
            <div class=\"form-group\">
              <label for=\"qa-amount\">Amount (Rs)</label>
              <input id=\"qa-amount\" name=\"amount\" type=\"number\" min=\"0\" step=\"0.01\" required placeholder=\"1000.00\" />
            </div>
            <div class=\"form-group\" style=\"grid-column: 1 / -1;\">
              <label for=\"qa-description\">Description</label>
              <input id=\"qa-description\" name=\"description\" type=\"text\" required placeholder=\"e.g. Salary, Grocery, Uber\" />
            </div>
            <div class=\"form-group\">
              <label for=\"qa-category\">Category</label>
              <select id=\"qa-category\" name=\"category\">
                <option value=\"\">— Select —</option>
                <option value=\"food\">Food</option>
                <option value=\"transport\">Transport</option>
                <option value=\"shopping\">Shopping</option>
                <option value=\"bills\">Bills</option>
                <option value=\"other\">Other</option>
              </select>
            </div>
            <div class=\"form-group\">
              <label for=\"qa-merchant\">Merchant</label>
              <input id=\"qa-merchant\" name=\"merchant\" type=\"text\" placeholder=\"e.g. Zomato, Amazon\" />
            </div>
          </form>`;

        MiniApp.showModal({
          title: 'Quick Add Transaction',
          body: body,
          confirmText: 'Add',
          cancelText: 'Cancel',
          onConfirm: async function () {
            const form = $('quick-add-form');
            if (!form) return;
            const fd = new FormData(form);
            try {
              const res = await fetch('/api/transactions/' + encodeURIComponent(userId), {
                method: 'POST',
                body: fd
              });
              const json = await res.json();
              if (!json || json.ok !== true) throw new Error((json && json.error) || 'Failed to add transaction');
              if (window.MiniApp && MiniApp.showToast) MiniApp.showToast('Transaction added and charts updated.', 'success');
              await refreshSnapshot();
            } catch (e) {
              if (window.MiniApp && MiniApp.showToast) MiniApp.showToast(String(e.message || e), 'error');
            }
          }
        });
      });
    }

    loadAndRender().catch(function (e) {
      if (window.MiniApp && MiniApp.showToast) MiniApp.showToast(String(e.message || e), 'error');
    });

    return { refresh: refreshSnapshot };
  }

  window.IntelliBankFinancialInsights = { init: initFinancialInsights };
})(); 

