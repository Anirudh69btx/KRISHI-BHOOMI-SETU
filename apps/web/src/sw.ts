/**
 * FLIP v3.0 — Service Worker (Workbox-based)
 * Strategy:
 *   - App Shell (HTML/JS/CSS): Cache-first with network fallback
 *   - API calls: Network-first with cache fallback (5min TTL)
 *   - Map tiles (PMTiles): Cache-first, long TTL
 *   - Images: Stale-while-revalidate
 *   - Offline fallback: /offline.html
 *
 * NOTE: This is a manual SW (not Vite PWA plugin generated) for full control.
 *       Build step injects PRECACHE_MANIFEST at __WB_MANIFEST.
 */

// @ts-check
/// <reference lib="webworker" />

import { clientsClaim } from 'workbox-core';
import {
  precacheAndRoute,
  createHandlerBoundToURL,
  cleanupOutdatedCaches,
} from 'workbox-precaching';
import { registerRoute, NavigationRoute } from 'workbox-routing';
import {
  NetworkFirst,
  CacheFirst,
  StaleWhileRevalidate,
} from 'workbox-strategies';
import { ExpirationPlugin } from 'workbox-expiration';
import { BackgroundSyncPlugin } from 'workbox-background-sync';

declare const self: ServiceWorkerGlobalScope;

clientsClaim();
self.skipWaiting();
cleanupOutdatedCaches();

// ── Precache App Shell ────────────────────────────────────────────────────────
precacheAndRoute(self.__WB_MANIFEST ?? []);

// ── Navigation: SPA fallback ──────────────────────────────────────────────────
registerRoute(new NavigationRoute(createHandlerBoundToURL('/index.html')));

// ── API: Network-first (5 min cache) ─────────────────────────────────────────
registerRoute(
  ({ url }) => url.pathname.startsWith('/api/') || url.pathname.startsWith('/graphql'),
  new NetworkFirst({
    cacheName: 'flip-api-cache',
    plugins: [
      new ExpirationPlugin({ maxEntries: 200, maxAgeSeconds: 5 * 60 }),
    ],
    networkTimeoutSeconds: 10,
  }),
);

// ── Map Tiles (PMTiles / MBTiles): Cache-first, 30 days ───────────────────────
registerRoute(
  ({ url }) =>
    url.pathname.startsWith('/tiles/') ||
    url.pathname.endsWith('.pmtiles') ||
    url.hostname.includes('tiles'),
  new CacheFirst({
    cacheName: 'flip-tiles-cache',
    plugins: [
      new ExpirationPlugin({ maxEntries: 1000, maxAgeSeconds: 30 * 24 * 60 * 60 }),
    ],
  }),
);

// ── WASM Binaries: Cache-first, 7 days ────────────────────────────────────────
registerRoute(
  ({ url }) => url.pathname.endsWith('.wasm'),
  new CacheFirst({
    cacheName: 'flip-wasm-cache',
    plugins: [
      new ExpirationPlugin({ maxEntries: 20, maxAgeSeconds: 7 * 24 * 60 * 60 }),
    ],
  }),
);

// ── Images: Stale-while-revalidate ────────────────────────────────────────────
registerRoute(
  ({ request }) => request.destination === 'image',
  new StaleWhileRevalidate({
    cacheName: 'flip-images-cache',
    plugins: [
      new ExpirationPlugin({ maxEntries: 100, maxAgeSeconds: 7 * 24 * 60 * 60 }),
    ],
  }),
);

// ── Background Sync for offline actions ───────────────────────────────────────
const bgSyncPlugin = new BackgroundSyncPlugin('flip-offline-queue', {
  maxRetentionTime: 24 * 60, // 24 hours in minutes
});

registerRoute(
  ({ url }) =>
    url.pathname.startsWith('/api/v1/sensors/manual') ||
    url.pathname.startsWith('/api/v1/actions') ||
    url.pathname.startsWith('/api/v1/advisories'),
  new NetworkFirst({
    cacheName: 'flip-sync-cache',
    plugins: [bgSyncPlugin],
    fetchOptions: { method: 'POST' },
  }),
  'POST',
);

// ── Push Notifications ────────────────────────────────────────────────────────
self.addEventListener('push', (event) => {
  if (!event.data) return;
  const data = event.data.json() as {
    title: string;
    body: string;
    tag?: string;
    data?: Record<string, unknown>;
  };

  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: '/icons/icon-192x192.png',
      badge: '/icons/badge-72x72.png',
      tag: data.tag ?? 'flip-notification',
      data: data.data,
      ...({ vibrate: [200, 100, 200] } as Record<string, unknown>),
    } as NotificationOptions),
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = (event.notification.data as { url?: string })?.url ?? '/';
  event.waitUntil((self as unknown as ServiceWorkerGlobalScope).clients.openWindow(url));
});

// ── Message Handler ───────────────────────────────────────────────────────────
self.addEventListener('message', (event) => {
  if ((event.data as { type?: string })?.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
