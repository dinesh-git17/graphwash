import { test } from 'node:test';
import assert from 'node:assert/strict';
import { validateMetrics } from '../build.mjs';

const baseMetrics = () => ({
  ticker: { items: [{ label: 'l', value: 'v', framing: 'target' }] },
  highlights: {
    baseline: { label: 'b', value: '0' },
    target:   { label: 't', value: '1' },
    deadline: { label: 'd', value: '2' },
  },
  modelCard: {
    architecture: 'HGT',
    params: null,
    dataset: 'it-aml',
    trainingStatus: 'x',
    runId: null,
  },
});

test('accepts minimal valid metrics', () => {
  assert.doesNotThrow(() => validateMetrics(baseMetrics()));
});

test('rejects ticker item missing framing', () => {
  const m = baseMetrics(); delete m.ticker.items[0].framing;
  assert.throws(() => validateMetrics(m), /framing/);
});

test('rejects ticker item with invalid framing', () => {
  const m = baseMetrics(); m.ticker.items[0].framing = 'live';
  assert.throws(() => validateMetrics(m), /framing/);
});

test('rejects delta on non-measured framing', () => {
  const m = baseMetrics(); m.ticker.items[0].delta = '+0.01';
  assert.throws(() => validateMetrics(m), /delta/);
});

test('accepts delta on measured framing', () => {
  const m = baseMetrics();
  m.ticker.items[0].framing = 'measured';
  m.ticker.items[0].delta = '+0.01';
  assert.doesNotThrow(() => validateMetrics(m));
});

test('rejects missing highlights', () => {
  const m = baseMetrics(); delete m.highlights.target;
  assert.throws(() => validateMetrics(m), /highlights/);
});

test('rejects missing modelCard fields', () => {
  const m = baseMetrics(); delete m.modelCard.architecture;
  assert.throws(() => validateMetrics(m), /modelCard/);
});

test('rejects null metrics', () => {
  assert.throws(() => validateMetrics(null), /non-null object/);
});

test('rejects non-object metrics', () => {
  assert.throws(() => validateMetrics('not-metrics'), /non-null object/);
});

test('rejects missing ticker.items', () => {
  const m = baseMetrics(); delete m.ticker.items;
  assert.throws(() => validateMetrics(m), /ticker/);
});

test('accepts empty ticker items array', () => {
  const m = baseMetrics(); m.ticker.items = [];
  assert.doesNotThrow(() => validateMetrics(m));
});

test('rejects modelCard missing params key', () => {
  const m = baseMetrics(); delete m.modelCard.params;
  assert.throws(() => validateMetrics(m), /params/);
});

test('rejects modelCard missing runId key', () => {
  const m = baseMetrics(); delete m.modelCard.runId;
  assert.throws(() => validateMetrics(m), /runId/);
});
