import { useDeferredValue, useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate } from 'react-router-dom'
import clsx from 'clsx'
import { Search, CornerDownLeft, Rocket, Plus, Flame, Sparkles, RefreshCw, Tv, Maximize2, CheckCheck, FileText, Lightbulb, RotateCw, type LucideIcon } from 'lucide-react'
import { api, invalidate, useApi, type Idea, type Script } from '../api'
import { useChannel } from '../ui'
import { ALL_ITEMS, hrefOf, warm } from './nav'
import { discoverIdeas, produceVideo, runRadar, syncChannel, syncMetrics } from './actions'
import { toggleFullscreen } from './desktop'

type Cmd = { id: string; label: string; group: string; icon: LucideIcon; hint?: string; keywords?: string; run: () => void; onIntent?: () => void }

const norm = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
/** Pontua: começo do texto > começo de palavra > contém. Várias palavras: todas precisam aparecer. */
function score(text: string, q: string) {
  if (!q) return 1
  const t = norm(text)
  let total = 0
  for (const w of q.split(/\s+/).filter(Boolean)) {
    const s = t.startsWith(w) ? 4 : t.includes(' ' + w) ? 3 : t.includes(w) ? 2 : 0
    if (!s) return 0
    total += s
  }
  return total
}

export default function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const nav = useNavigate()
  const { channels, channel, setChannelId } = useChannel()
  const [q, setQ] = useState('')
  const dq = useDeferredValue(q)
  const [sel, setSel] = useState(0)
  const listRef = useRef<HTMLDivElement>(null)
  const cid = channel?.id
  const searching = open && dq.trim().length >= 2
  // busca em pautas/roteiros do canal atual (mesmas chaves de cache das páginas)
  const { data: scripts = [] } = useApi<Script[]>(searching && cid ? `/scripts?channel_id=${cid}` : null)
  const { data: ideas = [] } = useApi<Idea[]>(searching && cid ? `/ideas?channel_id=${cid}&status=new,approved` : null)

  const cmds: Cmd[] = useMemo(() => [
    { id: 'produce', label: 'Produzir vídeo com a melhor pauta', group: 'Ações', icon: Rocket, keywords: 'render criar', run: () => produceVideo(cid) },
    { id: 'discover', label: 'Gerar pautas com IA', group: 'Ações', icon: Sparkles, keywords: 'ideias buscar descobrir', run: () => discoverIdeas(cid) },
    { id: 'discover-long', label: 'Gerar pautas de vídeo longo', group: 'Ações', icon: Sparkles, keywords: 'ideias longo', run: () => discoverIdeas(cid, 'long') },
    { id: 'idea', label: 'Nova pauta manual', group: 'Ações', icon: Plus, run: () => nav('/pautas?nova=1') },
    { id: 'radar', label: 'Rodar radar de tendências', group: 'Ações', icon: Flame, keywords: 'trends', run: () => runRadar(cid) },
    { id: 'metrics', label: 'Sincronizar métricas', group: 'Ações', icon: RefreshCw, keywords: 'analytics views youtube', run: () => syncMetrics(cid) },
    { id: 'sync', label: 'Sincronizar dados do canal', group: 'Ações', icon: RotateCw, keywords: 'youtube canal', run: () => syncChannel(cid) },
    { id: 'read', label: 'Marcar notificações como lidas', group: 'Ações', icon: CheckCheck, run: () => api('/notifications/read', { body: { all: true } }).then(() => invalidate('/notifications')).catch(() => {}) },
    { id: 'fs', label: 'Alternar tela cheia', group: 'Ações', icon: Maximize2, hint: 'F11', run: toggleFullscreen },
    ...ALL_ITEMS.map(i => ({ id: 'go' + i.to, label: i.label, group: 'Ir para', icon: i.icon, hint: i.group, keywords: i.desc + ' ' + (i.keywords ?? ''), run: () => nav(hrefOf(i, cid)), onIntent: () => warm(i, cid) })),
    ...channels.filter(c => c.id !== cid).map(c => ({ id: 'ch' + c.id, label: `Trocar para ${c.name}`, group: 'Canais', icon: Tv, hint: c.handle, keywords: c.niche, run: () => setChannelId(c.id) })),
  ], [channels, cid, nav, setChannelId])

  const list = useMemo(() => {
    const nq = norm(dq.trim())
    const base = cmds.map(c => ({ c, s: Math.max(score(c.label, nq) * 2, score(`${c.hint ?? ''} ${c.keywords ?? ''}`, nq)) })).filter(x => x.s > 0)
    if (nq) base.sort((a, b) => b.s - a.s)
    const out = base.map(x => x.c)
    if (nq.length >= 2) {
      const ents: Cmd[] = [
        ...scripts.filter(s => score(s.title, nq) >= 2).slice(0, 6).map(s => ({ id: 'sc' + s.id, label: s.title, group: 'Roteiros', icon: FileText, hint: s.format, run: () => nav(`/roteiros/${s.id}`) })),
        ...ideas.filter(i => score(i.title, nq) >= 2).slice(0, 6).map(i => ({ id: 'id' + i.id, label: i.title, group: 'Pautas', icon: Lightbulb, hint: i.score != null ? `nota ${i.score}` : undefined, run: () => nav('/pautas') })),
      ]
      out.push(...ents)
    }
    // agrupa mantendo a ordem de relevância do primeiro de cada grupo
    const order: string[] = []
    out.forEach(c => { if (!order.includes(c.group)) order.push(c.group) })
    return order.flatMap(g => out.filter(c => c.group === g))
  }, [cmds, dq, scripts, ideas, nav])

  useEffect(() => { if (open) { setQ(''); setSel(0) } }, [open])
  useEffect(() => setSel(0), [dq])
  useEffect(() => { list[sel]?.onIntent?.() }, [sel, list])
  useEffect(() => { listRef.current?.querySelector(`[data-i="${sel}"]`)?.scrollIntoView({ block: 'nearest' }) }, [sel])
  if (!open) return null
  const run = (c?: Cmd) => { if (!c) return; onClose(); c.run() }
  let lastGroup = ''
  return createPortal(
    <div className="fixed inset-0 z-[90] backdrop flex justify-center pt-[13vh] px-4 animate-[enter_.12s_ease_both]" onMouseDown={onClose}>
      <div role="dialog" aria-modal="true" aria-label="Paleta de comandos" className="w-full max-w-[620px] h-fit modal overflow-hidden animate-pop glass" onMouseDown={e => e.stopPropagation()}>
        <div className="flex items-center gap-2.5 px-4 h-[52px] border-b border-line2">
          <Search size={17} className="text-accent" />
          <input autoFocus value={q} onChange={e => setQ(e.target.value)} placeholder="Buscar páginas, ações, canais, roteiros…"
            className="flex-1 bg-transparent outline-none text-[15px] placeholder:text-faint" aria-label="Buscar"
            role="combobox" aria-expanded aria-controls="cmdk-list" aria-activedescendant={`cmdk-${sel}`}
            onKeyDown={e => {
              if (e.key === 'ArrowDown') { e.preventDefault(); setSel(s => Math.min(s + 1, list.length - 1)) }
              if (e.key === 'ArrowUp') { e.preventDefault(); setSel(s => Math.max(s - 1, 0)) }
              if (e.key === 'Enter') { e.preventDefault(); run(list[sel]) }
              if (e.key === 'Escape') onClose()
            }} />
          <span className="kbd">Esc</span>
        </div>
        <div ref={listRef} id="cmdk-list" role="listbox" className="max-h-[56vh] overflow-y-auto p-1.5">
          {!list.length && <div className="text-center text-[13px] text-muted py-10">Nada encontrado para “{q}”.</div>}
          {list.map((c, i) => {
            const head = c.group !== lastGroup ? (lastGroup = c.group) : null
            return (
              <div key={c.id}>
                {head && <div className="px-2.5 pt-2.5 pb-1 text-[11px] uppercase tracking-wider text-faint">{head}</div>}
                <button id={`cmdk-${i}`} data-i={i} role="option" aria-selected={i === sel} onMouseMove={() => i !== sel && setSel(i)} onClick={() => run(c)}
                  className={clsx('w-full flex items-center gap-2.5 h-10 px-2.5 rounded-[9px] text-[13.5px] text-left transition-colors', i === sel ? 'bg-white/[0.07] text-text' : 'text-text/90')}>
                  <span className={clsx('w-7 h-7 rounded-[8px] grid place-items-center border shrink-0 transition-colors', i === sel ? 'border-accent/50 text-accent bg-accent/10' : 'border-line2 text-muted bg-panel2')}><c.icon size={14} /></span>
                  <span className="flex-1 truncate">{c.label}</span>
                  {c.hint && <span className="text-[12px] text-faint truncate max-w-[40%]">{c.hint}</span>}
                  {i === sel && <CornerDownLeft size={13} className="text-faint shrink-0" />}
                </button>
              </div>
            )
          })}
        </div>
        <div className="border-t border-line px-4 h-9 flex items-center gap-4 text-[11.5px] text-faint">
          <span><span className="kbd">↑</span> <span className="kbd">↓</span> navegar</span>
          <span><span className="kbd">Enter</span> abrir</span>
          <span className="ml-auto">{channel ? `Canal: ${channel.name}` : 'Sem canal'}</span>
        </div>
      </div>
    </div>, document.body)
}
