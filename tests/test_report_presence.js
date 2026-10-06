const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function harness(filename, replies) {
  const calls = [];
  const intervals = [];
  const events = {};
  const appended = [];
  const elements = {
    'online-users': { textContent: 'Original student' },
    'presence-error': { textContent: '' }
  };
  const context = {
    console: { error() {} },
    document: {
      currentScript: { dataset: { presenceUrl: '/presence', onlineUsersUrl: '/online' } },
      hidden: false,
      body: { appendChild(element) { appended.push(element); } },
      createElement() {
        return {
          style: {}, setAttribute() {},
          remove() { this.removed = true; }
        };
      },
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
