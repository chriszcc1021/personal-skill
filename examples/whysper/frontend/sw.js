// Whysper SW - minimal offline shell
const CACHE='whysper-v11-ledger-sort';
const ASSETS=['./','./index.html','./manifest.webmanifest'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS)));self.skipWaiting()});
self.addEventListener('activate',e=>{
  e.waitUntil((async()=>{
    const keys=await caches.keys();
    await Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)));
    await self.clients.claim();
  })());
});
self.addEventListener('fetch',e=>{
  const u=new URL(e.request.url);
  if(u.pathname.includes('-api/')||u.pathname.includes('-media/')) return; // network only
  // Keep the app shell fresh so deployed UI changes are visible immediately.
  if(u.pathname.endsWith('/') || u.pathname.endsWith('/index.html')){
    e.respondWith(fetch(e.request).then(r=>{
      const copy = r.clone();
      caches.open(CACHE).then(c=>c.put(e.request, copy));
      return r;
    }).catch(()=>caches.match(e.request)));
    return;
  }
  e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request)));
});
