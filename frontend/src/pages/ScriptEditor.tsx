import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Save, Clapperboard, ShieldCheck, Wand2, Trash2, Plus, ArrowUp, ArrowDown, ExternalLink, ImageIcon, Sparkles, AlertTriangle } from 'lucide-react'
import clsx from 'clsx'
import { api, invalidate, mediaUrl, useApi, type Scene, type Script, type Video } from '../api'
import { act, Field, PageHeader, ScoreRing, Status } from '../ui'

const WPS = 2.7

export default function ScriptEditor() {
  const { id } = useParams()
  const nav = useNavigate()
  const { data } = useApi<Script & { videos: Video[] }>(`/scripts/${id}`)
  const [s, setS] = useState<Script | null>(null)
  const [dirty, setDirty] = useState(false)
  useEffect(() => { if (data && !dirty) setS(data) }, [data, dirty])
  if (!s || !data) return null

  const upd = (p: Partial<Script>) => { setS({ ...s, ...p }); setDirty(true) }
  const updScene = (i: number, p: Partial<Scene>) => upd({ scenes: s.scenes.map((x, j) => j === i ? { ...x, ...p } : x) })
  const move = (i: number, d: number) => { const a = [...s.scenes]; const [x] = a.splice(i, 1); a.splice(i + d, 0, x); upd({ scenes: a }) }
  const save = () => act(() => api(`/scripts/${id}`, { method: 'PUT', body: s }), 'Roteiro salvo').then(() => { setDirty(false); invalidate('/scripts') })
  const words = s.scenes.reduce((n, x) => n + x.text.split(/\s+/).filter(Boolean).length, 0)
  const secs = Math.round(words / WPS)
  const tooShort = s.format === 'short' && secs < 60

  return (
    <>
      <PageHeader title={s.title} subtitle={`${s.scenes.length} cenas · ${words} palavras · ≈${secs}s de narração · versão ${s.version}`}
        actions={<>
          <button className="btn btn-danger" onClick={() => confirm('Excluir roteiro?') && act(() => api(`/scripts/${id}`, { method: 'DELETE' })).then(() => nav('/roteiros'))}><Trash2 size={15} /></button>
          <button className="btn" onClick={() => act(() => api(`/scripts/${id}/review`, { body: { auto_fix: false } }), 'Revisão iniciada')}><ShieldCheck size={15} /> Revisar</button>
          <button className="btn" disabled={!dirty} onClick={save}><Save size={15} /> Salvar</button>
          <button className="btn btn-primary" onClick={async () => { if (dirty) await save(); act(() => api(`/scripts/${id}/render`, { body: {} }), 'Vídeo entrou na fila de produção!') }}><Clapperboard size={15} /> Gerar vídeo</button>
        </>} />

      {tooShort && <div className="card p-3 mb-4 text-sm border-warn/30 bg-warn/5 flex gap-2 items-center"><AlertTriangle size={16} className="text-warn" /> Menos de 60s: o Short pode não entrar na monetização. Adicione cenas.</div>}

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-3">
          <Field label="Título"><input className="input text-base font-semibold" value={s.title} onChange={e => upd({ title: e.target.value })} /></Field>
          {s.scenes.map((sc, i) => <SceneCard key={i} i={i} sc={sc} total={s.scenes.length} scriptId={s.id}
            onChange={p => updScene(i, p)} onMove={d => move(i, d)} onDelete={() => upd({ scenes: s.scenes.filter((_, j) => j !== i) })}
            onRewritten={() => { setDirty(false); invalidate(`/scripts/${id}`) }} />)}
          <button className="btn w-full justify-center" onClick={() => upd({ scenes: [...s.scenes, { text: '', visual: { kind: 'real', query: '' }, emphasis: [] }] })}><Plus size={15} /> Adicionar cena</button>
        </div>

        <div className="space-y-4">
          <div className="card p-4 flex items-center gap-4">
            <ScoreRing score={s.quality_score} size={64} />
            <div><div className="font-semibold">Nota do editor-chefe</div><div className="text-xs text-muted">gancho, ritmo, clareza, retenção e precisão</div></div>
          </div>
          {s.fact_check?.length > 0 && (
            <div className="card p-4">
              <div className="label !text-warn">Alertas de checagem</div>
              <div className="space-y-2">{s.fact_check.map((f, k) => (
                <div key={k} className="text-xs p-2 rounded bg-panel2 border border-line">
                  <div className="font-semibold">{f.scene ? `Cena ${f.scene}: ` : ''}{f.claim}</div>
                  <div className="text-muted mt-1">{f.problem}</div>
                  {f.fix && <div className="text-ok mt-1">→ {f.fix}</div>}
                </div>))}
              </div>
            </div>
          )}
          {s.review_notes && <div className="card p-4"><div className="label">Sugestões</div><p className="text-sm whitespace-pre-wrap text-text/80">{s.review_notes}</p></div>}
          <div className="card p-4 space-y-3">
            <Field label="Descrição"><textarea className="input min-h-32 text-xs" value={s.description} onChange={e => upd({ description: e.target.value })} /></Field>
            <Field label="Hashtags"><input className="input" value={s.hashtags.join(' ')} onChange={e => upd({ hashtags: e.target.value.split(/\s+/).filter(Boolean) })} /></Field>
            <Field label="Tags SEO"><input className="input" value={s.tags.join(', ')} onChange={e => upd({ tags: e.target.value.split(',').map(x => x.trim()).filter(Boolean) })} /></Field>
            <Field label="Texto da thumbnail"><input className="input" value={s.thumbnail_text} onChange={e => upd({ thumbnail_text: e.target.value })} /></Field>
          </div>
          {s.sources?.length > 0 && <div className="card p-4"><div className="label">Fontes</div>{s.sources.map((x, k) => (
            <a key={k} href={x.url} target="_blank" rel="noreferrer" className="flex gap-2 items-center text-xs text-info hover:underline truncate py-0.5"><ExternalLink size={12} className="shrink-0" />{x.title || x.url}</a>))}</div>}
          {data.videos?.length > 0 && <div className="card p-4"><div className="label">Vídeos gerados</div>{data.videos.map(v => (
            <div key={v.id} className="flex items-center justify-between text-sm py-1"><span>#{v.id} · {v.duration ? `${v.duration.toFixed(0)}s` : ''}</span><Status s={v.status} />
              {v.path && <a className="text-muted text-xs" href={mediaUrl(v.path)} target="_blank" rel="noreferrer">abrir</a>}</div>))}</div>}
        </div>
      </div>
    </>
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
  return (
    <div className={clsx('card p-4', busy && 'shimmer')}>
      <div className="flex items-center gap-2 mb-2">
        <span className="w-7 h-7 rounded-full bg-white/[0.08] text-text grid place-items-center text-xs font-bold">{i + 1}</span>
        <span className="text-xs text-muted">{i === 0 ? 'Gancho' : i === total - 1 ? 'Final' : 'Cena'} · ≈{Math.round(sc.text.split(/\s+/).filter(Boolean).length / WPS)}s</span>
        <div className="flex-1" />
        <button className="btn btn-ghost !p-1" title="Reescrever com IA" onClick={rewrite}><Wand2 size={15} /></button>
        <button className="btn btn-ghost !p-1" disabled={i === 0} onClick={() => onMove(-1)}><ArrowUp size={15} /></button>
        <button className="btn btn-ghost !p-1" disabled={i === total - 1} onClick={() => onMove(1)}><ArrowDown size={15} /></button>
        <button className="btn btn-ghost btn-danger !p-1" onClick={onDelete}><Trash2 size={15} /></button>
      </div>
      <textarea className="input min-h-16 text-[15px] leading-relaxed" value={sc.text} onChange={e => onChange({ text: e.target.value })} />
      <div className="grid grid-cols-[auto_1fr] gap-2 mt-2 items-center">
        <select className="input !w-auto !py-1.5 text-xs" value={v.kind} onChange={e => onChange({ visual: { ...v, kind: e.target.value } })}>
          <option value="real">📷 Foto real</option><option value="ai">✨ IA</option>
          <option value="timeline">📅 Linha do tempo</option><option value="counter">🔢 Contador</option>
          <option value="map">🗺️ Mapa</option><option value="dossier">🗂️ Ficha/dossiê</option>
          <option value="versus">⚖️ Mito × Verdade</option><option value="quote">❝ Citação</option>
          <option value="list">✅ Lista</option><option value="bigtext">🅰️ Texto de impacto</option>
        </select>
        {!['real', 'ai'].includes(v.kind)
          ? <DataEditor value={(v as any).data} onChange={data => onChange({ visual: { ...v, data } as any })} />
          : v.kind === 'ai'
          ? <div className="relative"><Sparkles size={13} className="absolute left-2.5 top-2.5 text-muted" /><input className="input !py-1.5 !pl-8 text-xs" placeholder="prompt da imagem (inglês)" value={v.prompt ?? ''} onChange={e => onChange({ visual: { ...v, prompt: e.target.value } })} /></div>
          : <div className="relative"><ImageIcon size={13} className="absolute left-2.5 top-2.5 text-muted" /><input className="input !py-1.5 !pl-8 text-xs" placeholder="busca da imagem (inglês)" value={v.query ?? ''} onChange={e => onChange({ visual: { ...v, query: e.target.value } })} /></div>}
      </div>
      <input className="input !py-1.5 text-xs mt-2" placeholder="palavras em destaque (dourado), separadas por vírgula" value={(sc.emphasis ?? []).join(', ')}
        onChange={e => onChange({ emphasis: e.target.value.split(',').map(x => x.trim()).filter(Boolean) })} />
    </div>
  )
}
