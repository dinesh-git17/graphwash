import { test } from 'node:test';
import assert from 'node:assert/strict';
import { validateManifest } from '../build.mjs';

const baseManifest = () => ({
  site: {
    name: 'graphwash',
    tagline: 'test',
    version: 'v1.0',
    repo: 'https://example.com',
    basePath: '/',
    liveDemoUrl: null,
  },
  categories: [
    { id: 'prd', label: 'PRD', index: '01', description: 'x' },
  ],
  docs: [
    { slug: 'prd', source: 'docs/graphwash-prd.md', title: 'PRD', description: 'x', category: 'prd', updated: '2026-04-19', order: 1 },
  ],
});

test('accepts a minimal valid manifest', () => {
  assert.doesNotThrow(() => validateManifest(baseManifest(), { docsRoot: 'docs', sourceExists: () => true }));
});

test('rejects basePath missing leading slash', () => {
  const m = baseManifest(); m.site.basePath = 'graphwash/';
  assert.throws(() => validateManifest(m, { docsRoot: 'docs', sourceExists: () => true }), /basePath/);
});

test('rejects basePath with duplicate trailing slash', () => {
  const m = baseManifest(); m.site.basePath = '/graphwash//';
  assert.throws(() => validateManifest(m, { docsRoot: 'docs', sourceExists: () => true }), /basePath/);
});

test('rejects basePath with duplicate leading slash', () => {
  const m = baseManifest(); m.site.basePath = '//graphwash/';
  assert.throws(() => validateManifest(m, { docsRoot: 'docs', sourceExists: () => true }), /basePath/);
});

test('rejects basePath with uppercase', () => {
  const m = baseManifest(); m.site.basePath = '/GraphWash/';
  assert.throws(() => validateManifest(m, { docsRoot: 'docs', sourceExists: () => true }), /basePath/);
});

test('rejects basePath without trailing slash', () => {
  const m = baseManifest(); m.site.basePath = '/graphwash';
  assert.throws(() => validateManifest(m, { docsRoot: 'docs', sourceExists: () => true }), /basePath/);
});

test('rejects slug with uppercase', () => {
  const m = baseManifest(); m.docs[0].slug = 'PRD';
  assert.throws(() => validateManifest(m, { docsRoot: 'docs', sourceExists: () => true }), /slug/);
});

test('rejects slug with leading slash', () => {
  const m = baseManifest(); m.docs[0].slug = '/prd';
  assert.throws(() => validateManifest(m, { docsRoot: 'docs', sourceExists: () => true }), /slug/);
});

test('rejects slug with dot segment', () => {
  const m = baseManifest(); m.docs[0].slug = '../admin';
  assert.throws(() => validateManifest(m, { docsRoot: 'docs', sourceExists: () => true }), /slug/);
});

test('rejects reserved slug', () => {
  const m = baseManifest(); m.docs[0].slug = 'index';
  assert.throws(() => validateManifest(m, { docsRoot: 'docs', sourceExists: () => true }), /reserved/i);
});

test('rejects case-insensitive slug collision', () => {
  const m = baseManifest();
  m.docs.push({ slug: 'PRD', source: 'docs/a.md', title: 'A', description: 'x', category: 'prd', updated: '2026-04-19', order: 2 });
  assert.throws(() => validateManifest(m, { docsRoot: 'docs', sourceExists: () => true }), /collision/i);
});

test('rejects unknown category reference', () => {
  const m = baseManifest(); m.docs[0].category = 'nope';
  assert.throws(() => validateManifest(m, { docsRoot: 'docs', sourceExists: () => true }), /category/);
});

test('rejects non-integer order', () => {
  const m = baseManifest(); m.docs[0].order = 'high';
  assert.throws(() => validateManifest(m, { docsRoot: 'docs', sourceExists: () => true }), /order/);
});

test('rejects negative order', () => {
  const m = baseManifest(); m.docs[0].order = -1;
  assert.throws(() => validateManifest(m, { docsRoot: 'docs', sourceExists: () => true }), /order/);
});

test('rejects fractional order', () => {
  const m = baseManifest(); m.docs[0].order = 1.5;
  assert.throws(() => validateManifest(m, { docsRoot: 'docs', sourceExists: () => true }), /order/);
});

test('rejects malformed updated date', () => {
  const m = baseManifest(); m.docs[0].updated = '2026-4-19';
  assert.throws(() => validateManifest(m, { docsRoot: 'docs', sourceExists: () => true }), /updated/);
});

test('rejects source outside docs/', () => {
  const m = baseManifest(); m.docs[0].source = '../CLAUDE.md';
  assert.throws(() => validateManifest(m, { docsRoot: 'docs', sourceExists: () => true }), /source/);
});

test('rejects source inside docs/superpowers/', () => {
  const m = baseManifest(); m.docs[0].source = 'docs/superpowers/a.md';
  assert.throws(() => validateManifest(m, { docsRoot: 'docs', sourceExists: () => true }), /superpowers/);
});

test('rejects missing source file when status not placeholder', () => {
  const m = baseManifest();
  assert.throws(() => validateManifest(m, { docsRoot: 'docs', sourceExists: () => false }), /source/);
});

test('accepts placeholder with source: null', () => {
  const m = baseManifest();
  m.docs.push({ slug: 'api', source: null, title: 'API', description: 'x', category: 'prd', updated: '2026-04-19', order: 2, status: 'placeholder' });
  assert.doesNotThrow(() => validateManifest(m, { docsRoot: 'docs', sourceExists: () => true }));
});
