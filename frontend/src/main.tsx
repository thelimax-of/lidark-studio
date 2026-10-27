import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import './index.css'
import App from './App'
import { qc } from './api'
import { ChannelProvider, Toaster } from './ui'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <ChannelProvider>
          <App />
          <Toaster />
        </ChannelProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)

if ('serviceWorker' in navigator && location.port !== '5173') {
  window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js').catch(() => {}))
}
