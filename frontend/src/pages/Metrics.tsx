import { useEffect, useMemo, useState } from 'react'
import { Area, AreaChart, CartesianGrid, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { BarChart3, Sparkles, ExternalLink, ArrowUpDown, RefreshCw, Film, Activity } from 'lucide-react'
import { api, invalidate, onJob, useApi, type Job } from '../api'
import { act, ChannelScope, ChannelTag, Empty, fmtNum, PageHeader, SectionTitle, Skeleton, toast, useChannel, useScope } from '../ui'
import { Bar, ChartDefs, ChartTip, RowsSkeleton, StatTile, chart, useProgressive } from './kit'
import { ExperimentsCard, YppCard } from './Growth'
import { dayLabel, dm, estRange, type Overview } from './Overview'
import { ChampionsCard, toLong } from './Champions'

type Row = {
  video_id: string | number; title: string; views: number; likes: number; comments: number; shares: number
  retention: number; engagement: number; perf: number; avg_duration?: number; watch_minutes?: number
  url?: string; thumbnail?: string; published_at?: string; duration?: number; channel_id?: number; engaged_views?: number
}

export default function Metrics() {
  const { channel } = useChannel()
  const [all, setAll] = useScope('metrics', false)
  const cid = all ? undefined : channel?.id
  const [days, setDays] = useState(28)
  const [sort, setSort] = useState<keyof Row>('perf')
  const [syncJob, setSyncJob] = useState<number | null>(null)
  useEffect(() => onJob(j => {
    if (j.id !== syncJob || !['done', 'failed', 'cancelled'].includes(j.status)) return
    setSyncJob(null)
    invalidate('/channels')
    if (j.status === 'done') toast.ok('Métricas sincronizadas')
    else if (j.status === 'failed') toast.err(`Falha ao sincronizar: ${j.error || 'erro desconhecido'}`)
  }), [syncJob])
  const sync = async () => {
    const j = await act(() => api<Job>(`/channels/${cid}/metrics/sync`, { body: {} }), 'Sincronizando com o YouTube…')
    if (j) setSyncJob(j.id)
  }
  const { data: rows = [], isLoading: rowsLoading } = useApi<Row[]>(all ? '/performance' : cid ? `/channels/${cid}/performance` : null)
  const { data: one } = useApi<{ rows: { day: string; views: number; minutes?: number; subs?: number; likes: number; engaged_views?: number; estimated?: boolean }[]; connected: boolean; error?: string }>(cid ? `/channels/${cid}/analytics?days=${days}` : null)
  const { data: ov } = useApi<Overview>(all ? `/overview?days=${days}` : null)
  // "Todos os canais": a série diária já vem somada pelo backend
  const daily = all ? (ov && { rows: ov.daily, connected: true, error: ov.errors.map(e => `${e.name}: ${e.error}`).join(' · ') || undefined }) : one
  const { data: insights = [] } = useApi<{ text: string; kind?: string }[]>(cid ? `/channels/${cid}/insights` : null)
  const sorted = useMemo(() => [...rows].sort((a, b) => Number(b[sort] ?? 0) - Number(a[sort] ?? 0)), [rows, sort])
  const [shownRows, moreRows] = useProgressive(sorted, 50, sort + String(cid))
  const d = daily?.rows ?? []
  const sum = (k: 'views' | 'minutes' | 'subs' | 'likes' | 'engaged_views') => d.reduce((n, r) => n + (r[k] ?? 0), 0)
  const engaged = d.some(r => r.engaged_views !== undefined)
  const est = estRange(d)
  const upTo = est ? ` · até ${dm(d.filter(r => !r.estimated).at(-1)?.day ?? est[0])}` : ''  // só o Analytics tem esses números
  const subs = all ? (ov?.totals.subscribers ?? 0) : (channel?.stats?.subscribers ?? 0)
  const totalViews = all ? (ov?.totals.total_views ?? 0) : (channel?.stats?.views ?? 0)
  const ret = rows.filter(r => r.retention > 0)
  const avgRet = ret.length ? ret.reduce((n, r) => n + r.retention, 0) / ret.length : 0

  if (!channel) return null
  if (!all && !channel.connected && !rows.length)
    return <><PageHeader title="Métricas" /><Empty icon={<BarChart3 size={36} />} title="Conecte o canal ao YouTube" text="Em Canais, conecte este canal para puxar views, retenção e inscritos." /></>

  return (
    <>
      <PageHeader title="Métricas" subtitle={`${all ? 'Todos os canais' : channel.name} · dados do YouTube Analytics (atualizados a cada 3 h)`}
        actions={<div className="flex flex-wrap items-center gap-2">
          <ChannelScope all={all} onChange={setAll} />
          {!all && channel.connected && <button className="btn" onClick={sync} disabled={syncJob !== null}>
            <RefreshCw size={15} className={syncJob !== null ? 'animate-spin' : ''} /> {syncJob !== null ? 'Sincronizando…' : 'Sincronizar'}</button>}
          <div className="seg">
            {[7, 28, 90].map(n => <button key={n} onClick={() => setDays(n)} data-active={days === n}>{n} dias</button>)}
          </div>
        </div>} />

      <div className={`grid grid-cols-2 md:grid-cols-3 gap-3 mb-5 ${engaged ? 'xl:grid-cols-6' : 'xl:grid-cols-5'}`}>
        <StatTile label="Inscritos" value={fmtNum(subs)} sub={`+${fmtNum(sum('subs'))} em ${days} dias${upTo}`} loading={!daily} tone="accent" />
        <StatTile label={`Views (${days} dias)`} value={fmtNum(sum('views'))} sub={`${fmtNum(totalViews)} no total`} loading={!daily} spark={d.map(r => r.views)} />
        {engaged && <StatTile label="Views engajadas" value={fmtNum(sum('engaged_views'))} sub={`${days} dias${upTo}`} spark={d.filter(r => !r.estimated).map(r => r.engaged_views ?? 0)} />}
        <StatTile label="Horas assistidas" value={fmtNum(Math.round(sum('minutes') / 60))} sub={`${days} dias${upTo}`} loading={!daily} spark={d.filter(r => !r.estimated).map(r => r.minutes ?? 0)} />
        <StatTile label="Retenção média" value={`${avgRet.toFixed(0)}%`} sub="dos vídeos assistidos" loading={rowsLoading && !rows.length}
          tone={avgRet >= 60 ? 'ok' : avgRet > 0 && avgRet < 35 ? 'warn' : undefined} />
        <StatTile label="Curtidas" value={fmtNum(sum('likes'))} sub={`${days} dias`} loading={!daily} spark={d.map(r => r.likes)} />
      </div>

      <section className="card overflow-hidden mb-5">
        <SectionTitle hint={daily?.error ? `Analytics indisponível: ${daily.error}` : est ? `A faixa destacada (desde ${dm(est[0])}) é estimada pelas nossas leituras de cada vídeo, até o YouTube Analytics liberar (~3 dias)` : 'O YouTube libera os dados com ~3 dias de atraso'}>
          Views por dia{all && <span className="text-muted font-normal"> · soma dos canais</span>}
        </SectionTitle>
        <div className="p-4 h-72">
          {!daily ? <Skeleton className="h-full" /> : !d.some(r => r.views > 0) ? (
            <div className="h-full grid place-items-center text-[13px] text-muted text-center px-6">Ainda sem views no período.</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={d} margin={{ left: -10, right: 8, top: 8 }}>
                <ChartDefs id="mv" />
                <CartesianGrid {...chart.grid} />
                <XAxis dataKey="day" {...chart.axis} tickFormatter={dm} minTickGap={24} />
                <YAxis {...chart.axis} allowDecimals={false} tickFormatter={v => fmtNum(Number(v))} width={52} />
                <Tooltip cursor={chart.cursor} content={<ChartTip fmtLabel={v => dayLabel(d, v)} rows={p => [{ name: 'views', value: fmtNum(Number(p[0].value)), color: 'var(--accent)' }]} />} />
                {est && <ReferenceArea x1={est[0]} x2={est[1]} {...chart.est} ifOverflow="extendDomain"
                  label={{ value: 'estimado', position: 'insideTopRight', fill: 'var(--faint)', fontSize: 10.5 }} />}
                <Area type="monotone" dataKey="views" stroke="url(#mv-line)" strokeWidth={2.25} fill="url(#mv)" isAnimationActive={false} activeDot={{ ...chart.dot, fill: 'var(--accent)' }} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </section>

      {!all && <div className="space-y-5 mb-5"><YppCard channelId={channel.id} /><ExperimentsCard channelId={channel.id} /></div>}

      {cid && <RetentionCard cid={cid} />}

      <div className="mb-5"><ChampionsCard channelId={cid} /></div>

      <div className={`grid gap-6 items-start ${all ? '' : 'xl:grid-cols-[1fr_340px]'}`}>
        <section className="card overflow-hidden min-w-0">
          <SectionTitle hint={all ? `${rows.length} vídeos de todos os canais · a nota de desempenho é relativa a cada canal` : `${rows.length} vídeo(s) publicado(s)`}
            action={<div className="flex items-center gap-2 text-xs text-muted"><ArrowUpDown size={13} />
              <select className="input !w-auto !h-7 text-xs" value={sort} onChange={e => setSort(e.target.value as keyof Row)} aria-label="Ordenar por">
                <option value="perf">Nota de desempenho</option><option value="views">Views</option><option value="retention">Retenção</option>
                <option value="likes">Curtidas</option><option value="engagement">Engajamento</option>
              </select></div>}>
            Desempenho por vídeo
          </SectionTitle>
          {rowsLoading && !rows.length ? <RowsSkeleton rows={5} h="h-12" /> : (
            <div className="overflow-x-auto">
              <table className="tbl">
                <thead>
                  <tr><th>Vídeo</th><th className="right">Views</th><th className="right">Curtidas</th>
                    <th className="right">Coment.</th><th className="right">Retenção</th><th className="right">Engaj.</th><th className="w-40">Desempenho</th></tr>
                </thead>
                <tbody>
                  {shownRows.map(r => (
                    <tr key={String(r.video_id)} className="group">
                      <td>
                        <div className="flex items-center gap-3 min-w-64">
                          {r.thumbnail ? <img src={r.thumbnail} referrerPolicy="no-referrer" loading="lazy" className="w-16 h-10 rounded-md object-cover bg-black border border-line shrink-0" alt="" />
                            : <div className="w-16 h-10 rounded-md bg-panel2 border border-line shrink-0" />}
                          <div className="min-w-0">
                            <div className="truncate max-w-80 font-medium">{r.title.replace(/#Shorts/i, '').trim()}</div>
                            <div className="text-xs text-muted flex items-center gap-1.5">{all && r.channel_id != null && <ChannelTag id={r.channel_id} />}{r.published_at ? new Date(r.published_at).toLocaleDateString('pt-BR') : ''}{r.duration ? ` · ${Math.round(r.duration)}s` : ''}</div>
                          </div>
                          <div className="ml-auto flex items-center gap-0.5 shrink-0 opacity-60 group-hover:opacity-100 transition-opacity">
                            {r.url?.includes('/shorts/') && (r.channel_id ?? cid) != null && <button className="btn btn-sm btn-icon btn-ghost" data-tip="Transformar em vídeo longo"
                              onClick={() => toLong((r.channel_id ?? cid)!, String(r.video_id), r.title.replace(/#Shorts/i, '').trim())}><Film size={14} /></button>}
                            {r.url && <a href={r.url} target="_blank" rel="noreferrer" className="btn btn-sm btn-icon btn-ghost" data-tip="Abrir no YouTube"><ExternalLink size={14} /></a>}
                          </div>
                        </div>
                      </td>
                      <td className="right">{fmtNum(r.views)}</td>
                      <td className="right">{fmtNum(r.likes)}</td>
                      <td className="right">{r.comments}</td>
                      <td className="right">{r.retention ? `${r.retention.toFixed(0)}%` : '—'}</td>
                      <td className="right">{r.engagement.toFixed(1)}%</td>
                      <td>
                        <div className="flex items-center gap-2">
                          <Bar value={r.perf} className="flex-1" />
                          <span className="text-xs w-7 text-right num">{r.perf}</span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {moreRows}
              {!rows.length && <div className="p-8 text-center text-sm text-muted">Nenhum vídeo publicado ainda.</div>}
            </div>
          )}
        </section>

        {!all && <section className="card overflow-hidden xl:sticky xl:top-4">
          <SectionTitle action={<button className="btn btn-sm" onClick={() => act(() => api(`/channels/${cid}/insights`, { body: {} }), 'Aprendizados atualizados').then(() => invalidate(`/channels/${cid}/insights`))}>
            <Sparkles size={13} /> Atualizar</button>}>
            <span className="inline-flex items-center gap-2"><Sparkles size={14} className="text-accent" />O que o sistema aprendeu</span>
          </SectionTitle>
          <ul className="p-4 space-y-3 text-sm text-text/85">
            {insights.map((i, k) => <li key={k} className="flex gap-2.5"><span className={`w-1.5 h-1.5 rounded-full mt-2 shrink-0 ${i.kind === 'retention' ? 'bg-accent2' : 'bg-line3'}`} />
              <span>{i.kind === 'retention' && <span className="badge badge-accent mr-1.5 !h-5 text-[11px]">retenção</span>}{i.text}</span></li>)}
            {!insights.length && <li className="text-sm text-muted">Com 3+ vídeos publicados, a IA encontra padrões do que funciona e usa isso nas notas das pautas.</li>}
          </ul>
        </section>}
      </div>
    </>
  )
}

type Ret = { publication_id: number; title: string; duration: number; views: number; curve: number[][]; hook?: number; mid?: number; end?: number
  scenes: { start: number; end: number; text: string }[]; worst_scenes?: { scene: number; text: string; drop_per_10s: number }[] }

function RetentionCard({ cid }: { cid: number }) {
  const { data = [] } = useApi<Ret[]>(`/channels/${cid}/retention`)
  const [sel, setSel] = useState<number | null>(null)
  const { data: rules } = useApi<{ rules: string[]; status?: string; videos: number }>(`/channels/${cid}/retention/rules`)
  const r = data.find(x => x.publication_id === sel) ?? data[0]
  if (!data.length) return (
    <div className="card p-5 mb-5 text-sm text-muted flex gap-3">
      <Activity size={18} className="text-faint shrink-0 mt-0.5" />
      <div>
        <div className="text-sm font-semibold text-text mb-1">Retenção segundo a segundo</div>
        O YouTube libera a curva de retenção depois que o vídeo acumula algumas dezenas de visualizações. Assim que houver dados, eles aparecem aqui e viram lições para o roteirista.
      </div>
    </div>
  )
  const start = r.curve[0]?.[1] || 1
  const pts = r.curve.map(([x, y]) => ({ t: Math.round(x * r.duration * 10) / 10, v: Math.round((y / start) * 1000) / 10 }))
  return (
    <div className="card p-5 mb-5">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-1">
        <div>
          <div className="text-sm font-semibold">Retenção segundo a segundo</div>
          <div className="text-xs text-muted">% do público que ainda está assistindo em cada momento · linhas tracejadas = início de cada cena</div>
        </div>
        <select className="input !w-auto text-sm max-w-96" value={r.publication_id} onChange={e => setSel(Number(e.target.value))}>
          {data.map(x => <option key={x.publication_id} value={x.publication_id}>{x.title.replace(/#Shorts/i, '')}</option>)}
        </select>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 my-4">
        {([['Gancho (3s)', r.hook], ['Meio', r.mid], ['Final', r.end]] as [string, number | undefined][]).map(([l, val]) => (
          <div key={l} className="surface-2 px-3 py-2">
            <div className="text-[11.5px] text-muted">{l}</div>
            <div className={`text-[18px] font-semibold num ${val == null ? 'text-faint' : val >= 70 ? 'text-ok' : val < 40 ? 'text-warn' : ''}`}>{val ?? '—'}{val != null && '%'}</div>
          </div>
        ))}
        {r.worst_scenes?.[0] ? (
          <div className="px-3 py-2 rounded-[var(--r-md)] border border-warn/30 bg-warn/[0.06]">
            <div className="text-[11.5px] text-warn">Maior queda</div>
            <div className="text-[13px] font-medium mt-0.5">cena {r.worst_scenes[0].scene} <span className="text-muted num">−{r.worst_scenes[0].drop_per_10s}%/10s</span></div>
          </div>
        ) : <div />}
      </div>
      <div className="h-60">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={pts} margin={{ left: -10, right: 8, top: 4 }}>
            <ChartDefs id="rt" color="var(--accent-2)" to="var(--accent)" />
            <CartesianGrid {...chart.grid} />
            <XAxis dataKey="t" type="number" domain={[0, Math.ceil(r.duration)]} {...chart.axis} tickFormatter={v => `${Math.round(v)}s`} />
            <YAxis {...chart.axis} unit="%" domain={[0, 'auto']} />
            {r.scenes.slice(1).map((sc, k) => <ReferenceLine key={k} x={Math.round(sc.start * 10) / 10} stroke="var(--line-2)" strokeDasharray="3 4" />)}
            <Tooltip cursor={chart.cursor} content={<ChartTip fmtLabel={v => `${v}s`} rows={p => [{ name: 'assistindo', value: `${p[0].value}%`, color: 'var(--accent-2)' }]} />} />
            <Area type="monotone" dataKey="v" stroke="url(#rt-line)" strokeWidth={2.25} fill="url(#rt)" isAnimationActive={false} activeDot={{ ...chart.dot, fill: 'var(--accent-2)' }} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-4 pt-4 border-t border-line">
        <div className="text-sm font-semibold">Regras automáticas para o roteirista</div>
        <div className="text-xs text-muted mb-2">Calculadas das quedas por cena (tipo de visual, posição, tamanho) — entram no prompt junto com as lições da IA</div>
        {rules?.rules?.length
          ? <ul className="space-y-1.5 text-sm text-text/85">{rules.rules.map((t, k) => <li key={k} className="flex gap-2.5"><span className="w-1.5 h-1.5 rounded-full bg-accent2 mt-2 shrink-0" /><span>{t}</span></li>)}</ul>
          : <p className="text-sm text-muted">{rules?.status || 'Ainda sem dados suficientes.'}</p>}
      </div>
    </div>
  )
}
