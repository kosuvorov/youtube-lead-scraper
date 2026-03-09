// Service Worker for YouTube Lead Scraper PWA
const CACHE_NAME = 'yt-scraper-v1';

self.addEventListener('install', (event) => {
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(clients.claim());
});

self.addEventListener('fetch', (event) => {
    // Network-first strategy for Streamlit app
    event.respondWith(
        fetch(event.request).catch(() => caches.match(event.request))
    );
});
