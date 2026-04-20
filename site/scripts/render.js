const ALLOWED_URI_REGEXP = /^(?:(?:https?|mailto|tel):|#|\/)/i;

function htmlEscape(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export function slugify(text) {
  return String(text)
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-')
    .slice(0, 64);
}

export function makeUniqueId(baseId, usedIds) {
  const root = baseId || 'section';
  let candidate = root;
  let suffix = 2;
  while (usedIds.has(candidate)) {
    candidate = `${root}-${suffix}`;
    suffix += 1;
  }
  usedIds.add(candidate);
  return candidate;
}

function rewriteInternalHref(href, sourceDir, sourceMap, url) {
  if (!href) return '';
  if (href.startsWith('#')) return href;
  if (/^(?:https?:\/\/|mailto:|tel:)/i.test(href)) return href;
  if (href.startsWith('/')) {
    throw new Error(
      `site-relative Markdown link "${href}" reached the renderer; ` +
      `build-time validation should have rejected it`
    );
  }
  const hashIndex = href.indexOf('#');
  const pathPart = hashIndex === -1 ? href : href.slice(0, hashIndex);
  const anchor = hashIndex === -1 ? '' : href.slice(hashIndex);
  const parts = sourceDir.split('/').filter(Boolean);
  for (const seg of pathPart.split('/')) {
    if (seg === '' || seg === '.') continue;
    if (seg === '..') parts.pop();
    else parts.push(seg);
  }
  const resolved = parts.join('/');
  const slug = sourceMap.get(resolved);
  if (!slug) {
    throw new Error(
      `Markdown link "${href}" in ${sourceDir}/* resolved to "${resolved}" which is not a manifest source`
    );
  }
  return url(`docs/${slug}/`) + anchor;
}

export function makeRenderer({ sourceRel, manifest, url }) {
  const renderer = new window.marked.Renderer();
  const segs = sourceRel.split('/');
  segs.pop();
  const sourceDir = segs.join('/');
  const sourceMap = new Map();
  for (const d of manifest.docs) {
    if (d.source) sourceMap.set(d.source, d.slug);
  }

  renderer.link = function({ href, title, tokens }) {
    const resolved = rewriteInternalHref(href, sourceDir, sourceMap, url);
    const titleAttr = title ? ` title="${htmlEscape(title)}"` : '';
    const inner = this.parser.parseInline(tokens);
    return `<a href="${htmlEscape(resolved)}"${titleAttr}>${inner}</a>`;
  };

  renderer.code = ({ text, lang: infoString }) => {
    const lang = ((infoString ?? '').trim().split(/\s+/)[0] ?? '').toLowerCase();
    if (lang === 'mermaid') {
      return `<pre class="mermaid-pending">${htmlEscape(text)}</pre>`;
    }
    const cls = lang ? ` class="language-${htmlEscape(lang)}"` : '';
    return `<pre><code${cls}>${htmlEscape(text)}</code></pre>`;
  };

  renderer.list = function(token) {
    const ordered = token.ordered;
    const start = token.start;
    let body = '';
    for (const item of token.items) {
      body += this.listitem(item);
    }
    const type = ordered ? 'ol' : 'ul';
    const startAttr = (ordered && start !== 1) ? ` start="${start}"` : '';
    const classAttr = token.items.some((item) => item.task) ? ' class="task-list"' : '';
    return `<${type}${startAttr}${classAttr}>\n${body}</${type}>\n`;
  };

  renderer.listitem = function(item) {
    const classAttr = item.task && item.checked ? ' class="done"' : '';
    const body = this.parser.parse(item.tokens, !!item.loose);
    return `<li${classAttr}>${body}</li>\n`;
  };

  return renderer;
}

function sanitize(rawHtml) {
  return window.DOMPurify.sanitize(rawHtml, {
    USE_PROFILES: { html: true },
    ADD_TAGS: ['kbd', 'sub', 'sup', 'details', 'summary', 'mark', 'abbr'],
    ALLOWED_URI_REGEXP,
    FORBID_TAGS: [
      'script', 'style', 'iframe', 'object', 'embed',
      'form', 'input', 'button', 'textarea', 'select', 'link',
    ],
    FORBID_ATTR: ['style'],
  });
}

function postProcess(frag) {
  const usedHeadingIds = new Set();
  for (const h of frag.querySelectorAll('h2, h3')) {
    const baseId = h.id || slugify(h.textContent);
    h.id = makeUniqueId(baseId, usedHeadingIds);
  }

  for (const code of frag.querySelectorAll('pre > code')) {
    const classes = code.className || '';
    if (classes.includes('language-mermaid')) continue;
    if (window.hljs) {
      try {
        window.hljs.highlightElement(code);
      } catch (err) {
        console.warn('hljs highlight failed', err);
      }
    }
  }

  for (const pre of frag.querySelectorAll('pre.mermaid-pending')) {
    const div = document.createElement('div');
    div.className = 'mermaid';
    div.textContent = pre.textContent ?? '';
    pre.replaceWith(div);
  }

  for (const a of frag.querySelectorAll('a[href]')) {
    const href = a.getAttribute('href');
    if (/^https?:\/\//i.test(href) && !href.startsWith(location.origin)) {
      a.setAttribute('target', '_blank');
      a.setAttribute('rel', 'noopener');
    }
  }
}

let mermaidInitialized = false;
function initMermaidOnce() {
  if (mermaidInitialized || !window.mermaid) return;
  window.mermaid.initialize({
    startOnLoad: false,
    theme: 'base',
    themeVariables: {
      primaryColor: '#12141a',
      primaryTextColor: '#eef0f4',
      lineColor: 'rgba(255,255,255,0.16)',
      mainBkg: '#12141a',
      nodeBorder: '#3b82f6',
    },
  });
  mermaidInitialized = true;
}

export async function renderMarkdownToFragment(md, { sourceRel, manifest, url }) {
  const renderer = makeRenderer({ sourceRel, manifest, url });
  const rawHtml = window.marked.parse(md, { renderer, gfm: true });
  const safeHtml = sanitize(rawHtml);
  const tpl = document.createElement('template');
  tpl.innerHTML = safeHtml;
  postProcess(tpl.content);
  return tpl.content;
}

export async function renderDocInto(el, { md, sourceRel, manifest, url }) {
  el.innerHTML = '';
  const frag = await renderMarkdownToFragment(md, { sourceRel, manifest, url });
  el.appendChild(frag);
  if (window.mermaid && el.querySelector('.mermaid')) {
    initMermaidOnce();
    try {
      await window.mermaid.run({ nodes: el.querySelectorAll('.mermaid') });
    } catch (err) {
      console.warn('mermaid render failed', err);
    }
  }
}
