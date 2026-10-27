import { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { NavLink, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import clsx from 'clsx'
import {
  LayoutDashboard, Lightbulb, FileText, Clapperboard, Send, BarChart3, Tv, Settings as Cog, Activity, ChevronsUpDown,
  Rocket, Flame, Plus, Check, Search, ChevronRight, CornerDownLeft, MessageSquare,
} from 'lucide-react'
import { api, invalidate, useApi, useLiveEvents, type Job } from './api'
import { act, useChannel, Progress } from './ui'
import Dashboard from './pages/Dashboard'
import Ideas from './pages/Ideas'
import Scripts from './pages/Scripts'
import ScriptEditor from './pages/ScriptEditor'
import Videos from './pages/Videos'
import Jobs from './pages/Jobs'
import Channels, { Avatar } from './pages/Channels'
import ChannelDetail from './pages/ChannelDetail'
import NewChannel from './pages/NewChannel'
import Settings from './pages/Settings'
import Publish from './pages/Publish'
import Metrics from './pages/Metrics'
import Comments from './pages/Comments'

const NAV = [
  { group: 'Criar', items: [
    { to: '/', label: 'Visão geral', icon: LayoutDashboard },
    { to: '/pautas', label: 'Pautas', icon: Lightbulb },
    { to: '/roteiros', label: 'Roteiros', icon: FileText },
    { to: '/videos', label: 'Vídeos', icon: Clapperboard },
  ] },
  { group: 'Distribuir', items: [
    { to: '/publicacao', label: 'Agenda', icon: Send },
    { to: '/comentarios', label: 'Comentários', icon: MessageSquare },
    { to: '/metricas', label: 'Métricas', icon: BarChart3 },
  ] },
  { group: 'Sistema', items: [
    { to: '/fila', label: 'Produção', icon: Activity },
    { to: '/canais', label: 'Canais', icon: Tv },
    { to: '/config', label: 'Configurações', icon: Cog },
  ] },
]
const ALL = NAV.flatMap(g => g.items.map(i => ({ ...i, group: g.group })))

const produce = (id?: number) => id && act(() => api(`/channels/${id}/autopilot`, { method: 'POST' }), 'Produzindo um vídeo com a melhor pauta').then(() => invalidate('/jobs'))
const radar = (id?: number) => id && act(() => api(`/channels/${id}/radar`, { body: {} }), 'Radar de tendências rodando').then(() => invalidate('/jobs'))

// ---------------------------------------------------------------- barra lateral

function ChannelSwitcher() {
  const { channels, channel, setChannelId } = useChannel()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const h = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false) }
    document.addEventListener('mousedown', h)
    return () => document.removeEventListener('mousedown', h)
  }, [])
  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setOpen(!open)} className="w-full flex items-center gap-2.5 h-11 px-2 rounded-lg hover:bg-white/[0.04] transition text-left">
        {channel ? <Avatar c={channel} size={26} /> : <div className="w-[26px] h-[26px] rounded-full bg-panel2" />}
        <div className="min-w-0 flex-1">
          <div className="text-[13px] font-medium truncate leading-tight">{channel?.name ?? 'Sem canal'}</div>
          <div className="text-[11.5px] text-muted truncate leading-tight">{channel?.handle || 'conecte um canal'}</div>
        </div>
        <ChevronsUpDown size={14} className="text-faint" />
      </button>
      {open && (
        <div className="menu left-0 right-0 top-full mt-1">
          <div className="px-2 pt-1 pb-1.5 text-[11.5px] text-faint">Canais</div>
          {channels.map(c => (
            <button key={c.id} onClick={() => { setChannelId(c.id); setOpen(false) }} className="menu-item h-10!">
              <Avatar c={c} size={22} />
              <span className="flex-1 min-w-0 truncate">{c.name}</span>
              {c.id === channel?.id && <Check size={14} />}
            </button>
          ))}
          <div className="menu-sep" />
          <NavLink to="/canais" onClick={() => setOpen(false)} className="menu-item text-muted"><Plus size={15} /> Conectar canal do YouTube</NavLink>
        </div>
      )}
    </div>
  )
}

function Sidebar({ connected, onSearch }: { connected: boolean; onSearch: () => void }) {
  const { data: health } = useApi<any>('/health', { refetchInterval: 60000 })
  const { data: jobs = [] } = useApi<Job[]>('/jobs?limit=25')
  const active = jobs.filter(j => j.status === 'running' || j.status === 'queued').length
  const { channel } = useChannel()
  const { data: com } = useApi<{ counts: Record<string, number> }>(channel ? `/comments?channel_id=${channel.id}&status=new` : null, { refetchInterval: 300000 })
  const pending = com?.counts?.new ?? 0
  return (
    <aside className="w-[240px] shrink-0 border-r border-line bg-panel flex flex-col">
      <div className="h-[52px] flex items-center gap-2.5 px-4 border-b border-line">
        <img src="/icon-192.png" className="w-6 h-6 rounded-md" alt="" />
        <span className="font-semibold text-[14px] tracking-tight">Lidark Studio</span>
      </div>
      <div className="p-2 border-b border-line"><ChannelSwitcher /></div>
      <div className="px-3 pt-3">
        <button onClick={onSearch} className="w-full h-8 flex items-center gap-2 px-2.5 rounded-md border border-line2 bg-bg text-muted text-[13px] hover:border-[#3a3a40] transition">
          <Search size={14} /> <span className="flex-1 text-left">Buscar ou executar…</span> <span className="kbd">Ctrl K</span>
        </button>
      </div>
      <nav className="flex-1 overflow-y-auto px-3 py-3 flex flex-col gap-4">
        {NAV.map(g => (
          <div key={g.group}>
            <div className="text-[11.5px] text-faint font-medium px-2 mb-1">{g.group}</div>
            <div className="flex flex-col gap-px">
              {g.items.map(n => (
                <NavLink key={n.to} to={n.to} end={n.to === '/'} className={({ isActive }) => clsx(
                  'flex items-center gap-2.5 h-8 px-2 rounded-md text-[13.5px] transition',
                  isActive ? 'bg-white/[0.07] text-text font-medium' : 'text-muted hover:bg-white/[0.04] hover:text-text')}>
                  <n.icon size={16} strokeWidth={1.8} />
                  <span className="flex-1">{n.label}</span>
                  {n.to === '/fila' && active > 0 && <span className="badge h-[18px]! px-1.5! text-[11px]! num">{active}</span>}
                  {n.to === '/comentarios' && pending > 0 && <span className="badge h-[18px]! px-1.5! text-[11px]! num">{pending}</span>}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>
      <div className="border-t border-line px-4 py-3 text-[12px] text-muted space-y-1.5">
        <div className="flex items-center gap-2">
          <span className={clsx('w-1.5 h-1.5 rounded-full', connected ? 'bg-ok' : 'bg-bad')} />
          <span className="flex-1">{connected ? 'Motor local online' : 'Motor desconectado'}</span>
        </div>
        {health && <div className="flex items-center justify-between text-faint"><span>GPU · IA</span>
          <span>{health.ffmpeg?.nvenc ? 'NVENC' : 'CPU'} · {health.llm?.gemini_keys ? 'Gemini' : ''}{health.llm?.glm ? '+GLM' : ''}</span></div>}
      </div>
    </aside>
  )
}

// ---------------------------------------------------------------- topo

const KIND: Record<string, string> = {
  discover_ideas: 'Pautas', score_idea: 'Nota', verify_idea: 'Checagem', manual_idea: 'Validação', write_script: 'Roteiro',
  review_script: 'Revisão', render_video: 'Vídeo', autopilot: 'Piloto', publish: 'Publicação', collect_metrics: 'Métricas',
  setup_channel: 'Canal', channel_identity: 'Identidade', trend_radar: 'Radar', inspect_video: 'Inspeção', import_youtube: 'Importação',
}

function LiveJobs() {
  const { data = [] } = useApi<Job[]>('/jobs?limit=25')
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const nav = useNavigate()
  useEffect(() => {
    const h = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false) }
    document.addEventListener('mousedown', h)
    return () => document.removeEventListener('mousedown', h)
  }, [])
  const active = data.filter(j => j.status === 'running' || j.status === 'queued')
  const running = active.filter(j => j.status === 'running')
  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setOpen(!open)} className="btn btn-sm">
        {active.length ? <span className="live-dot" /> : <span className="w-1.5 h-1.5 rounded-full bg-faint" />}
        <span className="num">{active.length ? `${active.length} em produção` : 'Ocioso'}</span>
      </button>
      {open && (
        <div className="menu right-0 top-full mt-1.5 w-[360px] p-0!">
          <div className="card-head py-2.5!"><span className="card-title text-[13px]!">Produção</span><span className="text-[12px] text-muted num">{running.length} rodando · {active.length - running.length} na fila</span></div>
          {!active.length && <div className="text-[13px] text-muted px-4 py-6 text-center">Nenhuma tarefa rodando agora.</div>}
          <div className="max-h-80 overflow-y-auto p-1">
            {[...running, ...active.filter(j => j.status === 'queued')].slice(0, 8).map(j => (
              <button key={j.id} onClick={() => { setOpen(false); nav('/fila') }} className="w-full text-left px-3 py-2.5 rounded-md hover:bg-white/[0.04]">
                <div className="flex items-center justify-between gap-2 text-[12px] text-muted">
                  <span>{KIND[j.kind] ?? j.kind}</span>
                  <span className="num">{j.status === 'queued' ? 'na fila' : `${Math.round(j.progress * 100)}%`}</span>
                </div>
                <div className="text-[13px] truncate mt-0.5">{j.title}</div>
                {j.status === 'running' && <><Progress value={j.progress} className="mt-2" /><div className="text-[12px] text-muted mt-1 truncate">{j.stage}</div></>}
              </button>
            ))}
          </div>
          <div className="border-t border-line p-1"><button onClick={() => { setOpen(false); nav('/fila') }} className="menu-item justify-center text-muted">Abrir painel de produção</button></div>
        </div>
      )}
    </div>
  )
}

function Topbar() {
  const { channel } = useChannel()
  const nav = useNavigate()
  const loc = useLocation()
  const page = ALL.find(i => i.to !== '/' && loc.pathname.startsWith(i.to)) ?? ALL[0]
  const sub = loc.pathname.match(/^\/(roteiros|canais)\/\d+/) ? 'Detalhe' : null
  return (
    <header className="sticky top-0 z-30 bg-bg/90 backdrop-blur border-b border-line">
      <div className="h-[52px] px-6 flex items-center gap-2">
        <nav className="flex items-center gap-1.5 text-[13px] min-w-0">
          <span className="text-muted truncate">{channel?.name ?? 'Lidark'}</span>
          <ChevronRight size={14} className="text-faint shrink-0" />
          <span className={clsx('truncate', sub ? 'text-muted' : 'text-text font-medium')}>{page.label}</span>
          {sub && <><ChevronRight size={14} className="text-faint shrink-0" /><span className="text-text font-medium">{sub}</span></>}
        </nav>
        <div className="flex-1" />
        <button className="btn btn-sm btn-ghost" data-tip="Buscar tendências agora" onClick={() => radar(channel?.id)}><Flame size={15} /><span className="hidden lg:inline">Radar</span></button>
        <button className="btn btn-sm btn-ghost" onClick={() => nav('/pautas?nova=1')}><Plus size={15} /><span className="hidden lg:inline">Nova pauta</span></button>
        <LiveJobs />
        <button className="btn btn-sm btn-primary" onClick={() => produce(channel?.id)}><Rocket size={14} /> Produzir vídeo</button>
      </div>
    </header>
  )
}

// ---------------------------------------------------------------- paleta de comandos

type Cmd = { id: string; label: string; group: string; icon: any; hint?: string; run: () => void }

function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const nav = useNavigate()
  const { channels, channel, setChannelId } = useChannel()
  const [q, setQ] = useState('')
  const [sel, setSel] = useState(0)
  const cmds: Cmd[] = useMemo(() => [
    { id: 'produce', label: 'Produzir vídeo com a melhor pauta', group: 'Ações', icon: Rocket, run: () => produce(channel?.id) },
    { id: 'idea', label: 'Nova pauta', group: 'Ações', icon: Plus, run: () => nav('/pautas?nova=1') },
    { id: 'radar', label: 'Rodar radar de tendências', group: 'Ações', icon: Flame, run: () => radar(channel?.id) },
    ...ALL.map(i => ({ id: i.to, label: i.label, group: 'Ir para', icon: i.icon, hint: i.group, run: () => nav(i.to) })),
    ...channels.filter(c => c.id !== channel?.id).map(c => ({ id: 'ch' + c.id, label: `Trocar para ${c.name}`, group: 'Canais', icon: Tv, hint: c.handle, run: () => setChannelId(c.id) })),
  ], [channels, channel?.id])
  const norm = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
  const list = cmds.filter(c => norm(c.label + ' ' + (c.hint ?? '')).includes(norm(q)))
  useEffect(() => { if (open) { setQ(''); setSel(0) } }, [open])
  useEffect(() => setSel(0), [q])
  if (!open) return null
  const run = (c?: Cmd) => { if (!c) return; onClose(); c.run() }
  let lastGroup = ''
  return createPortal(
    <div className="fixed inset-0 z-[90] bg-black/50 flex justify-center pt-[14vh] px-4" onMouseDown={onClose}>
      <div className="w-full max-w-[560px] h-fit card bg-panel2! border-line2! shadow-[0_24px_60px_-12px_#000e] overflow-hidden animate-pop" onMouseDown={e => e.stopPropagation()}>
        <div className="flex items-center gap-2.5 px-4 h-12 border-b border-line2">
          <Search size={16} className="text-muted" />
          <input autoFocus value={q} onChange={e => setQ(e.target.value)} placeholder="Digite um comando ou página…"
            className="flex-1 bg-transparent outline-none text-[14px] placeholder:text-faint"
            onKeyDown={e => {
              if (e.key === 'ArrowDown') { e.preventDefault(); setSel(s => Math.min(s + 1, list.length - 1)) }
              if (e.key === 'ArrowUp') { e.preventDefault(); setSel(s => Math.max(s - 1, 0)) }
              if (e.key === 'Enter') run(list[sel])
              if (e.key === 'Escape') onClose()
            }} />
          <span className="kbd">Esc</span>
        </div>
        <div className="max-h-[50vh] overflow-y-auto p-1.5">
          {!list.length && <div className="text-center text-[13px] text-muted py-8">Nada encontrado.</div>}
          {list.map((c, i) => {
            const head = c.group !== lastGroup ? (lastGroup = c.group) : null
            return (
              <div key={c.id}>
                {head && <div className="px-2.5 pt-2 pb-1 text-[11.5px] text-faint">{head}</div>}
                <button onMouseMove={() => setSel(i)} onClick={() => run(c)}
                  className={clsx('w-full flex items-center gap-2.5 h-9 px-2.5 rounded-md text-[13.5px] text-left', i === sel && 'bg-white/[0.07]')}>
                  <c.icon size={15} className="text-muted" />
                  <span className="flex-1 truncate">{c.label}</span>
                  {c.hint && <span className="text-[12px] text-faint">{c.hint}</span>}
                  {i === sel && <CornerDownLeft size={13} className="text-faint" />}
                </button>
              </div>
            )
          })}
        </div>
      </div>
    </div>, document.body)
}

export default function App() {
  const connected = useLiveEvents()
  const loc = useLocation()
  const [palette, setPalette] = useState(false)
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); setPalette(p => !p) } }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [])
  return (
    <div className="flex h-full">
      <Sidebar connected={connected} onSearch={() => setPalette(true)} />
      <main className="flex-1 min-w-0 overflow-y-auto">
        <Topbar />
        <div key={loc.pathname} className="max-w-[1360px] mx-auto px-6 lg:px-8 py-7 page">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/pautas" element={<Ideas />} />
            <Route path="/roteiros" element={<Scripts />} />
            <Route path="/roteiros/:id" element={<ScriptEditor />} />
            <Route path="/videos" element={<Videos />} />
            <Route path="/publicacao" element={<Publish />} />
            <Route path="/comentarios" element={<Comments />} />
            <Route path="/metricas" element={<Metrics />} />
            <Route path="/fila" element={<Jobs />} />
            <Route path="/canais" element={<Channels />} />
            <Route path="/canais/novo" element={<NewChannel />} />
            <Route path="/canais/:id" element={<ChannelDetail />} />
            <Route path="/config" element={<Settings />} />
          </Routes>
        </div>
      </main>
      <CommandPalette open={palette} onClose={() => setPalette(false)} />
    </div>
  )
}
