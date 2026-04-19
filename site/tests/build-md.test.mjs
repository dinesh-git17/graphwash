import { test } from 'node:test';
import assert from 'node:assert/strict';
import { validateMarkdown } from '../build.mjs';

const manifest = {
  docs: [
    { slug: 'prd', source: 'docs/graphwash-prd.md', category: 'prd', order: 1 },
    { slug: 'dev-guide', source: 'docs/dev-guide.md', category: 'guide', order: 1 },
  ],
};

function opts(overrides = {}) {
  return {
    manifest,
    docsRoot: '/repo/docs',
    pathExists: (abs) => [
      '/repo/docs/graphwash-prd.md',
      '/repo/docs/dev-guide.md',
    ].includes(abs),
    ...overrides,
  };
}

test('accepts a link to a shipped doc', () => {
  const md = '[dev guide](./dev-guide.md)';
  assert.doesNotThrow(() => validateMarkdown('docs/graphwash-prd.md', md, opts()));
});

test('accepts external https link', () => {
  const md = '[link](https://example.com)';
  assert.doesNotThrow(() => validateMarkdown('docs/graphwash-prd.md', md, opts()));
});

test('accepts external http link', () => {
  const md = '[link](http://example.com)';
  assert.doesNotThrow(() => validateMarkdown('docs/graphwash-prd.md', md, opts()));
});

test('accepts mailto link', () => {
  const md = '[email](mailto:x@y.z)';
  assert.doesNotThrow(() => validateMarkdown('docs/graphwash-prd.md', md, opts()));
});

test('accepts same-page fragment', () => {
  const md = '[top](#top)';
  assert.doesNotThrow(() => validateMarkdown('docs/graphwash-prd.md', md, opts()));
});

test('rejects site-relative Markdown link', () => {
  const md = '[prd](/docs/prd/)';
  assert.throws(() => validateMarkdown('docs/graphwash-prd.md', md, opts()), /site-relative/i);
});

test('rejects link to missing file', () => {
  const md = '[gone](./missing.md)';
  assert.throws(() => validateMarkdown('docs/graphwash-prd.md', md, opts()), /does not exist/i);
});

test('rejects link to unlisted .md', () => {
  const md = '[unlisted](./graphwash-setup-report.md)';
  const o = opts({
    pathExists: (p) => p === '/repo/docs/graphwash-setup-report.md'
      || p === '/repo/docs/graphwash-prd.md'
      || p === '/repo/docs/dev-guide.md',
  });
  assert.throws(() => validateMarkdown('docs/graphwash-prd.md', md, o), /manifest/i);
});

test('rejects link into docs/superpowers/', () => {
  const md = '[secret](./superpowers/plans/x.md)';
  const o = opts({ pathExists: () => true });
  assert.throws(() => validateMarkdown('docs/graphwash-prd.md', md, o), /superpowers/i);
});

test('accepts relative .md link with anchor', () => {
  const md = '[guide section](./dev-guide.md#setup)';
  assert.doesNotThrow(() => validateMarkdown('docs/graphwash-prd.md', md, opts()));
});

test('rejects raw <script> in Markdown', () => {
  const md = 'Hi\n\n<script>alert(1)</script>';
  assert.throws(() => validateMarkdown('docs/graphwash-prd.md', md, opts()), /script/i);
});

test('rejects raw <iframe>', () => {
  const md = '<iframe src="https://x"></iframe>';
  assert.throws(() => validateMarkdown('docs/graphwash-prd.md', md, opts()), /iframe/i);
});

test('rejects raw <object>', () => {
  const md = '<object data="x"></object>';
  assert.throws(() => validateMarkdown('docs/graphwash-prd.md', md, opts()), /object/i);
});

test('rejects raw <style>', () => {
  const md = '<style>.evil{color:red}</style>';
  assert.throws(() => validateMarkdown('docs/graphwash-prd.md', md, opts()), /style/i);
});

test('rejects raw href with javascript: scheme', () => {
  const md = '<a href="javascript:alert(1)">x</a>';
  assert.throws(() => validateMarkdown('docs/graphwash-prd.md', md, opts()), /scheme|javascript|href/i);
});

test('rejects raw href site-relative', () => {
  const md = '<a href="/docs/prd/">x</a>';
  assert.throws(() => validateMarkdown('docs/graphwash-prd.md', md, opts()), /href/i);
});

test('rejects raw href relative .md', () => {
  const md = '<a href="./dev-guide.md">x</a>';
  assert.throws(() => validateMarkdown('docs/graphwash-prd.md', md, opts()), /href/i);
});

test('rejects on* handler attribute', () => {
  const md = '<a href="https://x" onclick="evil()">x</a>';
  assert.throws(() => validateMarkdown('docs/graphwash-prd.md', md, opts()), /handler|onclick/i);
});

test('accepts <kbd> semantic tag', () => {
  const md = 'Press <kbd>Ctrl+C</kbd> to copy.';
  assert.doesNotThrow(() => validateMarkdown('docs/graphwash-prd.md', md, opts()));
});

test('accepts <details> and <summary>', () => {
  const md = '<details><summary>x</summary>y</details>';
  assert.doesNotThrow(() => validateMarkdown('docs/graphwash-prd.md', md, opts()));
});
