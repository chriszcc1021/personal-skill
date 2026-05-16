// Minimal SW for PWA installability on iOS
self.addEventListener('install', e => self.skipWaiting());
self.addEventListener('activate', e => self.clients.claim());
self.addEventListener('fetch', e => {/* network-first, no caching for now */});
