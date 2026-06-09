const CACHE_VERSION = 'ntuh-breast-v2026-06-09-a';
const APP_SHELL = [
  '/',
  '/index.html',
  '/assets/css/app.css',
  '/assets/css/ajcc-mobile.css',
  '/assets/js/app-config.js',
  '/assets/js/legacy-app.js',
  '/assets/js/modules/ajcc/prognostic-lookup.js',
  '/assets/js/modules/ajcc/mobile-panel.js',
  '/assets/js/modules/drug-cards.js',
  '/data/ajcc9_lookup.js',
  '/offline.html',
  '/manifest.webmanifest',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
  '/icons/maskable-512.png'
];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_VERSION).then(cache => cache.addAll(APP_SHELL)));
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE_VERSION).map(k => caches.delete(k))))
  );
  self.clients.claim();
});

async function networkFirst(request) {
  const cache = await caches.open(CACHE_VERSION);
  try {
    const response = await fetch(request);
    if (request.method === 'GET' && response.ok) cache.put(request, response.clone());
    return response;
  } catch (err) {
    const cached = await cache.match(request);
    if (cached) return cached;
    throw err;
  }
}

async function shellFallback(request) {
  const cache = await caches.open(CACHE_VERSION);
  try {
    const response = await fetch(request);
    if (response.ok) cache.put(request, response.clone());
    return response;
  } catch (err) {
    const cached = await cache.match(request, { ignoreSearch: true });
    if (cached) return cached;
    if (request.mode === 'navigate') return cache.match('/offline.html');
    throw err;
  }
}

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (url.origin !== location.origin) return;
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirst(event.request));
    return;
  }
  if (event.request.method === 'GET') {
    event.respondWith(shellFallback(event.request));
  }
});
