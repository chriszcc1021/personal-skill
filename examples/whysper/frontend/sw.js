// Whysper SW - minimal offline shell
const CACHE='whysper-v1';
const ASSETS=['./','./index.html','./manifest.webmanifest'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS)));self.skipWaiting()});
self.addEventListener('activate',e=>{e.waitUntil(self.clients.claim())});
self.addEventListener('fetch',e=>{
  const u=new URL(e.request.url);
  if(u.pathname.includes('-api/')||u.pathname.includes('-media/')) return; // network only
  e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request)));
});
