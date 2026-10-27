import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Sparkles, PenLine, Check, X, FileText, ShieldCheck, RefreshCw, Trash2, ExternalLink, Lightbulb, Clapperboard, Flame } from 'lucide-react'
import clsx from 'clsx'
import { api, invalidate, useApi, type Idea } from '../api'
import { act, Empty, Field, Menu, Modal, PageHeader, ScoreRing, Status, Tabs, useChannel } from '../ui'

const TABS = [
  { k: 'new,approved', label: 'Na fila' },
  { k: 'new', label: 'Novas' },
  { k: 'approved', label: 'Aprovadas' },
  { k: 'rejected', label: 'Rejeitadas' },
]
const CRIT: Record<string, string> = {
  gancho: 'Gancho', curiosidade: 'Curiosidade', relevancia: 'Relevância', emocao: 'Emoção',
  visual: 'Visual', compartilhamento: 'Compartilhável', originalidade: 'Originalidade', veracidade: 'Veracidade',
}

export default function Ideas() {
  const { channel } = useChannel()
  const [tab, setTab] = useState(TABS[0].k)
  const [sort, setSort] = useState<'score' | 'date'>('score')
  const [open, setOpen] = useState<Idea | null>(null)
  const [newOpen, setNewOpen] = useState(false)
  const [params, setParams] = useSearchParams()
  useEffect(() => { if (params.get('nova')) { setNewOpen(true); setParams({}, { replace: true }) } }, [params, setParams])
  const [discOpen, setDiscOpen] = useState(false)
  const { data = [], isLoading } = useApi<Idea[]>(channel ? `/ideas?channel_id=${channel.id}&status=${tab}` : null)
  const list = useMemo(() => [...data].sort((a, b) => sort === 'score' ? (b.score ?? -1) - (a.score ?? -1) : b.id - a.id), [data, sort])

  const patch = (i: Idea, body: Partial<Idea>) => act(() => api(`/ideas/${i.id}`, { method: 'PATCH', body })).then(() => invalidate('/ideas'))
  const video = (i: Idea) => act(() => api(`/ideas/${i.id}/script`, { body: { auto_render: true } }), 'Roteiro + vídeo na fila!').then(() => invalidate('/jobs'))

  return (
    <>
      <PageHeader title="Pautas" subtitle="A IA busca, verifica e dá nota de 0 a 100. Você aprova ou propõe as suas."
        actions={<>
          <button className="btn" onClick={() => channel && act(() => api(`/channels/${channel.id}/radar`, { body: {} }), 'Radar de tendências rodando — as pautas aparecem em instantes')}><Flame size={15} /> Radar</button>
          <button className="btn" onClick={() => setNewOpen(true)}><PenLine size={15} /> Escrever pauta</button>
          <button className="btn btn-primary" onClick={() => setDiscOpen(true)}><Sparkles size={15} /> Buscar com IA</button>
        </>} />

      <div className="flex flex-wrap items-end justify-between gap-3 mb-4">
        <Tabs value={tab} onChange={setTab} items={TABS.map(t => ({ key: t.k, label: t.label }))} />
        <div className="seg mb-1.5">
          <button data-active={sort === 'score'} onClick={() => setSort('score')}>Maior nota</button>
          <button data-active={sort === 'date'} onClick={() => setSort('date')}>Recentes</button>
        </div>
      </div>

      {!isLoading && list.length === 0 && <Empty icon={<Lightbulb size={20} />} title="Nenhuma pauta aqui" text="Peça para a IA buscar pautas na internet ou escreva a sua ideia." />}

      {!!list.length && (
        <div className="card overflow-hidden"><div className="overflow-x-auto">
          <table className="tbl">
            <thead><tr><th className="w-14">Nota</th><th>Pauta</th><th>Origem</th><th>Checagem</th><th>Status</th><th className="right w-[150px]"><span className="sr-only">Ações</span></th></tr></thead>
            <tbody>
              {list.map(i => (
                <tr key={i.id} className="cursor-pointer" onClick={() => setOpen(i)}>
                  <td><ScoreRing score={i.score} size={34} /></td>
                  <td className="max-w-0 w-[50%]">
                    <div className="font-medium truncate">{i.title}</div>
                    <div className="text-[12.5px] text-muted truncate">{i.origin === 'trend' && i.tags?.[0] ? i.tags[0] : (i.angle || i.summary)}</div>
                  </td>
                  <td className="whitespace-nowrap text-muted">
                    {i.origin === 'trend' ? <span className="badge"><Flame size={12} className="text-warn" />Tendência{i.tags?.[1]?.includes('alta') ? ' · urgente' : ''}</span>
                      : i.origin === 'manual' ? 'Sua ideia' : 'IA'} · {i.format === 'long' ? 'Longo' : 'Short'}
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
              ))}
            </tbody>
          </table>
        </div></div>
      )}

      {open && <IdeaModal idea={data.find(x => x.id === open.id) ?? open} onClose={() => setOpen(null)} />}
      <NewIdeaModal open={newOpen} onClose={() => setNewOpen(false)} />
      <DiscoverModal open={discOpen} onClose={() => setDiscOpen(false)} />
    </>
  )
}

function IdeaModal({ idea, onClose }: { idea: Idea; onClose: () => void }) {
  const crit = idea.score_breakdown?.criteria ?? {}
  const run = (a: string, msg: string) => act(() => api(`/ideas/${idea.id}/${a}`, { body: {} }), msg)
  return (
    <Modal open onClose={onClose} title="Detalhes da pauta" wide>
      <div className="flex gap-5 mb-5">
        <ScoreRing score={idea.score} size={84} />
        <div className="flex-1">
          <h2 className="text-[18px] font-semibold leading-snug">{idea.title}</h2>
          <p className="text-muted mt-1">{idea.angle}</p>
          <div className="flex gap-2 mt-3"><Status s={idea.status} /><Status s={idea.fact_status} /></div>
        </div>
      </div>
      <div className="grid md:grid-cols-2 gap-6">
        <div>
          <div className="label">Resumo verificado</div>
          <p className="text-sm leading-relaxed">{idea.summary}</p>
          {idea.score_reason && <>
            <div className="label mt-4">Por que essa nota</div>
            <p className="text-sm text-text/80">{idea.score_reason}</p>
          </>}
          {idea.score_breakdown?.better_title && <>
            <div className="label mt-4">Título sugerido</div>
            <p className="text-sm text-text font-medium">{idea.score_breakdown.better_title}</p>
          </>}
          {!!idea.score_breakdown?.improvements?.length && <>
            <div className="label mt-4">Como melhorar</div>
            <ul className="text-sm list-disc pl-5 space-y-1 text-text/80">{idea.score_breakdown.improvements.map((x, k) => <li key={k}>{x}</li>)}</ul>
          </>}
        </div>
        <div>
          <div className="label">Critérios</div>
          <div className="space-y-2">
            {Object.entries(CRIT).map(([k, label]) => (
              <div key={k} className="flex items-center gap-3 text-sm">
                <span className="w-28 text-muted">{label}</span>
                <div className="flex-1 h-1.5 rounded-full bg-line overflow-hidden"><div className="h-full bg-text/80" style={{ width: `${crit[k] ?? 0}%` }} /></div>
                <span className="w-8 text-right num">{crit[k] ?? '–'}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
      {idea.facts?.length > 0 && <>
        <div className="label mt-6">Checagem de fatos</div>
        <div className="space-y-2">
          {idea.facts.map((f, k) => (
            <div key={k} className="text-sm p-3 rounded-lg bg-panel2 border border-line">
              <span className={clsx('badge mr-2', f.verdict === 'confirmado' ? 'text-ok' : f.verdict === 'falso' ? 'text-bad' : 'text-warn')}>{f.verdict}</span>
              {f.claim}
              {f.note && <div className="text-xs text-muted mt-1">{f.note}</div>}
            </div>
          ))}
        </div>
      </>}
      {idea.sources?.length > 0 && <>
        <div className="label mt-6">Fontes</div>
        <div className="space-y-1">
          {idea.sources.map((s, k) => (
            <a key={k} href={s.url} target="_blank" rel="noreferrer" className="flex items-center gap-2 text-sm text-info hover:underline truncate">
              <ExternalLink size={13} className="shrink-0" /> {s.title || s.url}</a>
          ))}
        </div>
      </>}
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
        <Field label="Tema ou título"><input className="input" value={f.title} onChange={e => setF({ ...f, title: e.target.value })} placeholder="Ex.: Por que Dom Pedro II foi exilado?" /></Field>
        <Field label="Ângulo / o que é surpreendente (opcional)"><textarea className="input min-h-20" value={f.angle} onChange={e => setF({ ...f, angle: e.target.value })} /></Field>
        <Field label="O que você já sabe (opcional)"><textarea className="input min-h-20" value={f.summary} onChange={e => setF({ ...f, summary: e.target.value })} /></Field>
        <Field label="Formato">
          <select className="input" value={f.format} onChange={e => setF({ ...f, format: e.target.value })}>
            <option value="short">Short vertical (60s+)</option><option value="long">Vídeo longo (5min+)</option>
          </select>
        </Field>
        <p className="text-xs text-muted">O sistema vai pesquisar fontes, verificar se é verdade, corrigir o resumo e dar uma nota de 0 a 100.</p>
        <button className="btn btn-primary w-full justify-center" disabled={!f.title} onClick={submit}><ShieldCheck size={16} /> Validar ideia</button>
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
          <input className="input" value={f.seed} onChange={e => setF({ ...f, seed: e.target.value })} placeholder="Ex.: Revolução Francesa, Era Vargas, mitos do Egito" />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Quantidade"><input type="number" min={1} max={20} className="input" value={f.count} onChange={e => setF({ ...f, count: Number(e.target.value) })} /></Field>
          <Field label="Formato">
            <select className="input" value={f.format} onChange={e => setF({ ...f, format: e.target.value })}>
              <option value="short">Short</option><option value="long">Longo</option>
            </select>
          </Field>
        </div>
        <button className="btn btn-primary w-full justify-center" onClick={submit}><Sparkles size={16} /> Buscar</button>
      </div>
    </Modal>
  )
}
