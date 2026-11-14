// Service worker for installing the app on a phone (PWA).
//
// Some Chrome versions only install a site as an app (full-screen, own icon)
// when it has a service worker that handles requests; otherwise "Add to Home
// screen" makes a plain browser shortcut. This one deliberately caches
// nothing: every request goes straight to the network, so there are no stale
// pages, hot reload keeps working and streamed chat answers pass through.

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));

self.addEventListener("fetch", (event) => {
  event.respondWith(fetch(event.request));
});
