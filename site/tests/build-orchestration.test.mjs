import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as fs from 'node:fs';
import * as path from 'node:path';
import * as os from 'node:os';
import { main } from '../build.mjs';

function makeFixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'gw-build-'));
  fs.mkdirSync(path.join(root, 'docs/adr'), { recursive: true });
  fs.mkdirSync(path.join(root, 'site/assets'), { recursive: true });
  fs.mkdirSync(path.join(root, 'site/styles'), { recursive: true });
  fs.mkdirSync(path.join(root, 'site/scripts'), { recursive: true });
  fs.writeFileSync(path.join(root, 'docs/a.md'), '# A\n\n[b](./adr/0001.md)\n');
  fs.writeFileSync(path.join(root, 'docs/adr/0001.md'), '# ADR 1\n');
  fs.writeFileSync(path.join(root, 'site/index.html'),
    '<!doctype html><html><head><title>x</title></head><body></body></html>');
  fs.writeFileSync(path.join(root, 'site/manifest.json'), JSON.stringify({
    site: { name: 'n', tagline: 't', version: 'v', repo: 'r', basePath: '/graphwash/', liveDemoUrl: null },
    categories: [{ id: 'c', label: 'C', index: '01', description: 'x' }],
    docs: [
      { slug: 'a', source: 'docs/a.md', title: 'A', description: 'x', category: 'c', updated: '2026-04-19', order: 1 },
      { slug: 'adr/0001', source: 'docs/adr/0001.md', title: 'ADR', description: 'x', category: 'c', updated: '2026-04-19', order: 2 },
    ],
  }));
  fs.writeFileSync(path.join(root, 'site/metrics.json'), JSON.stringify({
    ticker: { items: [] },
    highlights: { baseline: { label: 'b', value: '0' }, target: { label: 't', value: '1' }, deadline: { label: 'd', value: '2' } },
    modelCard: { architecture: 'HGT', params: null, dataset: 'x', trainingStatus: 'y', runId: null },
  }));
  // Add a styles file and scripts file so copy paths are non-empty in the test.
  fs.writeFileSync(path.join(root, 'site/styles/tokens.css'), ':root{}');
  fs.writeFileSync(path.join(root, 'site/scripts/router.js'), 'export{}');
  return root;
}

test('main() produces _dist with content, base href, 404 copy, and receipt', (t) => {
  const root = makeFixture();
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  main({ repoRoot: root });
  const dist = path.join(root, 'site/_dist');

  assert.ok(fs.existsSync(path.join(dist, 'index.html')), 'dist has index.html');
  assert.ok(fs.existsSync(path.join(dist, '404.html')), 'dist has 404.html');
  assert.equal(
    fs.readFileSync(path.join(dist, 'index.html'), 'utf8'),
    fs.readFileSync(path.join(dist, '404.html'), 'utf8'),
    '404.html must be a byte-copy of index.html',
  );

  const html = fs.readFileSync(path.join(dist, 'index.html'), 'utf8');
  assert.match(html, /<base href="\/graphwash\/">/, 'base href injected');

  assert.ok(fs.existsSync(path.join(dist, '_content/a.md')), 'flat slug mirrored');
  assert.ok(fs.existsSync(path.join(dist, '_content/adr/0001.md')), 'nested slug mirrored');

  // Static assets mirrored
  assert.ok(fs.existsSync(path.join(dist, 'styles/tokens.css')), 'styles copied');
  assert.ok(fs.existsSync(path.join(dist, 'scripts/router.js')), 'scripts copied');
  assert.ok(fs.existsSync(path.join(dist, 'manifest.json')), 'manifest copied');
  assert.ok(fs.existsSync(path.join(dist, 'metrics.json')), 'metrics copied');

  // Build receipt
  const receipt = JSON.parse(fs.readFileSync(path.join(dist, '_build.json'), 'utf8'));
  assert.equal(receipt.shippedCount, 2, 'receipt counts 2 shipped docs');
  assert.equal(receipt.placeholderCount, 0, 'receipt counts 0 placeholders');
  assert.ok(receipt.manifestHash && receipt.manifestHash.length === 64, 'manifestHash is sha256 hex');
  assert.ok(receipt.metricsHash && receipt.metricsHash.length === 64, 'metricsHash is sha256 hex');
  assert.ok(receipt.builtAt, 'builtAt timestamp set');
});

test('main() refuses to ship a doc that links into docs/superpowers/', (t) => {
  const root = makeFixture();
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  fs.mkdirSync(path.join(root, 'docs/superpowers'), { recursive: true });
  fs.writeFileSync(path.join(root, 'docs/superpowers/y.md'), '# y\n');
  fs.writeFileSync(path.join(root, 'docs/a.md'), '[x](./superpowers/y.md)\n');
  assert.throws(() => main({ repoRoot: root }), /superpowers/);
});

test('main() does NOT copy build.mjs into _dist/', (t) => {
  const root = makeFixture();
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  // Place a build.mjs in the site root (simulating the real repo shape)
  fs.writeFileSync(path.join(root, 'site/build.mjs'), '// not shipped');
  main({ repoRoot: root });
  const dist = path.join(root, 'site/_dist');
  assert.ok(!fs.existsSync(path.join(dist, 'build.mjs')), 'build.mjs must not land in _dist root');
  assert.ok(!fs.existsSync(path.join(dist, 'scripts/build.mjs')), 'build.mjs must not land in _dist/scripts');
});

test('main() fresh-rebuilds _dist each call', (t) => {
  const root = makeFixture();
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  main({ repoRoot: root });
  const dist = path.join(root, 'site/_dist');
  // Plant a stale file in _dist
  fs.writeFileSync(path.join(dist, 'stale.txt'), 'nope');
  main({ repoRoot: root });
  assert.ok(!fs.existsSync(path.join(dist, 'stale.txt')), 'stale file removed on rebuild');
});
