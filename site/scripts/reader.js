import { makeUrl } from './manifest.js';
import { renderDocInto } from './render.js';

export async function showReader(manifest, slug) {
  const url = makeUrl(manifest.site.basePath);
  const entry = manifest.docs.find((d) => d.slug === slug);

  renderNav(document.getElementById('reader-topnav'), manifest, url);
  renderSidebar(document.getElementById('sidebar-scroll'), manifest, url, slug);
  renderHonestyFooter(document.getElementById('reader-honesty-footer'));

  if (!entry) {
    renderNotShipped(slug, url);
    return;
  }

  if (entry.status === 'placeholder') {
    renderPlaceholder(entry);
    return;
  }

  const res = await fetch(url(`_content/${slug}.md`));
  if (!res.ok) {
    renderNotShipped(slug, url);
    return;
  }
  const md = await res.text();

  renderHeader(entry, url);
  await renderBody(entry, md, manifest, url);
  wireProgress();
  scrollToHashIfPresent();
}

function renderNav(el, manifest, url) {
  el.innerHTML = `
    <a class="brand" href="${url('')}">
      <div class="brand-mark" style="background-image:url('assets/brand-mark-v2.png')"></div>
      <div class="brand-lockup">
        <span class="brand-name">graph<span class="w">wash</span></span>
        <span class="brand-sub">docs · ${esc(manifest.site.version)}</span>
      </div>
    </a>
    <div class="navlinks">
      ${manifest.categories.map((c) =>
        `<a href="${url('categories/' + c.id + '/')}">${esc(c.label)}</a>`,
      ).join('')}
    </div>
  `;
}

function renderSidebar(el, manifest, url, currentSlug) {
  const groups = new Map();
  for (const d of manifest.docs) {
    if (!groups.has(d.category)) groups.set(d.category, []);
    groups.get(d.category).push(d);
  }
  for (const list of groups.values()) {
    list.sort((a, b) => a.order - b.order || a.slug.localeCompare(b.slug));
  }

  const sections = manifest.categories.map((c) => {
    const docs = groups.get(c.id) ?? [];
    return `
      <div class="side-section">
        <div class="side-h"><span>${esc(c.label)}</span><span class="side-h-count">${docs.length}</span></div>
        ${docs.map((d) => `
          <a class="tree-leaf${d.slug === currentSlug ? ' active' : ''}" href="${url('docs/' + d.slug + '/')}">
            <span class="tree-leaf-label">${esc(d.title)}</span>
          </a>
        `).join('')}
      </div>
    `;
  }).join('');

  el.innerHTML = sections + '<div class="toc-divider"></div><ul class="toc-list" id="toc-list"></ul>';
}

function renderHeader(entry, url) {
  const inner = document.getElementById('doc-inner');
  inner.innerHTML = `
    <div class="doc-crumb">
      <a href="${url('categories/' + entry.category + '/')}">${esc(entry.category)}</a>
      <span class="sep">/</span>
      <span>${esc(entry.slug)}</span>
    </div>
    <h1 class="doc-title">${esc(entry.title)}</h1>
    <p class="doc-tagline">${esc(entry.description)}</p>
    ${entry.notice === 'internal-validation'
      ? `<div class="doc-notice">This is an internal validation report — not user-facing documentation.</div>`
      : ''}
    <div id="doc-body" class="prose"></div>
  `;
}

async function renderBody(entry, md, manifest, url) {
  const body = document.getElementById('doc-body');
  await renderDocInto(body, { md, sourceRel: entry.source, manifest, url });
  buildToc(body);
}

function buildToc(body) {
  const list = document.getElementById('toc-list');
  if (!list) return;
  const headings = body.querySelectorAll('h2, h3');
  list.innerHTML = Array.from(headings).map((h) => `
    <li class="toc-item ${h.tagName.toLowerCase()}">
      <a href="#${esc(h.id)}">${esc(h.textContent)}</a>
    </li>
  `).join('');

  const linkByHash = new Map();
  for (const a of list.querySelectorAll('a')) {
    linkByHash.set(a.getAttribute('href'), a.parentElement);
  }

  const observer = new IntersectionObserver((entries) => {
    for (const e of entries) {
      if (!e.isIntersecting) continue;
      for (const li of list.querySelectorAll('.toc-item.active')) li.classList.remove('active');
      const li = linkByHash.get('#' + e.target.id);
      if (li) li.classList.add('active');
    }
  }, { rootMargin: '-40% 0px -55% 0px', threshold: 0 });

  for (const h of headings) observer.observe(h);
}

function wireProgress() {
  const doc = document.documentElement;
  const fill = document.getElementById('progress-fill');
  const val = document.getElementById('progress-val');
  const handler = () => {
    const max = doc.scrollHeight - window.innerHeight;
    const pct = max <= 0 ? 100 : Math.min(100, Math.round((window.scrollY / max) * 100));
    if (fill) fill.style.setProperty('--pct', pct + '%');
    if (val) val.textContent = pct + '%';
  };
  window.addEventListener('scroll', handler, { passive: true });
  handler();
}

export function decodeHashTarget(hash) {
  if (!hash) return null;
  const raw = hash.startsWith('#') ? hash.slice(1) : hash;
  if (raw.length === 0) return null;
  try {
    return decodeURIComponent(raw);
  } catch {
    return raw;
  }
}

function scrollToHashIfPresent() {
  const targetId = decodeHashTarget(location.hash);
  if (!targetId) return;
  const target = document.getElementById(targetId);
  if (target) target.scrollIntoView();
}

function renderPlaceholder(entry) {
  const inner = document.getElementById('doc-inner');
  inner.innerHTML = `
    <h1 class="doc-title">${esc(entry.title)}</h1>
    <p class="doc-tagline">${esc(entry.description)}</p>
    <div class="coming-soon">Coming soon. This page will populate once the corresponding phase lands.</div>
  `;
}

function renderNotShipped(slug, url) {
  const inner = document.getElementById('doc-inner');
  inner.innerHTML = `
    <h1 class="doc-title">Not found</h1>
    <p class="doc-tagline">No doc is registered at <code>${esc(slug)}</code>.</p>
    <p><a href="${url('')}">Back to the docs home</a></p>
  `;
}

function renderHonestyFooter(el) {
  el.textContent = 'Synthetic data only · IBM IT-AML NeurIPS 2023 · not a production AML system.';
}

function esc(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
