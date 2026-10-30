// Séries do Modo História (canal dedicado): plano parte a parte de uma pauta-série e o quadro das séries em andamento,
// com status de cada parte, decisões A/B do público (votos dos comentários + enquete digitada) e a versão completa.
import { useState } from 'react'
import clsx from 'clsx'
import { CheckCircle2, Clapperboard, Film, Loader2, Play, Sparkles, Trash2, Vote } from 'lucide-react'
import { api, invalidate, mediaUrl, useApi } from '../api'
import { act, Skeleton } from '../ui'

type Decision = { question: string; options: { A: string; B: string }; default: 'A' | 'B'; branches?: Record<string, string> }
type PlanPart = { n: number; title: string; goal: string; obstacle?: string; twist?: string; cliffhanger: string; tip?: string; decision?: Decision | null }
type Plan = { title: string; logline: string; genre: string; setting: string; real_history: boolean; mode?: 'sequencial' | 'opcoes'; mission: { title: string; hours?: number }
  parts_count: number; parts: PlanPart[]; finale_tease?: string; newcomers?: { name: string; role: string }[] }
type Votes = { comments: { A: number; B: number }; manual: { A: number; B: number }; total: { A: number; B: number }; voters: number }
type SPart = PlanPart & { status: string; script_id?: number; video?: { id: number; status: string; thumbnail: string } | null
  scheduled_at?: string; url?: string; choice?: 'A' | 'B'; decided_by?: string; vote_until?: number; votes?: Votes | null }
type Serie = { id: string; title: string; idea_id: number; status: string; genre: string; logline: string; mission: { title: string }
  parts: SPart[]; blocked?: string | null; long?: { script_id: number } | null }

const GENRE: Record<string, string> = { zumbi: 'Zumbi', alien: 'Alien', ilha: 'Ilha', assombrada: 'Casa assombrada', apagao: 'Apagão',
  internet: 'Fim da internet', desastre: 'Desastre', historia: 'História real', espaco: 'Espaço', floresta: 'Floresta', deserto: 'Deserto', inverno: 'Inverno' }
const STATUS_TONE: Record<string, string> = { 'no ar': 'badge-ok', agendada: 'badge-accent', pronta: 'badge-accent', escrita: '', planejada: '' }

/** Plano de uma pauta-série (vai no modal da pauta). */
export function SeriesPlanCard({ channelId, ideaId }: { channelId: number; ideaId: number }) {
  const { data, isLoading } = useApi<{ plan: Plan; arc_id: string | null; status: string }>(`/story/${channelId}/plans/${ideaId}`, { keepPrevious: false })
  if (isLoading) return <Skeleton className="h-40" />
  if (!data) return null
  const p = data.plan
  const start = () => act(() => api(`/story/${channelId}/series/${ideaId}/start`, { method: 'POST' }), 'Série começando: parte 1 sendo escrita')
    .then(() => invalidate(`/story/${channelId}`))
  return (
    <div className="surface p-4 mb-5">
      <div className="flex flex-wrap items-center gap-2 mb-1">
        <span className="badge badge-accent"><Film size={11} /> Série · {p.parts_count} partes</span>
        <span className="badge">{GENRE[p.genre] ?? p.genre}</span>
        {p.real_history && <span className="badge badge-warn">História real (fatos checados)</span>}
        <span className="badge">Missão: {p.mission.title}{p.mission.hours ? ` · ${p.mission.hours}h` : ''}</span>
        <span className="text-[12px] text-muted ml-auto">{data.arc_id ? `em produção (${data.status})` : 'ainda não começou'}</span>
      </div>
      <p className="text-[13px] text-muted mb-3">{p.logline} <span className="text-faint">· {p.setting}</span></p>
      {!!p.newcomers?.length && <p className="text-[12px] text-muted mb-2">Personagem novo: {p.newcomers.map(c => `${c.name} (${c.role})`).join(', ')}</p>}
      <ol className="space-y-2">
        {p.parts.map(x => (
          <li key={x.n} className="text-[13px] flex gap-2">
            <span className="w-14 shrink-0 text-faint">Parte {x.n}</span>
            <div className="min-w-0">
              <b>{x.title}</b> — {x.goal}
              <div className="text-[12px] text-faint">Gancho: {x.cliffhanger}{x.tip ? ` · Dica: ${x.tip}` : ''}</div>
              {x.decision && <div className="text-[12px] text-accent mt-0.5"><Vote size={11} className="inline mr-1" />Público decide: {x.decision.question} — A: {x.decision.options.A} · B: {x.decision.options.B}</div>}
            </div>
          </li>))}
      </ol>
      {p.finale_tease && <p className="text-[12px] text-faint mt-2">Final anuncia: {p.finale_tease}</p>}
      {!data.arc_id && <button className="btn btn-sm btn-primary mt-3" onClick={start}><Play size={13} /> Produzir a série (parte 1 → {p.parts_count})</button>}
    </div>
  )
}

/** Quadro das séries do canal (aba Séries do Modo História). */
export function SeriesBoard({ channelId }: { channelId: number }) {
  const { data, isLoading } = useApi<{ dedicated: boolean; series: Serie[]; pending: { idea_id: number; title: string; status: string; plan: Plan }[]; vote_wait_hours: number }>(`/story/${channelId}/series`, { refetchInterval: 60_000 })
  const [busy, setBusy] = useState(false)
  const [mode, setMode] = useState<'sequencial' | 'opcoes'>('opcoes')
  if (isLoading || !data) return <Skeleton className="h-60" />
  const plan = () => { setBusy(true); act(() => api(`/story/${channelId}/series/new`, { body: { count: 2, mode } }), `Planejando 2 séries ${mode === 'sequencial' ? 'sequenciais' : 'com opções A/B'}…`).finally(() => setBusy(false)) }
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <div className="text-[13px] text-muted flex-1">
          {data.dedicated ? `Canal de séries: cada pauta é uma série inteira; as partes saem em ordem nos horários do canal. Votação A/B fica aberta ~${data.vote_wait_hours}h depois da parte ir ao ar.`
            : 'Este canal não é dedicado ao Modo História (as séries planejadas valem só para canais dedicados).'}
        </div>
        <div className="seg" title="Sequencial: a história segue sozinha. Com opções: 1-2 escolhas A/B do público por série.">
          {([['sequencial', 'Sequencial'], ['opcoes', 'Com opções A/B']] as const).map(([k, l]) =>
            <button key={k} type="button" data-active={mode === k} onClick={() => setMode(k)}>{l}</button>)}
        </div>
        <button className="btn btn-sm" disabled={busy} onClick={plan}>{busy ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />} Planejar séries</button>
        <button className="btn btn-sm btn-ghost" onClick={() => act(() => api(`/story/${channelId}/series/tick`, { method: 'POST' }), 'Séries atualizadas').then(() => invalidate(`/story/${channelId}/series`))}>Atualizar agora</button>
      </div>
      {data.series.map(s => <SerieCard key={s.id} cid={channelId} s={s} />)}
      {!!data.pending.length && (
        <section className="card overflow-hidden">
          <div className="card-head"><div className="card-title">Próximas séries (pautas)</div></div>
          <div className="divide-y divide-line">
            {data.pending.map(p => (
              <div key={p.idea_id} className="p-3 text-[13px] flex items-center gap-3">
                <Film size={14} className="text-faint" />
                <div className="flex-1 min-w-0"><b>{p.title}</b> <span className="text-muted">· {p.plan.parts_count} partes · {GENRE[p.plan.genre] ?? p.plan.genre}</span>
                  <div className="text-[12px] text-faint truncate">{p.plan.logline}</div></div>
                <span className="badge">{p.plan.mode === 'sequencial' ? 'sequencial' : 'com opções'}</span>
                <span className={clsx('badge', p.status === 'approved' && 'badge-ok')}>{p.status === 'approved' ? 'aprovada' : 'na fila'}</span>
                <button className="btn btn-sm btn-ghost text-bad" title="Apagar esta pauta-série" onClick={() => deleteSerie(channelId, p.idea_id, p.title)}><Trash2 size={13} /></button>
              </div>))}
          </div>
        </section>)}
      {!data.series.length && !data.pending.length && <div className="card p-6 text-[13px] text-muted">Nenhuma série ainda — clique em “Planejar séries”.</div>}
    </div>
  )
}

/** Cancela tudo da série na fila e apaga do painel (o que já foi ao ar continua no YouTube). */
export const deleteSerie = (cid: number, key: string | number, title: string) => {
  if (!window.confirm(`Cancelar e apagar a série "${title}"?

Para o que estiver na fila e apaga roteiros e vídeos que ainda não foram ao ar. Partes já publicadas continuam no YouTube.`)) return
  act(() => api(`/story/${cid}/series/${key}`, { method: 'DELETE' }), 'Série cancelada e apagada')
    .then(() => { invalidate(`/story/${cid}/series`); invalidate('/ideas'); invalidate('/videos'); invalidate('/jobs') })
}

function SerieCard({ cid, s }: { cid: number; s: Serie }) {
  const done = s.parts.filter(p => p.status === 'no ar').length
  return (
    <section className="card overflow-hidden">
      <div className="card-head">
        <div className="min-w-0">
          <div className="card-title">{s.title} <span className="text-faint font-normal">· {GENRE[s.genre] ?? s.genre} · {done}/{s.parts.length} no ar</span></div>
          <div className="card-sub">{s.logline}</div>
        </div>
        <div className="flex items-center gap-2">
          {s.blocked && <span className="badge badge-warn">{s.blocked}</span>}
          <span className={clsx('badge', s.status === 'closed' && 'badge-ok')}>{s.status === 'closed' ? 'terminada' : s.status === 'written' ? 'escrita' : 'em andamento'}</span>
          {s.status === 'closed' && !s.long && <button className="btn btn-sm" onClick={() => act(() => api(`/story/${cid}/arcs/${s.id}/long`, { method: 'POST' }), 'Versão completa na fila')}><Clapperboard size={13} /> Versão completa</button>}
          {s.long && <span className="badge badge-accent">versão completa #{s.long.script_id}</span>}
          <button className="btn btn-sm btn-ghost text-bad" title="Cancelar e apagar a série" onClick={() => deleteSerie(cid, s.id, s.title)}><Trash2 size={13} /></button>
        </div>
      </div>
      <div className="divide-y divide-line">
        {s.parts.map(p => <PartRow key={p.n} cid={cid} arc={s.id} p={p} />)}
      </div>
    </section>
  )
}

function PartRow({ cid, arc, p }: { cid: number; arc: string; p: SPart }) {
  const [a, setA] = useState<string>(String(p.votes?.manual?.A ?? ''))
  const [b, setB] = useState<string>(String(p.votes?.manual?.B ?? ''))
  const savePoll = () => act(() => api(`/story/${cid}/arcs/${arc}/parts/${p.n}/poll`, { body: { A: Number(a) || 0, B: Number(b) || 0 } }), 'Enquete somada aos votos')
    .then(() => invalidate(`/story/${cid}/series`))
  const decideNow = () => act(() => api(`/story/${cid}/arcs/${arc}/parts/${p.n}/decide`, { method: 'POST' }), 'Votação encerrada').then(() => invalidate(`/story/${cid}/series`))
  // botão do painel: escolhe o caminho e já gera a próxima parte (roteiro → imagens → vídeo)
  const pick = (c: 'A' | 'B') => act(() => api(`/story/${cid}/arcs/${arc}/parts/${p.n}/decide`, { body: { choice: c, generate: true } }),
    `Gerando a parte ${p.n + 1} com a opção ${c}…`).then(() => { invalidate(`/story/${cid}/series`); invalidate('/jobs') })
  return (
    <div className="p-3 flex gap-3 items-start">
      {p.video?.thumbnail ? <img src={mediaUrl(p.video.thumbnail)} alt="" className="w-10 aspect-[9/16] object-cover rounded bg-panel2" />
        : <div className="w-10 aspect-[9/16] rounded bg-panel2 grid place-items-center text-faint text-[11px]">{p.n}</div>}
      <div className="flex-1 min-w-0 text-[13px]">
        <div className="flex flex-wrap items-center gap-2">
          <b>Parte {p.n}: {p.title}</b>
          <span className={clsx('badge', STATUS_TONE[p.status])}>{p.status === 'no ar' && <CheckCircle2 size={11} />}{p.status}</span>
          {p.scheduled_at && p.status !== 'no ar' && <span className="text-[11.5px] text-faint">{new Date(p.scheduled_at).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}</span>}
          {p.url && <a className="text-[11.5px] text-accent" href={p.url} target="_blank" rel="noreferrer">abrir</a>}
        </div>
        <div className="text-[12px] text-muted">{p.goal}</div>
        {p.decision && (
          <div className="mt-1.5 rounded-md border border-line2 p-2 text-[12px]">
            <div className="flex items-center gap-1.5"><Vote size={12} className="text-accent" /> {p.decision.question} — <b>A</b>: {p.decision.options.A} · <b>B</b>: {p.decision.options.B}</div>
            {p.votes && <div className="text-faint mt-1">Comentários A {p.votes.comments.A} × B {p.votes.comments.B} · enquete A {p.votes.manual.A} × B {p.votes.manual.B} · total A {p.votes.total.A} × B {p.votes.total.B}</div>}
            {!p.choice && (
              <div className="mt-2 grid sm:grid-cols-2 gap-2">
                {(['A', 'B'] as const).map(c => (
                  <button key={c} className="btn btn-sm justify-start text-left !h-auto py-1.5" onClick={() => pick(c)}
                    title={`Escolher ${c} e gerar a parte ${p.n + 1}`}>
                    <span className="badge badge-accent">{c}</span>
                    <span className="flex-1 min-w-0"><span className="block text-[11px] text-faint">Gerar parte {p.n + 1} com</span><span className="block truncate">{p.decision!.options[c]}</span></span>
                  </button>
                ))}
              </div>)}
            {p.choice ? <div className="mt-1 text-ok">Escolha: {p.choice} ({p.decision.options[p.choice]}) · {p.decided_by === 'votos' ? 'pelos votos' : p.decided_by === 'painel' ? 'escolhida no painel' : 'padrão do plano (poucos votos)'}</div>
              : p.status === 'no ar' ? (
                <div className="mt-1.5 flex flex-wrap items-center gap-2">
                  <span className="text-faint">Enquete da aba Posts:</span>
                  <input className="input !h-7 !w-16" placeholder="A" value={a} onChange={e => setA(e.target.value)} />
                  <input className="input !h-7 !w-16" placeholder="B" value={b} onChange={e => setB(e.target.value)} />
                  <button className="btn btn-sm" onClick={savePoll}>Somar</button>
                  <button className="btn btn-sm btn-ghost" onClick={decideNow}>Encerrar votação agora</button>
                  {p.vote_until && <span className="text-faint">fecha {new Date(p.vote_until * 1000).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}</span>}
                </div>) : <div className="text-faint mt-1">A votação abre quando a parte for ao ar.</div>}
          </div>)}
      </div>
    </div>
  )
}
