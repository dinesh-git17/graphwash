import { test } from 'node:test';
import assert from 'node:assert/strict';
import { makeUrl } from '../scripts/manifest.js';

test('url("docs/prd/") with basePath "/" yields "/docs/prd/"', () => {
  const url = makeUrl('/');
  assert.equal(url('docs/prd/'), '/docs/prd/');
});

test('url("docs/prd/") with basePath "/graphwash/" yields "/graphwash/docs/prd/"', () => {
  const url = makeUrl('/graphwash/');
  assert.equal(url('docs/prd/'), '/graphwash/docs/prd/');
});

test('url("") with basePath "/graphwash/" yields "/graphwash/"', () => {
  const url = makeUrl('/graphwash/');
  assert.equal(url(''), '/graphwash/');
});

test('leading slash on tail is stripped before concat (basePath "/graphwash/")', () => {
  const url = makeUrl('/graphwash/');
  assert.equal(url('/docs/prd/'), '/graphwash/docs/prd/');
});

test('leading slash on tail is stripped before concat (basePath "/")', () => {
  const url = makeUrl('/');
  assert.equal(url('/docs/prd/'), '/docs/prd/');
});

test('url preserves nested slug with slashes', () => {
  const url = makeUrl('/graphwash/');
  assert.equal(url('docs/adr/0001-hgt-over-gat/'), '/graphwash/docs/adr/0001-hgt-over-gat/');
});

test('url preserves anchor hash', () => {
  const url = makeUrl('/graphwash/');
  assert.equal(url('docs/prd/#open-questions'), '/graphwash/docs/prd/#open-questions');
});
