(function () {
  'use strict';
  const endpoint = document.currentScript.dataset.presenceUrl;
  let stopped = false;
  let pending = false;
  let warning;

  function showError(message) {
    if (!warning) {
      warning = document.createElement('div');
      warning.setAttribute('role', 'status');
      warning.style.cssText = 'position:fixed;bottom:0;left:0;right:0;z-index:2000;padding:8px;background:#fff3cd;color:#664d03;font:14px system-ui;text-align:center;';
      document.body.appendChild(warning);
    }
    warning.textContent = message;
  }

  async function heartbeat() {
    if (stopped || pending) return;
    pending = true;
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'X-MX-Presence': '1' },
        cache: 'no-store'
      });
      if (response.status === 401 || response.status === 403) {
        stopped = true;
        throw new Error('Your login is no longer active. Please sign in again.');
      }
      if (!response.ok) throw new Error('Unable to update your online status. Retrying automatically.');
      if (warning) warning.remove();
      warning = null;
    } catch (error) {
      console.error('Student presence:', error);
      showError(error.message);
    } finally {
      pending = false;
    }
  }

  heartbeat();
  window.setInterval(heartbeat, 60000);
  window.addEventListener('pageshow', heartbeat);
  document.addEventListener('visibilitychange', function () {
    if (!document.hidden) heartbeat();
  });
}());
