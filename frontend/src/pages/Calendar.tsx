// Calendário de efemérides: datas dos próximos dias por nicho (aniversários redondos, astronomia, lançamentos,
// futebol, ENEM), cada uma a um clique de virar pauta. Nenhuma data é inventada: cada evento mostra a fonte e a confiança.
import { useMemo, useState } from 'react'
import clsx from 'clsx'
import { CalendarDays, ExternalLink, Plus, Check, Moon, Rocket, Trophy, GraduationCap, Landmark } from 'lucide-react'
import { api, invalidate, useApi } from '../api'
import { act, Empty, PageHeader, SectionTitle, Skeleton, useChannel } from '../ui'
import { Callout } from './kit'

type Ev = { id: string; date: string; kind: string; niche?: string; title: string; detail: string; year?: number; age?: number
  confidence: string; source: string; url: string; weight: number; days_ahead: number; idea_created: boolean }
type Cal = { channel_id: number; niches: string[]; start: string; end: string; events: Ev[]; sources: string[] }

const KIND: Record<string, { label: string; icon: typeof Moon }> = {
  'aniversário': { label: 'Aniversário', icon: Landmark }, futebol: { label: 'Futebol', icon: Trophy },
  astronomia: { label: 'Astronomia', icon: Moon }, 'lançamento': { label: 'Lançamento', icon: Rocket },
  enem: { label: 'ENEM', icon: GraduationCap },
}
const NICHE: Record<string, string> = { historia: 'História', espaco: 'Espaço', futebol: 'Futebol', ciencia: 'Ciência' }
const CONF_TONE = (c: string) => c.startsWith('calculado') || c.startsWith('oficial') ? 'badge-ok' : c.startsWith('fonte') ? 'badge-accent'
  : c === 'programado' || c === 'média' ? 'badge-warn' : 'badge'
const fmtDay = (iso: string) => new Date(iso + 'T12:00').toLocaleDateString('pt-BR', { weekday: 'short', day: '2-digit', month: 'short' })

export default function Calendar() {
  const { channel } = useChannel()
  const cid = channel?.id
  const [days, setDays] = useState(60)
  const [kind, setKind] = useState<string>('')
  const [top, setTop] = useState(false)
  const { data, isLoading } = useApi<Cal>(cid ? `/learning/almanac?channel_id=${cid}&days=${days}` : null)
  const events = useMemo(() => (data?.events ?? []).filter(e => (!kind || e.kind === kind) && (!top || e.weight >= 3)), [data, kind, top])
  const byMonth = useMemo(() => {
    const m = new Map<string, Ev[]>()
    for (const e of events) {
      const k = new Date(e.date + 'T12:00').toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })
      m.set(k, [...(m.get(k) ?? []), e])
    }
    return [...m.entries()]
  }, [events])
  const kinds = useMemo(() => [...new Set((data?.events ?? []).map(e => e.kind))], [data])
  const toIdea = (e: Ev) => cid && act(() => api('/learning/almanac/idea', { body: { channel_id: cid, event_id: e.id } }),
    'Pauta criada (origem: almanaque) — a IA dá nota e checa os fatos').then(() => { invalidate('/learning/almanac'); invalidate('/ideas') })

  if (!channel) return null
  return (
    <div>
      <PageHeader eyebrow="Crescer" title={<span className="inline-flex items-center gap-2"><CalendarDays size={20} />Calendário de efemérides</span>}
        subtitle={`Datas que vêm por aí (a partir de 7 dias) para ${channel.name}${data ? ` · nichos: ${data.niches.map(n => NICHE[n] ?? n).join(', ')}` : ''} — publique alguns dias antes. Cada data mostra de onde veio e quão confiável é.`}
        actions={<div className="seg">{[30, 60, 90].map(n => <button key={n} data-active={days === n} onClick={() => setDays(n)}>{n} dias</button>)}</div>} />
      <Callout tone="info" className="mb-4">
        Nada aqui é inventado: aniversários vêm do “Neste dia” da Wikipédia, astronomia é calculada (luas, estações, eclipses — algoritmos de Meeus),
        chuvas de meteoros seguem a IMO, lançamentos vêm da Launch Library 2 (mudam com frequência) e o ENEM vem do edital do Inep.
        A pauta criada ainda passa pela checagem de fatos antes de virar roteiro.
      </Callout>
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <div className="seg">
          <button data-active={!kind} onClick={() => setKind('')}>Tudo ({data?.events.length ?? 0})</button>
          {kinds.map(k => <button key={k} data-active={kind === k} onClick={() => setKind(k)}>{KIND[k]?.label ?? k}</button>)}
        </div>
        <label className="text-[12.5px] text-muted inline-flex items-center gap-1.5 ml-2"><input type="checkbox" checked={top} onChange={e => setTop(e.target.checked)} />só as mais fortes</label>
      </div>
      {isLoading ? <Skeleton className="h-96" /> : !events.length ? (
        <Empty icon={<CalendarDays size={20} />} title="Nenhuma efeméride no período" text="Aumente o período ou troque o filtro. Na primeira vez, as datas da Wikipédia levam alguns segundos para carregar." />
      ) : (
        <div className="space-y-4">
          {byMonth.map(([month, evs]) => (
            <section key={month} className="card overflow-hidden">
              <SectionTitle>{month[0].toUpperCase() + month.slice(1)}</SectionTitle>
              <ul className="divide-y divide-line">
                {evs.map(e => {
                  const K = KIND[e.kind] ?? KIND['aniversário']
                  return (
                    <li key={e.id} className="flex items-start gap-3 px-4 py-3">
                      <div className="w-20 shrink-0 text-center">
                        <div className="text-[12px] text-muted capitalize">{fmtDay(e.date)}</div>
                        <div className="text-[11px] text-faint">em {e.days_ahead} dias</div>
                      </div>
                      <span className={clsx('w-8 h-8 rounded-[9px] grid place-items-center shrink-0 border border-line2 bg-panel2', e.weight >= 3 ? 'text-warn' : 'text-muted')}><K.icon size={15} /></span>
                      <div className="min-w-0 flex-1">
                        <div className="text-[13px] font-medium">{e.title}</div>
                        <div className="text-[11.5px] text-muted mt-0.5">{e.detail}</div>
                        <div className="flex flex-wrap items-center gap-1.5 mt-1.5 text-[11px]">
                          <span className={clsx('badge !h-5', CONF_TONE(e.confidence))}>{e.confidence}</span>
                          <span className="text-faint">{e.source}</span>
                          {e.weight >= 3 && <span className="badge badge-warn !h-5">forte</span>}
                        </div>
                      </div>
                      <div className="flex gap-1 shrink-0">
                        {e.url && <a href={e.url} target="_blank" rel="noreferrer" className="btn btn-sm btn-icon btn-ghost" data-tip="Fonte"><ExternalLink size={14} /></a>}
                        {e.idea_created
                          ? <span className="btn btn-sm btn-ghost text-ok pointer-events-none"><Check size={14} /> Pauta criada</span>
                          : <button className="btn btn-sm" onClick={() => toIdea(e)} data-tip="Cria a pauta (origem almanaque); a IA dá nota e checa os fatos"><Plus size={14} /> Pauta</button>}
                      </div>
                    </li>
                  )
                })}
              </ul>
            </section>
          ))}
          <div className="text-[11.5px] text-faint">Fontes: {data?.sources.join(' · ')}</div>
        </div>
      )}
    </div>
  )
}
