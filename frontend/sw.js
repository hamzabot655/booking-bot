// Bump this version whenever the dashboard changes so old caches are purged.
const CACHE = "goethe-booking-v2";
const PRECACHE = ["/manifest.json"];

self.addEventListener("install", e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(PRECACHE)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", e => {
  // Delete every old cache version so a stale dashboard can't linger.
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => clients.claim())
  );
});

self.addEventListener("fetch", e => {
  if (e.request.method !== "GET") return;
  if (!e.request.url.startsWith(self.location.origin)) return;
  if (e.request.url.includes("/api/")) return;

  const isNavigation =
    e.request.mode === "navigate" ||
    e.request.destination === "document" ||
    e.request.url.endsWith("/") ||
    e.request.url.includes("index.html");

  if (isNavigation) {
    // NETWORK-FIRST for the dashboard HTML — always try fresh, fall back to
    // cache only when offline. Prevents clients being stuck on an old build.
    e.respondWith(
      fetch(e.request)
        .then(r => {
          const copy = r.clone();
          caches.open(CACHE).then(c => c.put(e.request, copy)).catch(() => {});
          return r;
        })
        .catch(() => caches.match(e.request).then(r => r || new Response("Offline", { status: 503 })))
    );
    return;
  }

  // Cache-first for static assets (manifest, icons).
  e.respondWith(
    caches.match(e.request).then(r => r || fetch(e.request).catch(() => new Response("Offline", { status: 503 })))
  );
});
