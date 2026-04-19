import { test } from 'node:test';
import assert from 'node:assert/strict';
import { marked } from '../vendor/marked.esm.js';
import { makeRenderer, makeUniqueId } from '../scripts/render.js';
import { decodeHashTarget } from '../scripts/reader.js';
import { resolveRoute } from '../scripts/router.js';

test('makeUniqueId appends numeric suffixes for duplicate heading ids', () => {
  const usedIds = new Set();
  assert.equal(makeUniqueId('purpose', usedIds), 'purpose');
  assert.equal(makeUniqueId('purpose', usedIds), 'purpose-2');
  assert.equal(makeUniqueId('purpose', usedIds), 'purpose-3');
});

test('decodeHashTarget decodes numeric heading hashes without using CSS selectors', () => {
  assert.equal(decodeHashTarget('#1-executive-summary'), '1-executive-summary');
  assert.equal(decodeHashTarget('#adr%2F0001'), 'adr/0001');
});

test('resolveRoute downgrades unknown category routes to notfound', () => {
  const route = resolveRoute(
    { view: 'category', categoryId: 'missing' },
    { categories: [{ id: 'adr' }] },
  );
  assert.deepEqual(route, { view: 'notfound' });
});

test('makeRenderer preserves task-list semantics without emitting checkbox inputs', (t) => {
  global.window = { marked };
  t.after(() => {
    delete global.window;
  });

  const renderer = makeRenderer({
    sourceRel: 'docs/graphwash-task-list.md',
    manifest: { docs: [] },
    url: (tail) => `/${tail}`,
  });

  const html = marked.parse('- [ ] todo\n- [x] done', { renderer, gfm: true });
  assert.match(html, /<ul class="task-list">/);
  assert.match(html, /<li>todo<\/li>/);
  assert.match(html, /<li class="done">done<\/li>/);
  assert.doesNotMatch(html, /<input\b/);
});
