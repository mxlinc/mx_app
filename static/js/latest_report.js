(function () {
  'use strict';
  const endpoint = document.currentScript.dataset.onlineUsersUrl;
  const users = document.getElementById('online-users');
  const errorMessage = document.getElementById('presence-error');
  let pending = false;
  let stopped = false;

  async function refreshOnlineUsers() {
    if (pending || stopped) return;
    pending = true;
    try {
      const response = await fetch(endpoint, { credentials: 'same-origin', cache: 'no-store' });
      if (response.redirected || response.status === 401 || response.status === 403) {
        stopped = true;
        throw new Error('Your login is no longer active. Please sign in again.');
      }
      if (!response.ok) throw new Error('Unable to load currently logged in users. Retrying automatically.');
      const data = await response.json();
      if (!Array.isArray(data.users) || !data.users.every(user => typeof user === 'string')) {
        throw new Error('Invalid online user response. Please reload the page.');
      }
      users.textContent = data.users.length ? data.users.join(', ') : 'None';
      errorMessage.textContent = '';
    } catch (error) {
      console.error('Latest report presence:', error);
      users.textContent = '';
      errorMessage.textContent = error.message;
    } finally {
      pending = false;
    }
  }

  window.setInterval(refreshOnlineUsers, 60000);
  document.addEventListener('visibilitychange', function () {
    if (!document.hidden) refreshOnlineUsers();
  });
}());
