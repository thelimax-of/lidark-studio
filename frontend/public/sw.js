// Service worker mínimo: torna o painel instalável. Sempre busca na rede (o motor roda local).
self.addEventListener('install', () => self.skipWaiting())
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()))
self.addEventListener('fetch', () => {})
