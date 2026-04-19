export function classifyRoute(pathname, opts) {
  const { basePath } = opts;

  if (!pathname.startsWith(basePath) && pathname + '/' !== basePath) {
    return { view: 'notfound' };
  }
  let rest = pathname.slice(basePath.length);

  try {
    rest = decodeURIComponent(rest);
  } catch {
    return { view: 'notfound' };
  }

  rest = rest.replace(/\/+/g, '/');

  if (rest.endsWith('/') && rest.length > 0) rest = rest.slice(0, -1);

  const segments = rest.split('/').filter((s) => s !== '');
  if (segments.some((seg) => seg === '.' || seg === '..')) {
    return { view: 'notfound' };
  }

  if (rest === '' || rest === 'index.html') {
    return { view: 'landing' };
  }

  const [head, ...tail] = rest.split('/').filter((s) => s !== '');
  if (head === 'docs') {
    if (tail.length === 0) return { view: 'notfound' };
    return { view: 'reader', slug: tail.join('/') };
  }
  if (head === 'categories') {
    if (tail.length !== 1) return { view: 'notfound' };
    return { view: 'category', categoryId: tail[0] };
  }
  return { view: 'notfound' };
}
