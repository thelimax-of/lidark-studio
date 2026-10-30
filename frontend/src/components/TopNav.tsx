import { useEffect, useRef, useState, type KeyboardEvent as RKE } from 'react'
import { Link, useLocation } from 'react-router-dom'
import clsx from 'clsx'
import { Check, ChevronDown, Menu as MenuIcon, Plus, Rocket, Search, X, Sparkles, RefreshCw, Flame, Link2, Command } from 'lucide-react'
import { useChannel } from '../ui'
import { NAV, activeGroup, hrefOf, isActiveItem, warm, type NavGroup, type NavItem } from './nav'
import { ChannelAvatar, useActiveJobs, useNotifications, usePendingComments } from './live'
import { usePopover } from './usePopover'
import { discoverIdeas, produceVideo, runRadar, syncMetrics } from './actions'
import JobsIndicator from './JobsIndicator'
import NotificationBell from './NotificationBell'
import WindowControls from './WindowControls'

// ---------------------------------------------------------------- marca

export function LogoMark({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden className="shrink-0 drop-shadow-[0_4px_14px_rgb(124_92_255/.55)]">
      <defs>
        <linearGradient id="lk-g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="var(--accent)" /><stop offset=".55" stopColor="#5b7cff" /><stop offset="1" stopColor="var(--accent-2)" /></linearGradient>
        <radialGradient id="lk-h" cx=".3" cy=".2" r=".9"><stop offset="0" stopColor="#fff" stopOpacity=".35" /><stop offset=".6" stopColor="#fff" stopOpacity="0" /></radialGradient>
      </defs>
      <rect x="2" y="2" width="60" height="60" rx="16" fill="url(#lk-g)" />
      <rect x="2" y="2" width="60" height="60" rx="16" fill="url(#lk-h)" />
      <path d="M22 16v28h20" fill="none" stroke="#fff" strokeWidth="7" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="42" cy="20" r="5" fill="#fff" fillOpacity=".92" />
    </svg>
  )
}

// ---------------------------------------------------------------- contadores nos itens

function useBadges() {
  const { active } = useActiveJobs()
  const comments = usePendingComments()
  const { unread } = useNotifications()
  return { jobs: active.length, comments, notifications: unread } as Record<NonNullable<NavItem['badge']>, number>
}

// ---------------------------------------------------------------- seletor de canal

function ChannelSwitcher() {
  const { channels, channel, setChannelId } = useChannel()
  const { open, setOpen, ref, toggle } = usePopover()
  const [q, setQ] = useState('')
  useEffect(() => { if (!open) setQ('') }, [open])
  const list = channels.filter(c => !q || (c.name + ' ' + (c.handle ?? '')).toLowerCase().includes(q.toLowerCase()))
  return (
    <div className="relative" ref={ref}>
      <button data-trigger onClick={toggle} aria-expanded={open} aria-haspopup="listbox"
        className="h-9 flex items-center gap-2 pl-1 pr-2 rounded-[10px] hover:bg-white/[0.05] transition-colors max-w-[220px]">
        <ChannelAvatar c={channel} size={26} />
        <span className="min-w-0 text-left hidden sm:block">
          <span className="block text-[13px] font-medium truncate leading-tight">{channel?.name ?? 'Sem canal'}</span>
          <span className="block text-[11px] text-muted truncate leading-tight">{channel?.handle || 'conecte um canal'}</span>
        </span>
        <ChevronDown size={14} className={clsx('text-faint transition-transform duration-150', open && 'rotate-180')} />
      </button>
      {open && (
        <div className="menu left-0 top-full mt-2 w-[290px] p-1.5!" role="listbox">
          {channels.length > 6 && (
            <input autoFocus className="input h-8! mb-1.5" placeholder="Buscar canal…" value={q} onChange={e => setQ(e.target.value)} />
          )}
          <div className="px-2 pt-1 pb-1.5 text-[11px] uppercase tracking-wider text-faint">Canais</div>
          <div className="max-h-[50vh] overflow-y-auto">
            {list.map(c => (
              <button key={c.id} role="option" aria-selected={c.id === channel?.id} onClick={() => { setChannelId(c.id); setOpen(false) }} className="menu-item h-11!">
                <ChannelAvatar c={c} size={26} />
                <span className="flex-1 min-w-0">
                  <span className="block truncate text-[13px]">{c.name}</span>
                  <span className="block truncate text-[11px] text-muted">{c.handle || c.niche}</span>
                </span>
                {c.id === channel?.id && <Check size={14} className="text-accent" />}
              </button>
            ))}
          </div>
          <div className="menu-sep" />
          <Link to="/canais" onClick={() => setOpen(false)} className="menu-item text-muted"><Link2 size={15} /> Conectar canal do YouTube</Link>
          <Link to="/canais/novo" onClick={() => setOpen(false)} className="menu-item text-muted"><Plus size={15} /> Criar canal novo</Link>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------- mega-menu

const QUICK: Record<string, { label: string; icon: any; run: (cid?: number) => unknown; hint: string }[]> = {
  criar: [
    { label: 'Gerar pautas com IA', icon: Sparkles, run: cid => discoverIdeas(cid), hint: '8 pautas de Short para o canal atual' },
    { label: 'Produzir vídeo agora', icon: Rocket, run: cid => produceVideo(cid), hint: 'Usa a melhor pauta aprovada' },
  ],
  crescer: [
    { label: 'Sincronizar métricas', icon: RefreshCw, run: cid => syncMetrics(cid), hint: 'Busca views e retenção no YouTube' },
    { label: 'Rodar radar de tendências', icon: Flame, run: cid => runRadar(cid), hint: 'Procura assuntos subindo agora' },
  ],
}

function MegaPanel({ group, cid, pathname, badges, onPick, panelRef, onKeyDown }: {
  group: NavGroup; cid?: number; pathname: string; badges: Record<string, number>
  onPick: () => void; panelRef: React.RefObject<HTMLDivElement | null>; onKeyDown: (e: RKE) => void
}) {
  const quick = QUICK[group.id]
  const cols = group.columns ?? 1
  return (
    <div ref={panelRef} className="mega" role="menu" aria-label={group.label} onKeyDown={onKeyDown}
      style={{ width: cols === 2 ? 620 : quick ? 560 : 360 }}>
      <div className={clsx('flex gap-2', quick && cols === 1 && 'items-stretch')}>
        <div className={clsx('grid gap-0.5 flex-1', cols === 2 && 'grid-cols-2')}>
          {group.items.map(i => {
            const n = i.badge ? badges[i.badge] : 0
            return (
              <Link key={i.to} to={hrefOf(i, cid)} role="menuitem" data-mega-item className="mega-item" data-active={isActiveItem(i, pathname, cid)}
                onPointerEnter={() => warm(i, cid)} onFocus={() => warm(i, cid)} onClick={onPick}>
                <span className="mega-icon"><i.icon size={16} strokeWidth={1.8} /></span>
                <span className="min-w-0">
                  <span className="mega-label">{i.label}{n > 0 && <span className="count-pill">{n > 99 ? '99+' : n}</span>}</span>
                  <span className="mega-desc block">{i.desc}</span>
                </span>
              </Link>
            )
          })}
        </div>
        {quick && cols === 1 && (
          <div className="w-[200px] shrink-0 rounded-[11px] border border-line bg-bg2/60 p-2 flex flex-col gap-1">
            <div className="px-1.5 pt-1 pb-1 text-[11px] uppercase tracking-wider text-faint">Ações rápidas</div>
            {quick.map(a => (
              <button key={a.label} data-mega-item role="menuitem" className="mega-item py-2!" onClick={() => { onPick(); a.run(cid) }}>
                <a.icon size={15} className="text-accent mt-0.5 shrink-0" />
                <span className="min-w-0"><span className="block text-[13px] font-medium">{a.label}</span><span className="mega-desc block">{a.hint}</span></span>
              </button>
            ))}
          </div>
        )}
      </div>
      {quick && cols === 2 && (
        <div className="mt-2 pt-2 border-t border-line flex flex-wrap gap-1.5 px-1">
          {quick.map(a => (
            <button key={a.label} data-mega-item role="menuitem" className="btn btn-sm" onClick={() => { onPick(); a.run(cid) }}>
              <a.icon size={14} className="text-accent" />{a.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function MegaNav() {
  const { channel } = useChannel()
  const loc = useLocation()
  const badges = useBadges()
  const [open, setOpen] = useState<string | null>(null)
  const openT = useRef<number | undefined>(undefined)
  const closeT = useRef<number | undefined>(undefined)
  const triggers = useRef<Record<string, HTMLButtonElement | null>>({})
  const panel = useRef<HTMLDivElement>(null)
  const wrap = useRef<HTMLDivElement>(null)
  const cur = activeGroup(loc.pathname)
  const cid = channel?.id

  useEffect(() => { setOpen(null) }, [loc.pathname])
  useEffect(() => {
    if (!open) return
    const down = (e: PointerEvent) => { if (!wrap.current?.contains(e.target as Node)) setOpen(null) }
    document.addEventListener('pointerdown', down)
    return () => document.removeEventListener('pointerdown', down)
  }, [open])
  useEffect(() => () => { window.clearTimeout(openT.current); window.clearTimeout(closeT.current) }, [])

  const warmGroup = (g: NavGroup) => g.items.forEach(i => warm({ ...i, data: undefined }, cid))
  const enter = (g: NavGroup) => {
    window.clearTimeout(closeT.current)
    warmGroup(g)
    if (open) { setOpen(g.id); return }
    window.clearTimeout(openT.current)
    openT.current = window.setTimeout(() => setOpen(g.id), 90)  // intenção: evita abrir só de passar o mouse
  }
  const leave = () => {
    window.clearTimeout(openT.current)
    closeT.current = window.setTimeout(() => setOpen(null), 220)
  }
  const focusItem = (dir: 1 | -1 | 0) => {
    const els = Array.from(panel.current?.querySelectorAll<HTMLElement>('[data-mega-item]') ?? [])
    if (!els.length) return
    const i = els.indexOf(document.activeElement as HTMLElement)
    const n = dir === 0 ? 0 : i < 0 ? (dir > 0 ? 0 : els.length - 1) : (i + dir + els.length) % els.length
    els[n].focus()
  }
  const moveTrigger = (id: string, dir: 1 | -1, keepOpen: boolean) => {
    const k = NAV.findIndex(g => g.id === id)
    const g = NAV[(k + dir + NAV.length) % NAV.length]
    triggers.current[g.id]?.focus()
    if (keepOpen) setOpen(g.id)
  }
  const onTriggerKey = (g: NavGroup) => (e: RKE) => {
    if (e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ') {
      e.preventDefault(); setOpen(g.id); requestAnimationFrame(() => focusItem(0))
    } else if (e.key === 'ArrowRight') { e.preventDefault(); moveTrigger(g.id, 1, !!open) }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); moveTrigger(g.id, -1, !!open) }
    else if (e.key === 'Escape') setOpen(null)
  }
  const onPanelKey = (e: RKE) => {
    if (!open) return
    if (e.key === 'ArrowDown') { e.preventDefault(); focusItem(1) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); focusItem(-1) }
    else if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') { e.preventDefault(); moveTrigger(open, e.key === 'ArrowRight' ? 1 : -1, true); requestAnimationFrame(() => focusItem(0)) }
    else if (e.key === 'Escape') { e.preventDefault(); const id = open; setOpen(null); triggers.current[id]?.focus() }
    else if (e.key === 'Tab') setOpen(null)
  }

  return (
    <div ref={wrap} className="hidden lg:flex items-center gap-0.5" onPointerLeave={leave} onPointerEnter={() => window.clearTimeout(closeT.current)}>
      {NAV.map(g => {
        const n = g.items.reduce((s, i) => s + (i.badge ? badges[i.badge] : 0), 0)
        return (
          <div key={g.id} className="relative" onPointerEnter={() => enter(g)}>
            <button ref={el => { triggers.current[g.id] = el }} className="nav-trigger" data-open={open === g.id} data-active={cur === g.id}
              aria-expanded={open === g.id} aria-haspopup="menu" onKeyDown={onTriggerKey(g)}
              onClick={() => { window.clearTimeout(openT.current); setOpen(open === g.id ? null : g.id) }}>
              {g.label}
              {n > 0 && g.id !== 'inicio' && <span className="w-1.5 h-1.5 rounded-full bg-accent2" aria-hidden />}
              <ChevronDown size={13} className={clsx('text-faint transition-transform duration-150', open === g.id && 'rotate-180')} />
            </button>
            {open === g.id && <MegaPanel group={g} cid={cid} pathname={loc.pathname} badges={badges} panelRef={panel} onKeyDown={onPanelKey} onPick={() => setOpen(null)} />}
          </div>
        )
      })}
    </div>
  )
}

// ---------------------------------------------------------------- folha (telas estreitas)

function MobileSheet({ onClose }: { onClose: () => void }) {
  const { channel } = useChannel()
  const loc = useLocation()
  const badges = useBadges()
  const cid = channel?.id
  useEffect(() => {
    const h = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [onClose])
  return (
    <div className="fixed inset-0 top-[var(--topbar-h)] z-[55] backdrop lg:hidden" onPointerDown={onClose}>
      <nav className="sheet glass border-b border-line2 max-h-full overflow-y-auto p-3 grid gap-4 sm:grid-cols-2" onPointerDown={e => e.stopPropagation()} aria-label="Menu">
        {NAV.map(g => (
          <div key={g.id}>
            <div className="px-2 pb-1 text-[11px] uppercase tracking-wider text-faint">{g.label}</div>
            {g.items.map(i => {
              const n = i.badge ? badges[i.badge] : 0
              return (
                <Link key={i.to} to={hrefOf(i, cid)} onClick={onClose} onFocus={() => warm(i, cid)} className="mega-item py-2!" data-active={isActiveItem(i, loc.pathname, cid)}>
                  <span className="mega-icon w-7! h-7!"><i.icon size={15} strokeWidth={1.8} /></span>
                  <span className="mega-label self-center">{i.label}{n > 0 && <span className="count-pill">{n}</span>}</span>
                </Link>
              )
            })}
          </div>
        ))}
      </nav>
    </div>
  )
}

// ---------------------------------------------------------------- barra do topo

export default function TopNav({ connected, onSearch }: { connected: boolean; onSearch: () => void }) {
  const { channel } = useChannel()
  const [sheet, setSheet] = useState(false)
  const loc = useLocation()
  useEffect(() => setSheet(false), [loc.pathname])
  return (
    <>
      <header className="topbar topbar-drag pywebview-drag-region relative z-50 shrink-0">
        <div className="h-full px-3 lg:px-4 flex items-center gap-2 pywebview-drag-region">
          <button className="btn btn-sm btn-icon btn-ghost lg:hidden" aria-label={sheet ? 'Fechar menu' : 'Abrir menu'} aria-expanded={sheet} onClick={() => setSheet(s => !s)}>
            {sheet ? <X size={17} /> : <MenuIcon size={17} />}
          </button>
          <Link to="/" className="flex items-center gap-2 pr-1 shrink-0 no-drag" aria-label="Lidark Studio — início">
            <LogoMark size={28} />
            <span className="hidden xl:block font-semibold text-[14px] tracking-tight">Lidark <span className="text-gradient">Studio</span></span>
          </Link>
          <div className="w-px h-5 bg-line2 mx-1 hidden sm:block" />
          <ChannelSwitcher />
          <div className="w-px h-5 bg-line2 mx-1 hidden lg:block" />
          <MegaNav />
          <div className="flex-1 self-stretch pywebview-drag-region" />
          <button onClick={onSearch} className="no-drag hidden md:flex h-8 w-[min(26vw,280px)] items-center gap-2 px-2.5 rounded-[9px] border border-line2 bg-bg2/70 text-muted text-[13px] hover:border-line3 hover:text-text transition-colors" aria-label="Buscar ou executar (Ctrl K)">
            <Search size={14} /><span className="flex-1 text-left truncate">Buscar ou executar…</span>
            <span className="kbd inline-flex items-center gap-0.5"><Command size={10} />K</span>
          </button>
          <button onClick={onSearch} className="btn btn-sm btn-icon btn-ghost md:hidden" aria-label="Buscar"><Search size={16} /></button>
          <button className="btn btn-sm btn-primary hidden sm:inline-flex" onClick={() => produceVideo(channel?.id)}><Rocket size={14} /><span className="hidden xl:inline">Produzir vídeo</span></button>
          <JobsIndicator connected={connected} />
          <NotificationBell />
          <div className="w-px h-5 bg-line2 mx-0.5" />
          <WindowControls />
        </div>
      </header>
      {sheet && <MobileSheet onClose={() => setSheet(false)} />}
    </>
  )
}
