import clsx from 'clsx'
import { createContext, useContext, useEffect, useId, useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { X, Loader2, CheckCircle2, AlertTriangle, Info, MoreHorizontal } from 'lucide-react'
import type { Channel } from './api'
import { useApi } from './api'

// ---------------------------------------------------------------- canal selecionado (cor de destaque)

type ChannelCtx = { channels: Channel[]; channel: Channel | null; setChannelId: (id: number) => void }
const Ctx = createContext<ChannelCtx>({ channels: [], channel: null, setChannelId: () => {} })

function lighten(hex: string, k = 0.28) {
  const h = hex.replace('#', '')
  if (h.length !== 6) return hex
  const n = [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16))
  return '#' + n.map(v => Math.round(v + (255 - v) * k).toString(16).padStart(2, '0')).join('')
}

export function ChannelProvider({ children }: { children: ReactNode }) {
  const { data = [] } = useApi<Channel[]>('/channels')
  const [id, setId] = useState<number | null>(() => {
    try { return Number(localStorage.getItem('channel')) || null } catch { return null }
  })
  const channel = data.find(c => c.id === id) ?? data[0] ?? null
  const setChannelId = (v: number) => { setId(v); try { localStorage.setItem('channel', String(v)) } catch { /* noop */ } }
  useEffect(() => {
    // A marca (violeta → ciano) é fixa; a cor do canal vira --channel (bg-channel, text-channel…).
    const c = channel?.color || channel?.theme?.gold || '#7c5cff'
    document.documentElement.style.setProperty('--channel', c)
    document.documentElement.style.setProperty('--channel-2', channel?.theme?.gold_light || lighten(c))
  }, [channel?.id, channel?.theme?.gold, channel?.theme?.gold_light, channel?.color])
  return <Ctx.Provider value={{ channels: data, channel, setChannelId }}>{children}</Ctx.Provider>
}
export const useChannel = () => useContext(Ctx)

// ---------------------------------------------------------------- filtro "Todos os canais" (local de cada página)

/** Cores fixas por canal para gráficos (as cores de marca dos canais são parecidas demais entre si). */
const SERIES = ['#8b6cff', '#22d3ee', '#34d399', '#f472b6', '#fbbf24', '#60a5fa', '#a3e635', '#fb923c']
export const seriesColor = (channels: Channel[], id: number) => SERIES[Math.max(0, channels.findIndex(c => c.id === id)) % SERIES.length]

/** Lembra, por página, se o filtro está em "Todos os canais" ou no canal selecionado. */
export function useScope(page: string, initialAll: boolean): [boolean, (all: boolean) => void] {
  const key = 'scope:' + page
  const [all, setAll] = useState<boolean>(() => {
    try { const v = localStorage.getItem(key); return v === null ? initialAll : v === 'all' } catch { return initialAll }
  })
  const set = (v: boolean) => { setAll(v); try { localStorage.setItem(key, v ? 'all' : 'one') } catch { /* noop */ } }
  return [all, set]
}

/** Seletor "Todos os canais" + canais. Escolher um canal também troca o canal selecionado no menu do topo. */
export function ChannelScope({ all, onChange }: { all: boolean; onChange: (all: boolean) => void }) {
  const { channels, channel, setChannelId } = useChannel()
  return (
    <select className="input !w-auto !py-1.5 text-sm" value={all ? 'all' : String(channel?.id ?? '')}
      onChange={e => { if (e.target.value === 'all') onChange(true); else { setChannelId(Number(e.target.value)); onChange(false) } }}>
      <option value="all">Todos os canais</option>
      {channels.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
    </select>
  )
}

export function ChannelTag({ id }: { id: number }) {
  const { channels } = useChannel()
  const ch = channels.find(c => c.id === id)
  return <span className="badge whitespace-nowrap"><span className="w-1.5 h-1.5 rounded-full" style={{ background: seriesColor(channels, id) }} />{ch?.name ?? `Canal ${id}`}</span>
}

// ---------------------------------------------------------------- toasts

type Toast = { id: number; kind: 'ok' | 'err' | 'info'; text: string }
let pushToast: (t: Omit<Toast, 'id'>) => void = () => {}
export const toast = {
  ok: (text: string) => pushToast({ kind: 'ok', text }),
  err: (text: string) => pushToast({ kind: 'err', text }),
  info: (text: string) => pushToast({ kind: 'info', text }),
}
export function Toaster() {
  const [items, setItems] = useState<Toast[]>([])
  useEffect(() => {
    pushToast = t => {
      const id = Date.now() + Math.random()
      setItems(x => [...x, { ...t, id }])
      setTimeout(() => setItems(x => x.filter(i => i.id !== id)), 4500)
    }
  }, [])
  return (
    <div className="fixed bottom-4 right-4 z-[80] flex flex-col gap-2 w-[360px] max-w-[calc(100vw-2rem)]">
      {items.map(t => (
        <div key={t.id} role="status" className="toast px-3.5 py-3 flex gap-2.5 items-start text-[13px] animate-pop">
          {t.kind === 'ok' ? <CheckCircle2 className="text-ok shrink-0 mt-px" size={16} /> :
            t.kind === 'err' ? <AlertTriangle className="text-bad shrink-0 mt-px" size={16} /> :
              <Info className="text-info shrink-0 mt-px" size={16} />}
          <span className="break-words leading-snug">{t.text}</span>
        </div>
      ))}
    </div>
  )
}

/** Executa uma ação assíncrona mostrando toast de sucesso/erro. */
export async function act<T>(fn: () => Promise<T>, ok?: string): Promise<T | undefined> {
  try {
    const r = await fn()
    if (ok) toast.ok(ok)
    return r
  } catch (e: any) {
    toast.err(e?.message ?? String(e))
  }
}

// ---------------------------------------------------------------- layout

export function PageHeader({ title, subtitle, actions, eyebrow }: { title: ReactNode; subtitle?: ReactNode; actions?: ReactNode; eyebrow?: string }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4 mb-6">
      <div className="min-w-0">
        {eyebrow && <div className="text-[12px] text-muted mb-1">{eyebrow}</div>}
        <h1 className="text-[22px] leading-tight font-semibold">{title}</h1>
        {subtitle && <p className="text-muted text-[13px] mt-1 max-w-2xl">{subtitle}</p>}
      </div>
      <div className="flex flex-wrap items-center gap-2">{actions}</div>
    </div>
  )
}

export function SectionTitle({ children, action, hint }: { children: ReactNode; action?: ReactNode; hint?: string }) {
  return (
    <div className="card-head">
      <div className="min-w-0"><div className="card-title">{children}</div>{hint && <div className="card-sub">{hint}</div>}</div>
      {action}
    </div>
  )
}

export function Tabs<T extends string>({ value, onChange, items }: { value: T; onChange: (v: T) => void; items: { key: T; label: string; count?: number }[] }) {
  return (
    <div className="tabs">
      {items.map(i => (
        <button key={i.key} className="tab" data-active={value === i.key} onClick={() => onChange(i.key)}>
          {i.label}{i.count !== undefined && <span className="count num">{i.count}</span>}
        </button>
      ))}
    </div>
  )
}

/** Menu de ações secundárias (“⋯”). Renderizado em portal para nunca ser cortado. */
export function Menu({ items, trigger, align = 'right' }: {
  items: ({ label: string; icon?: ReactNode; onClick?: () => void; href?: string; danger?: boolean; disabled?: boolean } | 'sep')[]
  trigger?: ReactNode; align?: 'left' | 'right'
}) {
  const [open, setOpen] = useState(false)
  const [pos, setPos] = useState({ top: 0, left: 0 })
  const btn = useRef<HTMLButtonElement>(null)
  const menu = useRef<HTMLDivElement>(null)
  useLayoutEffect(() => {
    if (!open || !btn.current) return
    const r = btn.current.getBoundingClientRect()
    const w = 210, h = (menu.current?.offsetHeight ?? 200)
    let top = r.bottom + 4
    if (top + h > window.innerHeight - 8) top = r.top - h - 4
    setPos({ top, left: align === 'right' ? Math.max(8, r.right - w) : r.left })
  }, [open, align])
  useEffect(() => {
    if (!open) return
    const close = (e: MouseEvent) => { if (!menu.current?.contains(e.target as Node) && !btn.current?.contains(e.target as Node)) setOpen(false) }
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('mousedown', close); document.addEventListener('keydown', esc)
    window.addEventListener('scroll', () => setOpen(false), { once: true, capture: true })
    return () => { document.removeEventListener('mousedown', close); document.removeEventListener('keydown', esc) }
  }, [open])
  return (
    <>
      <button ref={btn} className={trigger ? '' : 'btn btn-sm btn-icon btn-ghost'} onClick={e => { e.stopPropagation(); setOpen(!open) }} aria-label="Mais ações">
        {trigger ?? <MoreHorizontal size={16} />}
      </button>
      {open && createPortal(
        <div ref={menu} className="menu" style={{ top: pos.top, left: pos.left, width: 210, position: 'fixed' }} onClick={e => e.stopPropagation()}>
          {items.map((it, k) => it === 'sep' ? <div key={k} className="menu-sep" /> : it.href ? (
            <a key={k} href={it.href} target="_blank" rel="noreferrer" className="menu-item" onClick={() => setOpen(false)}>{it.icon}{it.label}</a>
          ) : (
            <button key={k} disabled={it.disabled} className={clsx('menu-item', it.danger && 'danger', it.disabled && 'opacity-40')}
              onClick={() => { setOpen(false); it.onClick?.() }}>{it.icon}{it.label}</button>
          ))}
        </div>, document.body)}
    </>
  )
}

export function ScoreRing({ score, size = 40 }: { score: number | null | undefined; size?: number }) {
  const s = score ?? 0
  const color = score == null ? 'var(--line-3)' : s >= 80 ? 'var(--ok)' : s >= 65 ? 'var(--warn)' : s >= 50 ? '#fb923c' : 'var(--bad)'
  const r = size / 2 - 3, c = 2 * Math.PI * r
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} stroke="var(--line)" strokeWidth="3" fill="none" />
        <circle cx={size / 2} cy={size / 2} r={r} stroke={color} strokeWidth="3" fill="none"
          strokeDasharray={c} strokeDashoffset={c * (1 - s / 100)} strokeLinecap="round" style={{ transition: 'stroke-dashoffset .5s ease' }} />
      </svg>
      <div className="absolute inset-0 grid place-items-center font-semibold num" style={{ fontSize: size * 0.32 }}>
        {score == null ? <Loader2 size={size * 0.35} className="animate-spin text-muted" /> : s}
      </div>
    </div>
  )
}

const TONES = { ok: 'text-ok', warn: 'text-warn', bad: 'text-bad', info: 'text-info', muted: 'text-muted', accent: 'text-accent', violet: 'text-violet-400' }
const STATUS: Record<string, [string, keyof typeof TONES]> = {
  new: ['Nova', 'info'], approved: ['Aprovada', 'ok'], rejected: ['Rejeitada', 'bad'], discarded: ['Descartada', 'bad'], scripted: ['Com roteiro', 'violet'],
  produced: ['Produzida', 'accent'], draft: ['Rascunho', 'info'], queued: ['Na fila', 'muted'], running: ['Rodando', 'warn'],
  rendering: ['Renderizando', 'warn'], done: ['Concluído', 'ok'], ready: ['Pronto', 'ok'], review: ['Revisar', 'warn'],
  failed: ['Falhou', 'bad'], cancelled: ['Cancelado', 'muted'], published: ['Publicado', 'ok'], scheduled: ['Agendado', 'info'],
  uploading: ['Enviando', 'warn'], verified: ['Fatos verificados', 'ok'], disputed: ['Fatos contestados', 'bad'],
  unverified: ['Não verificado', 'warn'], pending: ['Checando', 'muted'],
}
export function Status({ s }: { s: string }) {
  const [label, tone] = STATUS[s] ?? [s, 'muted']
  return <span className="badge"><span className={clsx('dot', TONES[tone], (s === 'running' || s === 'rendering' || s === 'uploading') && 'animate-pulse')} />{label}</span>
}

export function Modal({ open, onClose, title, children, wide }: { open: boolean; onClose: () => void; title: string; children: ReactNode; wide?: boolean }) {
  useEffect(() => {
    if (!open) return
    const h = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [open, onClose])
  if (!open) return null
  return createPortal(
    <div className="fixed inset-0 z-[70] backdrop grid place-items-center p-4 animate-[enter_.15s_ease_both]" onMouseDown={onClose}>
      <div role="dialog" aria-modal="true" aria-label={title} className={clsx('modal w-full max-h-[88vh] overflow-auto animate-pop', wide ? 'max-w-4xl' : 'max-w-lg')} onMouseDown={e => e.stopPropagation()}>
        <div className="card-head sticky top-0 glass z-10 rounded-t-[var(--r-lg)]">
          <h3 className="card-title">{title}</h3>
          <button className="btn btn-sm btn-icon btn-ghost" onClick={onClose}><X size={16} /></button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>, document.body)
}

export function Empty({ icon, title, text, action }: { icon: ReactNode; title: string; text?: string; action?: ReactNode }) {
  return (
    <div className="card py-14 px-6 text-center flex flex-col items-center gap-2">
      <div className="w-11 h-11 rounded-lg grid place-items-center text-muted border border-line2 bg-panel2 mb-1">{icon}</div>
      <div className="font-semibold">{title}</div>
      {text && <p className="text-muted text-[13px] max-w-md">{text}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}

export function Progress({ value, className }: { value: number; className?: string }) {
  return (
    <div className={clsx('h-1 rounded-full bg-line overflow-hidden', className)}>
      <div className="h-full rounded-full bg-grad transition-[width] duration-500" style={{ width: `${Math.round(value * 100)}%` }} />
    </div>
  )
}

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return (
    <label className="block">
      <span className="label">{label}</span>
      {children}
      {hint && <span className="text-xs text-muted mt-1 block">{hint}</span>}
    </label>
  )
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={clsx('skeleton', className)} />
}

/** Mini gráfico de linha (sem eixos) para cartões de indicador. */
export function Sparkline({ data, height = 32, className }: { data: number[]; height?: number; className?: string }) {
  const id = 'sg' + useId().replace(/:/g, '')
  if (data.length < 2) return <div style={{ height }} className={className} />
  const w = 120, max = Math.max(...data, 1), min = Math.min(...data, 0)
  const pts = data.map((v, i) => [(i / (data.length - 1)) * w, height - 2 - ((v - min) / (max - min || 1)) * (height - 4)])
  const d = pts.map((p, i) => (i ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join(' ')
  return (
    <svg viewBox={`0 0 ${w} ${height}`} preserveAspectRatio="none" className={clsx('w-full', className)} style={{ height }}>
      <defs><linearGradient id={id} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--accent)" stopOpacity=".22" /><stop offset="100%" stopColor="var(--accent)" stopOpacity="0" /></linearGradient></defs>
      <path d={`${d} L ${w} ${height} L 0 ${height} Z`} fill={`url(#${id})`} />
      <path d={d} fill="none" stroke="var(--accent)" strokeWidth="1.5" vectorEffect="non-scaling-stroke" strokeLinejoin="round" />
    </svg>
  )
}

export const ago = (iso?: string | null) => {
  if (!iso) return ''
  const d = (Date.now() - new Date(iso).getTime()) / 1000
  if (d < 60) return 'agora'
  if (d < 3600) return `há ${Math.floor(d / 60)} min`
  if (d < 86400) return `há ${Math.floor(d / 3600)} h`
  return `há ${Math.floor(d / 86400)} d`
}

export const fmtNum = (n: number) => n >= 1e6 ? (n / 1e6).toFixed(1).replace('.', ',') + ' mi' : n >= 1e3 ? (n / 1e3).toFixed(1).replace('.', ',') + ' mil' : String(n ?? 0)
export const fmtDur = (s: number) => `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, '0')}`
