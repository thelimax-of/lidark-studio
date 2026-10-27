import { useEffect, useMemo, useState } from 'react'
import { Area, AreaChart, CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { BarChart3, Sparkles, ExternalLink, ArrowUpDown, RefreshCw } from 'lucide-react'
import { api, invalidate, onJob, useApi, type Job } from '../api'
import { act, Empty, fmtNum, PageHeader, toast, useChannel } from '../ui'
import { ExperimentsCard, YppCard } from './Growth'

type Row = {
  video_id: string | number; title: string; views: number; likes: number; comments: number; shares: number
  retention: number; engagement: number; perf: number; avg_duration?: number; watch_minutes?: number
  url?: string; thumbnail?: string; published_at?: string; duration?: number
}
const GOLD = '#d9a53a'

export default function Metrics() {
  const { channel } = useChannel()
  const cid = channel?.id
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
  const { data: rows = [] } = useApi<Row[]>(cid ? `/channels/${cid}/performance` : null)
  const { data: daily } = useApi<{ rows: { day: string; views: number; minutes: number; subs: number; likes: number }[]; connected: boolean; error?: string }>(cid ? `/channels/${cid}/analytics?days=${days}` : null)
  const { data: insights = [] } = useApi<{ text: string; kind?: string }[]>(cid ? `/channels/${cid}/insights` : null)
  const sorted = useMemo(() => [...rows].sort((a, b) => Number(b[sort] ?? 0) - Number(a[sort] ?? 0)), [rows, sort])
  const d = daily?.rows ?? []
  const sum = (k: 'views' | 'minutes' | 'subs' | 'likes') => d.reduce((n, r) => n + (r[k] ?? 0), 0)
  const ret = rows.filter(r => r.retention > 0)
  const avgRet = ret.length ? ret.reduce((n, r) => n + r.retention, 0) / ret.length : 0

  if (!channel) return null
  if (!channel.connected && !rows.length)
    return <><PageHeader title="Métricas" /><Empty icon={<BarChart3 size={36} />} title="Conecte o canal ao YouTube" text="Em Canais, conecte este canal para puxar views, retenção e inscritos." /></>

  return (
    <>
      <PageHeader title="Métricas" subtitle={`${channel.name} · dados do YouTube Analytics (atualizados a cada 6 h)`}
        actions={<div className="flex items-center gap-2">
          {channel.connected && <button className="btn" onClick={sync} disabled={syncJob !== null}>
            <RefreshCw size={15} className={syncJob !== null ? 'animate-spin' : ''} /> {syncJob !== null ? 'Sincronizando…' : 'Sincronizar'}</button>}
          <div className="seg">
            {[7, 28, 90].map(n => <button key={n} onClick={() => setDays(n)} data-active={days === n}>{n} dias</button>)}
          </div>
        </div>} />

      <div className="space-y-5 mb-6"><YppCard channelId={channel.id} /><ExperimentsCard channelId={channel.id} /></div>

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
        <Tile label="Inscritos" v={fmtNum(channel.stats?.subscribers ?? 0)} sub={`+${fmtNum(sum('subs'))} em ${days} dias`} />
        <Tile label={`Views (${days} dias)`} v={fmtNum(sum('views'))} sub={`${fmtNum(channel.stats?.views ?? 0)} no total`} />
        <Tile label="Horas assistidas" v={fmtNum(Math.round(sum('minutes') / 60))} sub={`${days} dias`} />
        <Tile label="Retenção média" v={`${avgRet.toFixed(0)}%`} sub="dos vídeos assistidos" />
        <Tile label="Curtidas" v={fmtNum(sum('likes'))} sub={`${days} dias`} />
      </div>

      <div className="card p-5 mb-6">
        <div className="text-sm font-semibold mb-1">Views por dia</div>
        <div className="text-xs text-muted mb-4">{daily?.error ? `Analytics indisponível: ${daily.error}` : 'Passe o mouse para ver cada dia · o YouTube libera os dados com ~2 dias de atraso'}</div>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={d} margin={{ left: -10, right: 8, top: 4 }}>
              <defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={GOLD} stopOpacity={0.35} /><stop offset="100%" stopColor={GOLD} stopOpacity={0} /></linearGradient></defs>
              <CartesianGrid stroke="#1d232d" vertical={false} />
              <XAxis dataKey="day" tick={{ fill: '#8a9690', fontSize: 11 }} tickFormatter={v => v.slice(8, 10) + '/' + v.slice(5, 7)} axisLine={false} tickLine={false} minTickGap={24} />
              <YAxis tick={{ fill: '#8a9690', fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
              <Tooltip contentStyle={{ background: '#121816', border: '1px solid #24302b', borderRadius: 10, color: '#e9ece8' }}
                labelFormatter={v => new Date(v + 'T12:00').toLocaleDateString('pt-BR')} formatter={(v: any) => [fmtNum(Number(v)), 'views']} />
              <Area type="monotone" dataKey="views" stroke={GOLD} strokeWidth={2} fill="url(#g)" isAnimationActive={false} activeDot={{ r: 5, stroke: '#121816', strokeWidth: 2 }} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {cid && <RetentionCard cid={cid} />}

      <div className="grid xl:grid-cols-[1fr_340px] gap-6 items-start">
        <div className="card overflow-hidden">
          <div className="px-5 py-4 flex items-center justify-between">
            <div className="text-sm font-semibold">Desempenho por vídeo</div>
            <div className="flex items-center gap-2 text-xs text-muted"><ArrowUpDown size={13} /> ordenar por
              <select className="input !w-auto !py-1 text-xs" value={sort} onChange={e => setSort(e.target.value as keyof Row)}>
                <option value="perf">Nota de desempenho</option><option value="views">Views</option><option value="retention">Retenção</option>
                <option value="likes">Curtidas</option><option value="engagement">Engajamento</option>
              </select></div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-[12px] text-muted border-y border-line">
                <tr><th className="text-left px-5 py-2">Vídeo</th><th className="text-right px-3">Views</th><th className="text-right px-3">Curtidas</th>
                  <th className="text-right px-3">Coment.</th><th className="text-right px-3">Retenção</th><th className="text-right px-3">Engaj.</th><th className="px-5 text-left w-40">Desempenho</th></tr>
              </thead>
              <tbody className="divide-y divide-line">
                {sorted.map(r => (
                  <tr key={String(r.video_id)} className="hover:bg-panel2">
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-3 min-w-64">
                        {r.thumbnail ? <img src={r.thumbnail} referrerPolicy="no-referrer" className="w-16 h-10 rounded object-cover bg-black" alt="" /> : <div className="w-16 h-10 rounded bg-panel2" />}
                        <div className="min-w-0">
                          <div className="truncate max-w-80 font-medium">{r.title.replace(/#Shorts/i, '').trim()}</div>
                          <div className="text-xs text-muted">{r.published_at ? new Date(r.published_at).toLocaleDateString('pt-BR') : ''}{r.duration ? ` · ${Math.round(r.duration)}s` : ''}</div>
                        </div>
                        {r.url && <a href={r.url} target="_blank" rel="noreferrer" className="text-muted hover:text-text ml-auto"><ExternalLink size={14} /></a>}
                      </div>
                    </td>
                    <td className="text-right px-3 tabular-nums">{fmtNum(r.views)}</td>
                    <td className="text-right px-3 tabular-nums">{fmtNum(r.likes)}</td>
                    <td className="text-right px-3 tabular-nums">{r.comments}</td>
                    <td className="text-right px-3 tabular-nums">{r.retention ? `${r.retention.toFixed(0)}%` : '—'}</td>
                    <td className="text-right px-3 tabular-nums">{r.engagement.toFixed(1)}%</td>
                    <td className="px-5">
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-1.5 rounded-full bg-line overflow-hidden"><div className="h-full rounded-full bg-text/80" style={{ width: `${r.perf}%` }} /></div>
                        <span className="text-xs w-7 text-right tabular-nums">{r.perf}</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!rows.length && <div className="p-8 text-center text-sm text-muted">Nenhum vídeo publicado ainda.</div>}
          </div>
        </div>

        <div className="card p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="text-sm font-semibold">O que o sistema aprendeu</div>
            <button className="btn !py-1 text-xs" onClick={() => act(() => api(`/channels/${cid}/insights`, { body: {} }), 'Aprendizados atualizados').then(() => invalidate(`/channels/${cid}/insights`))}>
              <Sparkles size={13} /> Atualizar</button>
          </div>
          <ul className="space-y-3 text-sm text-text/85">
            {insights.map((i, k) => <li key={k} className="flex gap-2"><span className={i.kind === 'retention' ? 'text-info mt-0.5' : 'text-muted mt-0.5'}>•</span>
              <span>{i.kind === 'retention' && <span className="chip text-info  mr-1 !py-0">retenção</span>}{i.text}</span></li>)}
          </ul>
          {!insights.length && <p className="text-sm text-muted">Com 3+ vídeos publicados, a IA encontra padrões do que funciona e usa isso nas notas das pautas.</p>}
        </div>
      </div>
    </>
  )
}

function Tile({ label, v, sub }: { label: string; v: string; sub?: string }) {
  return (
    <div className="card p-5">
      <div className="text-muted text-[12.5px]">{label}</div>
      <div className="text-[26px] font-semibold mt-2 num tracking-tight">{v}</div>
      {sub && <div className="text-xs text-muted mt-1">{sub}</div>}
    </div>
  )
}

type Ret = { publication_id: number; title: string; duration: number; views: number; curve: number[][]; hook?: number; mid?: number; end?: number
  scenes: { start: number; end: number; text: string }[]; worst_scenes?: { scene: number; text: string; drop_per_10s: number }[] }

function RetentionCard({ cid }: { cid: number }) {
  const { data = [] } = useApi<Ret[]>(`/channels/${cid}/retention`)
  const [sel, setSel] = useState<number | null>(null)
  const r = data.find(x => x.publication_id === sel) ?? data[0]
  if (!data.length) return (
    <div className="card p-5 mb-6 text-sm text-muted">
      <div className="text-sm font-semibold text-text mb-1">Retenção segundo a segundo</div>
      O YouTube libera a curva de retenção depois que o vídeo acumula algumas dezenas de visualizações. Assim que houver dados, eles aparecem aqui e viram lições para o roteirista.
    </div>
  )
  const start = r.curve[0]?.[1] || 1
  const pts = r.curve.map(([x, y]) => ({ t: Math.round(x * r.duration * 10) / 10, v: Math.round((y / start) * 1000) / 10 }))
  return (
    <div className="card p-5 mb-6">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-1">
        <div>
          <div className="text-sm font-semibold">Retenção segundo a segundo</div>
          <div className="text-xs text-muted">% do público que ainda está assistindo em cada momento · linhas tracejadas = início de cada cena</div>
        </div>
        <select className="input !w-auto !py-1.5 text-sm max-w-96" value={r.publication_id} onChange={e => setSel(Number(e.target.value))}>
          {data.map(x => <option key={x.publication_id} value={x.publication_id}>{x.title.replace(/#Shorts/i, '')}</option>)}
        </select>
      </div>
      <div className="flex flex-wrap gap-2 my-3 text-sm">
        <span className="chip !text-sm">Gancho (3s): <b className="ml-1">{r.hook ?? '—'}%</b></span>
        <span className="chip !text-sm">Meio: <b className="ml-1">{r.mid ?? '—'}%</b></span>
        <span className="chip !text-sm">Final: <b className="ml-1">{r.end ?? '—'}%</b></span>
        {r.worst_scenes?.[0] && <span className="chip !text-sm text-warn ">Maior queda: cena {r.worst_scenes[0].scene} (−{r.worst_scenes[0].drop_per_10s}% a cada 10s)</span>}
      </div>
      <div className="h-60">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={pts} margin={{ left: -10, right: 8, top: 4 }}>
            <CartesianGrid stroke="#1d232d" vertical={false} />
            <XAxis dataKey="t" type="number" domain={[0, Math.ceil(r.duration)]} tick={{ fill: '#8a9690', fontSize: 11 }} tickFormatter={v => `${Math.round(v)}s`} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: '#8a9690', fontSize: 11 }} axisLine={false} tickLine={false} unit="%" domain={[0, 'auto']} />
            {r.scenes.slice(1).map((sc, k) => <ReferenceLine key={k} x={Math.round(sc.start * 10) / 10} stroke="#3a4a43" strokeDasharray="3 4" />)}
            <Tooltip contentStyle={{ background: '#121816', border: '1px solid #24302b', borderRadius: 10, color: '#e9ece8' }}
              labelFormatter={v => `${v}s`} formatter={(v: any) => [`${v}%`, 'assistindo']} />
            <Line type="monotone" dataKey="v" stroke={GOLD} strokeWidth={2} dot={false} isAnimationActive={false} activeDot={{ r: 5, stroke: '#121816', strokeWidth: 2 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
