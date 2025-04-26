// Service worker for offline functionality
const CACHE_NAME = 'amr-network-v1';
const OFFLINE_URL = '/offline.html';
const ASSETS_TO_CACHE = [
    '/',
    '/static/css/main.css',
    '/static/js/dashboard.js',
    '/static/js/alerts.js',
    '/static/js/maps.js',
    '/static/js/charts.js',
    '/static/manifest.json',
    '/offline.html',
    'https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
    'https://cdn.jsdelivr.net/npm/chart.js'
];

// Install event - cache assets
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('Opened cache');
                return cache.addAll(ASSETS_TO_CACHE);
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.filter(cacheName => {
                    return cacheName !== CACHE_NAME;
                }).map(cacheName => {
                    return caches.delete(cacheName);
                })
            );
        })
    );
});

// Fetch event - network first with cache fallback
self.addEventListener('fetch', event => {
    // Skip cross-origin requests
    if (!event.request.url.startsWith(self.location.origin)) {
        return;
    }
    
    // Skip if the request is for the Firebase SDK
    if (event.request.url.includes('gstatic.com/firebasejs')) {
        return;
    }
    
    // For API requests, always go to network
    if (event.request.url.includes('/api/')) {
        return;
    }
    
    // For navigation requests, use network first strategy
    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request)
                .catch(() => {
                    return caches.match(OFFLINE_URL);
                })
        );
        return;
    }
    
    // For all other requests, use cache first, falling back to network
    event.respondWith(
        caches.match(event.request)
            .then(response => {
                if (response) {
                    return response;
                }
                
                return fetch(event.request)
                    .then(response => {
                        // Don't cache non-successful responses
                        if (!response || response.status !== 200 || response.type !== 'basic') {
                            return response;
                        }
                        
                        // Clone the response
                        const responseToCache = response.clone();
                        
                        // Add to cache
                        caches.open(CACHE_NAME)
                            .then(cache => {
                                cache.put(event.request, responseToCache);
                            });
                        
                        return response;
                    })
                    .catch(error => {
                        console.error('Fetch failed:', error);
                        // For image requests, return a fallback
                        if (event.request.destination === 'image') {
                            return new Response(
                                '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">' +
                                '<rect width="200" height="200" fill="#ddd"></rect>' +
                                '<text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" font-family="sans-serif" font-size="20px" fill="#333">Image Not Available</text>' +
                                '</svg>',
                                { headers: { 'Content-Type': 'image/svg+xml' } }
                            );
                        }
                        
                        // Let the event handler deal with other request types
                        throw error;
                    });
            })
    );
});

// Background sync for offline data submission
self.addEventListener('sync', event => {
    if (event.tag === 'sync-lab-reports') {
        event.waitUntil(syncLabReports());
    }
});

// Push notification
self.addEventListener('push', event => {
    const data = event.data.json();
    
    const options = {
        body: data.message,
        icon: '/static/images/icon-192x192.png',
        badge: '/static/images/badge-72x72.png',
        data: {
            url: data.url || '/'
        }
    };
    
    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

// Notification click handler
self.addEventListener('notificationclick', event => {
    event.notification.close();
    
    event.waitUntil(
        clients.openWindow(event.notification.data.url)
    );
});

// Function to sync lab reports when back online
async function syncLabReports() {
    try {
        const reportsToSync = await getDataFromIndexedDB('offline-reports');
        
        for (const report of reportsToSync) {
            try {
                const response = await fetch('/api/lab-reports', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(report)
                });
                
                if (response.ok) {
                    // Remove from IndexedDB if successful
                    await removeReportFromIndexedDB(report.id);
                }
            } catch (error) {
                console.error('Failed to sync report:', error);
                // Will retry on next sync event
            }
        }
    } catch (error) {
        console.error('Error during sync:', error);
    }
}

// Helper function to get data from IndexedDB
function getDataFromIndexedDB(storeName) {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('amr-network-db', 1);
        
        request.onerror = event => reject('IndexedDB error');
        
        request.onsuccess = event => {
            const db = event.target.result;
            const transaction = db.transaction(storeName, 'readonly');
            const store = transaction.objectStore(storeName);
            const getAllRequest = store.getAll();
            
            getAllRequest.onsuccess = () => {
                resolve(getAllRequest.result);
            };
            
            getAllRequest.onerror = () => {
                reject('Error getting data from IndexedDB');
            };
        };
    });
}

// Helper function to remove a report from IndexedDB
function removeReportFromIndexedDB(id) {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('amr-network-db', 1);
        
        request.onerror = event => reject('IndexedDB error');
        
        request.onsuccess = event => {
            const db = event.target.result;
            const transaction = db.transaction('offline-reports', 'readwrite');
            const store = transaction.objectStore('offline-reports');
            const deleteRequest = store.delete(id);
            
            deleteRequest.onsuccess = () => {
                resolve();
            };
            
            deleteRequest.onerror = () => {
                reject('Error removing data from IndexedDB');
            };
        };
    });
}
