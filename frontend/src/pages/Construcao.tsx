import { useEffect, useRef, useState } from 'react'
import { Clapperboard, Hammer, Library, Loader2, Send, Sparkles } from 'lucide-react'
import clsx from 'clsx'
import { Link } from 'react-router-dom'
import { api, invalidate, mediaUrl, useApi } from '../api'
import { act, Empty, PageHeader } from '../ui'

type Msg = { de: 'voce' | 'ia'; texto: string }
type Projeto = {
  id: string; tema: string; titulo: string; status: string; erro: string; job_id?: number
  video_id: number | null; video_path?: string; capa_path?: string; duracao?: number; progresso?: number; etapa?: string; chat?: Msg[]
}

type Item = { chave: string; tema: string; categoria: string }
const EXEMPLOS = ['Afaste mais a câmera', 'Deixe a voz mais rápida', 'Troque a primeira frase']
const min = (s: number) => `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, '0')}`

export default function Construcao() {
  const url = '/construcao/projetos'
  const { data = [] } = useApi<Projeto[]>(url, { refetchInterval: 3000 })
  const { data: estado } = useApi<{ miniatura_bloqueada: boolean }>('/construcao/estado')
  const { data: bib = [] } = useApi<Item[]>('/construcao/biblioteca')
  const cats = [...new Set(bib.map(i => i.categoria))]
  const [tema, setTema] = useState('')
  const [enviando, setEnviando] = useState(false)
  const reload = () => invalidate(url)
  const criar = (t: string) => {
    setEnviando(true)
    act(async () => { await api(url, { body: { tema: t } }); setTema(''); reload() }).finally(() => setEnviando(false))
  }
  const pode = tema.trim().length >= 3 && !enviando

  return (
    <div className="max-w-5xl mx-auto">
      <PageHeader title="Construções 3D" subtitle="Canal Parte por Parte. Escreva o tema: o Claude faz o vídeo à mão, e isso pode levar horas." />
      {estado?.miniatura_bloqueada && <p className="card p-4 mb-4 text-sm" role="alert">O YouTube está recusando miniaturas neste canal. Verifique o telefone em <a className="underline" href="https://www.youtube.com/verify" target="_blank" rel="noreferrer">youtube.com/verify</a>. O aviso some depois do próximo envio aceito.</p>}
      <section className="card p-5 mb-6">
        <form className="flex flex-col sm:flex-row gap-2" onSubmit={e => { e.preventDefault(); if (pode) criar(tema.trim()) }}>
          <input className="input w-full sm:flex-1 !h-12 !text-base" aria-label="O que vamos construir" placeholder="O que vamos construir hoje?" value={tema} onChange={e => setTema(e.target.value)} />
          <button type="submit" className="btn btn-primary btn-lg justify-center" disabled={!pode}>
            {enviando ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />} Criar vídeo
          </button>
        </form>
        {bib.length > 0 && (
          <details className="mt-3">
            <summary className="text-sm text-muted cursor-pointer inline-flex items-center gap-2"><Library size={15} /> Biblioteca: {bib.length} temas no padrão máximo</summary>
            {cats.map(c => (
              <div key={c} className="mt-3">
                <p className="text-xs text-muted mb-1">{c}</p>
                <div className="flex flex-wrap gap-2">{bib.filter(i => i.categoria === c).map(i => <button key={i.chave} type="button" className="btn btn-sm" onClick={() => setTema(i.tema)}>{i.tema}</button>)}</div>
              </div>
            ))}
          </details>
        )}
      </section>
      {!data.length
        ? <Empty icon={<Hammer size={18} />} title="Nenhuma construção ainda" text="Escolha um tema acima para começar." />
        : <div className="flex flex-col gap-5">{data.map(p => <Card key={p.id} p={p} reload={reload} />)}</div>}
    </div>
  )
}

function Card({ p, reload }: { p: Projeto; reload: () => void }) {
  const [msg, setMsg] = useState('')
  const fim = useRef<HTMLDivElement>(null)
  const chat = p.chat ?? []
  const ocupado = p.status === 'criando' || p.status === 'renderizando'
  const prog = Math.round((p.progresso ?? 0) * 100)
  useEffect(() => { fim.current?.scrollIntoView({ block: 'nearest' }) }, [chat.length])
  const enviar = (t: string) => act(async () => { await api(`/construcao/projetos/${p.id}/chat`, { body: { mensagem: t } }); setMsg(''); reload() })

  return (
    <article className="card overflow-hidden flex flex-col md:flex-row">
      <div className="relative md:w-72 shrink-0 bg-black aspect-[9/16]">
        {p.video_path && <video key={`${p.video_path}-${p.job_id}-${p.status}`} className={clsx('w-full h-full object-contain', ocupado && 'opacity-30')} controls={!ocupado} preload="metadata" poster={`${mediaUrl(p.capa_path ?? '')}?v=${p.job_id ?? 0}`} src={`${mediaUrl(p.video_path)}?v=${p.job_id ?? 0}`} aria-label={`Vídeo: ${p.titulo}`} />}
        {ocupado && (
          <div className="absolute inset-0 grid place-items-center p-6" role="status">
            <div className="w-full text-center">
              <Loader2 size={26} className="animate-spin mx-auto mb-3 text-accent" />
              <p className="text-sm mb-2">{p.etapa || 'Na fila'}</p>
              <div className="h-1.5 rounded-full bg-line2 overflow-hidden"><div className="h-full bg-accent transition-all" style={{ width: `${prog}%` }} /></div>
            </div>
          </div>
        )}
        {!p.video_path && !ocupado && <div className="absolute inset-0 grid place-items-center text-muted"><Hammer size={26} /></div>}
      </div>

      <div className="flex-1 min-w-0 flex flex-col p-5 md:h-[512px]">
        <h3 className="font-semibold text-base leading-snug">{p.titulo}</h3>
        <p className="text-xs text-muted mt-1 mb-3">{p.duracao ? `${min(p.duracao)} de vídeo` : ocupado ? 'Em produção' : 'Sem vídeo'}</p>
        {p.erro && <p className="text-sm text-red-400 mb-3" role="alert">{p.erro}</p>}

        <div className="flex-1 min-h-40 overflow-y-auto rounded-[var(--r-lg)] border border-line p-3 flex flex-col gap-2" aria-label="Conversa de ajustes" aria-live="polite">
          {!chat.length && <p className="text-sm text-muted m-auto text-center px-4">Peça qualquer ajuste. O vídeo é refeito sozinho.</p>}
          {chat.map((m, i) => <div key={i} className={clsx('max-w-[85%] rounded-lg px-3 py-2 text-sm', m.de === 'voce' ? 'self-end bg-accent text-white' : 'self-start bg-panel2')}>{m.texto}</div>)}
          {ocupado && chat.length > 0 && <div className="self-start text-xs text-muted">Refazendo o vídeo…</div>}
          <div ref={fim} />
        </div>

        {!chat.length && !ocupado && p.video_path && <div className="flex flex-wrap gap-2 mt-3">{EXEMPLOS.map(e => <button key={e} className="btn btn-sm" onClick={() => setMsg(e)}>{e}</button>)}</div>}
        <form className="flex gap-2 mt-3" onSubmit={e => { e.preventDefault(); if (msg.trim() && !ocupado) enviar(msg.trim()) }}>
          <input className="input flex-1" aria-label={`Ajuste para ${p.titulo}`} placeholder="Ex.: afaste a câmera no começo" value={msg} disabled={!p.video_path} onChange={e => setMsg(e.target.value)} />
          <button className="btn btn-primary" aria-label="Enviar ajuste" disabled={!msg.trim() || ocupado || !p.video_path}><Send size={15} /></button>
        </form>
        {p.video_id && <Link className="btn mt-3 self-start" to="/videos"><Clapperboard size={15} /> Abrir em Vídeos</Link>}
      </div>
    </article>
  )
}
