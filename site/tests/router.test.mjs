import { test } from 'node:test';
import assert from 'node:assert/strict';
import { classifyRoute } from '../scripts/route.js';

const opts = { basePath: '/graphwash/' };

test('root → landing', () => {
  assert.deepEqual(classifyRoute('/graphwash/', opts), { view: 'landing' });
});

test('root with index.html → landing', () => {
  assert.deepEqual(classifyRoute('/graphwash/index.html', opts), { view: 'landing' });
});

test('/docs/<slug>/ → reader', () => {
  assert.deepEqual(classifyRoute('/graphwash/docs/prd/', opts), { view: 'reader', slug: 'prd' });
});

test('/docs/<nested/slug>/ → reader with nested slug', () => {
  assert.deepEqual(
    classifyRoute('/graphwash/docs/adr/0001-hgt-over-gat/', opts),
    { view: 'reader', slug: 'adr/0001-hgt-over-gat' }
  );
});

test('/categories/<id>/ → category', () => {
  assert.deepEqual(classifyRoute('/graphwash/categories/adr/', opts), { view: 'category', categoryId: 'adr' });
});

test('trailing slash absent still works', () => {
  assert.deepEqual(classifyRoute('/graphwash/docs/prd', opts), { view: 'reader', slug: 'prd' });
});

test('duplicate slashes collapsed', () => {
  assert.deepEqual(classifyRoute('/graphwash//docs//prd//', opts), { view: 'reader', slug: 'prd' });
});

test('URL-encoded slug decoded', () => {
  assert.deepEqual(classifyRoute('/graphwash/docs/adr%2F0001/', opts), { view: 'reader', slug: 'adr/0001' });
});

test('dot segment → notfound', () => {
  assert.deepEqual(classifyRoute('/graphwash/docs/../admin/', opts), { view: 'notfound' });
});

test('missing basePath prefix → notfound', () => {
  assert.deepEqual(classifyRoute('/other/', opts), { view: 'notfound' });
});

test('/categories/ with no id → notfound', () => {
  assert.deepEqual(classifyRoute('/graphwash/categories/', opts), { view: 'notfound' });
});

test('/categories/<id>/<extra> → notfound', () => {
  assert.deepEqual(classifyRoute('/graphwash/categories/adr/extra/', opts), { view: 'notfound' });
});

test('unknown top-level segment → notfound', () => {
  assert.deepEqual(classifyRoute('/graphwash/something/', opts), { view: 'notfound' });
});

test('basePath="/" with root → landing', () => {
  assert.deepEqual(classifyRoute('/', { basePath: '/' }), { view: 'landing' });
});

test('basePath="/" with /docs/prd/ → reader', () => {
  assert.deepEqual(classifyRoute('/docs/prd/', { basePath: '/' }), { view: 'reader', slug: 'prd' });
});
