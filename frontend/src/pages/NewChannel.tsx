import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import clsx from 'clsx'
import { ArrowLeft, Check, Copy, Download, Loader2, RefreshCw, Sparkles, Trash2, Wand2 } from 'lucide-react'
import { api, invalidate, onJob, useApi, type Channel } from '../api'
import { act, Field, PageHeader, toast } from '../ui'
import { connectYoutube } from './Channels'

type Option = { name: string; handle: string; tagline: string; kit: { avatar: string; banner: string; watermark: string; sheet: string } }
type Draft = {
  id: number; niche: string; notes: string; options: Option[]; chosen: number; status: string; channel_id: number | null
  texts: { bio?: string; bio_curta?: string; keywords?: string; hashtags?: string[]; cta?: string; comentario_fixado?: string; playlists?: string[]; editorial_guide?: string }
  txt_url: string
}

const v = () => `?v=${Date.now() >> 12}`

export default function NewChannel() {
  const { data: drafts = [], refetch } = useApi<Draft[]>('/brand-drafts')
  const [sel, setSel] = useState<number | null>(null)
  const current = drafts.find(d => d.id === sel) ?? null
  useEffect(() => onJob(j => {
    if (['brand_propose', 'brand_texts'].includes(j.kind) && ['done', 'failed'].includes(j.status)) {
      refetch()
      if (j.status === 'failed') toast.err('A IA não conseguiu terminar — tente de novo')
    }
  }), [refetch])

  return (
    <>
      <Link to="/canais" className="text-sm text-muted hover:text-text flex items-center gap-1 mb-4"><ArrowLeft size={15} /> Canais</Link>
      <PageHeader title="Novo canal" subtitle="Do nicho ao canal pronto: nomes, foto de perfil, capa, marca d'água, bio, palavras-chave e linha editorial. Quando você conectar o canal criado no YouTube, tudo é aplicado e travado." />
      <div className="grid lg:grid-cols-[280px_1fr] gap-6 items-start">
        <div className="space-y-3">
          <StartForm onCreated={id => { setSel(id); refetch() }} />
          {drafts.length > 0 && <div className="label">Planejados</div>}
          {drafts.map(d => (
            <button key={d.id} onClick={() => setSel(d.id)} className={clsx('card w-full text-left p-3 transition', sel === d.id ? 'border-text/50' : 'hover:border-line2')}>
              <div className="text-[13.5px] font-medium truncate">{d.chosen >= 0 ? d.options[d.chosen]?.name : d.niche}</div>
              <div className="text-[12px] text-muted truncate">{d.niche}</div>
              <div className="text-[11px] mt-1 text-faint">{{ draft: d.options.length ? 'escolha um nome' : 'gerando propostas…', chosen: 'pronto para conectar', applied: 'aplicado no canal' }[d.status] ?? d.status}</div>
            </button>
          ))}
        </div>
        <div>{current ? <DraftView d={current} refetch={refetch} onDeleted={() => setSel(null)} /> :
          <div className="card p-8 text-center text-muted text-sm">Descreva o nicho ao lado e a IA monta 3 propostas completas, no estilo das imagens do Sinal do Cosmos.</div>}</div>
      </div>
    </>
  )
}

function StartForm({ onCreated }: { onCreated: (id: number) => void }) {
  const [niche, setNiche] = useState('')
  const [notes, setNotes] = useState('')
  const [busy, setBusy] = useState(false)
  const go = async () => {
    setBusy(true)
    const r = await act(() => api<Draft>('/brand-drafts', { body: { niche, notes } }), 'IA criando as propostas…')
    setBusy(false)
    if (r) { setNiche(''); setNotes(''); onCreated(r.id) }
  }
  return (
    <div className="card p-4 space-y-3">
      <Field label="Nicho"><input className="input" value={niche} onChange={e => setNiche(e.target.value)} placeholder="ex.: ciência do dia a dia" /></Field>
      <Field label="Observações (opcional)"><textarea className="input min-h-20 text-sm" value={notes} onChange={e => setNotes(e.target.value)} placeholder="ex.: público jovem, cores escuras, mascote bola" /></Field>
      <button className="btn btn-primary w-full justify-center" disabled={busy || niche.trim().length < 3} onClick={go}>
        {busy ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} />} Criar propostas</button>
    </div>
  )
}

function DraftView({ d, refetch, onDeleted }: { d: Draft; refetch: () => void; onDeleted: () => void }) {
  const { data: channels = [] } = useApi<Channel[]>('/channels')
  const [target, setTarget] = useState<number | ''>('')
  const generating = d.status === 'draft' && !d.options.length
  const writing = d.chosen >= 0 && !d.texts?.bio
  const choose = (i: number) => act(() => api(`/brand-drafts/${d.id}/choose`, { body: { index: i } }), 'IA escrevendo os textos do canal…').then(refetch)
  const apply = () => act(() => api(`/brand-drafts/${d.id}/apply`, { body: { channel_id: target } }), 'Identidade aplicada no canal')
    .then(() => { refetch(); invalidate('/channels') })

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0"><div className="text-[12px] text-muted">Nicho</div><div className="font-semibold truncate">{d.niche}</div></div>
        <div className="flex gap-2">
          {!generating && d.status !== 'applied' && <button className="btn btn-sm" onClick={() => act(() => api(`/brand-drafts/${d.id}/redo`, { body: {} }), 'Gerando novas propostas…').then(refetch)}><RefreshCw size={13} /> Outras opções</button>}
          <button className="btn btn-sm btn-danger" onClick={() => act(() => api(`/brand-drafts/${d.id}`, { method: 'DELETE' })).then(() => { refetch(); onDeleted() })}><Trash2 size={13} /></button>
        </div>
      </div>

      {generating && <div className="card p-8 text-center text-sm text-muted flex items-center justify-center gap-2"><Loader2 size={16} className="animate-spin" /> A IA está criando nomes, cores, mascote e desenhando os 3 kits…</div>}

      {d.options.length > 0 && (
        <div className="grid md:grid-cols-3 gap-4">
          {d.options.map((o, i) => (
            <div key={i} className={clsx('card overflow-hidden', d.chosen === i && 'border-text/60')}>
              <a href={o.kit.sheet + v()} target="_blank" rel="noreferrer"><img src={o.kit.banner + v()} className="w-full aspect-video object-cover" alt="" /></a>
              <div className="p-3 flex gap-3 items-center">
                <img src={o.kit.avatar + v()} className="w-14 h-14 rounded-full border border-line" alt="" />
                <div className="min-w-0">
                  <div className="font-semibold truncate">{o.name}</div>
                  <div className="text-[12px] text-muted truncate">{o.handle}</div>
                  <div className="text-[12px] text-faint truncate">{o.tagline}</div>
                </div>
              </div>
              <div className="px-3 pb-3 flex gap-2">
                <button className={clsx('btn btn-sm flex-1 justify-center', d.chosen === i && 'btn-primary')} disabled={d.status === 'applied'} onClick={() => choose(i)}>
                  {d.chosen === i ? <><Check size={13} /> Escolhido</> : 'Escolher'}</button>
                {(['avatar', 'banner', 'watermark'] as const).map(k => (
                  <a key={k} className="btn btn-sm" href={o.kit[k]} download title={{ avatar: 'Foto de perfil', banner: 'Capa', watermark: "Marca d'água" }[k]}><Download size={13} /></a>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {writing && <div className="card p-6 text-center text-sm text-muted flex items-center justify-center gap-2"><Loader2 size={16} className="animate-spin" /> Escrevendo bio, palavras-chave, playlists e linha editorial…</div>}

      {d.texts?.bio && (
        <div className="card p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="font-semibold">Textos para o YouTube Studio</div>
            <a className="btn btn-sm" href={d.txt_url} download><Download size={13} /> Baixar TXT</a>
          </div>
          <CopyBlock label="Bio / descrição do canal" text={d.texts.bio} />
          <CopyBlock label="Bio curta (Instagram/TikTok)" text={d.texts.bio_curta ?? ''} />
          <CopyBlock label="Palavras-chave (cole a linha inteira)" text={d.texts.keywords ?? ''} />
          <CopyBlock label="Hashtags" text={(d.texts.hashtags ?? []).join(' ')} />
          <CopyBlock label="Comentário fixado" text={d.texts.comentario_fixado ?? ''} />
          <details><summary className="cursor-pointer text-sm text-muted">Playlists e linha editorial</summary>
            <pre className="text-xs whitespace-pre-wrap mt-2 text-text/80">{(d.texts.playlists ?? []).map(p => '- ' + p).join('\n')}{'\n\n'}{d.texts.editorial_guide}</pre>
          </details>
        </div>
      )}

      {d.texts?.bio && d.status !== 'applied' && (
        <div className="card p-5">
          <div className="font-semibold mb-1">Último passo</div>
          <ol className="text-sm text-muted list-decimal ml-5 space-y-1 mb-4">
            <li>Crie o canal no YouTube com o nome <b className="text-text">{d.options[d.chosen]?.name}</b> e o @ <b className="text-text">{d.options[d.chosen]?.handle}</b>.</li>
            <li>Suba a foto de perfil, a capa e a marca d'água, e cole a bio e as palavras-chave.</li>
            <li>Conecte aqui. Se o nome ou o @ baterem, a identidade é aplicada sozinha.</li>
          </ol>
          <div className="flex flex-wrap gap-2 items-center">
            <button className="btn btn-primary" onClick={() => connectYoutube()}><Wand2 size={15} /> Conectar com Google</button>
            <span className="text-sm text-muted ml-2">ou aplicar num canal já conectado:</span>
            <select className="input !w-auto" value={target} onChange={e => setTarget(e.target.value ? Number(e.target.value) : '')}>
              <option value="">escolher…</option>
              {channels.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <button className="btn" disabled={!target} onClick={apply}>Aplicar</button>
          </div>
        </div>
      )}
      {d.status === 'applied' && d.channel_id && (
        <div className="card p-4 text-sm flex items-center gap-2"><Check size={15} className="text-ok" /> Aplicado. <Link className="underline" to={`/canais/${d.channel_id}`}>Abrir o canal</Link></div>
      )}
    </div>
  )
}

function CopyBlock({ label, text }: { label: string; text: string }) {
  if (!text) return null
  return (
    <div>
      <div className="flex items-center justify-between"><div className="label !mb-1">{label}</div>
        <button className="btn btn-sm" onClick={() => navigator.clipboard.writeText(text).then(() => toast.ok('Copiado'))}><Copy size={12} /> Copiar</button></div>
      <pre className="text-xs whitespace-pre-wrap bg-bg border border-line rounded-lg p-3 text-text/80">{text}</pre>
    </div>
  )
}
