// Service Worker — Lotto Prediction Engine
const CACHE = 'lottopwa-v1';
const DATA_URL = './data/latest.json';

// File da mettere in cache per uso offline
const ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './icon-192.png',
  './icon-512.png',
];

// Installazione: mette in cache tutti i file statici
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

// Attivazione: rimuove vecchie cache
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// Fetch: network-first per i dati, cache-first per i file statici
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  // Per il file dati: network-first (prova internet, poi cache)
  if (url.pathname.endsWith('latest.json')) {
    e.respondWith(
      fetch(e.request)
        .then(res => {
          if (res.ok) {
            const clone = res.clone();
            caches.open(CACHE).then(c => c.put(e.request, clone));
          }
          return res;
        })
        .catch(() => caches.match(e.request))
    );
    return;
  }

  // Per tutto il resto: cache-first (funziona offline)
  e.respondWith(
    caches.match(e.request).then(cached => {
      if (cached) return cached;
      return fetch(e.request).then(res => {
        if (res.ok) {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return res;
      }).catch(() => caches.match('./index.html'));
    })
  );
});

// Background sync: controlla aggiornamenti ogni volta che torna la connessione
self.addEventListener('sync', e => {
  if (e.tag === 'check-updates') {
    e.waitUntil(checkForUpdates());
  }
});

async function checkForUpdates() {
  try {
    const res = await fetch(DATA_URL + '?t=' + Date.now());
    if (res.ok) {
      const c = await caches.open(CACHE);
      await c.put(DATA_URL, res);
      // Notifica tutte le finestre aperte
      const clients = await self.clients.matchAll();
      clients.forEach(client => client.postMessage({ type: 'DATA_UPDATED' }));
    }
  } catch (e) {}
}
