// Run from the repository root: node --test tests/test_live_refresh.cjs
// No dependencies or network: exercise the real inline dashboard script.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(process.env.DIANE_INDEX || path.join(__dirname, '..', 'index.html'), 'utf8');
const script = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n');
const item = name => ({name, url: 'https://example.test/' + encodeURIComponent(name), priority: 'A1', deadline: '2027-10-01', verified: '2026-09-27', discipline: ['Sculpture'], tags: ['exposition'], type: 'exposition'});
const payload = records => 'window.DIANE_OPPORTUNITIES = ' + JSON.stringify(records) + ';\n';
const settle = () => new Promise(resolve => setImmediate(resolve));
function runtime(initial = [item('old')]) {
  const elements = Object.fromEntries(['list', 'count', 'updated', 'tagbar', 'clear'].map(id => [id, {
    textContent: '', innerHTML: '', disabled: true, handlers: {},
    addEventListener(name, fn) { this.handlers[name] = fn; },
    querySelectorAll(selector) {
      if (id !== 'tagbar' || selector !== 'button') return [];
      this.buttons = [...this.innerHTML.matchAll(/data-tag="([^"]+)"/g)].map(m => ({dataset: {tag: m[1]}, handlers: {}, addEventListener(name, fn) { this.handlers[name] = fn; }}));
      return this.buttons;
    }
  }]));
  const docEvents = {}, winEvents = {}, intervals = [], timers = new Map(), requests = [];
  const document = {visibilityState: 'visible', baseURI: 'https://example.test/dashboard/', querySelector: s => elements[s.slice(1)], addEventListener: (e, fn) => { docEvents[e] = fn; }};
  let handler = async () => ({ok: true, status: 200, text: async () => payload(initial)});
  const context = {document, DIANE_OPPORTUNITIES: structuredClone(initial), URL, Intl, Date, AbortController,
    fetch: (url, options) => { requests.push({url: String(url), options}); return handler(url, options); },
    setTimeout: fn => { const id = timers.size + 1; timers.set(id, fn); return id; },
    clearTimeout: id => timers.delete(id), setInterval: (fn, ms) => { intervals.push({fn, ms}); },
    addEventListener: (e, fn) => { winEvents[e] = fn; }
  };
  context.window = context;
  vm.runInNewContext(script, context);
  return {context, elements, document, requests, timers, intervals,
    respond(body, status = 200) { handler = async () => ({ok: status === 200, status, text: async () => body}); },
    handler(fn) { handler = fn; },
    restore() { winEvents.pageshow({persisted: true}); },
    visible() { document.visibilityState = 'visible'; docEvents.visibilitychange(); }
  };
}

test('startup keeps the snapshot and requests uncached data', async () => {
  const r = runtime(); await settle();
  assert.equal(r.elements.count.textContent, '1 opportunité');
  assert.equal(r.requests[0].options.cache, 'no-store');
  assert.match(r.requests[0].url, /^https:\/\/example\.test\/dashboard\/data\.js\?refresh=/);
  assert.match(r.elements.updated.textContent, /Synchronisation/);
  assert.equal(r.intervals[0].ms, 60000);
});

test('restoring and periodic refresh add data without clearing filters', async () => {
  const r = runtime(); await settle();
  r.elements.tagbar.buttons.find(b => b.dataset.tag === 'exposition').handlers.click();
  r.respond(payload([item('old'), item('new')])); r.restore(); await settle();
  assert.equal(r.context.DIANE_OPPORTUNITIES.length, 2);
  assert.equal(r.elements.count.textContent, '2 opportunités · 1 tag actif');
  assert.match(r.elements.tagbar.innerHTML, /data-tag="exposition" class="on"/);
  assert.ok((r.elements.tagbar.innerHTML.match(/<button/g) || []).length <= 10);
  r.respond(payload([item('old'), item('new'), item('newest')])); r.intervals[0].fn(); await settle();
  assert.equal(r.context.DIANE_OPPORTUNITIES.length, 3);
});

test('invalid, empty, duplicate and HTTP-error responses never erase data or execute code', async () => {
  const r = runtime(); await settle();
  for (const [body, status] of [
    ['<html>Unavailable</html>', 200], [payload([]), 200],
    [payload([item('old'), item('old')]), 200], [payload([null]), 200],
    [payload([item('other')]) + 'window.injected = true;', 200],
    [payload([item('other')]), 503]
  ]) {
    r.respond(body, status); r.restore(); await settle();
    assert.equal(r.context.DIANE_OPPORTUNITIES[0].name, 'old');
    assert.equal(r.elements.count.textContent, '1 opportunité');
    assert.match(r.elements.updated.textContent, /Actualisation indisponible/);
    assert.equal(r.context.injected, undefined);
  }
});

test('hidden tabs do not poll, visible tabs recover, overlapping events coalesce', async () => {
  const r = runtime(); await settle(); const count = r.requests.length;
  r.document.visibilityState = 'hidden'; r.intervals[0].fn(); await settle();
  assert.equal(r.requests.length, count);
  let release;
  r.handler(() => new Promise(resolve => { release = resolve; }));
  r.visible(); r.restore(); r.intervals[0].fn();
  assert.equal(r.requests.length, count + 1);
  release({ok: true, text: async () => payload([item('old'), item('new')])}); await settle();
  assert.equal(r.context.DIANE_OPPORTUNITIES.length, 2);
  assert.notEqual(r.requests[0].url, r.requests[1].url);
});

test('a timed-out request releases single-flight and permits recovery', async () => {
  const r = runtime(); await settle();
  r.handler((url, options) => new Promise((resolve, reject) => options.signal.addEventListener('abort', () => reject(new Error('aborted')))));
  r.restore(); [...r.timers.values()][0](); await settle();
  assert.equal(r.context.DIANE_OPPORTUNITIES.length, 1);
  assert.match(r.elements.updated.textContent, /Actualisation indisponible/);
  r.respond(payload([item('recovered')])); r.restore(); await settle();
  assert.equal(r.context.DIANE_OPPORTUNITIES[0].name, 'recovered');
});

test('a missing initial snapshot can recover without a reload', async () => {
  const r = runtime([]); await settle();
  r.respond(payload([item('recovered')])); r.restore(); await settle();
  assert.equal(r.elements.count.textContent, '1 opportunité');
  assert.equal(r.context.DIANE_OPPORTUNITIES[0].name, 'recovered');
});
