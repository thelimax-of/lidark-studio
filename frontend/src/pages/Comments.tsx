import { useEffect, useState } from 'react'
import { MessageSquare, RefreshCw, Send, X, ThumbsUp, Link2, Pin, MessageCircle, ExternalLink, Lightbulb, Sparkles, Loader2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api, invalidate, useApi, type Idea } from '../api'
import { act, ago, ChannelScope, ChannelTag, Empty, PageHeader, Tabs, useChannel, useScope } from '../ui'
import { Callout, RowsSkeleton, useProgressive } from './kit'
import { connectYoutube } from './Channels'

type C = { id: number; channel_id: number; yt_id: string; video_id: string; video_title: string; author: string; author_avatar: string; text: string
  likes: number; published_at: string; kind: string; suggestion: string; reply: string; status: string
  seed_style?: string; pinned?: boolean; replies?: number }
type Res = { items: C[]; counts: Record<string, number>; can_write: boolean; can_write_by?: Record<string, boolean> }

const KIND: Record<string, string> = { pergunta: 'Pergunta', elogio: 'Elogio', correcao: 'Correção', sugestao: 'Sugestão', critica: 'Crítica', spam: 'Spam', outro: 'Comentário' }
// estilos do comentário que o próprio canal posta ao publicar (puxa conversa)
const SEED: Record<string, string> = { pergunta: 'Pergunta', escolha: 'A ou B?', proximo: 'Próximo tema', opiniao: 'Opinião', vivencia: 'Vivência' }

export default function Comments() {
  const { channel, channels } = useChannel()
  const [all, setAll] = useScope('comments', true)
  const [tab, setTab] = useState<'new' | 'replied' | 'ignored' | 'seed'>('new')
  const { data, isLoading } = useApi<Res>(all ? `/comments?status=${tab}` : channel ? `/comments?channel_id=${channel.id}&status=${tab}` : null)
  const refresh = () => (all || channel) && act(() => api(all ? '/comments/refresh' : `/channels/${channel!.id}/comments/refresh`, { body: {} }), 'Buscando comentários novos…')
    .then(() => setTimeout(() => invalidate('/comments'), all ? 12000 : 6000))
  const items = data?.items ?? []
  // perguntas do público que viraram pauta ("respondendo @fulano"): a pauta guarda o id do comentário na tag comentario:<id>
  const { data: ideas } = useApi<Idea[]>(tab === 'seed' ? null : all ? '/ideas?slim=1&limit=300' : channel ? `/ideas?slim=1&limit=300&channel_id=${channel.id}` : null)
  const asIdea: Record<string, Idea> = {}
  for (const i of ideas ?? []) if (i.origin === 'comment') for (const t of i.tags ?? []) if (t.startsWith('comentario:')) asIdea[t.slice(11)] = i
  const [shown, more] = useProgressive(items, 30, tab + String(all))
  // canais sem a permissão de responder (no modo "todos", um aviso por canal)
  const noWrite = all ? channels.filter(c => data?.can_write_by?.[c.id] === false) : data && !data.can_write && channel ? [channel] : []
  return (
    <>
      <PageHeader title="Comentários" subtitle="Responder rápido ajuda o algoritmo. A IA sugere a resposta na voz do canal; você revisa e envia."
        actions={<><ChannelScope all={all} onChange={setAll} /><button className="btn" onClick={refresh}><RefreshCw size={14} /> Buscar agora</button></>} />
      {noWrite.length > 0 && (
        <Callout tone="warn" icon={<Link2 size={15} />} className="mb-4"
          action={<div className="flex flex-wrap gap-2">{noWrite.map(c => <button key={c.id} className="btn btn-sm btn-primary" onClick={() => connectYoutube(c.id)}>Reconectar{all ? ` ${c.name}` : ''}</button>)}</div>}>
          Para responder pelo painel (e ligar Shorts aos vídeos longos), reconecte {all ? 'estes canais' : 'o canal'} e aceite as novas permissões do YouTube.
        </Callout>
      )}
      <div className="mb-4">
        <Tabs value={tab} onChange={setTab} items={[
          { key: 'new', label: 'Para responder', count: data?.counts.new }, { key: 'replied', label: 'Respondidos', count: data?.counts.replied },
          { key: 'ignored', label: 'Ignorados', count: data?.counts.ignored }, { key: 'seed', label: 'Do canal', count: data?.counts.seed },
        ]} />
      </div>
      {tab !== 'seed' && !!data?.counts.to_pin && (
        <button className="w-full rounded-[var(--r-md)] border border-warn/30 bg-warn/[0.05] px-4 py-3 mb-4 flex items-center gap-3 text-[13px] text-left hover:bg-warn/[0.09] transition-colors" onClick={() => setTab('seed')}>
          <Pin size={15} className="text-warn shrink-0" />
          <span className="flex-1">{data.counts.to_pin} comentário(s) do canal esperando ser fixado(s) no YouTube — fixar no topo puxa mais conversa.</span>
          <span className="btn btn-sm">Ver</span>
        </button>
      )}
      {tab === 'seed' && <p className="text-[12.5px] text-muted mb-3">Depois de publicar, o canal deixa um comentário que puxa conversa. A API do YouTube não permite fixar: abra o vídeo, toque em ⋮ no comentário → Fixar, e marque aqui.</p>}
      {isLoading && !data && <div className="card"><RowsSkeleton rows={4} h="h-20" /></div>}
      {!isLoading && !items.length && <Empty icon={<MessageSquare size={20} />} title={tab === 'new' ? 'Nenhum comentário esperando resposta' : tab === 'seed' ? 'O canal ainda não comentou nenhum vídeo' : 'Nada aqui'}
        text={tab === 'seed' ? 'Liga/desliga em Canais → Comentário do canal. Sai alguns minutos depois de o vídeo ir ao ar.' : 'O sistema busca comentários novos a cada 2 horas.'} />}
      <div className="space-y-3">{shown.map(c => c.status === 'seed' ? <Seed key={c.id} c={c} showChannel={all} /> : <Item key={c.id} c={c} idea={asIdea[c.yt_id]} showChannel={all} canWrite={!!(data?.can_write_by?.[c.channel_id] ?? data?.can_write)} />)}{more}</div>
    </>
  )
}

function Item({ c, canWrite, showChannel, idea }: { c: C; canWrite: boolean; showChannel?: boolean; idea?: Idea }) {
  const [text, setText] = useState(c.suggestion || '')
  useEffect(() => setText(c.suggestion || ''), [c.suggestion])
  const [gerando, setGerando] = useState(false)
  const done = () => invalidate('/comments')
  const sugerir = () => {
    setGerando(true)
    act(() => api(`/comments/${c.id}/suggest`, { body: {} })).then(done).finally(() => setGerando(false))
  }
  return (
    <div className="card card-hover overflow-hidden">
      <div className="p-4 flex gap-3">
        {c.author_avatar ? <img src={c.author_avatar} referrerPolicy="no-referrer" loading="lazy" className="w-8 h-8 rounded-full shrink-0 ring-1 ring-line2" alt="" /> : <div className="w-8 h-8 rounded-full bg-panel2 ring-1 ring-line2 shrink-0" />}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 text-[12.5px] flex-wrap">
            {showChannel && <ChannelTag id={c.channel_id} />}
            <b className="font-medium">{c.author}</b>
            <span className="text-faint">{ago(c.published_at)}</span>
            {c.kind && <span className={`badge ${c.kind === 'pergunta' ? 'badge-accent' : c.kind === 'correcao' || c.kind === 'critica' ? 'badge-warn' : c.kind === 'elogio' ? 'badge-ok' : 'text-muted'}`}>{KIND[c.kind] ?? c.kind}</span>}
            {c.likes > 0 && <span className="text-faint flex items-center gap-1"><ThumbsUp size={11} />{c.likes}</span>}
            {idea && <Link to="/pautas" className="badge badge-ok" data-tip={`Pauta: ${idea.title}`}><Lightbulb size={11} />virou pauta</Link>}
            <a href={`https://www.youtube.com/watch?v=${c.video_id}&lc=${c.yt_id}`} target="_blank" rel="noreferrer" className="text-faint hover:text-accent2 transition-colors truncate max-w-[45%] ml-auto">
              {c.video_title || 'ver no YouTube'}</a>
          </div>
          <p className="text-[13.5px] mt-1 whitespace-pre-wrap break-words">{c.text}</p>
        </div>
      </div>
      {c.status === 'new' && (
        <div className="px-4 pb-4 pl-[60px]">
          <textarea className="input min-h-[64px] text-[13px] bg-panel2!" value={text} onChange={e => setText(e.target.value)}
            placeholder={c.suggestion ? '' : 'Escreva sua resposta…'} />
          <div className="flex items-center gap-2 mt-2">
            {c.suggestion && <span className="badge badge-accent !h-5 text-[11px]">sugerido pela IA</span>}
            <span className={`text-[11.5px] num ${text.length > 1000 ? 'text-bad' : 'text-faint'}`}>{text.length}/1000</span>
            <div className="flex-1" />
            <button className="btn btn-sm btn-ghost" disabled={gerando} onClick={sugerir}>{gerando ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />} {c.suggestion ? 'Outra sugestão' : 'Sugerir resposta'}</button>
            <button className="btn btn-sm btn-ghost" onClick={() => act(() => api(`/comments/${c.id}/ignore`, { body: {} })).then(done)}><X size={13} /> Ignorar</button>
            <button className="btn btn-sm btn-primary" disabled={!canWrite || !text.trim()}
              onClick={() => act(() => api(`/comments/${c.id}/reply`, { body: { text } }), 'Resposta publicada').then(done)}><Send size={13} /> Responder</button>
          </div>
        </div>
      )}
      {c.status === 'replied' && c.reply && <div className="mx-4 mb-4 ml-[60px] pl-3 text-[13px] text-muted border-l-2 border-accent/40">{c.reply}</div>}
    </div>
  )
}

function Seed({ c, showChannel }: { c: C; showChannel?: boolean }) {
  const toggle = () => act(() => api(`/comments/${c.id}/pinned`, { body: {} }), c.pinned ? undefined : 'Marcado como fixado').then(() => invalidate('/comments'))
  return (
    <div className={`card overflow-hidden border-l-2 ${c.pinned ? 'border-l-ok/60' : 'border-l-warn/60'}`}>
      <div className="p-4 flex gap-3">
        {c.author_avatar ? <img src={c.author_avatar} referrerPolicy="no-referrer" className="w-8 h-8 rounded-full shrink-0" alt="" /> : <div className="w-8 h-8 rounded-full bg-panel2 shrink-0" />}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 text-[12.5px] flex-wrap">
            {showChannel && <ChannelTag id={c.channel_id} />}
            <b className="font-medium">{c.author}</b>
            <span className="badge badge-accent">Comentário do canal</span>
            {c.seed_style && <span className="badge">{SEED[c.seed_style] ?? c.seed_style}</span>}
            <span className="text-faint">{ago(c.published_at)}</span>
            {(c.likes > 0) && <span className="text-faint flex items-center gap-1"><ThumbsUp size={11} />{c.likes}</span>}
            {!!c.replies && <span className="text-faint flex items-center gap-1"><MessageCircle size={11} />{c.replies}</span>}
            <span className="text-faint truncate max-w-[45%] ml-auto">{c.video_title}</span>
          </div>
          <p className="text-[13.5px] mt-1 whitespace-pre-wrap break-words">{c.text}</p>
          <div className="flex flex-wrap items-center gap-2 mt-3">
            {c.pinned ? <span className="text-[12px] text-ok flex items-center gap-1"><Pin size={12} /> Fixado</span>
              : <a className="btn btn-sm btn-primary" href={`https://www.youtube.com/watch?v=${c.video_id}&lc=${c.yt_id}`} target="_blank" rel="noreferrer"><Pin size={13} /> Abrir para fixar</a>}
            <a className="btn btn-sm btn-ghost" href={`https://studio.youtube.com/video/${c.video_id}/comments`} target="_blank" rel="noreferrer"><ExternalLink size={13} /> Comentários no Studio</a>
            <div className="flex-1" />
            <button className="btn btn-sm btn-ghost" onClick={toggle}>{c.pinned ? 'Desmarcar' : 'Já fixei'}</button>
          </div>
        </div>
      </div>
    </div>
  )
}
