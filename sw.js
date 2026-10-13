// Service worker do Windex: guarda uma cópia para abrir sem internet.
// Para forçar atualização de todos os aparelhos, troque o número da versão.
const VERSION = 'index';
const CORE = ['./index.html', './manifest.webmanifest', './icon-192.png', './icon-512.png'];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(VERSION)
      .then(c => Promise.all(CORE.map(u => c.add(u).catch(() => {}))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

function offlinePage() {
  return new Response(
    '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><body style="font:14px sans-serif;padding:20px;color:#444"><p><b>Não foi possível carregar este app.</b></p><p>Sem conexão, e ele ainda não foi guardado para uso offline. Tente de novo quando estiver online.</p>',
    { status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8' } }
  );
}

function store(req, res) {
  if (res && (res.status === 200 || res.type === 'opaque')) {
    const copy = res.clone();
    caches.open(VERSION).then(c => c.put(req, copy)).catch(() => {});
  }
}

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET' || req.headers.has('range')) return;
  if (req.destination === 'audio' || req.destination === 'video') return;

  // Páginas (inclui apps dentro de iframes): rede primeiro, cópia guardada se estiver offline.
  // O Windex só serve de reserva para o próprio Windex. Um app que falhar nunca pode virar uma
  // segunda sessão do Windex dentro da janela.
  if (req.mode === 'navigate') {
    const isShell = req.destination === 'document' && /\/(windex\.html)?$/.test(new URL(req.url).pathname);
    e.respondWith(
      fetch(req)
        .then(res => { store(req, res); return res; })
        .catch(() => caches.match(req, { ignoreSearch: true }).then(r =>
          r || (isShell ? caches.match('./windex.html') : offlinePage())
        ))
    );
    return;
  }

  // Demais arquivos (CSS, scripts, fontes, imagens): usa a cópia e atualiza em segundo plano
  e.respondWith(
    caches.match(req).then(hit => {
      const net = fetch(req).then(res => { store(req, res); return res; }).catch(() => hit);
      return hit || net;
    })
  );
});
