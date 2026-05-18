const CACHE = 'reno-v3';
const CORE = [
  '/appliance-guide/',
  '/appliance-guide/index.html',
  '/appliance-guide/manifest.webmanifest',
  '/appliance-guide/icons/icon-180.png',
  '/appliance-guide/icons/icon-192.png',
  '/appliance-guide/icons/icon-512.png'
];
self.addEventListener('install', e=>{
  e.waitUntil(caches.open(CACHE).then(c=>c.addAll(CORE)).then(()=>self.skipWaiting()));
});
self.addEventListener('activate', e=>{
  e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));
});
self.addEventListener('fetch', e=>{
  const url = new URL(e.request.url);
  if(e.request.method!=='GET') return;
  if(!url.pathname.startsWith('/appliance-guide/')) return;
  e.respondWith(
    caches.match(e.request).then(hit=>{
      if(hit) {
        // background revalidate for html
        if(/\.html?$/.test(url.pathname) || url.pathname.endsWith('/')){
          fetch(e.request).then(r=>{ if(r.ok) caches.open(CACHE).then(c=>c.put(e.request,r.clone())); }).catch(()=>{});
        }
        return hit;
      }
      return fetch(e.request).then(r=>{
        if(r.ok) { const cp=r.clone(); caches.open(CACHE).then(c=>c.put(e.request,cp)); }
        return r;
      }).catch(()=>caches.match('/appliance-guide/'));
    })
  );
});
