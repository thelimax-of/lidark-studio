import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client'
import { createAsyncStoragePersister } from '@tanstack/query-async-storage-persister'
import { get, set, del } from 'idb-keyval'
import './index.css'
import App from './App'
import { qc } from './api'
import { ChannelProvider, Toaster } from './ui'

// Cache das consultas salvo no IndexedDB: ao abrir, as telas aparecem na hora com os últimos dados
// e se atualizam em segundo plano. Mude CACHE_VERSION quando o formato de alguma resposta mudar.
const CACHE_VERSION = 'v2'
const persister = createAsyncStoragePersister({
  key: 'lidark-rq',
  throttleTime: 1500,
  storage: { getItem: k => get(k), setItem: (k, v) => set(k, v), removeItem: k => del(k) },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <PersistQueryClientProvider client={qc} persistOptions={{
      persister, maxAge: 24 * 3600_000, buster: CACHE_VERSION,
      dehydrateOptions: {
        shouldDehydrateQuery: q => q.state.status === 'success' && q.state.data != null && !String(q.queryKey[0] ?? '').startsWith('/jobs'),
      },
    }}>
      <BrowserRouter>
        <ChannelProvider>
          <App />
          <Toaster />
        </ChannelProvider>
      </BrowserRouter>
    </PersistQueryClientProvider>
  </StrictMode>,
)

if ('serviceWorker' in navigator && location.port !== '5173') {
  window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js').catch(() => {}))
}
