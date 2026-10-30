import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Sparkles, PenLine, Check, X, FileText, ShieldCheck, RefreshCw, Trash2, ExternalLink, Lightbulb, Clapperboard, Flame,
  Zap, TrendingUp, Quote, Search, Target, Copy, MessageCircle, GraduationCap,
} from 'lucide-react'
import clsx from 'clsx'
import { api, invalidate, useApi, type Idea } from '../api'
import { act, Empty, Field, Menu, Modal, PageHeader, ScoreRing, Status, Tabs, toast, useChannel } from '../ui'
import { Bar, Callout, RowsSkeleton, useProgressive } from './kit'

const TABS = [
  { k: 'new,approved', label: 'Na fila' },
  { k: 'new', label: 'Novas' },
  { k: 'approved', label: 'Aprovadas' },
  { k: 'rejected', label: 'Rejeitadas' },
]
const CRIT: Record<string, string> = {
  gancho: 'Gancho', curiosidade: 'Curiosidade', relevancia: 'Relevância', emocao: 'Emoção',
  visual: 'Visual', compartilhamento: 'Compartilhável', originalidade: 'Originalidade', veracidade: 'Veracidade',
  busca: 'Busca', momento: 'Momento',
}
const BASE_CRIT = ['gancho', 'curiosidade', 'relevancia', 'emocao', 'visual', 'compartilhamento', 'originalidade', 'veracidade']
const VIRAL: Record<string, string> = { busca: 'Busca', curiosidade: 'Curiosidade', emocao: 'Emoção', momento: 'Momento' }

/** Origem da pauta com destaque: pergunta de um espectador (comentário) ou banco de questões no estilo ENEM. */
function OriginBadge({ i }: { i: Idea }) {
  if (i.origin === 'comment') {
    const who = i.tags?.find(t => t.startsWith('autor:'))?.slice(6)
    return <span className="badge badge-accent" data-tip={who ? `Pergunta de ${who} nos comentários` : 'Pergunta do público nos comentários'}>
      <MessageCircle size={11} />Comentário{who ? ` · ${who}` : ''}</span>
  }
  if (i.origin === 'enem_bank') return <span className="badge badge-ok" data-tip="Tema recorrente no ENEM (pergunta autoral no estilo da prova; provas oficiais: INEP)"><GraduationCap size={11} />Banco ENEM</span>
  if (i.origin === 'trend') return <span className="badge badge-warn"><Flame size={11} />Tendência{i.tags?.[1]?.includes('alta') ? ' · urgente' : ''}</span>
  return null
}

// ---------------------------------------------------------------- campos novos da nota (opcionais; o backend pode não mandar)

type Viral = Partial<Record<'busca' | 'curiosidade' | 'emocao' | 'momento', number>>
type Prediction = { score: number; low?: number; high?: number; reasons?: string[]; similar?: any[]; confidence?: string | number }
type Breakdown = Idea['score_breakdown'] & {
  discovery?: { hook?: string; search_query?: string; viral?: Viral; viral_score?: number; rank_score?: number }
  better_hook?: string; prediction?: Prediction | null; viral?: Viral; viral_score?: number
}
type IdeaX = Idea & { score_breakdown: Breakdown; facts_count?: number; sources_count?: number; better_title?: string | null }

/** Junta o que veio da nota (score) e o que veio da descoberta (radar/busca). */
function insights(i: IdeaX) {
  const sb = (i.score_breakdown ?? {}) as Breakdown
  const disc = sb.discovery ?? {}
  return {
    viralScore: sb.viral_score ?? disc.viral_score ?? null,
    viral: sb.viral ?? disc.viral ?? null,
    hook: sb.better_hook || disc.hook || '',
    query: disc.search_query || '',
    pred: sb.prediction && typeof sb.prediction.score === 'number' ? sb.prediction : null,
    betterTitle: sb.better_title || i.better_title || '',
  }
}
const conf = (c: Prediction['confidence']) => c == null ? '' : typeof c === 'number' ? (c >= 0.66 ? 'alta' : c >= 0.33 ? 'média' : 'baixa') : String(c)
const tone = (v: number) => v >= 75 ? 'text-ok' : v >= 55 ? 'text-warn' : 'text-bad'
/** previsão é percentil (50 = típico do canal) */
const predTone = (v: number) => v >= 60 ? 'text-ok' : v >= 40 ? 'text-warn' : 'text-bad'

function ViralBadge({ v, compact }: { v: number | null; compact?: boolean }) {
  if (v == null) return null
  return (
    <span className={clsx('badge', v >= 70 ? 'badge-accent' : '')} data-tip="Potencial viral (busca, curiosidade, emoção, momento)">
      <Zap size={11} className={v >= 70 ? 'text-accent2' : 'text-muted'} /><span className="num">{Math.round(v)}</span>{!compact && <span className="text-muted">viral</span>}
    </span>
  )
}

export default function Ideas() {
  const { channel } = useChannel()
  const [tab, setTab] = useState(TABS[0].k)
  const [sort, setSort] = useState<'score' | 'viral' | 'date'>('score')
  const [q, setQ] = useState('')
  const [open, setOpen] = useState<IdeaX | null>(null)
  const [newOpen, setNewOpen] = useState(false)
  const [params, setParams] = useSearchParams()
  useEffect(() => { if (params.get('nova')) { setNewOpen(true); setParams({}, { replace: true }) } }, [params, setParams])
  const [discOpen, setDiscOpen] = useState(false)
  // lista completa (não slim): a linha mostra potencial viral e previsão, que vêm de score_breakdown
  const { data = [], isLoading } = useApi<IdeaX[]>(channel ? `/ideas?channel_id=${channel.id}&status=${tab}` : null)
  const list = useMemo(() => {
    const s = q.trim().toLowerCase()
    const f = s ? data.filter(i => (i.title + ' ' + (i.angle ?? '')).toLowerCase().includes(s)) : data
    return [...f].sort((a, b) => sort === 'score' ? (b.score ?? -1) - (a.score ?? -1)
      : sort === 'viral' ? (insights(b).viralScore ?? -1) - (insights(a).viralScore ?? -1) : b.id - a.id)
  }, [data, sort, q])
  const [shown, more] = useProgressive(list, 60, tab + sort + q)

  const patch = (i: Idea, body: Partial<Idea>) => act(() => api(`/ideas/${i.id}`, { method: 'PATCH', body })).then(() => invalidate('/ideas'))
  const video = (i: Idea) => act(() => api(`/ideas/${i.id}/script`, { body: { auto_render: true } }), 'Roteiro + vídeo na fila!').then(() => invalidate('/jobs'))

  return (
    <>
      <PageHeader eyebrow={channel?.name} title="Pautas" subtitle="A IA busca, verifica e dá nota de 0 a 100. Você aprova ou propõe as suas."
        actions={<>
          <button className="btn" onClick={() => channel && act(() => api(`/channels/${channel.id}/radar`, { body: {} }), 'Radar de tendências rodando — as pautas aparecem em instantes')}><Flame size={15} /> Radar</button>
          <button className="btn" onClick={() => setNewOpen(true)}><PenLine size={15} /> Escrever pauta</button>
          <button className="btn btn-primary" onClick={() => setDiscOpen(true)}><Sparkles size={15} /> Buscar com IA</button>
        </>} />

      <div className="flex flex-wrap items-end justify-between gap-3 mb-4">
        <Tabs value={tab} onChange={setTab} items={TABS.map(t => ({ key: t.k, label: t.label, count: t.k === tab && !isLoading ? data.length : undefined }))} />
        <div className="flex items-center gap-2 pb-1.5">
          <div className="relative">
            <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-faint" />
            <input className="input h-8! w-52 pl-8!" placeholder="Filtrar pautas…" value={q} onChange={e => setQ(e.target.value)} />
          </div>
          <div className="seg">
            <button data-active={sort === 'score'} onClick={() => setSort('score')}>Maior nota</button>
            <button data-active={sort === 'viral'} onClick={() => setSort('viral')}><Zap size={12} />Viral</button>
            <button data-active={sort === 'date'} onClick={() => setSort('date')}>Recentes</button>
          </div>
        </div>
      </div>

      {isLoading && !data.length && <div className="card"><RowsSkeleton rows={6} h="h-11" /></div>}
      {!isLoading && list.length === 0 && <Empty icon={<Lightbulb size={20} />} title={q ? 'Nada com esse filtro' : 'Nenhuma pauta aqui'}
        text={q ? 'Tente outra palavra.' : 'Peça para a IA buscar pautas na internet ou escreva a sua ideia.'}
        action={!q && <button className="btn btn-primary" onClick={() => setDiscOpen(true)}><Sparkles size={15} /> Buscar com IA</button>} />}

      {!!list.length && (
        <div className="card overflow-hidden"><div className="overflow-x-auto">
          <table className="tbl">
            <thead><tr><th className="w-14">Nota</th><th>Pauta</th><th>Potencial</th><th>Origem</th><th>Checagem</th><th>Status</th><th className="right w-[150px]"><span className="sr-only">Ações</span></th></tr></thead>
            <tbody>
              {shown.map(i => {
                const x = insights(i)
                return (
                  <tr key={i.id} className="cursor-pointer group" onClick={() => setOpen(i)}>
                    <td><ScoreRing score={i.score} size={34} /></td>
                    <td className="max-w-0 w-[44%]">
                      <div className="font-medium truncate group-hover:text-text">{i.title}</div>
                      <div className="text-[12.5px] text-muted truncate">
                        {x.hook ? <span className="inline-flex items-center gap-1"><Quote size={11} className="text-faint shrink-0" />{x.hook}</span>
                          : i.origin === 'trend' && i.tags?.[0] ? i.tags[0] : (i.angle || i.summary)}
                      </div>
                    </td>
                    <td>
                      <div className="flex items-center gap-1.5">
                        <ViralBadge v={x.viralScore} compact />
                        {x.pred && <span className="badge" data-tip="Nota prevista pelo histórico do canal">
                          <TrendingUp size={11} className="text-muted" /><span className="num">{x.pred.low != null && x.pred.high != null ? `${Math.round(x.pred.low)}–${Math.round(x.pred.high)}` : Math.round(x.pred.score)}</span></span>}
                        {x.viralScore == null && !x.pred && <span className="text-faint">—</span>}
                      </div>
                    </td>
                    <td className="whitespace-nowrap text-muted">
                      {['trend', 'comment', 'enem_bank'].includes(i.origin) ? <OriginBadge i={i} />
                        : <span>{i.origin === 'manual' ? 'Sua ideia' : i.origin === 'champion' ? 'Short campeão' : 'IA'}</span>} <span className="text-faint">· {i.format === 'long' ? 'Longo' : 'Short'}</span>
                    </td>
                    <td><Status s={i.fact_status} /></td>
                    <td><Status s={i.status} /></td>
                    <td className="right" onClick={e => e.stopPropagation()}>
                      <div className="flex items-center justify-end gap-1">
                        <button className="btn btn-sm" onClick={() => video(i)}><Clapperboard size={13} /> Vídeo</button>
                        <Menu items={[
                          ...(i.status !== 'approved' ? [{ label: 'Aprovar', icon: <Check size={15} />, onClick: () => patch(i, { status: 'approved' }) }] : []),
                          { label: 'Só gerar roteiro', icon: <FileText size={15} />, onClick: () => act(() => api(`/ideas/${i.id}/script`, { body: {} }), 'Escrevendo roteiro…') },
                          { label: 'Ver detalhes', icon: <Lightbulb size={15} />, onClick: () => setOpen(i) },
                          'sep',
                          ...(i.status !== 'rejected' ? [{ label: 'Rejeitar', icon: <X size={15} />, danger: true, onClick: () => patch(i, { status: 'rejected' }) }] : []),
                          { label: 'Excluir', icon: <Trash2 size={15} />, danger: true, onClick: () => act(() => api(`/ideas/${i.id}`, { method: 'DELETE' })).then(() => invalidate('/ideas')) },
                        ]} />
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          {more}
        </div></div>
      )}

      {open && <IdeaModal base={data.find(x => x.id === open.id) ?? open} onClose={() => setOpen(null)} />}
      <NewIdeaModal open={newOpen} onClose={() => setNewOpen(false)} />
      <DiscoverModal open={discOpen} onClose={() => setDiscOpen(false)} />
    </>
  )
}

const Block = ({ label, icon, children, className }: { label: string; icon?: ReactNode; children: ReactNode; className?: string }) => (
  <div className={className}>
    <div className="label flex items-center gap-1.5">{icon}{label}</div>
    {children}
  </div>
)

function IdeaModal({ base, onClose }: { base: IdeaX; onClose: () => void }) {
  // item completo (fatos/fontes/nota detalhada); se a rota ainda não existir, fica o item da lista
  const { data: full, isLoading: loadingFull } = useApi<IdeaX>(`/ideas/${base.id}`, { keepPrevious: false })
  const idea: IdeaX = full && full.id === base.id ? { ...base, ...full } : base
  const crit = idea.score_breakdown?.criteria ?? {}
  const x = insights(idea)
  const run = (a: string, msg: string) => act(() => api(`/ideas/${idea.id}/${a}`, { body: {} }), msg)
  const copy = (t: string) => navigator.clipboard.writeText(t).then(() => toast.ok('Copiado'))
  const facts = idea.facts ?? []
  const sources = idea.sources ?? []
  const extraCrit = Object.keys(crit).filter(k => !(k in CRIT))
  return (
    <Modal open onClose={onClose} title="Detalhes da pauta" wide>
      <div className="flex gap-5 mb-5">
        <ScoreRing score={idea.score} size={84} />
        <div className="flex-1 min-w-0">
          <h2 className="text-[18px] font-semibold leading-snug">{idea.title}</h2>
          {idea.angle && <p className="text-muted mt-1">{idea.angle}</p>}
          <div className="flex flex-wrap gap-2 mt-3">
            <Status s={idea.status} /><Status s={idea.fact_status} />
            <ViralBadge v={x.viralScore} />
            <OriginBadge i={idea} />
            <span className="badge text-muted">{idea.format === 'long' ? 'Vídeo longo' : 'Short'}</span>
          </div>
        </div>
      </div>

      {/* faixa de previsão + potencial viral */}
      {(x.pred || x.viral) && (
        <div className="grid md:grid-cols-2 gap-3 mb-6">
          {x.pred && (
            <div className="surface-2 p-4">
              <div className="flex items-center justify-between">
                <div className="label !mb-0 flex items-center gap-1.5"><TrendingUp size={12} />Desempenho previsto</div>
                {conf(x.pred.confidence) && <span className="text-[11.5px] text-faint">confiança {conf(x.pred.confidence)}</span>}
              </div>
              <div className="flex items-baseline gap-2 mt-2">
                <span className={clsx('text-[28px] font-semibold num leading-none', predTone(x.pred.score))}>{Math.round(x.pred.score)}</span>
                {x.pred.low != null && x.pred.high != null && <span className="text-[13px] text-muted num">faixa {Math.round(x.pred.low)}–{Math.round(x.pred.high)}</span>}
              </div>
              {x.pred.low != null && x.pred.high != null && (
                <div className="relative h-1.5 rounded-full bg-line mt-3">
                  <div className="absolute h-full rounded-full bg-grad opacity-60" style={{ left: `${x.pred.low}%`, width: `${Math.max(2, x.pred.high - x.pred.low)}%` }} />
                  <div className="absolute -top-[3px] w-[3px] h-3 rounded-full bg-text" style={{ left: `calc(${x.pred.score}% - 1.5px)` }} />
                </div>
              )}
              {!!x.pred.reasons?.length && <ul className="text-[12.5px] text-muted mt-3 space-y-1">{x.pred.reasons.slice(0, 4).map((r, k) => <li key={k} className="flex gap-1.5"><span className="text-faint">•</span>{r}</li>)}</ul>}
              {!!x.pred.similar?.length && <div className="text-[11.5px] text-faint mt-2">com base em {x.pred.similar.length} vídeo(s) parecido(s) do canal</div>}
            </div>
          )}
          {x.viral && (
            <div className="surface-2 p-4">
              <div className="flex items-center justify-between">
                <div className="label !mb-0 flex items-center gap-1.5"><Zap size={12} />Potencial viral</div>
                {x.viralScore != null && <span className="text-[20px] font-semibold num text-gradient leading-none">{Math.round(x.viralScore)}</span>}
              </div>
              <div className="space-y-2 mt-3">
                {Object.entries(VIRAL).map(([k, label]) => {
                  const v = (x.viral as Viral)[k as keyof Viral]
                  return v == null ? null : (
                    <div key={k} className="flex items-center gap-3 text-[12.5px]">
                      <span className="w-24 text-muted">{label}</span>
                      <Bar value={v} className="flex-1" />
                      <span className="w-7 text-right num">{Math.round(v)}</span>
                    </div>
                  )
                })}
              </div>
              {x.query && <div className="text-[12px] text-muted mt-3 flex items-center gap-1.5 min-w-0"><Search size={12} className="shrink-0 text-faint" />busca: <span className="text-text truncate">“{x.query}”</span></div>}
            </div>
          )}
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-6">
        <div className="space-y-4">
          <Block label="Resumo verificado"><p className="text-sm leading-relaxed">{idea.summary}</p></Block>
          {x.hook && (
            <Block label="Gancho sugerido (1ª frase)" icon={<Quote size={12} />}>
              <div className="rounded-[var(--r-md)] border border-accent/30 bg-accent/[0.07] px-3 py-2.5 text-[14px] font-medium flex items-start gap-2">
                <span className="flex-1">“{x.hook}”</span>
                <button className="btn btn-sm btn-icon btn-ghost -mr-1 -mt-0.5" data-tip="Copiar" onClick={() => copy(x.hook)}><Copy size={13} /></button>
              </div>
            </Block>
          )}
          {x.betterTitle && x.betterTitle !== idea.title && (
            <Block label="Título sugerido" icon={<Target size={12} />}>
              <div className="flex items-start gap-2">
                <p className="text-sm text-text font-medium flex-1">{x.betterTitle}</p>
                <button className="btn btn-sm" onClick={() => act(() => api(`/ideas/${idea.id}`, { method: 'PATCH', body: { title: x.betterTitle } }), 'Título trocado').then(() => { invalidate('/ideas') })}>Usar</button>
              </div>
            </Block>
          )}
          {idea.score_reason && <Block label="Por que essa nota"><p className="text-sm text-text/80">{idea.score_reason}</p></Block>}
          {!!idea.score_breakdown?.improvements?.length && (
            <Block label="Como melhorar">
              <ul className="text-sm space-y-1.5 text-text/85">{idea.score_breakdown.improvements.map((t, k) => <li key={k} className="flex gap-2"><Check size={13} className="text-accent2 shrink-0 mt-1" />{t}</li>)}</ul>
            </Block>
          )}
        </div>
        <Block label="Critérios">
          <div className="space-y-2">
            {[...BASE_CRIT, ...['busca', 'momento'].filter(k => k in crit), ...extraCrit].map(k => (
              <div key={k} className="flex items-center gap-3 text-sm">
                <span className="w-28 text-muted truncate">{CRIT[k] ?? k}</span>
                <Bar value={crit[k] ?? 0} className="flex-1" tone={crit[k] == null ? 'muted' : undefined} />
                <span className={clsx('w-8 text-right num', crit[k] != null && tone(crit[k]))}>{crit[k] ?? '–'}</span>
              </div>
            ))}
          </div>
        </Block>
      </div>

      {loadingFull && !idea.facts && (idea.facts_count || idea.sources_count) ? <div className="mt-6"><RowsSkeleton rows={2} h="h-10" className="!p-0" /></div> : null}
      {facts.length > 0 && <>
        <div className="label mt-6">Checagem de fatos</div>
        <div className="space-y-2">
          {facts.map((f, k) => (
            <div key={k} className="text-sm p-3 rounded-[var(--r-md)] bg-panel2 border border-line">
              <span className={clsx('badge mr-2', f.verdict === 'confirmado' ? 'badge-ok' : f.verdict === 'falso' ? 'badge-bad' : 'badge-warn')}>{f.verdict}</span>
              {f.claim}
              {f.note && <div className="text-xs text-muted mt-1">{f.note}</div>}
            </div>
          ))}
        </div>
      </>}
      {sources.length > 0 && <>
        <div className="label mt-6">Fontes</div>
        <div className="space-y-1">
          {sources.map((s, k) => (
            <a key={k} href={s.url} target="_blank" rel="noreferrer" className="flex items-center gap-2 text-sm text-info hover:underline truncate">
              <ExternalLink size={13} className="shrink-0" /> {s.title || s.url}</a>
          ))}
        </div>
      </>}
      {idea.fact_status === 'disputed' && <Callout tone="bad" className="mt-5">As fontes contestam parte desta pauta — revise antes de produzir.</Callout>}
      <div className="flex flex-wrap gap-2 mt-6 pt-4 border-t border-line">
        <button className="btn" onClick={() => run('verify', 'Checando fatos…')}><ShieldCheck size={15} /> Checar fatos</button>
        <button className="btn" onClick={() => run('score', 'Reavaliando…')}><RefreshCw size={15} /> Reavaliar nota</button>
        <button className="btn btn-danger" onClick={() => act(() => api(`/ideas/${idea.id}`, { method: 'DELETE' })).then(() => { invalidate('/ideas'); onClose() })}><Trash2 size={15} /> Excluir</button>
        <div className="flex-1" />
        <button className="btn" onClick={() => run('script', 'Escrevendo roteiro…')}><FileText size={15} /> Gerar roteiro</button>
        <button className="btn btn-primary" onClick={() => act(() => api(`/ideas/${idea.id}/script`, { body: { auto_render: true } }), 'Roteiro + vídeo na fila!').then(onClose)}><Clapperboard size={15} /> Produzir vídeo</button>
      </div>
    </Modal>
  )
}

function NewIdeaModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { channel } = useChannel()
  const [f, setF] = useState({ title: '', angle: '', summary: '', format: 'short' })
  const submit = () => channel && act(() => api('/ideas', { body: { ...f, channel_id: channel.id } }), 'Pesquisando e validando sua ideia…')
    .then(r => { if (r) { invalidate('/ideas'); setF({ title: '', angle: '', summary: '', format: 'short' }); onClose() } })
  return (
    <Modal open={open} onClose={onClose} title="Escrever minha pauta">
      <div className="space-y-4">
        <Field label="Tema ou título"><input className="input" autoFocus value={f.title} onChange={e => setF({ ...f, title: e.target.value })} placeholder="Ex.: Por que Dom Pedro II foi exilado?" /></Field>
        <Field label="Ângulo / o que é surpreendente (opcional)"><textarea className="input min-h-20" value={f.angle} onChange={e => setF({ ...f, angle: e.target.value })} /></Field>
        <Field label="O que você já sabe (opcional)"><textarea className="input min-h-20" value={f.summary} onChange={e => setF({ ...f, summary: e.target.value })} /></Field>
        <Field label="Formato">
          <div className="seg w-full">
            {[['short', 'Short vertical (60s+)'], ['long', 'Vídeo longo (5min+)']].map(([k, l]) => (
              <button key={k} type="button" className="flex-1 justify-center" data-active={f.format === k} onClick={() => setF({ ...f, format: k })}>{l}</button>
            ))}
          </div>
        </Field>
        <p className="text-xs text-muted">O sistema vai pesquisar fontes, verificar se é verdade, corrigir o resumo e dar uma nota de 0 a 100.</p>
        <button className="btn btn-primary btn-lg w-full" disabled={!f.title} onClick={submit}><ShieldCheck size={16} /> Validar ideia</button>
      </div>
    </Modal>
  )
}

function DiscoverModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { channel } = useChannel()
  const [f, setF] = useState({ seed: '', count: 8, format: 'short' })
  const submit = () => channel && act(() => api('/ideas/discover', { body: { ...f, channel_id: channel.id } }), 'Buscando pautas na internet…').then(onClose)
  return (
    <Modal open={open} onClose={onClose} title="Buscar pautas com IA">
      <div className="space-y-4">
        <Field label="Direcionar a busca (opcional)" hint="Deixe vazio para a IA buscar em 'neste dia na história', notícias e no que performou bem.">
          <input className="input" autoFocus value={f.seed} onChange={e => setF({ ...f, seed: e.target.value })} placeholder="Ex.: Revolução Francesa, Era Vargas, mitos do Egito" />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Quantidade"><input type="number" min={1} max={20} className="input" value={f.count} onChange={e => setF({ ...f, count: Number(e.target.value) })} /></Field>
          <Field label="Formato">
            <div className="seg w-full">
              {[['short', 'Short'], ['long', 'Longo']].map(([k, l]) => (
                <button key={k} type="button" className="flex-1 justify-center" data-active={f.format === k} onClick={() => setF({ ...f, format: k })}>{l}</button>
              ))}
            </div>
          </Field>
        </div>
        <button className="btn btn-primary btn-lg w-full" onClick={submit}><Sparkles size={16} /> Buscar</button>
      </div>
    </Modal>
  )
}
