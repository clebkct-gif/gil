// Service worker do Windex.
// - VERSION: o "casco" do Windex (index, manifest, ícones). Troque o número para publicar uma versão nova.
// - DATA: apps das pastas, ícones e bibliotecas. Não é apagado nas atualizações, então os apps continuam offline.
const VERSION = 'windex-v3';
const DATA = 'windex-data';
const CORE = ['./', './index.html', './manifest.webmanifest', './icon-192.png', './icon-512.png'];

const SCOPE_PATH = new URL('./', self.registration.scope).pathname;
const SHELL_PATHS = [SCOPE_PATH, SCOPE_PATH + 'index.html', SCOPE_PATH + 'manifest.webmanifest'];
const ASSET_RE = /\.(?:js|mjs|css|png|jpe?g|gif|svg|webp|ico|json|woff2?|ttf|otf|txt|glb|gltf|wasm)$/i;

self.addEventListener('install', e => {
  // Sem skipWaiting automático: a página avisa que há versão nova e o usuário escolhe quando atualizar.
  e.waitUntil(
    caches.open(VERSION).then(c => Promise.all(CORE.map(u => c.add(u).catch(() => {}))))
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== VERSION && k !== DATA).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('message', e => {
  const d = e.data || {};
  if (d.type === 'SKIP_WAITING') self.skipWaiting();
  if (d.type === 'PRECACHE' && Array.isArray(d.urls)) e.waitUntil(precache(d.urls.slice(0, 500)));
});

function offlinePage() {
  return new Response(
    '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><body style="font:14px sans-serif;padding:20px;color:#444"><p><b>Não foi possível carregar este app.</b></p><p>Sem conexão, e ele ainda não foi guardado para uso offline. Tente de novo quando estiver online.</p>',
    { status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8' } }
  );
}

function isShell(url) {
  const u = new URL(url);
  return u.origin === self.location.origin && SHELL_PATHS.includes(u.pathname);
}

function cacheNameFor(url) { return isShell(url) ? VERSION : DATA; }

function store(req, res) {
  if (res && (res.status === 200 || res.type === 'opaque')) {
    const copy = res.clone();
    caches.open(cacheNameFor(req.url)).then(c => c.put(req, copy)).catch(() => {});
  }
}

function fetchTimeout(req, ms) {
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), ms);
  return fetch(req, { signal: ctl.signal }).finally(() => clearTimeout(t));
}

// Guarda também os arquivos que uma página de app usa (scripts, estilos, imagens), um nível só.
async function cacheSubresources(res, pageUrl) {
  try {
    const type = res.headers.get('content-type') || '';
    if (!/text\/html/i.test(type)) return;
    const html = await res.text();
    const base = new URL(pageUrl);
    const found = new Set();
    const re = /(?:src|href)\s*=\s*["']([^"'#]+)["']/gi;
    let m;
    while ((m = re.exec(html)) && found.size < 40) {
      const raw = m[1].trim();
      if (!raw || /^(?:data:|blob:|javascript:|mailto:|tel:)/i.test(raw)) continue;
      let u;
      try { u = new URL(raw, base); } catch (_) { continue; }
      if (u.origin !== base.origin) continue;
      if (!ASSET_RE.test(u.pathname)) continue;
      found.add(u.href);
    }
    const cache = await caches.open(DATA);
    await Promise.all([...found].map(async u => {
      if (await cache.match(u)) return;
      try { const r = await fetch(u); if (r.ok) await cache.put(u, r); } catch (_) {}
    }));
  } catch (_) {}
}

// Chamado pela página com a lista de apps, ícones e bibliotecas para ficarem disponíveis offline.
async function precache(urls) {
  const cache = await caches.open(DATA);
  const shell = await caches.open(VERSION);
  const list = [...new Set(urls)].filter(u => /^https?:/i.test(u));
  for (let i = 0; i < list.length; i += 6) {
    await Promise.all(list.slice(i, i + 6).map(async u => {
      try {
        const sh = isShell(u);
        if (!sh && await cache.match(u)) return;
        const res = await fetch(u, { cache: 'no-cache' });
        if (!res || !res.ok) return;
        await (sh ? shell : cache).put(u, res.clone());
        if (new URL(u).origin === self.location.origin) await cacheSubresources(res, u);
      } catch (_) {}
    }));
  }
}

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET' || req.headers.has('range')) return;
  if (req.destination === 'audio' || req.destination === 'video') return;

  // Páginas (inclui apps dentro de iframes): rede primeiro (com limite de tempo), cópia guardada se estiver offline.
  // O Windex só serve de reserva para o próprio Windex. Um app que falhar nunca pode virar uma
  // segunda sessão do Windex dentro da janela.
  if (req.mode === 'navigate') {
    const shell = req.destination === 'document' && isShell(req.url);
    e.respondWith(
      fetchTimeout(req, shell ? 5000 : 8000)
        .then(res => {
          store(req, res.clone());
          if (!shell) e.waitUntil(cacheSubresources(res.clone(), req.url));
          return res;
        })
        .catch(() => caches.match(req, { ignoreSearch: true }).then(r =>
          r || (shell ? caches.open(VERSION).then(c => c.match('./index.html')) : null)
        ).then(r => r || offlinePage()))
    );
    return;
  }

  // Demais arquivos (CSS, scripts, fontes, imagens): usa a cópia e atualiza em segundo plano
  e.respondWith(
    caches.match(req).then(hit => {
      const net = fetch(req).then(res => { store(req, res.clone()); return res; }).catch(() => hit);
      return hit || net;
    })
  );
});
