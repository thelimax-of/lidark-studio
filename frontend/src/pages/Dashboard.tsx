import { Link, useNavigate } from 'react-router-dom'
import { AlertTriangle, CalendarClock, Play, ShieldCheck, Send, ArrowUpRight, Clapperboard } from 'lucide-react'
import { api, invalidate, mediaUrl, useApi, type Idea, type Job, type Video } from '../api'
import VarietyCard from './VarietyCard'
import { YppCard } from './Growth'
import { act, ago, fmtNum, PageHeader, Progress, ScoreRing, SectionTitle, Skeleton, Sparkline, Status, useChannel } from '../ui'

type Daily = { rows: { day: string; views: number; minutes: number; subs: number; likes: number }[] }

const More = ({ to, children }: { to: string; children: string }) =>
  <Link to={to} className="text-[12.5px] text-muted hover:text-text inline-flex items-center gap-0.5">{children}<ArrowUpRight size={13} /></Link>

export default function Dashboard() {
  const { channel } = useChannel()
  const nav = useNavigate()
  const cid = channel?.id
  const { data: dash } = useApi<any>(cid ? `/dashboard?channel_id=${cid}` : null)
  const { data: health } = useApi<any>('/health')
  const { data: daily } = useApi<Daily>(cid ? `/channels/${cid}/analytics?days=28` : null)
  const { data: ideas = [] } = useApi<Idea[]>(cid ? `/ideas?channel_id=${cid}&status=new,approved` : null)
  const { data: videos = [] } = useApi<Video[]>(cid ? `/videos?channel_id=${cid}` : null)
  const { data: pubs = [] } = useApi<any[]>(cid ? `/publications?channel_id=${cid}` : null)
  const { data: jobs = [] } = useApi<Job[]>('/jobs?limit=12')
  const { data: insights = [] } = useApi<{ text: string; kind?: string }[]>(cid ? `/channels/${cid}/insights` : null)

  if (!channel) return <div className="space-y-4"><Skeleton className="h-24" /><Skeleton className="h-32" /></div>
  const c = dash?.counts ?? {}
  const rows = daily?.rows ?? []
  const sum = (k: 'views' | 'minutes' | 'subs' | 'likes') => rows.reduce((n, r) => n + (r[k] ?? 0), 0)
  const series = (k: 'views' | 'minutes' | 'subs' | 'likes') => rows.map(r => r[k] ?? 0)
  const top = [...ideas].sort((a, b) => (b.score ?? -1) - (a.score ?? -1)).slice(0, 5)
  const upcoming = pubs.filter(p => p.status === 'scheduled' || p.status === 'uploading')
    .sort((a, b) => String(a.scheduled_at).localeCompare(String(b.scheduled_at))).slice(0, 5)
  const recent = videos.filter(v => v.status !== 'failed').slice(0, 6)
  const noLLM = health && !health.llm.gemini_keys && !health.llm.glm

  return (
    <div className="space-y-5">
      <PageHeader title="Visão geral" subtitle={<>
        <span className="num">{fmtNum(channel.stats?.subscribers ?? 0)}</span> inscritos · <span className="num">{fmtNum(channel.stats?.views ?? 0)}</span> views no total · <span className="num">{channel.stats?.videos ?? c.published ?? 0}</span> vídeos
        {channel.auto_pilot && <> · <span className="inline-flex items-center gap-1.5 text-ok"><span className="dot" />Piloto automático ligado</span></>}
      </>} />

      {noLLM && (
        <Link to="/config" className="card px-4 py-3 flex items-center gap-3 border-warn/40! hover:bg-warn/5">
          <AlertTriangle size={16} className="text-warn" />
          <div className="text-[13px]"><b>Configure uma IA para começar.</b> <span className="text-muted">Adicione a chave do Gemini (e do GLM como reserva) em Configurações.</span></div>
        </Link>
      )}

      {/* indicadores */}
      <section className="card grid grid-cols-2 xl:grid-cols-4 divide-x divide-line overflow-hidden">
        {[
          { label: 'Views', v: fmtNum(sum('views')), s: series('views') },
          { label: 'Horas assistidas', v: fmtNum(Math.round(sum('minutes') / 60)), s: series('minutes') },
          { label: 'Inscritos ganhos', v: '+' + fmtNum(sum('subs')), s: series('subs') },
          { label: 'Curtidas', v: fmtNum(sum('likes')), s: series('likes') },
        ].map(k => (
          <div key={k.label} className="p-4">
            <div className="flex items-center justify-between text-[12.5px] text-muted">{k.label}<span className="text-faint text-[11.5px]">28 dias</span></div>
            <div className="text-[26px] leading-none font-semibold mt-2.5 num tracking-tight">{daily ? k.v : '—'}</div>
            <Sparkline data={k.s} height={28} className="mt-3" />
          </div>
        ))}
      </section>

      <YppCard channelId={channel.id} compact />

      {/* esteira */}
      <section className="card grid grid-cols-2 md:grid-cols-5 divide-x divide-line overflow-hidden">
        {[
          { label: 'Pautas novas', v: c.ideas_new, to: '/pautas' },
          { label: 'Aprovadas', v: c.ideas_approved, to: '/pautas' },
          { label: 'Roteiros', v: c.scripts, to: '/roteiros' },
          { label: 'Vídeos prontos', v: c.videos_ready, to: '/videos' },
          { label: 'Publicados', v: c.published, to: '/publicacao' },
        ].map((s, i) => (
          <Link to={s.to} key={s.label} className="px-4 py-3.5 hover:bg-white/[0.02] transition group">
            <div className="text-[12.5px] text-muted flex items-center gap-1.5"><span className="text-faint num">{i + 1}</span>{s.label}</div>
            <div className="text-[22px] font-semibold num mt-1 flex items-center justify-between">{s.v ?? 0}<ArrowUpRight size={14} className="text-faint opacity-0 group-hover:opacity-100 transition" /></div>
          </Link>
        ))}
      </section>

      <div className="grid xl:grid-cols-5 gap-5 items-start">
        <section className="card overflow-hidden xl:col-span-3">
          <SectionTitle hint="Ordenadas pela nota da IA" action={<More to="/pautas">Ver todas</More>}>Melhores pautas</SectionTitle>
          {top.length === 0 && <div className="text-[13px] text-muted py-10 text-center">Nenhuma pauta na fila. Rode o radar de tendências ou busque pautas.</div>}
          {top.map(i => (
            <div key={i.id} className="flex items-center gap-3 px-4 py-2.5 border-b border-line last:border-0 hover:bg-white/[0.02]">
              <ScoreRing score={i.score} size={34} />
              <div className="min-w-0 flex-1">
                <div className="text-[13.5px] font-medium truncate">{i.title}</div>
                <div className="text-[12px] text-muted truncate">{i.origin === 'trend' ? 'Tendência · ' : ''}{i.angle}</div>
              </div>
              <span className="hidden md:inline-flex"><Status s={i.fact_status} /></span>
              <button className="btn btn-sm" onClick={() => act(() => api(`/ideas/${i.id}/script`, { body: { auto_render: true } }), 'Roteiro + vídeo na fila!').then(() => invalidate('/jobs'))}>
                <Clapperboard size={13} /> Produzir</button>
            </div>
          ))}
        </section>

        <div className="xl:col-span-2 space-y-5">
          <section className="card overflow-hidden">
            <SectionTitle action={<More to="/publicacao">Agenda</More>}>Próximas postagens</SectionTitle>
            {upcoming.length === 0 ? (
              <div className="text-[13px] text-muted flex items-center gap-2 px-4 py-5"><CalendarClock size={15} /> Nada agendado. {channel.auto_pilot ? 'O piloto automático agenda sozinho.' : 'Ligue o piloto automático em Canais.'}</div>
            ) : upcoming.map(p => (
              <div key={p.id} className="flex items-center gap-3 px-4 py-2.5 border-b border-line last:border-0">
                <div className="w-14 shrink-0 text-[12px] leading-tight">
                  <div className="text-muted capitalize">{new Date(p.scheduled_at).toLocaleDateString('pt-BR', { weekday: 'short', day: '2-digit' })}</div>
                  <div className="font-medium num">{new Date(p.scheduled_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</div>
                </div>
                <div className="text-[13px] truncate flex-1">{p.title}</div>
                <Status s={p.status} />
              </div>
            ))}
          </section>
          <section className="card overflow-hidden">
            <SectionTitle action={<More to="/fila">Produção</More>}>Atividade</SectionTitle>
            {jobs.slice(0, 6).map(j => (
              <div key={j.id} className="px-4 py-2.5 border-b border-line last:border-0 text-[13px]">
                <div className="flex items-center justify-between gap-2"><span className="truncate">{j.title}</span><Status s={j.status} /></div>
                {j.status === 'running' ? <Progress value={j.progress} className="mt-2" /> : <div className="text-[12px] text-muted truncate">{j.stage} · {ago(j.created_at)}</div>}
              </div>
            ))}
            {!jobs.length && <div className="text-[13px] text-muted px-4 py-5">Sem atividade ainda.</div>}
          </section>
        </div>
      </div>

      {recent.length > 0 && (
        <section className="card overflow-hidden">
          <SectionTitle action={<More to="/videos">Todos os vídeos</More>}>Últimos vídeos</SectionTitle>
          <div className="grid grid-cols-3 md:grid-cols-6 gap-3 p-4">
            {recent.map(v => (
              <button key={v.id} onClick={() => nav('/videos')} className="group text-left">
                <div className="relative rounded-md overflow-hidden border border-line aspect-[9/16] bg-black">
                  {v.thumbnail_path ? <img src={mediaUrl(v.thumbnail_path)} className="w-full h-full object-cover" alt="" /> : <div className="w-full h-full skeleton" />}
                  <div className="absolute top-1.5 left-1.5 flex gap-1">
                    {v.assets?.qa?.passed && <span className="badge bg-black/70! border-white/10! px-1.5!"><ShieldCheck size={11} className="text-ok" /></span>}
                    {v.status === 'published' && <span className="badge bg-black/70! border-white/10! px-1.5!"><Send size={11} className="text-ok" /></span>}
                  </div>
                  <div className="absolute inset-0 grid place-items-center bg-black/30 opacity-0 group-hover:opacity-100 transition"><div className="w-9 h-9 rounded-full bg-white text-black grid place-items-center"><Play size={15} fill="currentColor" /></div></div>
                </div>
                <div className="text-[12.5px] mt-2 leading-snug line-clamp-2 text-muted group-hover:text-text">{v.title}</div>
              </button>
            ))}
          </div>
        </section>
      )}

      <VarietyCard channelId={channel.id} />

      {insights.length > 0 && (
        <section className="card overflow-hidden">
          <SectionTitle hint="Gerado a partir das métricas e da retenção dos seus vídeos">O que o sistema aprendeu</SectionTitle>
          <div className="grid md:grid-cols-2">
            {insights.slice(0, 6).map((i, k) => (
              <div key={k} className="flex gap-3 px-4 py-3 border-b border-line md:odd:border-r text-[13px] text-text/85">
                <span className="badge shrink-0 text-muted">{i.kind === 'retention' ? 'Retenção' : 'Métricas'}</span><span>{i.text}</span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
