import { useEffect, useState, type ReactNode } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  Save, Clapperboard, ShieldCheck, Wand2, Trash2, Plus, ArrowUp, ArrowDown, ExternalLink, ImageIcon, Sparkles, AlertTriangle,
  ArrowLeft, Check, Copy, Type, MessageSquarePlus, Trophy, Image as Img, Layers,
} from 'lucide-react'
import clsx from 'clsx'
import { api, invalidate, mediaUrl, useApi, type Scene, type Script, type Video } from '../api'
import { act, Field, PageHeader, ScoreRing, Skeleton, Status, toast } from '../ui'
import { Bar, Callout } from './kit'
import { STRUCT } from './Scripts'

const WPS = 2.7

/** Campos que o roteirista grava em variety (opcionais: roteiros antigos não têm). */
type TitleLab = { options: string[]; scores: number[]; best: number; predicted?: boolean }
type Variety = NonNullable<Script['variety']> & {
  title_options?: string[]; thumb_options?: string[]; pinned_comment?: string; title_lab?: TitleLab
  hook_style?: string; title_style?: string
}
type Full = Script & { variety?: Variety; videos: Video[] }

function Card({ title, icon, hint, action, children, className }: { title: string; icon?: ReactNode; hint?: string; action?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={clsx('card overflow-hidden', className)}>
      <div className="card-head !py-3">
        <div className="min-w-0">
          <div className="card-title flex items-center gap-2">{icon && <span className="text-muted">{icon}</span>}{title}</div>
          {hint && <div className="card-sub">{hint}</div>}
        </div>
        {action}
      </div>
      <div className="p-4">{children}</div>
    </section>
  )
}

export default function ScriptEditor() {
  const { id } = useParams()
  const nav = useNavigate()
  const { data } = useApi<Full>(`/scripts/${id}`, { keepPrevious: false })
  const [s, setS] = useState<Full | null>(null)
  const [dirty, setDirty] = useState(false)
  useEffect(() => { if (data && !dirty) setS(data) }, [data, dirty])
  if (!s || !data) return (
    <div aria-busy="true">
      <Skeleton className="h-3 w-24 mb-2" /><Skeleton className="h-7 w-[min(560px,80%)] mb-7" />
      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-3">{[0, 1, 2, 3].map(i => <Skeleton key={i} className="h-36" />)}</div>
        <div className="space-y-4"><Skeleton className="h-24" /><Skeleton className="h-56" /></div>
      </div>
    </div>
  )

  const v: Variety = s.variety ?? {}
  const upd = (p: Partial<Full>) => { setS({ ...s, ...p }); setDirty(true) }
  const updScene = (i: number, p: Partial<Scene>) => upd({ scenes: s.scenes.map((x, j) => j === i ? { ...x, ...p } : x) })
  const move = (i: number, d: number) => { const a = [...s.scenes]; const [x] = a.splice(i, 1); a.splice(i + d, 0, x); upd({ scenes: a }) }
  const save = () => act(() => api(`/scripts/${id}`, { method: 'PUT', body: s }), 'Roteiro salvo').then(() => { setDirty(false); invalidate('/scripts') })
  /** Troca um campo com um clique: com edições pendentes só muda no editor (vai junto no Salvar); senão grava na hora. */
  const quick = (p: Partial<Full>, msg: string) => {
    if (dirty) { upd(p); return }
    setS({ ...s, ...p })
    act(() => api(`/scripts/${id}`, { method: 'PUT', body: p }), msg).then(() => { invalidate('/scripts'); invalidate(`/scripts/${id}`) })
  }
  const copy = (t: string) => navigator.clipboard.writeText(t).then(() => toast.ok('Copiado'))
  const words = s.scenes.reduce((n, x) => n + x.text.split(/\s+/).filter(Boolean).length, 0)
  const secs = Math.round(words / WPS)
  const tooShort = s.format === 'short' && secs < 60

  const lab = v.title_lab
  const titleOpts = (lab?.options?.length ? lab.options : v.title_options ?? []).filter(Boolean)
  const scoreOf = (t: string) => { const k = lab?.options?.indexOf(t) ?? -1; return k >= 0 ? lab!.scores[k] : null }
  const maxScore = lab?.scores?.length ? Math.max(...lab.scores) : 0
  const thumbOpts = [...new Set([s.thumbnail_text, ...(v.thumb_options ?? [])].filter(Boolean))]

  return (
    <div className="pb-20">
      <Link to="/roteiros" className="text-[13px] text-muted hover:text-text inline-flex items-center gap-1 mb-3 transition-colors"><ArrowLeft size={14} /> Roteiros</Link>
      <PageHeader title={s.title} subtitle={<span className="inline-flex flex-wrap items-center gap-x-2 gap-y-1">
        <Status s={s.status} />
        <span className={s.format === 'long' ? 'badge badge-accent' : 'badge'}>{s.format === 'long' ? 'Longo' : 'Short'}</span>
        <span className="num">{s.scenes.length}</span> cenas · <span className="num">{words}</span> palavras · ≈<span className={clsx('num', tooShort && 'text-warn')}>{secs}s</span> de narração · versão <span className="num">{s.version}</span>
      </span>}
        actions={<>
          <button className="btn btn-icon btn-danger" data-tip="Excluir roteiro" onClick={() => confirm('Excluir roteiro?') && act(() => api(`/scripts/${id}`, { method: 'DELETE' })).then(() => nav('/roteiros'))}><Trash2 size={15} /></button>
          <button className="btn" onClick={() => act(() => api(`/scripts/${id}/review`, { body: { auto_fix: false } }), 'Revisão iniciada')}><ShieldCheck size={15} /> Revisar</button>
          <button className="btn" disabled={!dirty} onClick={save}><Save size={15} /> Salvar</button>
          <button className="btn btn-primary" onClick={async () => { if (dirty) await save(); act(() => api(`/scripts/${id}/render`, { body: {} }), 'Vídeo entrou na fila de produção!') }}><Clapperboard size={15} /> Gerar vídeo</button>
        </>} />

      {tooShort && <Callout tone="warn" className="mb-4">Menos de 60s: o Short pode não entrar na monetização. Adicione cenas.</Callout>}

      <div className="grid lg:grid-cols-3 gap-6 items-start">
        <div className="lg:col-span-2 space-y-3">
          <Field label="Título"><input className="input !h-11 text-[16px] font-semibold" value={s.title} onChange={e => upd({ title: e.target.value })} /></Field>
          {titleOpts.length > 1 && (
            <div className="surface p-3">
              <div className="flex items-center justify-between mb-2">
                <div className="label !mb-0 flex items-center gap-1.5"><Type size={12} /> Outras opções de título</div>
                <span className="text-[11.5px] text-faint">{lab?.predicted ? 'nota prevista pelo histórico do canal' : lab ? 'nota pelo tamanho e escolha do roteirista' : 'um clique troca o título'}</span>
              </div>
              <div className="space-y-1">
                {titleOpts.map((t, k) => {
                  const cur = t === s.title, sc = scoreOf(t), best = lab && lab.options[lab.best] === t
                  return (
                    <button key={k} onClick={() => !cur && quick({ title: t }, 'Título trocado')} disabled={cur}
                      className={clsx('w-full flex items-center gap-3 px-2.5 py-2 rounded-[var(--r-sm)] text-left border transition-colors',
                        cur ? 'border-accent/45 bg-accent/[0.08] cursor-default' : 'border-transparent hover:border-line2 hover:bg-white/[0.03]')}>
                      <span className={clsx('w-4 h-4 rounded-full border grid place-items-center shrink-0', cur ? 'bg-grad border-transparent text-white' : 'border-line3')}>{cur && <Check size={10} strokeWidth={3} />}</span>
                      <span className="flex-1 min-w-0 text-[13.5px] truncate">{t}</span>
                      {best && <span className="badge badge-ok !h-5 text-[11px]"><Trophy size={10} />melhor</span>}
                      <span className={clsx('text-[11px] num w-7 text-right', t.length > 60 ? 'text-bad' : t.length > 50 ? 'text-warn' : 'text-faint')} title="caracteres">{t.length}</span>
                      {sc != null && <span className="w-16 flex items-center gap-1.5" title={`nota ${sc}`}><Bar value={maxScore ? (sc / maxScore) * 100 : 0} className="flex-1" /><span className="text-[11px] num text-muted w-6 text-right">{Math.round(sc)}</span></span>}
                    </button>
                  )
                })}
              </div>
            </div>
          )}
          {s.scenes.map((sc, i) => <SceneCard key={i} i={i} sc={sc} total={s.scenes.length} scriptId={s.id}
            onChange={p => updScene(i, p)} onMove={d => move(i, d)} onDelete={() => upd({ scenes: s.scenes.filter((_, j) => j !== i) })}
            onRewritten={() => { setDirty(false); invalidate(`/scripts/${id}`) }} />)}
          <button className="btn w-full !h-10 border-dashed" onClick={() => upd({ scenes: [...s.scenes, { text: '', visual: { kind: 'real', query: '' }, emphasis: [] }] })}><Plus size={15} /> Adicionar cena</button>
        </div>

        <div className="space-y-4 lg:sticky lg:top-4">
          <div className="card p-4 flex items-center gap-4">
            <ScoreRing score={s.quality_score} size={64} />
            <div className="min-w-0">
              <div className="font-semibold">Nota do editor-chefe</div>
              <div className="text-xs text-muted">gancho, ritmo, clareza, retenção e precisão</div>
              {(v.structure || v.hook_style) && <div className="flex flex-wrap gap-1 mt-2">
                {v.structure && <span className="badge text-[11px]"><Layers size={10} />{STRUCT[v.structure] ?? v.structure}</span>}
                {v.series && <span className="badge text-[11px]">{v.series}</span>}
              </div>}
            </div>
          </div>

          {s.fact_check?.length > 0 && (
            <Card title="Alertas de checagem" icon={<AlertTriangle size={14} className="text-warn" />}>
              <div className="space-y-2">{s.fact_check.map((f, k) => (
                <div key={k} className="text-xs p-2.5 rounded-[var(--r-sm)] bg-warn/[0.05] border border-warn/25">
                  <div className="font-semibold">{f.scene ? `Cena ${f.scene}: ` : ''}{f.claim}</div>
                  <div className="text-muted mt-1">{f.problem}</div>
                  {f.fix && <div className="text-ok mt-1">→ {f.fix}</div>}
                </div>))}
              </div>
            </Card>
          )}

          {(s.claims?.items?.length ?? 0) > 0 && (() => {
            const items = s.claims!.items, ok = items.filter(c => c.verdict === 'confirmado').length
            return (
              <Card title="Fatos frase a frase" icon={<ShieldCheck size={14} />}
                hint={`${ok}/${items.length} confirmadas nas fontes${s.claims!.fixed ? ` · ${s.claims!.fixed} cena(s) corrigida(s)` : ''}`}>
                <Bar value={(ok / items.length) * 100} tone={ok === items.length ? 'ok' : undefined} className="mb-3" />
                {(s.claims!.unresolved?.length ?? 0) > 0 && (
                  <div className="space-y-2 mb-3">{s.claims!.unresolved!.map((c, k) => (
                    <div key={k} className="text-xs p-2.5 rounded-[var(--r-sm)] bg-bad/[0.05] border border-bad/30">
                      <div className="font-semibold">Cena {c.scene}: {c.claim}</div>
                      <div className="text-muted mt-1">{c.verdict === 'contradiz' ? 'As fontes dizem outra coisa' : 'Nenhuma fonte confirma'} — revise antes do vídeo</div>
                    </div>))}
                  </div>
                )}
                <details className="text-xs group">
                  <summary className="cursor-pointer text-muted hover:text-text transition-colors list-none">Ver todas as afirmações</summary>
                  <div className="space-y-1 mt-2">{items.map((c, k) => (
                    <div key={k} className="flex gap-2">
                      <span className={c.verdict === 'confirmado' ? 'text-ok' : 'text-bad'}>{c.verdict === 'confirmado' ? '✓' : '✗'}</span>
                      <span><span className="text-muted">Cena {c.scene}:</span> {c.claim}{c.source && <> · <a className="underline text-muted" href={c.source} target="_blank" rel="noreferrer">fonte</a></>}</span>
                    </div>))}
                  </div>
                </details>
              </Card>
            )
          })()}

          {s.review_notes && <Card title="Sugestões do editor" icon={<Sparkles size={14} className="text-accent" />}><p className="text-sm whitespace-pre-wrap text-text/80">{s.review_notes}</p></Card>}

          <Card title="Publicação" icon={<Img size={14} />}>
            <div className="space-y-3">
              <Field label="Texto da thumbnail"><input className="input" value={s.thumbnail_text} onChange={e => upd({ thumbnail_text: e.target.value })} /></Field>
              {thumbOpts.length > 1 && (
                <div className="flex flex-wrap gap-1.5 -mt-1">
                  {thumbOpts.map(t => (
                    <button key={t} onClick={() => t !== s.thumbnail_text && quick({ thumbnail_text: t }, 'Texto da thumbnail trocado')}
                      className={clsx('badge transition-colors', t === s.thumbnail_text ? 'badge-accent' : 'hover:border-line3 hover:text-text text-muted')}>
                      {t === s.thumbnail_text && <Check size={11} />}{t}</button>
                  ))}
                </div>
              )}
              <Field label="Descrição"><textarea className="input min-h-32 text-xs" value={s.description} onChange={e => upd({ description: e.target.value })} /></Field>
              <Field label="Hashtags"><input className="input" value={s.hashtags.join(' ')} onChange={e => upd({ hashtags: e.target.value.split(/\s+/).filter(Boolean) })} /></Field>
              <Field label="Tags SEO"><input className="input" value={s.tags.join(', ')} onChange={e => upd({ tags: e.target.value.split(',').map(x => x.trim()).filter(Boolean) })} /></Field>
            </div>
          </Card>

          {(v.pinned_comment !== undefined) && (
            <Card title="Comentário do canal" icon={<MessageSquarePlus size={14} />} hint="Postado minutos depois de o vídeo ir ao ar — fixe-o para puxar conversa"
              action={v.pinned_comment ? <button className="btn btn-sm btn-icon btn-ghost" data-tip="Copiar" onClick={() => copy(v.pinned_comment!)}><Copy size={13} /></button> : undefined}>
              <textarea className="input min-h-20 text-[13px]" value={v.pinned_comment ?? ''} placeholder="Uma pergunta específica sobre o vídeo…"
                onChange={e => upd({ variety: { ...v, pinned_comment: e.target.value } })} />
            </Card>
          )}

          {s.sources?.length > 0 && <Card title="Fontes" icon={<ExternalLink size={14} />}>{s.sources.map((x, k) => (
            <a key={k} href={x.url} target="_blank" rel="noreferrer" className="flex gap-2 items-center text-xs text-info hover:underline truncate py-0.5"><ExternalLink size={12} className="shrink-0" />{x.title || x.url}</a>))}</Card>}

          {data.videos?.length > 0 && <Card title="Vídeos gerados" icon={<Clapperboard size={14} />}>{data.videos.map(vd => (
            <div key={vd.id} className="flex items-center gap-2 justify-between text-sm py-1.5 border-b border-line last:border-0">
              <span className="num text-muted">#{vd.id}{vd.duration ? ` · ${vd.duration.toFixed(0)}s` : ''}</span>
              <span className="flex-1" /><Status s={vd.status} />
              {vd.path && <a className="btn btn-sm btn-ghost" href={mediaUrl(vd.path)} target="_blank" rel="noreferrer">abrir</a>}
            </div>))}</Card>}
        </div>
      </div>

      {dirty && (
        <div className="fixed bottom-5 left-1/2 -translate-x-1/2 z-30 glass rounded-[var(--r-lg)] border border-line2 shadow-[var(--shadow-lg)] px-4 py-2.5 flex items-center gap-3 animate-pop">
          <span className="w-2 h-2 rounded-full bg-warn" /><span className="text-sm">Alterações não salvas</span>
          <button className="btn btn-sm" onClick={() => { setDirty(false); setS(data) }}>Descartar</button>
          <button className="btn btn-sm btn-primary" onClick={save}><Save size={14} /> Salvar</button>
        </div>
      )}
    </div>
  )
}

function DataEditor({ value, onChange }: { value: any; onChange: (v: any) => void }) {
  const [txt, setTxt] = useState(() => JSON.stringify(value ?? {}, null, 1))
  const [err, setErr] = useState(false)
  return (
    <textarea className={clsx('input !py-1.5 text-[11px] font-mono min-h-20', err && '!border-bad')} value={txt}
      onChange={e => {
        setTxt(e.target.value)
        try { onChange(JSON.parse(e.target.value)); setErr(false) } catch { setErr(true) }
      }} />
  )
}

function SceneCard({ i, sc, total, scriptId, onChange, onMove, onDelete, onRewritten }: {
  i: number; sc: Scene; total: number; scriptId: number; onChange: (p: Partial<Scene>) => void
  onMove: (d: number) => void; onDelete: () => void; onRewritten: () => void
}) {
  const [busy, setBusy] = useState(false)
  const v = sc.visual ?? { kind: 'real' }
  const rewrite = async () => {
    const instruction = prompt('Como reescrever esta cena?', 'Deixe mais impactante e curiosa')
    if (!instruction) return
    setBusy(true)
    await act(() => api(`/scripts/${scriptId}/scenes/${i}/rewrite`, { body: { instruction } }), 'Cena reescrita')
    setBusy(false)
    onRewritten()
  }
  const role = i === 0 ? 'Gancho' : i === total - 1 ? 'Final' : 'Cena'
  return (
    <div className={clsx('card card-hover p-4 group/s', busy && 'shimmer', i === 0 && 'ring-grad')}>
      <div className="flex items-center gap-2 mb-2">
        <span className={clsx('w-7 h-7 rounded-full grid place-items-center text-xs font-semibold num', i === 0 ? 'bg-grad text-white' : 'bg-panel2 border border-line2 text-text')}>{i + 1}</span>
        <span className="text-xs text-muted">{role} · ≈{Math.round(sc.text.split(/\s+/).filter(Boolean).length / WPS)}s</span>
        <div className="flex-1" />
        <div className="flex items-center gap-0.5 opacity-60 group-hover/s:opacity-100 focus-within:opacity-100 transition-opacity">
          <button className="btn btn-sm btn-icon btn-ghost" data-tip="Reescrever com IA" onClick={rewrite}><Wand2 size={14} /></button>
          <button className="btn btn-sm btn-icon btn-ghost" data-tip="Subir" disabled={i === 0} onClick={() => onMove(-1)}><ArrowUp size={14} /></button>
          <button className="btn btn-sm btn-icon btn-ghost" data-tip="Descer" disabled={i === total - 1} onClick={() => onMove(1)}><ArrowDown size={14} /></button>
          <button className="btn btn-sm btn-icon btn-ghost btn-danger" data-tip="Remover" onClick={onDelete}><Trash2 size={14} /></button>
        </div>
      </div>
      <textarea className="input min-h-16 text-[15px] leading-relaxed" value={sc.text} onChange={e => onChange({ text: e.target.value })} />
      <div className="grid grid-cols-[auto_1fr] gap-2 mt-2 items-center">
        <select className="input !w-auto !h-8 text-xs" value={v.kind} onChange={e => onChange({ visual: { ...v, kind: e.target.value } })}>
          <option value="real">📷 Foto real</option><option value="ai">✨ IA</option>
          <option value="timeline">📅 Linha do tempo</option><option value="counter">🔢 Contador</option>
          <option value="map">🗺️ Mapa</option><option value="dossier">🗂️ Ficha/dossiê</option>
          <option value="versus">⚖️ Mito × Verdade</option><option value="quote">❝ Citação</option>
          <option value="list">✅ Lista</option><option value="bigtext">🅰️ Texto de impacto</option>
        </select>
        {!['real', 'ai'].includes(v.kind)
          ? <DataEditor value={(v as any).data} onChange={data => onChange({ visual: { ...v, data } as any })} />
          : v.kind === 'ai'
            ? <div className="relative"><Sparkles size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted" /><input className="input !h-8 !pl-8 text-xs" placeholder="prompt da imagem (inglês)" value={v.prompt ?? ''} onChange={e => onChange({ visual: { ...v, prompt: e.target.value } })} /></div>
            : <div className="relative"><ImageIcon size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted" /><input className="input !h-8 !pl-8 text-xs" placeholder="busca da imagem (inglês)" value={v.query ?? ''} onChange={e => onChange({ visual: { ...v, query: e.target.value } })} /></div>}
      </div>
      <input className="input !h-8 text-xs mt-2" placeholder="palavras em destaque na legenda, separadas por vírgula" value={(sc.emphasis ?? []).join(', ')}
        onChange={e => onChange({ emphasis: e.target.value.split(',').map(x => x.trim()).filter(Boolean) })} />
    </div>
  )
}
