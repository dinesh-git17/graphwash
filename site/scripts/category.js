import { makeUrl } from './manifest.js';

export async function showCategory(manifest, categoryId) {
  const url = makeUrl(manifest.site.basePath);
  const category = manifest.categories.find((c) => c.id === categoryId);

  const honesty = document.getElementById('cat-honesty-footer');
  if (honesty) {
    honesty.textContent = 'Synthetic data only · IBM IT-AML NeurIPS 2023 · not a production AML system.';
  }

  if (!category) return false;

  renderNav(document.getElementById('cat-topnav'), manifest, url, categoryId);

  const crumb = document.getElementById('cat-crumb');
  crumb.innerHTML = `<a href="${url('')}">Home</a><span class="sep">/</span><span>categories</span>`;

  document.getElementById('cat-title').textContent = category.label;
  document.getElementById('cat-tagline').textContent = category.description;

  const grid = document.getElementById('category-grid');
  const docs = manifest.docs
    .filter((d) => d.category === categoryId)
    .sort((a, b) => a.order - b.order || a.slug.localeCompare(b.slug));

  grid.innerHTML = docs.map((d) => renderCard(d, url)).join('');

  for (const d of docs) {
    if (d.status === 'placeholder' || !d.source) continue;
    fetch(url(`_content/${d.slug}.md`))
      .then((r) => (r.ok ? r.text() : ''))
      .then((text) => {
        if (!text) return;
        const words = text.split(/\s+/).filter(Boolean).length;
        const minutes = Math.max(1, Math.round(words / 220));
        const cell = document.getElementById(`read-${cssId(d.slug)}`);
        if (cell) cell.textContent = `${minutes} min read`;
      })
      .catch(() => { /* swallow per-doc failures; card stays with placeholder dots */ });
  }

  return true;
}

function renderCard(d, url) {
  const isPlaceholder = d.status === 'placeholder' || !d.source;
  const pill = isPlaceholder
    ? `<span class="card-pill">Coming soon</span>`
    : `<span class="card-pill" id="read-${cssId(d.slug)}">…</span>`;
  const dimClass = isPlaceholder ? ' placeholder' : '';
  return `
    <a class="category-card${dimClass}" href="${url('docs/' + d.slug + '/')}">
      <div class="card-title">${esc(d.title)}</div>
      <div class="card-description">${esc(d.description)}</div>
      <div class="card-meta">
        <span>${esc(d.updated)}</span>
        ${pill}
      </div>
    </a>
  `;
}

function renderNav(el, manifest, url, currentCategoryId) {
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
        `<a href="${url('categories/' + c.id + '/')}"${c.id === currentCategoryId ? ' class="current"' : ''}>${esc(c.label)}</a>`,
      ).join('')}
    </div>
  `;
}

function esc(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function cssId(slug) {
  return slug.replace(/[^a-z0-9]/gi, '-');
}
