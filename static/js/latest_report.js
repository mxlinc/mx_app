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

  const detailsButton = document.getElementById('report-details-button');
  if (!detailsButton) return;
  const details = document.getElementById('report-details');
  const detailsError = document.getElementById('details-error');
  let detailsPending = false;
  let detailsLoaded = false;
  let detailsStopped = false;

  detailsButton.addEventListener('click', async function () {
    if (detailsPending || detailsLoaded || detailsStopped) return;
    detailsPending = true;
    detailsButton.disabled = true;
    detailsButton.textContent = 'Loading...';
    details.setAttribute('aria-busy', 'true');
    detailsError.textContent = '';
    try {
      const response = await fetch(detailsButton.dataset.detailsUrl, {
        credentials: 'same-origin', cache: 'no-store'
      });
      if (response.redirected || response.status === 401 || response.status === 403) {
        detailsStopped = true;
        throw new Error('Your login is no longer active. Please sign in again.');
      }
      const data = await response.json();
      if (!response.ok) {
        throw new Error(typeof data.error === 'string' ? data.error : 'Unable to load report details. Please try again.');
      }
      if (!Array.isArray(data.records) || !data.records.every(record =>
        record && ['user', 'quiz', 'score', 'updated'].every(key => typeof record[key] === 'string')
      )) {
        throw new Error('Invalid report details response. Please try again.');
      }
      const table = document.createElement('table');
      const head = document.createElement('thead');
      const heading = document.createElement('tr');
      for (const label of ['User', 'Quiz item code-title', 'Score', 'Last updated']) {
        const cell = document.createElement('th');
        cell.setAttribute('scope', 'col');
        cell.textContent = label;
        heading.appendChild(cell);
      }
      head.appendChild(heading);
      table.appendChild(head);
      const body = document.createElement('tbody');
      for (const record of data.records) {
        const row = document.createElement('tr');
        for (const key of ['user', 'quiz', 'score', 'updated']) {
          const cell = document.createElement('td');
          cell.textContent = record[key];
          row.appendChild(cell);
        }
        body.appendChild(row);
      }
      if (!data.records.length) {
        const row = document.createElement('tr');
        const cell = document.createElement('td');
        cell.colSpan = 4;
        cell.textContent = 'No completed quizzes in the selected period.';
        row.appendChild(cell);
        body.appendChild(row);
      }
      table.appendChild(body);
      details.replaceChildren(table);
      details.hidden = false;
      detailsButton.setAttribute('aria-expanded', 'true');
      detailsLoaded = true;
    } catch (error) {
      console.error('Latest report details:', error);
      detailsError.textContent = error.message;
    } finally {
      detailsPending = false;
      details.setAttribute('aria-busy', 'false');
      detailsButton.disabled = detailsStopped;
      detailsButton.textContent = 'Details';
    }
  });
}());
