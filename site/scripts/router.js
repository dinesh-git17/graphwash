import { classifyRoute } from './route.js';
import { loadManifest } from './manifest.js';
import { showLanding } from './landing.js';
import { showReader } from './reader.js';
import { showCategory } from './category.js';

function switchBodyView(view) {
  document.body.className = 'view-' + view;
  for (const id of ['view-landing', 'view-reader', 'view-category', 'view-notfound']) {
    const el = document.getElementById(id);
    if (el) el.hidden = id !== 'view-' + view;
  }
}

async function dispatch() {
  const manifest = await loadManifest();
  const route = classifyRoute(location.pathname, { basePath: manifest.site.basePath });
  switchBodyView(route.view);
  if (route.view === 'landing') await showLanding(manifest);
  else if (route.view === 'reader') await showReader(manifest, route.slug);
  else if (route.view === 'category') await showCategory(manifest, route.categoryId);
  else await showNotFound(manifest);
}

async function showNotFound(manifest) {
  const link = document.getElementById('nf-home-link');
  if (link) link.setAttribute('href', manifest.site.basePath);
}

window.addEventListener('DOMContentLoaded', () => {
  dispatch().catch((err) => {
    console.error('router dispatch failed', err);
    switchBodyView('notfound');
  });
});
