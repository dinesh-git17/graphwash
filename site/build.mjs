const BASE_PATH_RE = /^\/(?:[a-z0-9][a-z0-9-]*(?:\/[a-z0-9][a-z0-9-]*)*\/)?$/;
const SLUG_SEGMENT_RE = /^[a-z0-9][a-z0-9-]*$/;
const RESERVED_SLUGS = new Set([
  'index', '404', 'robots', 'sitemap',
  '_build', '_content', 'assets', 'styles', 'scripts',
  'docs', 'categories',
]);
const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

function isValidSlug(slug) {
  if (typeof slug !== 'string' || slug.length === 0) return false;
  const segments = slug.split('/');
  for (const seg of segments) {
    if (!SLUG_SEGMENT_RE.test(seg)) return false;
    if (seg === '.' || seg === '..') return false;
  }
  const firstSegment = segments[0];
  if (RESERVED_SLUGS.has(firstSegment)) return false;
  return true;
}

function isNonNegativeInteger(value) {
  return Number.isInteger(value) && value >= 0;
}

export function validateManifest(manifest, opts) {
  if (manifest == null || typeof manifest !== 'object') {
    throw new Error('manifest must be a non-null object');
  }
  const { sourceExists } = opts;

  if (!manifest.site || !BASE_PATH_RE.test(manifest.site.basePath ?? '')) {
    throw new Error(`manifest.site.basePath fails regex ${BASE_PATH_RE}`);
  }

  const categoryIds = new Set();
  for (const c of manifest.categories ?? []) {
    if (!c.id || !c.label || !c.index || !c.description) {
      throw new Error(`manifest.categories entry missing required field: ${JSON.stringify(c)}`);
    }
    categoryIds.add(c.id);
  }

  const slugsSeenLower = new Map();
  for (const d of manifest.docs ?? []) {
    for (const k of ['slug', 'title', 'description', 'category', 'updated', 'order']) {
      if (d[k] === undefined || d[k] === null) {
        throw new Error(`manifest.docs entry missing required field "${k}": ${JSON.stringify(d)}`);
      }
    }
    const lower = typeof d.slug === 'string' ? d.slug.toLowerCase() : String(d.slug);
    if (slugsSeenLower.has(lower)) {
      throw new Error(`slug collision (case-insensitive) between "${d.slug}" and "${slugsSeenLower.get(lower)}"`);
    }
    if (!isValidSlug(d.slug)) {
      const firstSeg = String(d.slug).split('/')[0];
      if (RESERVED_SLUGS.has(firstSeg)) {
        throw new Error(`slug "${d.slug}" uses reserved name "${firstSeg}"`);
      }
      throw new Error(`slug "${d.slug}" fails validation`);
    }
    slugsSeenLower.set(lower, d.slug);
    if (!categoryIds.has(d.category)) {
      throw new Error(`doc "${d.slug}" references unknown category "${d.category}"`);
    }
    if (!ISO_DATE_RE.test(d.updated)) {
      throw new Error(`doc "${d.slug}" has malformed updated date "${d.updated}"`);
    }
    if (!isNonNegativeInteger(d.order)) {
      throw new Error(`doc "${d.slug}" has non-integer or negative order: ${d.order}`);
    }
    const isPlaceholder = d.status === 'placeholder';
    if (!isPlaceholder) {
      if (typeof d.source !== 'string' || d.source.length === 0) {
        throw new Error(`doc "${d.slug}" missing required source`);
      }
      if (d.source.includes('..') || !d.source.startsWith('docs/')) {
        throw new Error(`doc "${d.slug}" source "${d.source}" resolves outside docs/`);
      }
      if (d.source.startsWith('docs/superpowers/')) {
        throw new Error(`doc "${d.slug}" source "${d.source}" is inside docs/superpowers/ (stealth)`);
      }
      if (!sourceExists(d.source)) {
        throw new Error(`doc "${d.slug}" source file not found: ${d.source}`);
      }
    }
  }

  return { ok: true };
}

const FRAMINGS = new Set(['target', 'baseline', 'measured']);

export function validateMetrics(metrics) {
  if (metrics == null || typeof metrics !== 'object') {
    throw new Error('metrics must be a non-null object');
  }

  const { ticker, highlights, modelCard } = metrics;

  if (!ticker || !Array.isArray(ticker.items)) {
    throw new Error('metrics.ticker.items must be an array');
  }
  for (const it of ticker.items) {
    if (!it || !it.label || !it.value || !FRAMINGS.has(it.framing)) {
      throw new Error(`metrics.ticker.items entry invalid or missing framing: ${JSON.stringify(it)}`);
    }
    if (it.delta !== undefined && it.framing !== 'measured') {
      throw new Error(`metrics.ticker.items entry has delta but framing !== "measured": ${JSON.stringify(it)}`);
    }
  }

  for (const key of ['baseline', 'target', 'deadline']) {
    const h = highlights?.[key];
    if (!h || !h.label || !h.value) {
      throw new Error(`metrics.highlights.${key} missing label/value`);
    }
  }

  if (!modelCard || typeof modelCard !== 'object') {
    throw new Error('metrics.modelCard must be an object');
  }
  for (const key of ['architecture', 'dataset', 'trainingStatus']) {
    if (!modelCard[key]) {
      throw new Error(`metrics.modelCard.${key} missing`);
    }
  }
  if (!('params' in modelCard)) {
    throw new Error('metrics.modelCard.params key missing (null allowed)');
  }
  if (!('runId' in modelCard)) {
    throw new Error('metrics.modelCard.runId key missing (null allowed)');
  }

  return { ok: true };
}
