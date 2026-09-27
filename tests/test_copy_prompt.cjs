// Run from the repository root: node --test tests/test_copy_prompt.cjs
// Dependency-free tests of the actual inline script, using a small DOM/clipboard stub.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(process.env.DIANE_INDEX || path.join(__dirname, '..', 'index.html'), 'utf8');
const script = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n');
const item = (name, priority = 'A1') => ({name, priority, url: 'https://example.test/' + encodeURIComponent(name), deadline: '2027-10-01', verified: '2026-09-27', discipline: ['Sculpture'], type: 'exposition'});
const payload = records => 'window.DIANE_OPPORTUNITIES = ' + JSON.stringify(records) + ';';
const settle = () => new Promise(resolve => setImmediate(resolve));

class Element {
  constructor(tag = 'div') { this.tag = tag; this.children = []; this.handlers = {}; this.dataset = {}; this.textContent = ''; this.innerHTML = ''; this.disabled = false; }
  addEventListener(name, handler) { this.handlers[name] = handler; }
  appendChild(child) { child.parent = this; this.children.push(child); return child; }
  remove() { this.parent.children = this.parent.children.filter(c => c !== this); }
  querySelector(selector) { return this.children.find(c => selector.startsWith('.') ? c.className === selector.slice(1) : c.tag === selector) || null; }
  querySelectorAll() { return []; }
  focus() { this.focused = true; }
  select() { this.selected = true; }
  setSelectionRange(start, end) { this.range = [start, end]; }
}
function runtime(initial, clipboardMode = 'success') {
  const elements = Object.fromEntries(['list', 'count', 'updated', 'tagbar', 'clear'].map(id => [id, new Element()]));
  elements.list.querySelectorAll = function(selector) {
    if (selector !== '.copy-btn') return [];
    this.buttons = [...this.innerHTML.matchAll(/class="copy-btn" data-copy-id="(\d+)"/g)].map(m => {
      const card = new Element(); const status = new Element('p'); status.className = 'copy-status'; card.appendChild(status);
      const b = new Element('button'); b.dataset.copyId = m[1]; b.textContent = 'copy prompt'; b.closest = () => card; b.card = card; return b;
    });
    return this.buttons;
  };
  elements.tagbar.querySelectorAll = function(selector) {
    if (selector !== 'button') return [];
    this.buttons = [...this.innerHTML.matchAll(/data-tag="([^"]+)"/g)].map(m => {const b = new Element('button'); b.dataset.tag = m[1]; return b;});
    return this.buttons;
  };
  const copies = [], requests = [], events = {}, timers = [];
  let current = initial, pendingResolve;
  const navigator = clipboardMode === 'missing' ? {} : {clipboard: {writeText(text) {
    copies.push(text);
    if (clipboardMode === 'denied') return Promise.reject(new Error('NotAllowedError'));
    if (clipboardMode === 'throws') throw new Error('Clipboard failure');
    if (clipboardMode === 'pending') return new Promise(resolve => {pendingResolve = resolve;});
    return Promise.resolve();
  }}};
  const document = {visibilityState: 'visible', baseURI: 'https://example.test/dashboard/', querySelector: s => elements[s.slice(1)], createElement: tag => new Element(tag), addEventListener() {}};
  const context = {document, navigator, isSecureContext: clipboardMode !== 'insecure', DIANE_OPPORTUNITIES: structuredClone(initial), URL, Intl, Date, AbortController,
    fetch: async (url, options) => {requests.push({url: String(url), options}); return {ok: true, text: async () => payload(current)};},
    setTimeout: (fn, ms) => {timers.push({fn, ms}); return timers.length;}, clearTimeout() {}, setInterval() {},
    addEventListener: (name, fn) => {events[name] = fn;}
  };
  context.window = context; vm.runInNewContext(script, context);
  return {elements, context, copies, requests, timers,
    buttons: () => elements.list.buttons,
    refresh(records) {current = records; events.pageshow();},
    resolveCopy() {pendingResolve();}
  };
}
function copiedRecord(text) { return JSON.parse(text.slice(text.indexOf('\n\n{') + 2)); }

test('every entry, including closed and ineligible leads, receives its own copy button', async () => {
  const entries = [item('closed', 'C'), {...item('ineligible', 'B'), status: 'étudiants inéligibles'}, item('open')];
  const r = runtime(entries); await settle();
  assert.equal(r.buttons().length, entries.length);
  for (let i = 0; i < entries.length; i++) await r.buttons()[i].handlers.click();
  assert.deepEqual(r.copies.map(copiedRecord).map(o => o.name), ['open', 'ineligible', 'closed']);
  assert.equal(JSON.stringify(r.context.DIANE_OPPORTUNITIES), JSON.stringify(entries));
});

test('prompt includes complete raw record, profile, sources, caveats and ready-to-apply instructions', async () => {
  const entry = {...item('Prix « Terre & feu »'), sources: ['https://example.test/rules'], maxWorks: '3 œuvres', fee: 'À confirmer', rights: 'Donation obligatoire', verificationScope: 'Éligibilité non confirmée', tags: Array.from({length: 30}, (_, i) => 'tag-' + i), customField: {nested: 'unabridged'}};
  const r = runtime([entry]); await settle(); await r.buttons()[0].handlers.click();
  const text = r.copies[0];
  assert.deepEqual(copiedRecord(text), entry);
  for (const term of ['Diane Niederman', 'Accademia di Belle Arti di Firenze', 'règlement', 'textes prêts à coller', '[À COMPLÉTER]', 'sans ma validation explicite', 'clos']) assert.ok(text.includes(term), term);
  assert.match(r.buttons()[0].card.querySelector('.copy-status').textContent, /Prompt copié/);
  assert.equal(r.buttons()[0].textContent, 'Copié !');
  assert.equal(r.buttons()[0].disabled, false);
  assert.equal(r.requests.length, 1, 'copy makes no network request');
  r.timers.find(t => t.ms === 2500).fn();
  assert.equal(r.buttons()[0].textContent, 'copy prompt');
});

test('filtered and newly refreshed cards copy the correct current record', async () => {
  const a = {...item('A', 'C'), type: 'résidence'}, b = item('B');
  const r = runtime([a, b]); await settle();
  r.elements.tagbar.buttons.find(b => b.dataset.tag === 'résidence').handlers.click();
  assert.equal(r.buttons().length, 1);
  await r.buttons()[0].handlers.click(); assert.equal(copiedRecord(r.copies.at(-1)).name, 'A');
  const changed = {...a, fee: 'Updated cost'};
  r.refresh([changed, b, {...item('C'), type: 'résidence'}]); await settle();
  assert.equal(r.buttons().length, 2);
  await r.buttons()[1].handlers.click(); assert.deepEqual(copiedRecord(r.copies.at(-1)), changed);
  assert.match(r.elements.count.textContent, /1 tag actif/);
});

for (const mode of ['denied', 'missing', 'insecure', 'throws']) {
  test('manual copy is selectable and truthful when clipboard is ' + mode, async () => {
    const entry = item('Manual'); const r = runtime([entry], mode); await settle();
    const b = r.buttons()[0]; await b.handlers.click();
    const box = b.card.querySelector('.manual-copy'), field = box.querySelector('textarea');
    assert.deepEqual(copiedRecord(field.value), entry);
    assert.equal(field.readOnly, true); assert.equal(field.selected, true);
    assert.deepEqual(field.range, [0, field.value.length]);
    assert.equal(box.querySelector('label').htmlFor, field.id);
    assert.match(b.card.querySelector('.copy-status').textContent, /indisponible/);
    assert.equal(b.textContent, 'copy prompt'); assert.equal(b.disabled, false);
    box.querySelector('button').handlers.click(); assert.equal(field.focused, true);
    await b.handlers.click(); assert.equal(b.card.children.filter(c => c.className === 'manual-copy').length, 1);
    if (mode === 'insecure' || mode === 'missing') assert.equal(r.copies.length, 0);
  });
}

test('success is not announced until the clipboard promise resolves', async () => {
  const r = runtime([item('Pending')], 'pending'); await settle();
  const b = r.buttons()[0], done = b.handlers.click();
  assert.equal(r.copies.length, 1, 'write is called synchronously in the click');
  assert.equal(b.disabled, true); assert.notEqual(b.textContent, 'Copié !');
  r.resolveCopy(); await done;
  assert.equal(b.textContent, 'Copié !'); assert.equal(b.disabled, false);
});

test('entry names are escaped in button attributes but copied without HTML encoding', async () => {
  const entry = item('A " <img src=x onerror=alert(1)> & B');
  const r = runtime([entry]); await settle();
  assert.ok(r.elements.list.innerHTML.includes('aria-label="copy prompt — A &quot; &lt;img'));
  assert.ok(!r.elements.list.innerHTML.includes('<img src=x'));
  await r.buttons()[0].handlers.click(); assert.deepEqual(copiedRecord(r.copies[0]), entry);
});
