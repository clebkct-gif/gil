// Service worker do Bingo: guarda o app para abrir sem internet. Coloque na MESMA pasta do Bingo.html (https).
const C='bingo-v1';
self.addEventListener('install',e=>{self.skipWaiting()});
self.addEventListener('activate',e=>{e.waitUntil(self.clients.claim())});
self.addEventListener('message',e=>{if(e.data&&e.data.cache)e.waitUntil(caches.open(C).then(c=>c.add(e.data.cache)).catch(()=>{}))});
self.addEventListener('fetch',e=>{
  if(e.request.method!=='GET')return;
  e.respondWith(fetch(e.request).then(r=>{if(r&&r.ok){const k=r.clone();caches.open(C).then(c=>c.put(e.request,k)).catch(()=>{})}return r})
    .catch(()=>caches.match(e.request).then(r=>r||caches.match(e.request,{ignoreSearch:true}))));
});
