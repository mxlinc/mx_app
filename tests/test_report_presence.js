const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function harness(filename, replies, withDetails = true) {
  const calls = [];
  const intervals = [];
  const events = {};
  const appended = [];
  function element(tagName) {
    return {
      tagName, style: {}, textContent: '', hidden: false, disabled: false,
      children: [], attributes: {}, events: {},
      setAttribute(name, value) { this.attributes[name] = value; },
      appendChild(child) { this.children.push(child); },
      replaceChildren(...children) { this.children = children; },
      addEventListener(name, callback) { this.events[name] = callback; },
      remove() { this.removed = true; }
    };
  }
  const elements = {
    'online-users': { textContent: 'Original student' },
    'presence-error': { textContent: '' }
  };
  if (withDetails) {
    elements['report-details-button'] = element('button');
    elements['report-details-button'].dataset = {
      detailsUrl: '/details?days=7&end=2026-03-25T03%3A44%3A00.000000'
    };
    elements['report-details'] = element('div');
    elements['report-details'].hidden = true;
    elements['details-error'] = element('p');
  }
  const context = {
    console: { error() {} },
    document: {
      currentScript: { dataset: { presenceUrl: '/presence', onlineUsersUrl: '/online' } },
      hidden: false,
      body: { appendChild(element) { appended.push(element); } },
      createElement: element,
      getElementById(id) { return elements[id]; },
      addEventListener(name, callback) { events[name] = callback; }
    },
    window: {
      setInterval(callback, duration) { intervals.push({ callback, duration }); },
      addEventListener(name, callback) { events[name] = callback; }
    },
    async fetch(url, options) {
      calls.push({ url, options });
      const reply = replies.shift();
      if (reply instanceof Error) throw reply;
      if (typeof reply === 'function') return reply();
      return reply;
    }
  };
  vm.runInNewContext(
    fs.readFileSync(path.join(__dirname, '..', 'static', 'js', filename), 'utf8'),
    context
  );
  return { calls, intervals, events, appended, elements, context };
}

const success = users => ({
  ok: true, status: 200, redirected: false, async json() { return { users }; }
});
const tick = () => new Promise(resolve => setImmediate(resolve));

test('student heartbeat sends immediately and every minute with same-origin protection', async () => {
  const h = harness('student_presence.js', [
    { ok: true, status: 204 }, { ok: true, status: 204 }
  ]);
  await tick();
  assert.equal(h.calls.length, 1);
  assert.equal(h.calls[0].url, '/presence');
  assert.equal(h.calls[0].options.method, 'POST');
  assert.equal(h.calls[0].options.credentials, 'same-origin');
  assert.equal(h.calls[0].options.headers['X-MX-Presence'], '1');
  assert.equal(h.intervals[0].duration, 60000);
  await h.intervals[0].callback();
  assert.equal(h.calls.length, 2);
});

test('heartbeat failure is visible, retries, and clears its warning on success', async () => {
  const h = harness('student_presence.js', [
    new Error('Network unavailable'), { ok: true, status: 204 }
  ]);
  await tick();
  assert.equal(h.appended[0].textContent, 'Network unavailable');
  await h.intervals[0].callback();
  assert.equal(h.appended[0].removed, true);
});

test('expired heartbeat stops instead of re-registering a signed-out student', async () => {
  const h = harness('student_presence.js', [{ ok: false, status: 401 }]);
  await tick();
  assert.match(h.appended[0].textContent, /sign in again/);
  await h.intervals[0].callback();
  assert.equal(h.calls.length, 1);
});

test('heartbeat resumes immediately when a hidden tab becomes visible', async () => {
  const h = harness('student_presence.js', [
    { ok: true, status: 204 }, { ok: true, status: 204 }
  ]);
  await tick();
  h.context.document.hidden = true;
  h.events.visibilitychange();
  assert.equal(h.calls.length, 1);
  h.context.document.hidden = false;
  h.events.visibilitychange();
  await tick();
  assert.equal(h.calls.length, 2);
});

test('online row refresh uses text only and comma separates students', async () => {
  const h = harness('latest_report.js', [success(['Alice (alice)', '<script>Bob</script>'])]);
  assert.equal(h.intervals[0].duration, 60000);
  await h.intervals[0].callback();
  assert.equal(h.elements['online-users'].textContent, 'Alice (alice), <script>Bob</script>');
  assert.equal(h.elements['presence-error'].textContent, '');
});

test('an empty successful online response displays None', async () => {
  const h = harness('latest_report.js', [success([])]);
  await h.intervals[0].callback();
  assert.equal(h.elements['online-users'].textContent, 'None');
});

test('online fetch failure clears stale users, displays an error, and recovers', async () => {
  const h = harness('latest_report.js', [
    { ok: false, status: 503 }, success(['Alice (alice)'])
  ]);
  await h.intervals[0].callback();
  assert.equal(h.elements['online-users'].textContent, '');
  assert.match(h.elements['presence-error'].textContent, /Unable to load/);
  await h.intervals[0].callback();
  assert.equal(h.elements['online-users'].textContent, 'Alice (alice)');
  assert.equal(h.elements['presence-error'].textContent, '');
});

test('online login redirect is visible and stops background retries', async () => {
  const h = harness('latest_report.js', [{ ok: true, status: 200, redirected: true }]);
  await h.intervals[0].callback();
  assert.match(h.elements['presence-error'].textContent, /sign in again/);
  await h.intervals[0].callback();
  assert.equal(h.calls.length, 1);
});

test('invalid online response is reported, not treated as an empty list', async () => {
  const h = harness('latest_report.js', [success([42])]);
  await h.intervals[0].callback();
  assert.match(h.elements['presence-error'].textContent, /Invalid online user response/);
  assert.equal(h.elements['online-users'].textContent, '');
});

const detailsSuccess = records => ({
  ok: true, status: 200, redirected: false, async json() { return { records }; }
});
const record = {
  user: 'Rebecca', quiz: 'Q-0001-Adding fractions', score: '8 of 10', updated: '24 Mar 23:44'
};
const clickDetails = h => h.elements['report-details-button'].events.click();

test('details are fetched only on click using the applied period and rendered as text', async () => {
  const h = harness('latest_report.js', [detailsSuccess([
    { ...record, quiz: 'Q-0001-<script>unsafe title</script>' }
  ])]);
  await tick();
  assert.equal(h.calls.length, 0);
  assert.equal(h.elements['report-details'].hidden, true);
  await clickDetails(h);
  assert.equal(h.calls.length, 1);
  assert.equal(h.calls[0].url, h.elements['report-details-button'].dataset.detailsUrl);
  assert.equal(h.calls[0].options.credentials, 'same-origin');
  assert.equal(h.calls[0].options.cache, 'no-store');
  const table = h.elements['report-details'].children[0];
  assert.equal(table.tagName, 'table');
  assert.deepEqual(Array.from(table.children[0].children[0].children, cell => cell.textContent),
    ['User', 'Quiz item code-title', 'Score', 'Last updated']);
  assert.equal(table.children[1].children[0].children[1].textContent,
    'Q-0001-<script>unsafe title</script>');
  assert.equal(h.elements['report-details'].hidden, false);
  assert.equal(h.elements['report-details-button'].attributes['aria-expanded'], 'true');
  assert.equal(h.elements['report-details'].attributes['aria-busy'], 'false');
  await clickDetails(h);
  assert.equal(h.calls.length, 1);
});

test('details loading prevents duplicate requests and clears its loading state', async () => {
  let resolve;
  const h = harness('latest_report.js', [() => new Promise(done => { resolve = done; })]);
  const loading = clickDetails(h);
  assert.equal(h.elements['report-details-button'].disabled, true);
  assert.equal(h.elements['report-details-button'].textContent, 'Loading...');
  await clickDetails(h);
  assert.equal(h.calls.length, 1);
  resolve(detailsSuccess([record]));
  await loading;
  assert.equal(h.elements['report-details-button'].disabled, false);
  assert.equal(h.elements['report-details-button'].textContent, 'Details');
});

test('details failure is visible and can be retried successfully', async () => {
  const h = harness('latest_report.js', [
    { ok: false, status: 503, async json() { return { error: 'Database unavailable. Please retry.' }; } },
    detailsSuccess([record])
  ]);
  await clickDetails(h);
  assert.equal(h.elements['details-error'].textContent, 'Database unavailable. Please retry.');
  assert.equal(h.elements['report-details'].hidden, true);
  assert.equal(h.elements['report-details-button'].disabled, false);
  await clickDetails(h);
  assert.equal(h.elements['details-error'].textContent, '');
  assert.equal(h.elements['report-details'].hidden, false);
});

test('details rejects malformed responses without revealing a success table', async () => {
  for (const records of [null, [null], [42], [{ ...record, quiz: 42 }]]) {
    const h = harness('latest_report.js', [detailsSuccess(records)]);
    await clickDetails(h);
    assert.match(h.elements['details-error'].textContent, /Invalid report details response/);
    assert.equal(h.elements['report-details'].hidden, true);
    assert.equal(h.elements['report-details-button'].disabled, false);
  }
});

test('details login expiry is visible and stops further requests', async () => {
  for (const reply of [
    { ok: true, status: 200, redirected: true },
    { ok: false, status: 401 }, { ok: false, status: 403 }
  ]) {
    const h = harness('latest_report.js', [reply]);
    await clickDetails(h);
    assert.match(h.elements['details-error'].textContent, /sign in again/);
    assert.equal(h.elements['report-details-button'].disabled, true);
    await clickDetails(h);
    assert.equal(h.calls.length, 1);
  }
});

test('empty details render an explicit empty state', async () => {
  const h = harness('latest_report.js', [detailsSuccess([])]);
  await clickDetails(h);
  const cell = h.elements['report-details'].children[0].children[1].children[0].children[0];
  assert.equal(cell.colSpan, 4);
  assert.equal(cell.textContent, 'No completed quizzes in the selected period.');
});

test('details network failure is shown without affecting presence refresh', async () => {
  const h = harness('latest_report.js', [new Error('Network unavailable'), success(['Alice (alice)'])]);
  await clickDetails(h);
  assert.equal(h.elements['details-error'].textContent, 'Network unavailable');
  assert.equal(h.elements['report-details'].hidden, true);
  await h.intervals[0].callback();
  assert.equal(h.elements['online-users'].textContent, 'Alice (alice)');
});

test('report error pages without a Details button still refresh presence', async () => {
  const h = harness('latest_report.js', [success(['Alice (alice)'])], false);
  await h.intervals[0].callback();
  assert.equal(h.elements['online-users'].textContent, 'Alice (alice)');
});
