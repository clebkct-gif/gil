// Service worker do Windex: guarda uma cópia para abrir sem internet.
// Para forçar atualização de todos os aparelhos, troque o número da versão.
const VERSION = 'windex-v4';
const CORE = ['./windex.html', './manifest.webmanifest', './icon-192.png', './icon-512.png'];

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

  // Páginas (inclui apps dentro de iframes): rede primeiro, cópia guardada se estiver offline
  if (req.mode === 'navigate') {
    e.respondWith(
      fetch(req)
        .then(res => { store(req, res); return res; })
        .catch(() => caches.match(req, { ignoreSearch: true }).then(r => r || caches.match('./windex.html')))
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
