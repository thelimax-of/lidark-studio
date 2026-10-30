import { Link, useNavigate } from 'react-router-dom'
import { CalendarClock, Play, ShieldCheck, Send, ArrowUpRight, Clapperboard, Lightbulb, Activity, Eye, Clock, UserPlus, Heart, Sparkles, Flame } from 'lucide-react'
import { api, invalidate, mediaUrl, useApi, type Idea, type Job, type Video } from '../api'
import VarietyCard from './VarietyCard'
import { YppCard } from './Growth'
import AllChannels from './Overview'
import { act, ago, ChannelScope, fmtNum, PageHeader, Progress, ScoreRing, SectionTitle, Skeleton, Status, useChannel, useScope } from '../ui'
import { Callout, RowsSkeleton, StatTile } from './kit'

type Daily = { rows: { day: string; views: number; minutes: number; subs: number; likes: number }[] }

const More = ({ to, children }: { to: string; children: string }) =>
  <Link to={to} className="btn btn-sm btn-ghost -mr-1.5">{children}<ArrowUpRight size={13} /></Link>

export default function Dashboard() {
  const { channel, setChannelId } = useChannel()
  const nav = useNavigate()
  const [all, setAll] = useScope('dashboard', true)
  const cid = all ? undefined : channel?.id
  const { data: dash } = useApi<any>(cid ? `/dashboard?channel_id=${cid}` : null)
  const { data: health } = useApi<any>('/health')
  const { data: daily } = useApi<Daily>(cid ? `/channels/${cid}/analytics?days=28` : null)
  // mesma chave da tela de Pautas (cache compartilhado); vídeos na versão leve (aqui só lemos miniatura, status e QA)
  const { data: ideas = [], isLoading: ideasLoading } = useApi<Idea[]>(cid ? `/ideas?channel_id=${cid}&status=new,approved` : null)
  const { data: videos = [] } = useApi<Video[]>(cid ? `/videos?channel_id=${cid}&slim=1` : null)
  const { data: pubs = [] } = useApi<any[]>(cid ? `/publications?channel_id=${cid}` : null)
  const { data: jobs = [], isLoading: jobsLoading } = useApi<Job[]>('/jobs?limit=12')
  const { data: insights = [] } = useApi<{ text: string; kind?: string }[]>(cid ? `/channels/${cid}/insights` : null)

  if (!channel) return (
    <div className="space-y-4" aria-busy="true">
      <Skeleton className="h-7 w-64" />
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">{[0, 1, 2, 3].map(i => <Skeleton key={i} className="h-32" />)}</div>
      <Skeleton className="h-40" />
    </div>
  )
  const scope = <ChannelScope all={all} onChange={setAll} />
  if (all) return <AllChannels scope={scope} onOpen={id => { setChannelId(id); setAll(false) }} />
  const c = dash?.counts ?? {}
  const rows = daily?.rows ?? []
  const sum = (k: 'views' | 'minutes' | 'subs' | 'likes') => rows.reduce((n, r) => n + (r[k] ?? 0), 0)
  const series = (k: 'views' | 'minutes' | 'subs' | 'likes') => rows.map(r => r[k] ?? 0)
  const top = [...ideas].sort((a, b) => (b.score ?? -1) - (a.score ?? -1)).slice(0, 5)
  const upcoming = pubs.filter(p => p.status === 'scheduled' || p.status === 'uploading')
    .sort((a, b) => String(a.scheduled_at).localeCompare(String(b.scheduled_at))).slice(0, 5)
  const recent = videos.filter(v => v.status !== 'failed').slice(0, 6)
  const noLLM = health && !health.llm.gemini_keys && !health.llm.glm
  const produce = (i: Idea) => act(() => api(`/ideas/${i.id}/script`, { body: { auto_render: true } }), 'Roteiro + vídeo na fila!').then(() => invalidate('/jobs'))

  return (
    <div className="space-y-5">
      <PageHeader eyebrow="Painel do canal" title={channel.name} subtitle={<>
        <span className="num text-text">{fmtNum(channel.stats?.subscribers ?? 0)}</span> inscritos · <span className="num text-text">{fmtNum(channel.stats?.views ?? 0)}</span> views no total · <span className="num text-text">{channel.stats?.videos ?? c.published ?? 0}</span> vídeos
        {channel.auto_pilot && <> · <span className="inline-flex items-center gap-1.5 text-ok"><span className="live-dot" />Piloto automático ligado</span></>}
      </>} actions={scope} />

      {noLLM && (
        <Link to="/config" className="block">
          <Callout tone="warn" action={<span className="btn btn-sm">Configurar</span>}>
            <b>Configure uma IA para começar.</b> <span className="text-muted">Adicione a chave do Gemini (e do GLM como reserva) em Configurações.</span>
          </Callout>
        </Link>
      )}

      {/* indicadores */}
      <section className="grid grid-cols-2 xl:grid-cols-4 gap-3">
        {[
          { label: 'Views', icon: <Eye size={14} />, v: fmtNum(sum('views')), s: series('views') },
          { label: 'Horas assistidas', icon: <Clock size={14} />, v: fmtNum(Math.round(sum('minutes') / 60)), s: series('minutes') },
          { label: 'Inscritos ganhos', icon: <UserPlus size={14} />, v: '+' + fmtNum(sum('subs')), s: series('subs') },
          { label: 'Curtidas', icon: <Heart size={14} />, v: fmtNum(sum('likes')), s: series('likes') },
        ].map((k, i) => (
          <StatTile key={k.label} label={k.label} icon={k.icon} value={k.v} sub="últimos 28 dias" spark={k.s} loading={!daily} tone={i === 0 ? 'accent' : undefined} />
        ))}
      </section>

      <YppCard channelId={channel.id} compact />

      {/* esteira de produção */}
      <section className="card overflow-hidden">
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5">
          {[
            { label: 'Pautas novas', v: c.ideas_new, to: '/pautas' },
            { label: 'Aprovadas', v: c.ideas_approved, to: '/pautas' },
            { label: 'Roteiros', v: c.scripts, to: '/roteiros' },
            { label: 'Vídeos prontos', v: c.videos_ready, to: '/videos' },
            { label: 'Publicados', v: c.published, to: '/publicacao' },
          ].map((s, i) => (
            <Link to={s.to} key={s.label} className="relative px-4 py-3.5 hover:bg-white/[0.025] transition-colors group border-line md:[&:not(:last-child)]:border-r max-md:border-b">
              <div className="text-[12px] text-muted flex items-center gap-1.5">
                <span className="w-4 h-4 rounded-full grid place-items-center text-[10px] num border border-line2 text-faint group-hover:border-accent/50 group-hover:text-accent transition-colors">{i + 1}</span>{s.label}
              </div>
              <div className="text-[24px] font-semibold num mt-1.5 flex items-center justify-between tracking-tight">
                {dash ? s.v ?? 0 : <span className="skeleton h-6 w-10 inline-block" />}
                <ArrowUpRight size={14} className="text-faint opacity-0 -translate-x-1 group-hover:opacity-100 group-hover:translate-x-0 transition" />
              </div>
            </Link>
          ))}
        </div>
      </section>

      <div className="grid xl:grid-cols-5 gap-5 items-start">
        <section className="card overflow-hidden xl:col-span-3">
          <SectionTitle hint="Ordenadas pela nota da IA" action={<More to="/pautas">Ver todas</More>}>Melhores pautas</SectionTitle>
          {ideasLoading && !ideas.length ? <RowsSkeleton rows={4} h="h-10" /> : top.length === 0 && (
            <div className="py-10 px-6 text-center">
              <Lightbulb size={18} className="mx-auto text-faint mb-2" />
              <div className="text-[13px] text-muted">Nenhuma pauta na fila. Rode o radar de tendências ou busque pautas.</div>
            </div>
          )}
          {top.map(i => (
            <div key={i.id} className="flex items-center gap-3 px-4 py-2.5 border-b border-line last:border-0 hover:bg-white/[0.025] transition-colors">
              <ScoreRing score={i.score} size={34} />
              <div className="min-w-0 flex-1">
                <Link to="/pautas" className="text-[13.5px] font-medium truncate block hover:text-accent2 transition-colors">{i.title}</Link>
                <div className="text-[12px] text-muted truncate">
                  {i.origin === 'trend' && <span className="text-warn inline-flex items-center gap-1 mr-1"><Flame size={11} />Tendência ·</span>}{i.angle}
                </div>
              </div>
              <span className="hidden md:inline-flex"><Status s={i.fact_status} /></span>
              <button className="btn btn-sm" onClick={() => produce(i)}><Clapperboard size={13} /> Produzir</button>
            </div>
          ))}
        </section>

        <div className="xl:col-span-2 space-y-5">
          <section className="card overflow-hidden">
            <SectionTitle action={<More to="/publicacao">Agenda</More>}>Próximas postagens</SectionTitle>
            {upcoming.length === 0 ? (
              <div className="text-[13px] text-muted flex items-center gap-2 px-4 py-6">
                <CalendarClock size={15} className="text-faint shrink-0" /> Nada agendado. {channel.auto_pilot ? 'O piloto automático agenda sozinho.' : 'Ligue o piloto automático em Canais.'}
              </div>
            ) : upcoming.map(p => (
              <div key={p.id} className="flex items-center gap-3 px-4 py-2.5 border-b border-line last:border-0">
                <div className="w-14 shrink-0 leading-tight rounded-md border border-line bg-bg2 px-1.5 py-1 text-center">
                  <div className="text-muted capitalize text-[10.5px]">{new Date(p.scheduled_at).toLocaleDateString('pt-BR', { weekday: 'short', day: '2-digit' })}</div>
                  <div className="font-semibold num text-[12.5px]">{new Date(p.scheduled_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</div>
                </div>
                <div className="text-[13px] truncate flex-1">{p.title}</div>
                <Status s={p.status} />
              </div>
            ))}
          </section>
          <section className="card overflow-hidden">
            <SectionTitle action={<More to="/fila">Produção</More>}>Atividade</SectionTitle>
            {jobsLoading && !jobs.length && <RowsSkeleton rows={3} h="h-9" />}
            {jobs.slice(0, 6).map(j => (
              <div key={j.id} className="px-4 py-2.5 border-b border-line last:border-0 text-[13px]">
                <div className="flex items-center justify-between gap-2"><span className="truncate">{j.title}</span><Status s={j.status} /></div>
                {j.status === 'running' ? <Progress value={j.progress} className="mt-2" /> : <div className="text-[12px] text-faint truncate mt-0.5">{j.stage} · {ago(j.created_at)}</div>}
              </div>
            ))}
            {!jobsLoading && !jobs.length && <div className="text-[13px] text-muted px-4 py-6 flex items-center gap-2"><Activity size={15} className="text-faint" /> Sem atividade ainda.</div>}
          </section>
        </div>
      </div>

      {recent.length > 0 && (
        <section className="card overflow-hidden">
          <SectionTitle action={<More to="/videos">Todos os vídeos</More>}>Últimos vídeos</SectionTitle>
          <div className="grid grid-cols-3 md:grid-cols-6 gap-3 p-4">
            {recent.map(v => (
              <button key={v.id} onClick={() => nav('/videos')} className="group text-left">
                <div className="relative rounded-[var(--r-md)] overflow-hidden border border-line aspect-[9/16] bg-black shadow-[var(--shadow-sm)] group-hover:border-line3 transition-colors">
                  {v.thumbnail_path
                    ? <img src={mediaUrl(v.thumbnail_path)} loading="lazy" className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-[1.03]" alt="" />
                    : <div className="w-full h-full skeleton" />}
                  <div className="absolute top-1.5 left-1.5 flex gap-1">
                    {v.assets?.qa?.passed && <span className="badge bg-black/70! border-white/10! px-1.5!"><ShieldCheck size={11} className="text-ok" /></span>}
                    {v.status === 'published' && <span className="badge bg-black/70! border-white/10! px-1.5!"><Send size={11} className="text-ok" /></span>}
                  </div>
                  <div className="absolute inset-0 grid place-items-center bg-black/30 opacity-0 group-hover:opacity-100 transition">
                    <div className="w-10 h-10 rounded-full bg-grad text-white grid place-items-center shadow-lg"><Play size={15} fill="currentColor" /></div>
                  </div>
                </div>
                <div className="text-[12.5px] mt-2 leading-snug line-clamp-2 text-muted group-hover:text-text transition-colors">{v.title}</div>
              </button>
            ))}
          </div>
        </section>
      )}

      <VarietyCard channelId={channel.id} />

      {insights.length > 0 && (
        <section className="card overflow-hidden">
          <SectionTitle hint="Gerado a partir das métricas e da retenção dos seus vídeos">
            <span className="inline-flex items-center gap-2"><Sparkles size={14} className="text-accent" />O que o sistema aprendeu</span>
          </SectionTitle>
          <div className="grid md:grid-cols-2">
            {insights.slice(0, 6).map((i, k) => (
              <div key={k} className="flex gap-3 px-4 py-3 border-b border-line md:odd:border-r text-[13px] text-text/85">
                <span className={`badge shrink-0 ${i.kind === 'retention' ? 'badge-accent' : 'text-muted'}`}>{i.kind === 'retention' ? 'Retenção' : 'Métricas'}</span><span>{i.text}</span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
