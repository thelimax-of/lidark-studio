import { useState, type ReactNode } from 'react'
import { CartesianGrid, Line, LineChart, ReferenceArea, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { AlertTriangle, ArrowUpRight } from 'lucide-react'
import { useApi } from '../api'
import { fmtNum, PageHeader, SectionTitle, seriesColor, Skeleton, Sparkline, useChannel } from '../ui'
import { FocusBadge, useFocus } from './FocusMode'
import { ChampionsCard } from './Champions'

type Period = { views: number; minutes: number; subs: number; likes: number; shares: number; engaged_views?: number }
type ChannelSum = {
  id: number; name: string; avatar_url: string; subscribers: number; total_views: number; videos: number; published_period: number
  views_per_video: number; avg_retention: number; engagement_rate: number; likes_total: number; comments_total: number
  engaged_views_total?: number; connected: boolean; error: string; period: Period
}
export type Overview = {
  days: number; channels: ChannelSum[]; errors: { channel_id: number; name: string; error: string }[]
  // estimated: dia que o Analytics ainda não liberou (~3 dias de atraso) — views/curtidas tiradas das leituras de cada vídeo
  daily: ({ day: string; views: number; minutes?: number; subs?: number; likes: number; engaged_views?: number; estimated?: boolean } & Record<string, number | string | boolean | undefined>)[]
  totals: Period & { subscribers: number; total_views: number; published_period: number; comments_total: number }
}

/** primeiro e último dia estimado (sem dados do Analytics ainda) */
export const estRange = (d: { day: string; estimated?: boolean }[]): [string, string] | null => {
  const e = d.filter(r => r.estimated)
  return e.length ? [e[0].day, e[e.length - 1].day] : null
}
export const dm = (v: string) => v.slice(8, 10) + '/' + v.slice(5, 7)
export const dayLabel = (d: { day: string; estimated?: boolean }[], v: any) =>
  new Date(v + 'T12:00').toLocaleDateString('pt-BR') + (d.find(r => r.day === v)?.estimated ? ' · estimado' : '')

const tip = { background: '#121816', border: '1px solid #24302b', borderRadius: 10, color: '#e9ece8' }

/** Visão geral de todos os canais: totais do período, views diárias por canal e comparação entre canais. */
export default function AllChannels({ scope, onOpen }: { scope: ReactNode; onOpen: (id: number) => void }) {
  const { channels } = useChannel()
  const [days, setDays] = useState(28)
  const { data, isLoading } = useApi<Overview>(`/overview?days=${days}`)
  const { data: focus } = useFocus()  // modo foco de cada canal + sugestão pelos dados
  const t = data?.totals
  const d = data?.daily ?? []
  const list = data?.channels ?? []
  // minutos/inscritos/engajadas só o Analytics tem: os dias estimados ficam fora dessas linhas
  const series = (k: 'views' | 'minutes' | 'subs' | 'likes' | 'engaged_views') =>
    d.filter(r => k === 'views' || k === 'likes' || !r.estimated).map(r => Number(r[k] ?? 0))
  const est = estRange(d)
  const noData = !!data && !d.some(r => r.views > 0)

  // melhor e pior canal em cada coluna (só entre canais com dados)
  const rank = (k: (c: ChannelSum) => number) => {
    const vals = list.map(k).filter(v => v > 0)
    return vals.length > 1 ? { best: Math.max(...vals), worst: Math.min(...vals) } : null
  }
  const cols: { label: string; get: (c: ChannelSum) => number; fmt: (v: number) => string; hint?: string }[] = [
    { label: 'Inscritos', get: c => c.subscribers ?? 0, fmt: fmtNum },
    { label: `Views (${days}d)`, get: c => c.period.views, fmt: fmtNum },
    ...(t?.engaged_views !== undefined ? [{ label: `Engajadas (${days}d)`, get: (c: ChannelSum) => c.period.engaged_views ?? 0, fmt: fmtNum }] : []),
    { label: `Inscritos (${days}d)`, get: c => c.period.subs, fmt: v => '+' + fmtNum(v) },
    { label: `Publicados (${days}d)`, get: c => c.published_period, fmt: String },
    { label: 'Views/vídeo', get: c => c.views_per_video, fmt: fmtNum, hint: 'Média de views por vídeo publicado' },
    { label: 'Retenção', get: c => c.avg_retention, fmt: v => v ? `${v.toFixed(0)}%` : '—', hint: '% médio assistido de cada vídeo' },
    { label: 'Engajamento', get: c => c.engagement_rate, fmt: v => `${v.toFixed(1)}%`, hint: '(curtidas + comentários + compart.) ÷ views' },
  ]
  const ranks = cols.map(c => rank(c.get))

  const kpis = [
    { label: 'Views', v: fmtNum(t?.views ?? 0), s: series('views'), sub: `${days} dias` },
    ...(t?.engaged_views !== undefined ? [{ label: 'Views engajadas', v: fmtNum(t.engaged_views), s: series('engaged_views'), sub: `${days} dias` }] : []),
    { label: 'Horas assistidas', v: fmtNum(Math.round((t?.minutes ?? 0) / 60)), s: series('minutes'), sub: `${days} dias` },
    { label: 'Inscritos ganhos', v: '+' + fmtNum(t?.subs ?? 0), s: series('subs'), sub: `${fmtNum(t?.subscribers ?? 0)} no total` },
    { label: 'Curtidas', v: fmtNum(t?.likes ?? 0), s: series('likes'), sub: `${days} dias` },
    { label: 'Comentários', v: fmtNum(t?.comments_total ?? 0), s: [], sub: 'somando todos os vídeos' },
    { label: 'Vídeos publicados', v: String(t?.published_period ?? 0), s: [], sub: `${days} dias` },
  ]

  return (
    <div className="space-y-5">
      <PageHeader title="Visão geral" subtitle={<>
        Todos os canais · <span className="num">{list.length || channels.length}</span> canais · <span className="num">{fmtNum(t?.subscribers ?? 0)}</span> inscritos · <span className="num">{fmtNum(t?.total_views ?? 0)}</span> views no total
      </>} actions={<>
        {scope}
        <div className="seg">{[7, 28, 90].map(n => <button key={n} onClick={() => setDays(n)} data-active={days === n}>{n} dias</button>)}</div>
      </>} />

      {!!data?.errors.length && (
        <div className="card px-4 py-3 flex items-start gap-3 text-[13px] border-warn/40!">
          <AlertTriangle size={16} className="text-warn shrink-0 mt-px" />
          <div>Não foi possível ler o YouTube Analytics de {data.errors.map(e => e.name).join(', ')} — os totais mostram só os outros canais.
            <div className="text-muted text-[12px] mt-0.5 break-words">{data.errors.map(e => `${e.name}: ${e.error}`).join(' · ')}</div></div>
        </div>
      )}

      {/* indicadores somando os canais */}
      <section className="card grid grid-cols-2 md:grid-cols-4 xl:grid-cols-7 divide-x divide-line overflow-hidden">
        {kpis.map(k => (
          <div key={k.label} className="p-4 border-b border-line xl:border-b-0">
            <div className="text-[12.5px] text-muted truncate">{k.label}</div>
            <div className="text-[24px] leading-none font-semibold mt-2.5 num tracking-tight">{data ? k.v : '—'}</div>
            <div className="text-[11.5px] text-faint mt-1.5 truncate">{k.sub}</div>
            <Sparkline data={k.s} height={24} className="mt-2" />
          </div>
        ))}
      </section>

      {/* Shorts campeões → vídeos longos (horas assistidas para o YPP) */}
      <ChampionsCard />

      {/* views diárias por canal */}
      <section className="card overflow-hidden">
        <SectionTitle hint={`Uma linha por canal${est ? ` · a faixa clara (desde ${dm(est[0])}) é estimada pelas nossas leituras, até o YouTube Analytics liberar` : ' · o YouTube libera os dados com 2 a 3 dias de atraso'}`}>Views por dia</SectionTitle>
        <div className="p-4">
          {isLoading ? <Skeleton className="h-64" /> : noData ? (
            <div className="h-40 grid place-items-center text-[13px] text-muted text-center px-6">
              Ainda sem views no período. Canais novos levam alguns dias até o YouTube Analytics liberar os primeiros números.</div>
          ) : (
            <>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={d} margin={{ left: -10, right: 8, top: 4 }}>
                    <CartesianGrid stroke="#1d232d" vertical={false} />
                    <XAxis dataKey="day" tick={{ fill: '#8a9690', fontSize: 11 }} tickFormatter={v => v.slice(8, 10) + '/' + v.slice(5, 7)} axisLine={false} tickLine={false} minTickGap={24} />
                    <YAxis tick={{ fill: '#8a9690', fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                    {est && <ReferenceArea x1={est[0]} x2={est[1]} fill="#d9a53a" fillOpacity={0.07} stroke="none" ifOverflow="extendDomain" />}
                    <Tooltip contentStyle={tip} labelFormatter={v => dayLabel(d, v)}
                      formatter={(v: any, k: any) => [fmtNum(Number(v)), list.find(c => `c${c.id}` === k)?.name ?? k]} />
                    {list.map(c => <Line key={c.id} type="monotone" dataKey={`c${c.id}`} stroke={seriesColor(channels, c.id)} strokeWidth={2} dot={false}
                      isAnimationActive={false} activeDot={{ r: 4, stroke: '#121816', strokeWidth: 2 }} />)}
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-[12px] text-muted">
                {list.map(c => <span key={c.id} className="inline-flex items-center gap-1.5"><span className="w-2.5 h-0.5 rounded-full" style={{ background: seriesColor(channels, c.id) }} />
                  {c.name} <span className="num text-text/80">{fmtNum(c.period.views)}</span></span>)}
              </div>
            </>
          )}
        </div>
      </section>

      {/* comparação entre canais */}
      <section className="card overflow-hidden">
        <SectionTitle hint="Verde = melhor canal na coluna · vermelho = pior (entre os canais com dados)">Comparação entre canais</SectionTitle>
        {isLoading ? <div className="p-4"><Skeleton className="h-32" /></div> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-[12px] text-muted border-b border-line">
                <tr><th className="text-left px-4 py-2 font-medium">Canal</th>
                  <th className="text-left px-3 py-2 font-medium" title="Modo foco atual · passe o mouse para ver o porquê da sugestão">Modo</th>
                  {cols.map(c => <th key={c.label} title={c.hint} className="text-right px-3 py-2 font-medium whitespace-nowrap">{c.label}</th>)}
                  <th className="w-10" /></tr>
              </thead>
              <tbody className="divide-y divide-line">
                {list.map(ch => (
                  <tr key={ch.id} className="hover:bg-white/[0.02]">
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-2.5 min-w-44">
                        {ch.avatar_url ? <img src={ch.avatar_url} referrerPolicy="no-referrer" className="w-7 h-7 rounded-full shrink-0" alt="" /> : <div className="w-7 h-7 rounded-full bg-panel2 shrink-0" />}
                        <div className="min-w-0">
                          <div className="font-medium truncate flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: seriesColor(channels, ch.id) }} />{ch.name}</div>
                          <div className="text-[11.5px] text-muted">{ch.error ? <span className="text-warn">Analytics com erro</span> : !ch.connected ? 'Não conectado' : `${ch.videos} vídeos`}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-3"><FocusBadge info={focus?.channels.find(f => f.channel_id === ch.id)} /></td>
                    {cols.map((c, k) => {
                      const v = c.get(ch), r = ranks[k]
                      const tone = r && v > 0 ? (v === r.best ? 'text-ok font-medium' : v === r.worst ? 'text-bad' : '') : ''
                      return <td key={c.label} className={`text-right px-3 tabular-nums ${tone}`}>{c.fmt(v)}</td>
                    })}
                    <td className="pr-3 text-right">
                      <button className="btn btn-sm btn-icon btn-ghost" title={`Abrir ${ch.name}`} onClick={() => onOpen(ch.id)}><ArrowUpRight size={14} /></button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!list.length && <div className="p-8 text-center text-sm text-muted">Nenhum canal ainda.</div>}
          </div>
        )}
      </section>
    </div>
  )
}
