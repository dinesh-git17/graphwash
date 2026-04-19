import { makeUrl } from './manifest.js';

export async function showLanding(manifest) {
  const url = makeUrl(manifest.site.basePath);
  const metrics = await (await fetch(new URL('metrics.json', document.baseURI))).json();

  renderNav(document.getElementById('topnav'), manifest, url);
  renderTicker(document.getElementById('ticker-track'), metrics);
  renderHeroLeft(document.getElementById('hero-left'), manifest, url);
  renderHeroRight(document.getElementById('hero-right'), metrics);
  renderHeroFooter(document.getElementById('hero-footer'), metrics, manifest, url);
  renderHonestyFooter(document.getElementById('honesty-footer'));
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
      ${manifest.categories.map(c => `
        <a href="${url('categories/' + c.id + '/')}">${esc(c.label)}</a>
      `).join('')}
    </div>
    <div class="nav-right">
      <a class="nav-link-external" href="${esc(manifest.site.repo)}" target="_blank" rel="noopener">GitHub</a>
    </div>
  `;
}

function renderTicker(el, metrics) {
  const items = metrics.ticker.items.map(it => {
    const prefix = it.framing === 'target' ? 'target ' : it.framing === 'baseline' ? 'baseline ' : '';
    const framedClass = it.framing !== 'measured' ? ' ticker-framed' : '';
    const delta = it.delta ? `<span class="ticker-delta mono">${esc(it.delta)}</span>` : '';
    return `
      <span class="ticker-item${framedClass}">
        <span class="ticker-label">${esc(prefix)}${esc(it.label)}</span>
        <span class="ticker-value mono">${esc(it.value)}</span>
        ${delta}
      </span>
      <span class="ticker-sep">·</span>
    `;
  }).join('');
  el.innerHTML = items + items;
}

function renderHeroLeft(el, manifest, url) {
  const hasBenchmarks = manifest.docs.some(d => d.slug === 'benchmarks');
  const hasLiveDemo = Boolean(manifest.site.liveDemoUrl);
  el.innerHTML = `
    <div class="eyebrow">
      <span class="eyebrow-dot"></span>
      <span>Docs</span>
      <span class="eyebrow-sep">/</span>
      <span>${esc(manifest.site.version)} · ibm it-aml medium</span>
    </div>
    <h1>Reading the topology<br>of <span class="em">laundered money</span><br>
      <span class="soft">one edge at a time.</span></h1>
    <p class="lede">${esc(manifest.site.tagline)}. Synthetic data only; not a production AML system.</p>
    <div class="cta-row">
      <a class="btn btn-primary" href="${url('docs/prd/')}">Read the docs</a>
      ${hasBenchmarks ? `<a class="btn btn-ghost" href="${url('docs/benchmarks/')}">View benchmarks</a>` : ''}
      ${hasLiveDemo ? `<a class="btn btn-ghost" href="${esc(manifest.site.liveDemoUrl)}" target="_blank" rel="noopener">Live demo</a>` : ''}
    </div>
    <div class="quick-nav">
      ${manifest.categories.map(c => {
        const count = manifest.docs.filter(d => d.category === c.id).length;
        return `
          <a class="quick" href="${url('categories/' + c.id + '/')}">
            <div class="quick-head">
              <span class="quick-ix">${esc(c.index)} · ${esc(c.label)}</span>
              <span class="quick-count">${count} doc${count === 1 ? '' : 's'}</span>
            </div>
            <span class="quick-title">${esc(c.label)}</span>
            <span class="quick-sub">${esc(c.description)}</span>
          </a>`;
      }).join('')}
    </div>
  `;
}

function renderHeroRight(el, metrics) {
  el.innerHTML = `
    <div class="graph-stage">
      <div class="stage-chrome">
        <div class="stage-chrome-left">
          <span class="stage-title"><strong>ILLUSTRATIVE</strong> · subgraph example</span>
        </div>
      </div>
      <span class="crosshair tl">illustrative</span>
      <svg class="graph" id="graph" viewBox="0 0 800 600" preserveAspectRatio="xMidYMid slice">
        <defs>
          <radialGradient id="glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stop-color="#3b82f6" stop-opacity="0.5"/>
            <stop offset="100%" stop-color="#3b82f6" stop-opacity="0"/>
          </radialGradient>
        </defs>
        <g id="edges-layer"></g>
        <g id="nodes-layer"></g>
      </svg>
      <div class="scoreboard" id="model-card">
        <div class="sb-row"><span class="sb-label">Architecture</span><span class="sb-val mono">${esc(metrics.modelCard.architecture)}</span></div>
        <div class="sb-row"><span class="sb-label">Dataset</span><span class="sb-val mono">${esc(metrics.modelCard.dataset)}</span></div>
        <div class="sb-row"><span class="sb-label">Status</span><span class="sb-val mono">${esc(metrics.modelCard.trainingStatus)}</span></div>
        ${metrics.modelCard.params !== null ? `<div class="sb-row"><span class="sb-label">Params</span><span class="sb-val mono">${esc(String(metrics.modelCard.params))}</span></div>` : ''}
        ${metrics.modelCard.runId ? `<div class="sb-row"><span class="sb-label">Run</span><span class="sb-val mono">${esc(metrics.modelCard.runId)}</span></div>` : ''}
      </div>
    </div>
  `;
  runHeroGraph();
}

function runHeroGraph() {
  const svg = document.getElementById('graph');
  const edgesLayer = document.getElementById('edges-layer');
  const nodesLayer = document.getElementById('nodes-layer');

  const W = 800, H = 600;

  const NT = {
    individual: { fill: '#8aa2ff', ring: '#bac4ea', r: 5.5 },
    business:   { fill: '#c4a464', ring: '#ddc895', r: 6.5 },
    bank:       { fill: '#74a8a8', ring: '#a9cece', r: 8.5 },
  };

  const rand = (seed => {
    let s = seed >>> 0;
    return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 0xFFFFFFFF; };
  })(20260418);

  const nodes = [];
  const pushN = (t, cx, cy) => {
    const type = t;
    const j = (rand()-0.5);
    nodes.push({
      id: nodes.length,
      type,
      x: cx + j * 30,
      y: cy + (rand()-0.5) * 30,
      vx: 0, vy: 0,
      r: NT[type].r,
    });
    return nodes.length - 1;
  };

  const banks = [
    pushN('bank', W*0.28, H*0.32),
    pushN('bank', W*0.72, H*0.35),
    pushN('bank', W*0.5,  H*0.72),
  ];

  const businesses = [];
  for (let i = 0; i < 11; i++) {
    const angle = rand() * Math.PI * 2;
    const rr = 120 + rand() * 150;
    businesses.push(pushN('business', W*0.5 + Math.cos(angle)*rr, H*0.5 + Math.sin(angle)*rr*0.7));
  }

  const individuals = [];
  for (let i = 0; i < 34; i++) {
    individuals.push(pushN('individual', rand()*W, rand()*H));
  }

  const edges = [];
  const addE = (a, b, opts={}) => {
    if (a === b) return;
    edges.push({ src: a, dst: b, w: opts.w ?? (0.08 + rand()*0.2), flagged: !!opts.flagged, attention: opts.attention ?? false });
  };
  individuals.forEach(i => {
    const bCount = 1 + Math.floor(rand()*2);
    for (let k = 0; k < bCount; k++) {
      const b = businesses[Math.floor(rand()*businesses.length)];
      addE(i, b);
    }
    if (rand() < 0.18) addE(i, banks[Math.floor(rand()*banks.length)]);
    if (rand() < 0.22) addE(i, individuals[Math.floor(rand()*individuals.length)]);
  });
  businesses.forEach(b => {
    addE(b, banks[Math.floor(rand()*banks.length)]);
    if (rand() < 0.4) addE(b, banks[Math.floor(rand()*banks.length)]);
  });
  addE(banks[0], banks[1], { w: 0.18 });
  addE(banks[1], banks[2], { w: 0.18 });

  const attentionEdges = [];
  for (let i = 0; i < 9; i++) {
    const e = edges[Math.floor(rand()*edges.length)];
    e.attention = true;
    e.w = 0.55 + rand()*0.35;
    attentionEdges.push(e);
  }
  const flagged = [];
  const centerBiz = businesses[3];
  const donors = [individuals[3], individuals[9], individuals[17]];
  donors.forEach(d => {
    const e = { src: d, dst: centerBiz, w: 0.9, flagged: true, attention: true };
    edges.push(e); flagged.push(e);
  });
  const bankOut = banks[2];
  const fe = { src: centerBiz, dst: bankOut, w: 0.95, flagged: true, attention: true };
  edges.push(fe); flagged.push(fe);

  const EDGE_LEN = 62;
  const REPULSE = 1600;
  const GRAVITY = 0.02;

  function step() {
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i+1; j < nodes.length; j++) {
        const a = nodes[i], b = nodes[j];
        let dx = a.x - b.x, dy = a.y - b.y;
        let d2 = dx*dx + dy*dy + 0.01;
        const f = REPULSE / d2;
        const d = Math.sqrt(d2);
        dx /= d; dy /= d;
        a.vx += dx * f * 0.01; a.vy += dy * f * 0.01;
        b.vx -= dx * f * 0.01; b.vy -= dy * f * 0.01;
      }
    }
    edges.forEach(e => {
      const a = nodes[e.src], b = nodes[e.dst];
      let dx = b.x - a.x, dy = b.y - a.y;
      const d = Math.sqrt(dx*dx + dy*dy) + 0.01;
      const targetLen = e.flagged ? EDGE_LEN * 1.3 : EDGE_LEN;
      const f = (d - targetLen) * 0.025;
      dx /= d; dy /= d;
      a.vx += dx * f; a.vy += dy * f;
      b.vx -= dx * f; b.vy -= dy * f;
    });
    nodes.forEach(n => {
      n.vx += (W/2 - n.x) * GRAVITY * 0.01;
      n.vy += (H/2 - n.y) * GRAVITY * 0.01;
      n.vx *= 0.82; n.vy *= 0.82;
      n.x += n.vx; n.y += n.vy;
      n.x = Math.max(30, Math.min(W-30, n.x));
      n.y = Math.max(30, Math.min(H-30, n.y));
    });
  }
  for (let k = 0; k < 220; k++) step();

  const ns = 'http://www.w3.org/2000/svg';
  edgesLayer.innerHTML = '';
  nodesLayer.innerHTML = '';

  const edgeEls = [];
  edges.sort((a,b) => (a.flagged?2:(a.attention?1:0)) - (b.flagged?2:(b.attention?1:0)));

  edges.forEach((e, idx) => {
    const a = nodes[e.src], b = nodes[e.dst];
    const line = document.createElementNS(ns, 'line');
    line.setAttribute('x1', a.x.toFixed(1));
    line.setAttribute('y1', a.y.toFixed(1));
    line.setAttribute('x2', b.x.toFixed(1));
    line.setAttribute('y2', b.y.toFixed(1));
    if (e.flagged) {
      line.setAttribute('stroke', '#ef4770');
      line.setAttribute('stroke-width', (1.2 + e.w * 2).toFixed(2));
      line.setAttribute('stroke-opacity', '0.9');
      line.setAttribute('stroke-linecap', 'round');
      line.classList.add('flagged-edge');
    } else if (e.attention) {
      line.setAttribute('stroke', '#3b82f6');
      line.setAttribute('stroke-width', (0.8 + e.w * 1.8).toFixed(2));
      line.setAttribute('stroke-opacity', (0.35 + e.w * 0.4).toFixed(2));
      line.setAttribute('stroke-linecap', 'round');
    } else {
      line.setAttribute('stroke', '#2a2f3b');
      line.setAttribute('stroke-width', '0.9');
      line.setAttribute('stroke-opacity', '0.55');
    }
    edgesLayer.appendChild(line);
    edgeEls.push(line);
  });

  const flaggedLines = Array.from(edgesLayer.querySelectorAll('.flagged-edge'));
  flaggedLines.forEach((ln, i) => {
    const pulse = document.createElementNS(ns, 'line');
    ['x1','y1','x2','y2'].forEach(a => pulse.setAttribute(a, ln.getAttribute(a)));
    pulse.setAttribute('stroke', '#ff7e9b');
    pulse.setAttribute('stroke-width', '3');
    pulse.setAttribute('stroke-linecap', 'round');
    pulse.setAttribute('opacity', '0.0');
    edgesLayer.appendChild(pulse);
    pulse.style.animation = `flagpulse 2.2s ease-in-out ${i*0.25}s infinite`;
  });

  nodes.forEach(n => {
    const spec = NT[n.type];
    if (n.type === 'bank') {
      const halo = document.createElementNS(ns, 'circle');
      halo.setAttribute('cx', n.x.toFixed(1));
      halo.setAttribute('cy', n.y.toFixed(1));
      halo.setAttribute('r', (n.r * 3.2).toFixed(1));
      halo.setAttribute('fill', 'url(#glow)');
      halo.setAttribute('opacity', '0.6');
      nodesLayer.appendChild(halo);
    }
    const c = document.createElementNS(ns, 'circle');
    c.setAttribute('cx', n.x.toFixed(1));
    c.setAttribute('cy', n.y.toFixed(1));
    c.setAttribute('r', n.r.toFixed(1));
    c.setAttribute('fill', spec.fill);
    c.setAttribute('stroke', spec.ring);
    c.setAttribute('stroke-width', '0.6');
    c.setAttribute('opacity', '0.9');
    nodesLayer.appendChild(c);
  });

  flagged.forEach(e => {
    [nodes[e.src], nodes[e.dst]].forEach(n => {
      if (!n || n._ringed) return;
      n._ringed = true;
      const ring = document.createElementNS(ns, 'circle');
      ring.setAttribute('cx', n.x.toFixed(1));
      ring.setAttribute('cy', n.y.toFixed(1));
      ring.setAttribute('r', (n.r + 5).toFixed(1));
      ring.setAttribute('fill', 'none');
      ring.setAttribute('stroke', '#ef4770');
      ring.setAttribute('stroke-width', '0.8');
      ring.setAttribute('opacity', '0.55');
      ring.style.animation = 'ringpulse 2.4s ease-in-out infinite';
      nodesLayer.appendChild(ring);
    });
  });

  const st = document.createElement('style');
  st.textContent = `
    @keyframes flagpulse {
      0%, 100% { opacity: 0; stroke-width: 1.5; }
      50%      { opacity: 0.55; stroke-width: 3.2; }
    }
    @keyframes ringpulse {
      0%, 100% { opacity: 0.25; r-transform: scale(1); }
      50%      { opacity: 0.65; }
    }
    .flagged-edge {
      animation: flaghue 4s ease-in-out infinite;
    }
    @keyframes flaghue {
      0%,100% { stroke: #ef4770; }
      50%     { stroke: #ff96ad; }
    }
  `;
  document.head.appendChild(st);
}

function renderHeroFooter(el, metrics, manifest, url) {
  const hasChangelog = manifest.docs.some(d => d.slug === 'changelog');
  el.innerHTML = `
    <div class="foot-item"><span class="foot-label">${esc(metrics.highlights.baseline.label)}</span><span class="foot-val">${esc(metrics.highlights.baseline.value)}</span></div>
    <div class="foot-item"><span class="foot-label">${esc(metrics.highlights.target.label)}</span><span class="foot-val">${esc(metrics.highlights.target.value)}</span></div>
    <div class="foot-item"><span class="foot-label">${esc(metrics.highlights.deadline.label)}</span><span class="foot-val">${esc(metrics.highlights.deadline.value)}</span></div>
    <div></div>
    ${hasChangelog ? `<a class="foot-cta" href="${url('docs/changelog/')}">Changelog</a>` : ''}
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
