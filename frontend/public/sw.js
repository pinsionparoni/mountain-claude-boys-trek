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
  // The page itself is always checked with the server ("no-cache"), so a new
  // deploy reaches phones on the next visit; otherwise a copy the browser
  // considered fresh could be served for weeks. Everything else (hashed
  // files under assets/, API calls) passes through unchanged.
  const request = event.request;
  event.respondWith(request.mode === "navigate" ? fetch(request, { cache: "no-cache" }) : fetch(request));
});
