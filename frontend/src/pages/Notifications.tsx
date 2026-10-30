import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import clsx from 'clsx'
import {
  Bell, CheckCheck, Rocket, TrendingDown, AlertTriangle, Clapperboard, Send, MessageSquare, Trophy, Bot, Flame, Gauge, Info,
  ExternalLink, ListChecks, Smartphone, Check, X, type LucideIcon,
} from 'lucide-react'
import { api, invalidate, useApi, type Notification } from '../api'
import { act, ago, ChannelTag, Empty, PageHeader, Skeleton, Tabs } from '../ui'

type Item = Notification & { channel_id?: number | null; key?: string }
type Resp = { items: Item[]; unread: number }

const KINDS: Record<string, { label: string; icon: LucideIcon; tone: string }> = {
  breakout: { label: 'Estouro', icon: Rocket, tone: 'text-ok' },
  flop: { label: 'Abaixo do esperado', icon: TrendingDown, tone: 'text-bad' },
  failed: { label: 'Falha', icon: AlertTriangle, tone: 'text-bad' },
  review: { label: 'Revisar', icon: AlertTriangle, tone: 'text-warn' },
  ready: { label: 'Vídeo pronto', icon: Clapperboard, tone: 'text-info' },
  published: { label: 'Publicado', icon: Send, tone: 'text-ok' },
  comments: { label: 'Comentários', icon: MessageSquare, tone: 'text-info' },
  ypp: { label: 'Marco do YPP', icon: Trophy, tone: 'text-warn' },
  autopilot: { label: 'Piloto automático', icon: Bot, tone: 'text-accent' },
  trend: { label: 'Tendência', icon: Flame, tone: 'text-warn' },
  quota: { label: 'Cota', icon: Gauge, tone: 'text-warn' },
  checklist: { label: 'Checklist do Studio', icon: ListChecks, tone: 'text-info' },
  approval: { label: 'Aprovar', icon: Smartphone, tone: 'text-accent' },
}

/** Aprovação (mesmos botões do aviso no celular): "approval:<tipo>:<id>" → POST /publish2/approval/<tipo>/<id>/<ação>. */
function ApprovalButtons({ n }: { n: Item }) {
  const [, kind, id] = (n.key ?? '').split(':')
  const [done, setDone] = useState('')
  if (!kind || !id) return null
  if (done) return <div className="text-[12px] text-muted mt-1.5">{done}</div>
  const go = (action: 'approve' | 'reject') => act(() => api<{ message: string; already?: boolean }>(`/publish2/approval/${kind}/${id}/${action}`, { body: {} }))
    .then(r => { if (r) { setDone(r.message + (r.already ? ' (já estava decidido)' : '')); invalidate('/notifications') } })
  return (
    <div className="flex gap-2 mt-2" onClick={e => e.stopPropagation()}>
      <button className="btn btn-sm btn-primary" onClick={() => go('approve')}><Check size={13} /> Aprovar</button>
      <button className="btn btn-sm" onClick={() => go('reject')}><X size={13} /> Recusar</button>
    </div>
  )
}
const meta = (k: string) => KINDS[k] ?? { label: 'Aviso', icon: Info, tone: 'text-muted' }

const FILTERS = {
  all: '', unread: '', approval: 'approval', perf: 'breakout,flop,ypp', prod: 'ready,review,published,failed,quota,checklist',
  growth: 'autopilot,trend,comments',
} as const
type F = keyof typeof FILTERS

export default function Notifications() {
  const [f, setF] = useState<F>('all')
  const q = `/notifications?limit=200${f === 'unread' ? '&unread=true' : ''}${FILTERS[f] ? `&kind=${FILTERS[f]}` : ''}`
  const { data, isLoading } = useApi<Resp>(q)
  const nav = useNavigate()
  const read = (body: { ids?: (number | string)[]; all?: boolean }) =>
    api('/notifications/read', { body }).then(() => invalidate('/notifications'))
  const open = async (n: Item) => {
    if (!n.read) read({ ids: [n.id] })
    if (!n.link) return
    if (n.link.startsWith('http')) window.open(n.link, '_blank', 'noopener')
    else nav(n.link)
  }
  const items = data?.items ?? []
  return (
    <div>
      <PageHeader eyebrow="Início" title="Notificações"
        subtitle="Tudo o que o sistema fez ou percebeu: vídeos estourando ou fracassando, renders, publicações, comentários, cota de IA, marcos do YPP e ações do piloto automático."
        actions={<button className="btn btn-sm" disabled={!data?.unread} onClick={() => act(() => read({ all: true }), 'Tudo marcado como lido')}>
          <CheckCheck size={14} /> Marcar tudo como lido</button>} />
      <div className="mb-4">
        <Tabs value={f} onChange={setF} items={[
          { key: 'all', label: 'Todas' }, { key: 'unread', label: 'Não lidas', count: data?.unread }, { key: 'approval', label: 'Aprovar' },
          { key: 'perf', label: 'Desempenho' }, { key: 'prod', label: 'Produção' }, { key: 'growth', label: 'Crescimento' },
        ]} />
      </div>
      {isLoading ? <Skeleton className="h-72" /> : !items.length ? (
        <Empty icon={<Bell size={18} />} title="Nada por aqui" text="Quando algo acontecer nos canais, aparece aqui e no sino do topo." />
      ) : (
        <ul className="card divide-y divide-line overflow-hidden">
          {items.map(n => {
            const m = meta(n.kind)
            return (
              <li key={n.id}>
                <button onClick={() => open(n)} className={clsx('w-full text-left flex gap-3 px-4 py-3 hover:bg-white/[0.03] transition', !n.read && 'bg-white/[0.02]')}>
                  <div className={clsx('w-8 h-8 rounded-lg grid place-items-center border border-line2 bg-panel2 shrink-0', m.tone)}><m.icon size={15} /></div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={clsx('text-[13.5px] truncate', !n.read ? 'font-semibold' : 'text-muted')}>{n.title}</span>
                      {!n.read && <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)]" />}
                    </div>
                    {n.body && <div className="text-[12.5px] text-muted whitespace-pre-line line-clamp-3 mt-0.5">{n.body}</div>}
                    <div className="flex items-center gap-2 mt-1.5 text-[11.5px] text-faint">
                      <span>{m.label}</span><span>·</span><span>{ago(n.created_at)}</span>
                      {n.channel_id ? <ChannelTag id={n.channel_id} /> : null}
                      {n.link?.startsWith('http') && <ExternalLink size={11} />}
                    </div>
                  </div>
                </button>
                {n.kind === 'approval' && !n.read && <div className="pl-[60px] pb-3 -mt-1"><ApprovalButtons n={n} /></div>}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
