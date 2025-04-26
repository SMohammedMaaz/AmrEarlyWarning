// AMR Network Service Worker for offline functionality
const CACHE_NAME = 'amr-network-v1';

// Resources to cache on install
const PRECACHE_RESOURCES = [
  '/',
  '/static/css/styles.css',
  '/static/js/offline-manager.js',
  '/static/js/notifications.js',
  '/static/js/charts.js',
  '/static/js/maps.js',
  '/static/js/dashboard.js',
  '/static/js/data-uploader.js',
  '/static/icons/alert.svg',
  '/static/icons/dashboard.svg',
  '/static/icons/upload.svg',
  '/static/offline.html',
  '/static/manifest.json'
];

// Install event - precache key resources
self.addEventListener('install', event => {
  self.skipWaiting();
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Opened cache');
        return cache.addAll(PRECACHE_RESOURCES);
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.filter(cacheName => {
          return cacheName.startsWith('amr-network-') && cacheName !== CACHE_NAME;
        }).map(cacheName => {
          return caches.delete(cacheName);
        })
      );
    }).then(() => {
      return self.clients.claim();
    })
  );
});

// Fetch event - serve from cache if available, otherwise fetch from network
self.addEventListener('fetch', event => {
  // Skip non-GET requests
  if (event.request.method !== 'GET') return;
  
  // Skip browser extensions and third-party requests
  const url = new URL(event.request.url);
  if (!url.origin.match(/localhost|127\.0\.0\.1/)) return;
  
  // Handle API requests differently - network first for freshness
  if (url.pathname.startsWith('/api/') || url.pathname.includes('/api/')) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          // Cache a copy of the response
          if (response.status === 200) {
            const responseClone = response.clone();
            caches.open(CACHE_NAME).then(cache => {
              cache.put(event.request, responseClone);
            });
          }
          return response;
        })
        .catch(() => {
          // If network fails, try to serve from cache
          return caches.match(event.request);
        })
    );
    return;
  }
  
  // For HTML pages, use network-first strategy
  if (event.request.headers.get('Accept').includes('text/html')) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          // Cache a copy of the response
          if (response.status === 200) {
            const responseClone = response.clone();
            caches.open(CACHE_NAME).then(cache => {
              cache.put(event.request, responseClone);
            });
          }
          return response;
        })
        .catch(() => {
          // If network fails, serve from cache or offline page
          return caches.match(event.request)
            .then(cachedResponse => {
              return cachedResponse || caches.match('/static/offline.html');
            });
        })
    );
    return;
  }
  
  // For other assets, use cache-first strategy
  event.respondWith(
    caches.match(event.request)
      .then(cachedResponse => {
        if (cachedResponse) {
          return cachedResponse;
        }
        
        return fetch(event.request)
          .then(response => {
            // Cache the fetched response
            if (response.status === 200) {
              const responseClone = response.clone();
              caches.open(CACHE_NAME).then(cache => {
                cache.put(event.request, responseClone);
              });
            }
            return response;
          });
      })
  );
});

// Background sync for deferred data uploads
self.addEventListener('sync', event => {
  if (event.tag === 'sync-data') {
    event.waitUntil(syncPendingData());
  }
});

// Push event for notifications
self.addEventListener('push', event => {
  let notificationData = {};
  
  try {
    notificationData = event.data.json();
  } catch (e) {
    notificationData = {
      title: 'AMR Network Alert',
      message: event.data ? event.data.text() : 'New notification'
    };
  }
  
  const options = {
    body: notificationData.message || 'No details available',
    icon: '/static/icons/alert.svg',
    badge: '/static/icons/badge.svg',
    data: notificationData.data || {},
    vibrate: [100, 50, 100],
    tag: notificationData.tag || 'amr-alert'
  };
  
  event.waitUntil(
    self.registration.showNotification(notificationData.title, options)
  );
});

// Notification click event
self.addEventListener('notificationclick', event => {
  event.notification.close();
  
  const alertId = event.notification.data.alertId;
  const urlToOpen = alertId ? 
    new URL(`/alerts/#alert-${alertId}`, self.location.origin).href : 
    new URL('/alerts/', self.location.origin).href;
  
  event.waitUntil(
    clients.matchAll({type: 'window'})
      .then(windowClients => {
        // Check if there is already a window/tab open with the target URL
        const matchingClient = windowClients.find(client => {
          return new URL(client.url).pathname === new URL(urlToOpen).pathname;
        });
        
        if (matchingClient) {
          return matchingClient.focus();
        }
        
        // If no existing window, open a new one
        return clients.openWindow(urlToOpen);
      })
  );
});

// Message handler from clients
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'CACHE_RESOURCES') {
    event.waitUntil(
      caches.open(CACHE_NAME)
        .then(cache => {
          return cache.addAll(event.data.resources || []);
        })
    );
  }
});

// Sync pending data uploads
async function syncPendingData() {
  try {
    // Get all clients
    const clients = await self.clients.matchAll();
    
    // Send message to clients to sync data
    clients.forEach(client => {
      client.postMessage({
        type: 'SYNC_PENDING_DATA'
      });
    });
    
    return true;
  } catch (error) {
    console.error('Error syncing pending data:', error);
    return false;
  }
}
