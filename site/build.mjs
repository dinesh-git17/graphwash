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
