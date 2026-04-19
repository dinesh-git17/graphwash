let cache = null;

export async function loadManifest() {
  if (cache) return cache;
  const res = await fetch(new URL('manifest.json', document.baseURI));
  if (!res.ok) throw new Error(`manifest fetch failed: ${res.status}`);
  cache = await res.json();
  return cache;
}

export function makeUrl(basePath) {
  return function url(tail) {
    const cleanTail = tail.startsWith('/') ? tail.slice(1) : tail;
    return basePath + cleanTail;
  };
}

export async function getUrlHelper() {
  const m = await loadManifest();
  return makeUrl(m.site.basePath);
}
