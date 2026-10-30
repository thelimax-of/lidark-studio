import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import clsx from 'clsx'
import { FlaskConical, Sparkles, Check, X, Trophy, Wand2, Loader2, ExternalLink, Image as ImageIcon } from 'lucide-react'
import { api, invalidate, mediaUrl, useApi } from '../api'
import { act, ChannelTag, Empty, PageHeader, ScoreRing, SectionTitle, Skeleton, fmtNum, useChannel } from '../ui'

type QItem = { script_id: number; video_id: number | null; channel_id: number; title: string; format: string; stage: string; thumbnail_path: string; heuristic: number; fails: number }
type Check_ = { id: string; ok: boolean; label: string; detail: string; fix: string; weight: number; field: string }
type Pred = { score?: number; low?: number; high?: number; reasons?: string[]; similar?: { title: string; views: number; url?: string; x?: number }[]; views_48h?: { mid: number; low: number; high: number }; confidence?: string } | null
type Opt = { title?: string; thumbnail_text?: string; hook?: string; style?: string; why?: string; prediction?: Pred }
type Analysis = {
  script: { id: number; title: string; hook: string; thumbnail_text: string; format: string; status: string; seconds: number; channel_id: number; channel: string }
  video: { id: number; status: string; thumbnail_path: string } | null
  publications: { id: number; status: string; title: string; url: string; scheduled_at: string | null }[]
  score: number; heuristic: number; prediction: Pred; checks: Check_[]; checklist: Check_[]
  champions: { title: string; views: number; retention?: number; url?: string; thumbnail?: string; reasons: string[] }[]
  compare: Record<string, { mine: number | boolean; champions: number }>
  suggestions: Opt[]; applied: { at: string; field: string; before: string; after: string }[]; hook_editable: boolean
}

const CMP: Record<string, string> = { title_len: 'Tamanho do título', number: 'Tem número', question: 'É pergunta', curiosity: 'Lacuna de curiosidade' }

export default function ViralLab() {
  const { channel } = useChannel()
  const [params, setParams] = useSearchParams()
  const { data: queue, isLoading } = useApi<QItem[]>(channel ? `/viral/queue?channel_id=${channel.id}` : null)
  const sid = Number(params.get('script')) || queue?.[0]?.script_id || null
  const vid = Number(params.get('video')) || null
  const path = vid ? `/viral/video/${vid}` : sid ? `/viral/script/${sid}` : null
  return (
    <div>
      <PageHeader eyebrow="Criar" title="Laboratório viral"
        subtitle="Antes de publicar: nota de potencial viral (modelo do canal + checagens), comparação com os campeões e 3 alternativas de título e miniatura — aplicar é um clique." />
      <div className="grid gap-4 lg:grid-cols-[320px_1fr] items-start">
        <section className="card overflow-hidden">
          <SectionTitle hint="Vídeos prontos e roteiros ainda não publicados">Na fila para publicar</SectionTitle>
          {isLoading ? <div className="p-4"><Skeleton className="h-40" /></div> : !queue?.length ? (
            <div className="p-5 text-[13px] text-muted">Nada pronto agora. Abra um vídeo publicado pelo link “?video=ID” ou gere roteiros.</div>
          ) : (
            <ul className="divide-y divide-line max-h-[70vh] overflow-y-auto">
              {queue.map(q => (
                <li key={q.script_id}>
                  <button onClick={() => setParams({ script: String(q.script_id) })}
                    className={clsx('w-full text-left flex gap-3 px-3 py-2.5 hover:bg-white/[0.03]', q.script_id === sid && !vid && 'bg-white/[0.05]')}>
                    {q.thumbnail_path ? <img src={mediaUrl(q.thumbnail_path)} className={clsx('rounded object-cover shrink-0 bg-panel2', q.format === 'short' ? 'w-9 h-16' : 'w-20 h-11')} alt="" />
                      : <div className="w-9 h-16 rounded bg-panel2 shrink-0" />}
                    <div className="min-w-0 flex-1">
                      <div className="text-[13px] font-medium line-clamp-2">{q.title.replace(/#shorts/i, '')}</div>
                      <div className="text-[11.5px] text-muted mt-1">{q.stage} · {q.fails ? `${q.fails} ajuste(s)` : 'tudo ok'}</div>
                    </div>
                    <ScoreRing score={q.heuristic} size={34} />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
        {path ? <Lab path={path} /> : <Empty icon={<FlaskConical size={18} />} title="Escolha um vídeo" text="Selecione um item da fila ao lado." />}
      </div>
    </div>
  )
}

function PredLine({ p }: { p: Pred }) {
  if (!p) return null
  return (
    <span className="text-[12px] text-muted">
      modelo: <b className="text-text num">{p.score}</b>{p.low != null && <> ({p.low}–{p.high})</>}
      {p.views_48h && <> · ~{fmtNum(p.views_48h.mid)} views em 48 h</>}
    </span>
  )
}

function Lab({ path }: { path: string }) {
  const { data: a, isLoading } = useApi<Analysis>(path)
  const [busy, setBusy] = useState(false)
  const [yt, setYt] = useState(false)
  const [opts, setOpts] = useState<Opt[]>([])
  useEffect(() => { setOpts(a?.suggestions ?? []) }, [a?.script.id, a?.suggestions])
  if (isLoading || !a) return <Skeleton className="h-96" />
  const published = a.publications.some(p => p.status === 'published')
  const suggest = async () => {
    setBusy(true)
    const r = await act(() => api<{ suggestions: Opt[] }>(`/viral/script/${a.script.id}/suggest`, { method: 'POST' }))
    if (r) setOpts(r.suggestions)
    setBusy(false)
  }
  const apply = (body: Record<string, unknown>) =>
    act(() => api(`/viral/script/${a.script.id}/apply`, { body: { ...body, youtube: yt } }), 'Aplicado').then(r => {
      ['/viral', '/scripts', '/videos', '/thumbs'].forEach(invalidate)
      return r
    })
  return (
    <div className="space-y-4">
      <section className="card p-5">
        <div className="flex flex-wrap items-start gap-4">
          <ScoreRing score={a.score} size={72} />
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <ChannelTag id={a.script.channel_id} />
              <span className="badge">{a.script.format === 'short' ? 'Short' : 'Longo'} · {a.script.seconds} s</span>
              {a.video && <span className="badge">vídeo {a.video.status}</span>}
            </div>
            <h2 className="text-[17px] font-semibold leading-snug">{a.script.title.replace(/#shorts/i, '')}</h2>
            <div className="text-[13px] text-muted mt-1">Gancho: “{a.script.hook}”</div>
            <div className="text-[13px] text-muted">Miniatura: <b className="text-text">{a.script.thumbnail_text || '—'}</b></div>
            <div className="mt-2 flex flex-wrap gap-3 text-[12px] text-muted">
              <span>checagens: <b className="text-text num">{a.heuristic}</b>/100</span>
              <PredLine p={a.prediction} />
              {a.video && <Link className="text-info hover:underline" to={`/thumbs?video=${a.video.id}`}><ImageIcon size={12} className="inline" /> estúdio de miniaturas</Link>}
            </div>
            {!!a.prediction?.reasons?.length && (
              <ul className="mt-2 text-[12px] text-muted list-disc pl-4">{a.prediction.reasons.slice(0, 4).map((r, i) => <li key={i}>{r}</li>)}</ul>
            )}
          </div>
          {a.video?.thumbnail_path && <img src={mediaUrl(a.video.thumbnail_path)} alt="" className={clsx('rounded-lg border border-line object-cover', a.script.format === 'short' ? 'w-24 h-[170px]' : 'w-56 h-[126px]')} />}
        </div>
      </section>

      <section className="card overflow-hidden">
        <SectionTitle hint="O que segura o clique e a retenção — corrigir os itens em vermelho sobe a nota">Checklist antes de publicar</SectionTitle>
        <ul className="divide-y divide-line">
          {a.checks.map(c => (
            <li key={c.id} className="flex gap-3 px-4 py-2.5">
              <span className={clsx('mt-0.5', c.ok ? 'text-ok' : 'text-bad')}>{c.ok ? <Check size={15} /> : <X size={15} />}</span>
              <div className="min-w-0">
                <div className="text-[13px]"><b className="font-medium">{c.label}</b> <span className="text-muted">— {c.detail}</span></div>
                {!c.ok && c.fix && <div className="text-[12.5px] text-warn mt-0.5">{c.fix}</div>}
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section className="card overflow-hidden">
        <SectionTitle hint="Uma única chamada à IA, em estilos diferentes entre si (variedade: nada de fórmula repetida)"
          action={<div className="flex items-center gap-3">
            {published && <label className="flex items-center gap-1.5 text-[12.5px] text-muted"><input type="checkbox" checked={yt} onChange={e => setYt(e.target.checked)} /> trocar também no YouTube</label>}
            <button className="btn btn-sm btn-primary" disabled={busy} onClick={suggest}>{busy ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />} {opts.length ? 'Gerar de novo' : 'Gerar 3 alternativas'}</button>
          </div>}>
          <span className="inline-flex items-center gap-2"><Wand2 size={15} />Alternativas de título e miniatura</span>
        </SectionTitle>
        {!opts.length ? <div className="p-5 text-[13px] text-muted">Clique em “Gerar 3 alternativas”.</div> : (
          <ul className="divide-y divide-line">
            {opts.map((o, i) => (
              <li key={i} className="px-4 py-3 flex flex-wrap items-center gap-3">
                <div className="min-w-0 flex-1">
                  {o.title ? <>
                    <div className="text-[14px] font-medium">{o.title}</div>
                    <div className="text-[12.5px] text-muted mt-0.5">Miniatura: <b className="text-text">{o.thumbnail_text}</b>{o.style && <> · {o.style}</>}</div>
                  </> : <div className="text-[14px]">Gancho: “{o.hook}”</div>}
                  {o.why && <div className="text-[12px] text-faint mt-0.5">{o.why}</div>}
                  <PredLine p={o.prediction ?? null} />
                </div>
                {o.title ? <div className="flex gap-2">
                  <button className="btn btn-sm" onClick={() => apply({ title: o.title })}>Só o título</button>
                  <button className="btn btn-sm btn-primary" onClick={() => apply({ title: o.title, thumbnail_text: o.thumbnail_text })}>Aplicar tudo</button>
                </div> : <button className="btn btn-sm" disabled={!a.hook_editable} data-tip={a.hook_editable ? undefined : 'O vídeo já foi gerado'}
                  onClick={() => apply({ hook: o.hook })}>Usar gancho</button>}
              </li>
            ))}
          </ul>
        )}
        {!!a.applied.length && (
          <div className="px-4 py-3 border-t border-line text-[12px] text-muted space-y-0.5">
            {a.applied.slice(-4).reverse().map((c, i) => <div key={i}>{c.field}: “{c.before}” → <b className="text-text">“{c.after}”</b></div>)}
          </div>
        )}
      </section>

      <section className="card overflow-hidden">
        <SectionTitle hint="Inspire-se no porquê, não copie a fórmula"><span className="inline-flex items-center gap-2"><Trophy size={15} className="text-warn" />Comparação com os campeões do canal</span></SectionTitle>
        {!a.champions.length ? <div className="p-5 text-[13px] text-muted">O canal ainda não tem Shorts campeões com métricas.</div> : <>
          <div className="grid sm:grid-cols-4 gap-px bg-line">
            {Object.entries(a.compare).map(([k, v]) => (
              <div key={k} className="bg-panel p-3">
                <div className="text-[11.5px] text-muted">{CMP[k] ?? k}</div>
                <div className="text-[15px] font-semibold num">{typeof v.mine === 'boolean' ? (v.mine ? 'sim' : 'não') : v.mine}</div>
                <div className="text-[11.5px] text-faint">campeões: {k === 'title_len' ? v.champions : `${v.champions}%`}</div>
              </div>
            ))}
          </div>
          <ul className="divide-y divide-line">
            {a.champions.map((c, i) => (
              <li key={i} className="px-4 py-2.5 flex items-center gap-3">
                <div className="min-w-0 flex-1">
                  <div className="text-[13px] truncate">{c.title}</div>
                  <div className="text-[11.5px] text-muted">{fmtNum(c.views)} views{c.retention ? ` · retenção ${Math.round(c.retention)}%` : ''}{c.reasons[0] ? ` · ${c.reasons[0]}` : ''}</div>
                </div>
                {c.url && <a href={c.url} target="_blank" rel="noreferrer" className="btn btn-sm btn-icon btn-ghost"><ExternalLink size={14} /></a>}
              </li>
            ))}
          </ul>
        </>}
      </section>
    </div>
  )
}
