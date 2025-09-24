// Minimal service worker: cache app shell for offline/startup. Expand as needed.
const CACHE_NAME = 'trackpad-v1';
const ASSETS = [
  '/',
  '/static/manifest.json',
  '/static/script.js',
  '/static/style.css'
];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS)));
});

self.addEventListener('fetch', event => {
  event.respondWith(caches.match(event.request).then(resp => resp || fetch(event.request)));
});
