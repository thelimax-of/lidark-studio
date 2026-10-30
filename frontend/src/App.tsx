import { Suspense, useEffect, useState } from 'react'
import { Link, Route, Routes, useLocation } from 'react-router-dom'
import { Compass } from 'lucide-react'
import { useLiveEvents } from './api'
import { Empty, Skeleton } from './ui'
import TopNav from './components/TopNav'
import CommandPalette from './components/CommandPalette'
import { PAGES, ROUTES, warmAllWhenIdle } from './components/nav'
import { toggleFullscreen } from './components/desktop'

/** Esqueleto com a mesma silhueta das páginas (cabeçalho + cartões) — sem salto de layout. */
function PageFallback() {
  return (
    <div aria-busy="true" aria-label="Carregando">
      <div className="route-progress" />
      <Skeleton className="h-3 w-24 mb-2" />
      <Skeleton className="h-7 w-64 mb-7" />
      <div className="grid gap-4 md:grid-cols-3 mb-4">
        <Skeleton className="h-28" /><Skeleton className="h-28" /><Skeleton className="h-28" />
      </div>
      <Skeleton className="h-72" />
    </div>
  )
}

function NotFound() {
  return <Empty icon={<Compass size={18} />} title="Página não encontrada" text="Use o menu do topo ou Ctrl K para ir a qualquer lugar."
    action={<Link to="/" className="btn btn-primary">Ir para o painel</Link>} />
}

export default function App() {
  const connected = useLiveEvents()
  const loc = useLocation()
  const [palette, setPalette] = useState(false)
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); setPalette(p => !p) }
      else if (e.key === 'F11') { e.preventDefault(); toggleFullscreen() }
    }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [])
  useEffect(() => { warmAllWhenIdle() }, [])
  useEffect(() => { document.getElementById('main')?.scrollTo(0, 0) }, [loc.pathname])
  return (
    <div className="flex flex-col h-full">
      <TopNav connected={connected} onSearch={() => setPalette(true)} />
      <main id="main" className="flex-1 min-h-0 overflow-y-auto [scrollbar-gutter:stable]">
        <Suspense fallback={<div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-7"><PageFallback /></div>}>
          <div key={loc.pathname} className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-7 page">
            <Routes>
              {ROUTES.map(r => { const P = PAGES[r.page]; return <Route key={r.path} path={r.path} element={<P />} /> })}
              <Route path="*" element={<NotFound />} />
            </Routes>
          </div>
        </Suspense>
      </main>
      <CommandPalette open={palette} onClose={() => setPalette(false)} />
    </div>
  )
}
