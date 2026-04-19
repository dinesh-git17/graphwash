import { marked } from './vendor/marked.esm.js';
import * as path from 'node:path';

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
    if (!it || it.label == null || it.value == null || !FRAMINGS.has(it.framing)) {
      throw new Error(`metrics.ticker.items entry invalid or missing framing: ${JSON.stringify(it)}`);
    }
    if (it.delta !== undefined && it.framing !== 'measured') {
      throw new Error(`metrics.ticker.items entry has delta but framing !== "measured": ${JSON.stringify(it)}`);
    }
  }

  for (const key of ['baseline', 'target', 'deadline']) {
    const h = highlights?.[key];
    if (!h || h.label == null || h.value == null) {
      throw new Error(`metrics.highlights.${key} missing label/value`);
    }
  }

  if (!modelCard || typeof modelCard !== 'object') {
    throw new Error('metrics.modelCard must be an object');
  }
  for (const key of ['architecture', 'dataset', 'trainingStatus']) {
    if (modelCard[key] == null) {
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

const FORBIDDEN_TAGS_RE = /<(script|iframe|object|embed|style)\b/i;
const ON_HANDLER_RE = /\s+on[a-z]+\s*=/i;
const HREF_SRC_RE = /\s(?:href|src)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))/gi;
const SAFE_SCHEME_OR_FRAGMENT_RE = /^(?:https?:\/\/|mailto:|tel:|#)/i;

function classifyRawHtmlAttr(value) {
  if (value === '' || value == null) return 'ok';
  if (/^[a-z]+:/i.test(value) && !SAFE_SCHEME_OR_FRAGMENT_RE.test(value)) return 'unsafe-scheme';
  if (value.startsWith('/')) return 'site-relative';
  if (value.startsWith('#')) return 'ok';
  if (/^(?:https?:\/\/|mailto:|tel:)/i.test(value)) return 'ok';
  return 'relative';
}

export function validateMarkdown(sourceRel, md, opts) {
  const { manifest, docsRoot, pathExists } = opts;
  const relFromDocs = path.relative('docs', sourceRel);
  const sourceAbsDir = path.dirname(path.join(docsRoot, relFromDocs));
  const shippedSources = new Set(
    (manifest.docs ?? []).filter(d => d.source).map(d => d.source),
  );

  const tokens = marked.lexer(md);

  function walkLinks(list) {
    for (const tok of list) {
      if (tok.type === 'link') {
        validateLink(tok.href, sourceAbsDir, sourceRel);
      }
      if (Array.isArray(tok.tokens)) walkLinks(tok.tokens);
      if (Array.isArray(tok.items)) {
        for (const it of tok.items) {
          if (Array.isArray(it.tokens)) walkLinks(it.tokens);
        }
      }
    }
  }

  function validateLink(href, fromDirAbs, fromRel) {
    if (!href) return;
    if (href.startsWith('#')) return;
    if (/^(?:https?:\/\/|mailto:|tel:)/i.test(href)) return;
    if (href.startsWith('/')) {
      throw new Error(`${fromRel}: site-relative Markdown link "${href}" is forbidden; use a relative .md path`);
    }
    const [pathPart] = href.split('#');
    const resolvedAbs = path.resolve(fromDirAbs, pathPart);
    if (resolvedAbs !== docsRoot && !resolvedAbs.startsWith(docsRoot + path.sep)) {
      throw new Error(`${fromRel}: link "${href}" resolves outside docs/`);
    }
    const resolvedRel = 'docs/' + path.relative(docsRoot, resolvedAbs).split(path.sep).join('/');
    if (resolvedRel.startsWith('docs/superpowers/')) {
      throw new Error(`${fromRel}: link "${href}" points into docs/superpowers/ (stealth leak)`);
    }
    if (!pathExists(resolvedAbs)) {
      throw new Error(`${fromRel}: link "${href}" target does not exist (${resolvedRel})`);
    }
    if (resolvedRel.endsWith('.md') && !shippedSources.has(resolvedRel)) {
      throw new Error(`${fromRel}: link "${href}" points to .md not in manifest: ${resolvedRel}`);
    }
  }

  walkLinks(tokens);

  function scanRawHtml(html) {
    const m = FORBIDDEN_TAGS_RE.exec(html);
    if (m) {
      throw new Error(`${sourceRel}: raw HTML contains forbidden tag <${m[1]}>`);
    }
    if (ON_HANDLER_RE.test(html)) {
      const handlerMatch = html.match(/\s+(on[a-z]+)\s*=/i);
      const handler = handlerMatch ? handlerMatch[1] : 'on*';
      throw new Error(`${sourceRel}: raw HTML contains ${handler} handler attribute`);
    }
    HREF_SRC_RE.lastIndex = 0;
    let attrMatch;
    while ((attrMatch = HREF_SRC_RE.exec(html)) !== null) {
      const value = attrMatch[1] ?? attrMatch[2] ?? attrMatch[3] ?? '';
      const kind = classifyRawHtmlAttr(value);
      if (kind !== 'ok') {
        throw new Error(`${sourceRel}: raw HTML href/src="${value}" is ${kind}; allowed: https://, http://, mailto:, tel:, #fragment`);
      }
    }
  }

  for (const tok of tokens) {
    if (tok.type === 'html') scanRawHtml(tok.raw ?? tok.text ?? '');
    if (Array.isArray(tok.tokens)) {
      for (const inner of tok.tokens) {
        if (inner.type === 'html') scanRawHtml(inner.raw ?? inner.text ?? '');
      }
    }
  }

  return { ok: true };
}
