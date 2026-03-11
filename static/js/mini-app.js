/**
 * Mini-App: Popups, Modals & Toast Notifications
 * Use from any page that extends base.html
 */

(function () {
  'use strict';

  window.MiniApp = window.MiniApp || {};

  // ----- Toast Notifications -----
  const TOAST_CONTAINER_ID = 'mini-app-toast-container';
  const TOAST_DURATION = 4000;

  function ensureToastContainer() {
    let el = document.getElementById(TOAST_CONTAINER_ID);
    if (!el) {
      el = document.createElement('div');
      el.id = TOAST_CONTAINER_ID;
      el.className = 'mini-app-toast-container';
      document.body.appendChild(el);
    }
    return el;
  }

  /**
   * Show a toast notification.
   * @param {string} message - Message text
   * @param {string} type - 'success' | 'error' | 'info' | 'warning'
   */
  function showToast(message, type) {
    type = type || 'info';
    const container = ensureToastContainer();
    const toast = document.createElement('div');
    toast.className = 'mini-app-toast mini-app-toast--' + type;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = '<span class="mini-app-toast__message">' + escapeHtml(message) + '</span><button class="mini-app-toast__close" aria-label="Close">&times;</button>';
    container.appendChild(toast);

    const close = function () {
      toast.classList.add('mini-app-toast--hide');
      setTimeout(function () {
        if (toast.parentNode) toast.parentNode.removeChild(toast);
      }, 300);
    };

    toast.querySelector('.mini-app-toast__close').addEventListener('click', close);
    const t = setTimeout(close, TOAST_DURATION);

    toast.addEventListener('mouseenter', function () { clearTimeout(t); });
    toast.addEventListener('mouseleave', function () { setTimeout(close, 1500); });
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  MiniApp.showToast = showToast;

  // ----- Modal / Popup -----
  const MODAL_OVERLAY_ID = 'mini-app-modal-overlay';
  const MODAL_BOX_ID = 'mini-app-modal-box';

  function ensureModalDOM() {
    let overlay = document.getElementById(MODAL_OVERLAY_ID);
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.id = MODAL_OVERLAY_ID;
      overlay.className = 'mini-app-modal-overlay';
      overlay.innerHTML = '<div id="' + MODAL_BOX_ID + '" class="mini-app-modal-box" role="dialog" aria-modal="true"><div class="mini-app-modal__content"></div><div class="mini-app-modal__actions"></div></div>';
      document.body.appendChild(overlay);
      overlay.addEventListener('click', function (e) {
        if (e.target === overlay) MiniApp.closeModal();
      });
      document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') MiniApp.closeModal();
      });
    }
    return overlay;
  }

  /**
   * Show a modal popup.
   * @param {object} opts - { title, body (HTML string), confirmText, cancelText, onConfirm, onCancel }
   */
  function showModal(opts) {
    opts = opts || {};
    const overlay = ensureModalDOM();
    const box = document.getElementById(MODAL_BOX_ID);
    const content = box.querySelector('.mini-app-modal__content');
    const actions = box.querySelector('.mini-app-modal__actions');

    content.innerHTML = '';
    if (opts.title) {
      const h = document.createElement('h3');
      h.className = 'mini-app-modal__title';
      h.textContent = opts.title;
      content.appendChild(h);
    }
    if (opts.body) {
      const b = document.createElement('div');
      b.className = 'mini-app-modal__body';
      b.innerHTML = opts.body;
      content.appendChild(b);
    }

    actions.innerHTML = '';
    if (opts.cancelText !== undefined && opts.cancelText !== null) {
      const cancelBtn = document.createElement('button');
      cancelBtn.type = 'button';
      cancelBtn.className = 'btn btn-secondary mini-app-modal__btn';
      cancelBtn.textContent = opts.cancelText || 'Cancel';
      cancelBtn.addEventListener('click', function () {
        MiniApp.closeModal();
        if (typeof opts.onCancel === 'function') opts.onCancel();
      });
      actions.appendChild(cancelBtn);
    }
    if (opts.confirmText) {
      const confirmBtn = document.createElement('button');
      confirmBtn.type = 'button';
      confirmBtn.className = 'btn mini-app-modal__btn';
      confirmBtn.textContent = opts.confirmText;
      confirmBtn.addEventListener('click', function () {
        MiniApp.closeModal();
        if (typeof opts.onConfirm === 'function') opts.onConfirm();
      });
      actions.appendChild(confirmBtn);
    }

    overlay.classList.add('mini-app-modal--open');
    box.focus();
  }

  function closeModal() {
    const overlay = document.getElementById(MODAL_OVERLAY_ID);
    if (overlay) overlay.classList.remove('mini-app-modal--open');
  }

  MiniApp.showModal = showModal;
  MiniApp.closeModal = closeModal;

  /**
   * Confirm dialog. onConfirm receives true, onCancel receives false.
   */
  function confirmPopup(opts) {
    opts = opts || {};
    showModal({
      title: opts.title || 'Confirm',
      body: opts.message || 'Are you sure?',
      confirmText: opts.confirmText || 'Yes',
      cancelText: opts.cancelText !== undefined ? opts.cancelText : 'No',
      onConfirm: function () { if (opts.onConfirm) opts.onConfirm(true); },
      onCancel: function () { if (opts.onCancel) opts.onCancel(false); }
    });
  }

  MiniApp.confirmPopup = confirmPopup;

  /**
   * Show notifications in a popup (e.g. from dashboard).
   */
  function showNotificationsPopup(notifications) {
    if (!notifications || !notifications.length) {
      showModal({ title: 'Notifications', body: '<p>No new notifications.</p>' });
      return;
    }
    let html = '<ul class="mini-app-notif-list">';
    notifications.forEach(function (n) {
      // Supports both legacy notification objects and new smart notifications:
      // New: { type: info|warning|critical, message, timestamp }
      // Old: { priority: high|medium|low, title, message, action_suggestion }
      const type = (n.type || '').toLowerCase();
      let priority = (n.priority || '').toLowerCase();
      if (!priority) {
        if (type === 'critical') priority = 'high';
        else if (type === 'warning') priority = 'medium';
        else priority = 'low';
      }
      html += '<li class="mini-app-notif-item mini-app-notif-item--' + priority + '">';
      const title = n.title || (type ? type.toUpperCase() : 'Notification');
      html += '<strong>' + escapeHtml(title) + '</strong>';
      html += '<p>' + escapeHtml(n.message || '') + '</p>';
      if (n.action_suggestion) html += '<small>' + escapeHtml(n.action_suggestion) + '</small>';
      if (n.timestamp) html += '<small>' + escapeHtml(n.timestamp) + '</small>';
      html += '</li>';
    });
    html += '</ul>';
    showModal({ title: 'Notifications & Alerts', body: html });
  }

  MiniApp.showNotificationsPopup = showNotificationsPopup;

  // Optional: read flash toasts from data attribute (set by server)
  document.addEventListener('DOMContentLoaded', function () {
    const flash = document.getElementById('mini-app-flash');
    if (flash) {
      const msg = flash.getAttribute('data-message');
      const typ = flash.getAttribute('data-type') || 'info';
      if (msg) showToast(msg, typ);
    }
  });
})();
