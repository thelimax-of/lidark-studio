import { useState } from 'react'
import clsx from 'clsx'
import { Activity, RotateCcw, Square, Check, Loader2, Mic, Captions, Image as ImageIcon, Music, Film, ShieldCheck, Search, PenLine, Sparkles, ArrowUp, Power, Gauge } from 'lucide-react'
import { api, invalidate, useApi, type Job } from '../api'
import { act, ago, Empty, PageHeader, Progress, Status, Tabs } from '../ui'
import { Bar, RowsSkeleton, useProgressive } from './kit'

const KIND: Record<string, string> = {
  discover_ideas: 'Busca de pautas', score_idea: 'Nota da pauta', verify_idea: 'Checagem de fatos', manual_idea: 'Validação de ideia',
  write_script: 'Roteiro', review_script: 'Revisão', render_video: 'Vídeo', autopilot: 'Piloto automático',
  publish: 'Publicação', collect_metrics: 'Métricas', setup_channel: 'Configuração do canal', channel_identity: 'Identidade do canal',
  trend_radar: 'Radar de tendências', inspect_video: 'Inspeção de qualidade', import_youtube: 'Importação',
  brand_propose: 'Novo canal: propostas', brand_texts: 'Novo canal: textos',
}

const STEPS: Record<string, { label: string; icon: any; match: RegExp }[]> = {
  render_video: [
    { label: 'Narração', icon: Mic, match: /narra|roteiro curto|expans/i },
    { label: 'Legendas', icon: Captions, match: /legenda|sincroniz/i },
    { label: 'Imagens', icon: ImageIcon, match: /imagens|buscando e avaliando/i },
    { label: 'Trilha', icon: Music, match: /trilha|mixando/i },
    { label: 'Render', icon: Film, match: /renderiz/i },
    { label: 'Inspeção', icon: ShieldCheck, match: /inspetor|miniatura/i },
  ],
  write_script: [
    { label: 'Pesquisa', icon: Search, match: /pesquis/i },
    { label: 'Roteiro', icon: PenLine, match: /escrev|roteiro/i },
    { label: 'Revisão', icon: Sparkles, match: /revis|editor/i },
    { label: 'Fatos', icon: ShieldCheck, match: /fatos frase/i },
  ],
}

function Stepper({ job }: { job: Job }) {
  const steps = STEPS[job.kind]
  if (!steps) return null
  let cur = steps.findIndex(s => s.match.test(job.stage || ''))
  if (job.status === 'done') cur = steps.length
  if (cur < 0) cur = 0
  return (
    <div className="grid border border-line rounded-[var(--r-md)] overflow-hidden mt-5 bg-bg2/50" style={{ gridTemplateColumns: `repeat(${steps.length}, minmax(0,1fr))` }}>
      {steps.map((s, i) => {
        const done = i < cur, active = i === cur && job.status === 'running'
        return (
          <div key={s.label} className={clsx('px-3 py-2.5 border-r border-line last:border-0 relative transition-colors', active && 'bg-accent/[0.07]')}>
            <div className={clsx('flex items-center gap-1.5 text-[12.5px]', active ? 'text-text font-medium' : done ? 'text-text/80' : 'text-faint')}>
              {done ? <Check size={14} className="text-ok" /> : active ? <Loader2 size={14} className="animate-spin text-accent" /> : <s.icon size={14} />}
              <span className="truncate">{s.label}</span>
            </div>
            <div className={clsx('absolute left-0 right-0 bottom-0 h-[2px]', done ? 'bg-ok/70' : active ? 'bg-grad' : 'bg-transparent')} />
          </div>
        )
      })}
    </div>
  )
}

export default function Jobs() {
  const { data = [], isLoading } = useApi<Job[]>('/jobs?limit=100')
  const [sel, setSel] = useState<number | null>(null)
  const [only, setOnly] = useState<'all' | 'active' | 'failed'>('all')
  const current = sel ?? data.find(j => j.status === 'running')?.id ?? data[0]?.id ?? null
  const { data: detail } = useApi<Job>(current ? `/jobs/${current}` : null, { refetchInterval: 1500 })
  const list = data.filter(j => only === 'all' || (only === 'active' ? ['running', 'queued'].includes(j.status) : j.status === 'failed'))
  const [shown, more] = useProgressive(list, 40, only)

  return (
    <>
      <PageHeader title="Produção" subtitle="Tudo que o motor está fazendo agora, etapa por etapa." actions={<RestartButton />} />
      <Capacity />
      {isLoading && !data.length ? <div className="grid lg:grid-cols-5 gap-5"><div className="lg:col-span-2 card"><RowsSkeleton rows={6} h="h-14" /></div><div className="lg:col-span-3 skeleton h-96" /></div>
        : !data.length ? <Empty icon={<Activity size={20} />} title="Nenhuma tarefa ainda" text="Quando o motor buscar pautas, escrever roteiros ou renderizar vídeos, as etapas aparecem aqui." /> : (
        <div className="grid lg:grid-cols-5 gap-5 items-start">
          <div className="lg:col-span-2 card overflow-hidden">
            <div className="px-3 pt-1 border-b border-line">
              <Tabs value={only} onChange={setOnly} items={[
                { key: 'all', label: 'Todas', count: data.length },
                { key: 'active', label: 'Rodando', count: data.filter(j => ['running', 'queued'].includes(j.status)).length },
                { key: 'failed', label: 'Com erro', count: data.filter(j => j.status === 'failed').length },
              ]} />
            </div>
            <div className="max-h-[72vh] overflow-y-auto">
              {shown.map(j => (
                <button key={j.id} onClick={() => setSel(j.id)} className={clsx('w-full block px-4 py-3 text-left border-b border-line last:border-0 transition relative',
                  current === j.id ? 'bg-accent/[0.07]' : 'hover:bg-white/[0.025]')}>
                  {current === j.id && <span className="absolute left-0 top-0 bottom-0 w-[2px] bg-grad" />}
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[12px] text-muted flex items-center gap-1.5">{KIND[j.kind] ?? j.kind} <span className="text-faint num">#{j.id}</span></span>
                    <Status s={j.status} />
                  </div>
                  <div className="text-[13.5px] font-medium truncate mt-1">{j.title}</div>
                  {j.status === 'running' ? <><Progress value={j.progress} className="mt-2" /><div className="text-[12px] text-muted mt-1 truncate">{j.stage}</div></>
                    : <div className="text-[12px] text-faint mt-0.5 truncate">{ago(j.created_at)}{j.stage && j.status !== 'done' ? ` · ${j.stage}` : ''}</div>}
                </button>
              ))}
              {more}
              {!list.length && <div className="text-[13px] text-muted px-4 py-8 text-center">Nada aqui.</div>}
            </div>
          </div>
          <div className="lg:col-span-3">
            {detail && (
              <div className="card lg:sticky lg:top-4 overflow-hidden">
                <div className="card-head">
                  <div className="min-w-0">
                    <div className="text-[12px] text-muted">{KIND[detail.kind] ?? detail.kind} · <span className="num">#{detail.id}</span></div>
                    <h3 className="text-[16px] font-semibold mt-0.5 truncate">{detail.title}</h3>
                  </div>
                  <div className="flex gap-2 shrink-0">
                    {detail.status === 'queued' &&
                      <button className="btn btn-sm" onClick={() => act(() => api(`/jobs/${detail.id}/bump`, { body: {} }), 'Passou na frente da fila').then(() => invalidate('/jobs'))}><ArrowUp size={13} /> Passar na frente</button>}
                    {(detail.status === 'running' || detail.status === 'queued') &&
                      <button className="btn btn-sm btn-danger" onClick={() => act(() => api(`/jobs/${detail.id}/cancel`, { body: {} }), 'Cancelado')}><Square size={13} /> Parar</button>}
                    {(detail.status === 'failed' || detail.status === 'cancelled') &&
                      <button className="btn btn-sm" onClick={() => act(() => api(`/jobs/${detail.id}/retry`, { body: {} }), 'Reenviado').then(() => invalidate('/jobs'))}><RotateCcw size={13} /> Tentar de novo</button>}
                  </div>
                </div>
                <div className="p-4">
                  <div className="flex items-center gap-3">
                    <Status s={detail.status} />
                    <span className="text-[13px] text-muted truncate flex-1">{detail.status === 'running' ? detail.stage : ago(detail.created_at)}</span>
                    <span className="text-[15px] font-semibold num text-gradient">{Math.round(detail.progress * 100)}%</span>
                  </div>
                  <Progress value={detail.progress} className="mt-3" />
                  <Stepper job={detail} />
                  <div className="label mt-5">Registro</div>
                  <pre className="text-[12px] bg-bg2 border border-line rounded-[var(--r-md)] p-3.5 max-h-[42vh] overflow-auto whitespace-pre-wrap font-mono text-text/75 leading-relaxed">{detail.log || '—'}</pre>
                  {detail.error && <>
                    <div className="label mt-4 text-bad!">Erro</div>
                    <pre className="text-[12px] bg-bad/[0.06] border border-bad/30 rounded-[var(--r-md)] p-3.5 max-h-60 overflow-auto whitespace-pre-wrap font-mono text-bad">{detail.error}</pre>
                  </>}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  )
}

type Cap = {
  avg_minutes: { short: number; long: number }; measured: { short: number; long: number }
  channels: { channel_id: number; name: string; shorts_day: number; longs_week: number; minutes_day: number }[]
  need_hours_day: number; usage: number; queue_renders: number; queue_hours: number
}

function Capacity() {
  const { data } = useApi<Cap>('/jobs-capacity', { refetchInterval: 30000 })
  if (!data) return null
  const pct = Math.round(data.usage * 100)
  const tone = pct > 85 ? 'text-bad' : pct > 60 ? 'text-warn' : 'text-ok'
  return (
    <div className="card p-4 mb-5">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
        <div className="flex items-center gap-2 font-semibold"><span className="w-8 h-8 rounded-[9px] grid place-items-center border border-line2 bg-panel2 text-muted"><Gauge size={15} /></span> Capacidade do notebook</div>
        <div className="text-[13px]"><span className={clsx('font-semibold num', tone)}>{data.need_hours_day}h</span> <span className="text-muted">de render por dia nos horários atuais ({pct}% do dia)</span></div>
        <div className="text-[13px] text-muted">Short ≈ <span className="text-text num">{data.avg_minutes.short} min</span> · Longo ≈ <span className="text-text num">{data.avg_minutes.long} min</span>
          {!(data.measured.short + data.measured.long) && ' (estimativa — ainda sem renders medidos)'}</div>
        {data.queue_renders > 0 && <div className="text-[13px] text-muted">Fila: <span className="text-text num">{data.queue_renders}</span> vídeo(s) · ~<span className="text-text num">{data.queue_hours}h</span></div>}
      </div>
      <Bar value={pct} tone={pct > 85 ? 'bad' : pct > 60 ? 'warn' : undefined} className="mt-3" />
      {pct > 85 && <p className="text-[12.5px] text-bad mt-2">Os horários pedem mais render do que o notebook dá conta — a fila vai crescer. Tire horários ou deixe algum canal só com Shorts.</p>}
      <div className="flex flex-wrap gap-2 mt-3">
        {data.channels.map(c => (
          <span key={c.channel_id} className="text-[12px] px-2 py-1 rounded-md border border-line bg-bg2/50 text-muted">
            {c.name}: <span className="text-text num">{c.shorts_day}</span> short/dia · <span className="text-text num">{c.longs_week}</span> longo/sem · <span className="num">{c.minutes_day} min</span>
          </span>
        ))}
      </div>
    </div>
  )
}

function RestartButton() {
  const { data, refetch } = useApi<{ draining: boolean; running: number[] }>('/system/restart', { refetchInterval: 5000 })
  if (data?.draining) {
    return (
      <div className="flex items-center gap-2 text-[13px] text-warn">
        <Loader2 size={14} className="animate-spin" /> Reiniciando quando ficar livre ({data.running.length} tarefa(s) rodando)
        <button className="btn btn-sm" onClick={() => act(() => api('/system/restart/cancel', { body: {} })).then(() => refetch())}>Cancelar</button>
      </div>
    )
  }
  return (
    <button className="btn btn-sm" title="Para de pegar tarefas novas, espera o que está rodando terminar e reinicia — nunca no meio de um vídeo"
      onClick={() => act(() => api('/system/restart', { body: { when_idle: true } }), 'O servidor reinicia assim que ficar livre').then(() => refetch())}>
      <Power size={13} /> Reiniciar quando ficar livre
    </button>
  )
}
