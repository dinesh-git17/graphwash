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

test('makeRenderer rewrites internal markdown links to doc slugs without throwing', (t) => {
  global.window = { marked };
  t.after(() => {
    delete global.window;
  });

  const renderer = makeRenderer({
    sourceRel: 'docs/graphwash-prd.md',
    manifest: {
      docs: [
        { slug: 'task-list', source: 'docs/graphwash-task-list.md' },
      ],
    },
    url: (tail) => `/graphwash/${tail}`,
  });

  const html = marked.parse('See [the plan](graphwash-task-list.md) for detail.', {
    renderer,
    gfm: true,
  });
  assert.match(html, /<a href="\/graphwash\/docs\/task-list\/">the plan<\/a>/);
});

test('makeRenderer preserves external, hash, and mailto links verbatim', (t) => {
  global.window = { marked };
  t.after(() => {
    delete global.window;
  });

  const renderer = makeRenderer({
    sourceRel: 'docs/graphwash-prd.md',
    manifest: { docs: [] },
    url: (tail) => `/graphwash/${tail}`,
  });

  for (const [md, expected] of [
    ['[docs](https://example.com)',        'href="https://example.com"'],
    ['[top](#overview)',                   'href="#overview"'],
    ['[mail](mailto:x@y.z)',               'href="mailto:x@y.z"'],
  ]) {
    const html = marked.parse(md, { renderer, gfm: true });
    assert.ok(html.includes(expected), `${md} → ${html}`);
  }
});

test('mermaid blocks survive DOMPurify sanitize via textContent, not an attribute', (t) => {
  global.window = { marked };
  t.after(() => {
    delete global.window;
  });

  const renderer = makeRenderer({
    sourceRel: 'docs/graphwash-task-list.md',
    manifest: { docs: [] },
    url: (tail) => `/${tail}`,
  });

  const src = 'flowchart LR\n    A["Node <br/> break"]:::x --> B';
  const html = marked.parse('```mermaid\n' + src + '\n```', { renderer, gfm: true });
  assert.ok(html.includes('<pre class="mermaid-pending">'), html);
  assert.ok(!html.includes('data-mermaid'), 'attribute form would be stripped by DOMPurify');
  assert.ok(html.includes('&lt;br/&gt;'), 'HTML entities inside the pre survive escaping');
});

test('makeRenderer emits language-tagged pre/code blocks and preserves mermaid', (t) => {
  global.window = { marked };
  t.after(() => {
    delete global.window;
  });

  const renderer = makeRenderer({
    sourceRel: 'docs/graphwash-prd.md',
    manifest: { docs: [] },
    url: (tail) => `/graphwash/${tail}`,
  });

  const tsHtml = marked.parse('```ts\nconst x = 1;\n```', { renderer, gfm: true });
  assert.match(tsHtml, /<pre><code class="language-ts">const x = 1;<\/code><\/pre>/);

  const mmHtml = marked.parse('```mermaid\nflowchart TD\n  A --> B\n```', { renderer, gfm: true });
  assert.match(mmHtml, /<pre class="mermaid-pending">flowchart TD\n {2}A --&gt; B<\/pre>/);
  assert.doesNotMatch(mmHtml, /data-mermaid=/);
});
