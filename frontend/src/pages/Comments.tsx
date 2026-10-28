import { useEffect, useState } from 'react'
import { MessageSquare, RefreshCw, Send, X, ThumbsUp, Link2 } from 'lucide-react'
import { api, invalidate, useApi } from '../api'
import { act, ago, ChannelScope, ChannelTag, Empty, PageHeader, Tabs, useChannel, useScope } from '../ui'
import { connectYoutube } from './Channels'

type C = { id: number; channel_id: number; yt_id: string; video_id: string; video_title: string; author: string; author_avatar: string; text: string
  likes: number; published_at: string; kind: string; suggestion: string; reply: string; status: string }
type Res = { items: C[]; counts: Record<string, number>; can_write: boolean; can_write_by?: Record<string, boolean> }

const KIND: Record<string, string> = { pergunta: 'Pergunta', elogio: 'Elogio', correcao: 'Correção', sugestao: 'Sugestão', critica: 'Crítica', spam: 'Spam', outro: 'Comentário' }

export default function Comments() {
  const { channel, channels } = useChannel()
  const [all, setAll] = useScope('comments', true)
  const [tab, setTab] = useState<'new' | 'replied' | 'ignored'>('new')
  const { data } = useApi<Res>(all ? `/comments?status=${tab}` : channel ? `/comments?channel_id=${channel.id}&status=${tab}` : null)
  const refresh = () => (all || channel) && act(() => api(all ? '/comments/refresh' : `/channels/${channel!.id}/comments/refresh`, { body: {} }), 'Buscando comentários novos…')
    .then(() => setTimeout(() => invalidate('/comments'), all ? 12000 : 6000))
  const items = data?.items ?? []
  // canais sem a permissão de responder (no modo "todos", um aviso por canal)
  const noWrite = all ? channels.filter(c => data?.can_write_by?.[c.id] === false) : data && !data.can_write && channel ? [channel] : []
  return (
    <>
      <PageHeader title="Comentários" subtitle="Responder rápido ajuda o algoritmo. A IA sugere a resposta na voz do canal; você revisa e envia."
        actions={<><ChannelScope all={all} onChange={setAll} /><button className="btn" onClick={refresh}><RefreshCw size={14} /> Buscar agora</button></>} />
      {noWrite.length > 0 && (
        <div className="card px-4 py-3 mb-4 flex flex-wrap items-center gap-3 text-[13px]">
          <Link2 size={15} className="text-warn shrink-0" />
          <span className="flex-1 min-w-60">Para responder pelo painel (e ligar Shorts aos vídeos longos), reconecte {all ? 'estes canais' : 'o canal'} e aceite as novas permissões do YouTube.</span>
          {noWrite.map(c => <button key={c.id} className="btn btn-sm btn-primary" onClick={() => connectYoutube(c.id)}>Reconectar{all ? ` ${c.name}` : ''}</button>)}
        </div>
      )}
      <div className="mb-4">
        <Tabs value={tab} onChange={setTab} items={[
          { key: 'new', label: 'Para responder', count: data?.counts.new }, { key: 'replied', label: 'Respondidos', count: data?.counts.replied },
          { key: 'ignored', label: 'Ignorados', count: data?.counts.ignored },
        ]} />
      </div>
      {!items.length && <Empty icon={<MessageSquare size={20} />} title={tab === 'new' ? 'Nenhum comentário esperando resposta' : 'Nada aqui'}
        text="O sistema busca comentários novos a cada 2 horas." />}
      <div className="space-y-3">{items.map(c => <Item key={c.id} c={c} showChannel={all} canWrite={!!(data?.can_write_by?.[c.channel_id] ?? data?.can_write)} />)}</div>
    </>
  )
}

function Item({ c, canWrite, showChannel }: { c: C; canWrite: boolean; showChannel?: boolean }) {
  const [text, setText] = useState(c.suggestion || '')
  useEffect(() => setText(c.suggestion || ''), [c.suggestion])
  const done = () => invalidate('/comments')
  return (
    <div className="card overflow-hidden">
      <div className="p-4 flex gap-3">
        {c.author_avatar ? <img src={c.author_avatar} referrerPolicy="no-referrer" className="w-8 h-8 rounded-full shrink-0" alt="" /> : <div className="w-8 h-8 rounded-full bg-panel2 shrink-0" />}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 text-[12.5px] flex-wrap">
            {showChannel && <ChannelTag id={c.channel_id} />}
            <b className="font-medium">{c.author}</b>
            <span className="text-faint">{ago(c.published_at)}</span>
            {c.kind && <span className="badge">{KIND[c.kind] ?? c.kind}</span>}
            {c.likes > 0 && <span className="text-faint flex items-center gap-1"><ThumbsUp size={11} />{c.likes}</span>}
            <a href={`https://www.youtube.com/watch?v=${c.video_id}&lc=${c.yt_id}`} target="_blank" rel="noreferrer" className="text-faint hover:text-text truncate max-w-[45%] ml-auto">
              {c.video_title || 'ver no YouTube'}</a>
          </div>
          <p className="text-[13.5px] mt-1 whitespace-pre-wrap break-words">{c.text}</p>
        </div>
      </div>
      {c.status === 'new' && (
        <div className="px-4 pb-4 pl-[60px]">
          <textarea className="input min-h-[64px] text-[13px]" value={text} onChange={e => setText(e.target.value)}
            placeholder={c.suggestion ? '' : 'Escreva sua resposta…'} />
          <div className="flex items-center gap-2 mt-2">
            <span className="text-[11.5px] text-faint num">{text.length}/1000</span>
            <div className="flex-1" />
            <button className="btn btn-sm btn-ghost" onClick={() => act(() => api(`/comments/${c.id}/ignore`, { body: {} })).then(done)}><X size={13} /> Ignorar</button>
            <button className="btn btn-sm btn-primary" disabled={!canWrite || !text.trim()}
              onClick={() => act(() => api(`/comments/${c.id}/reply`, { body: { text } }), 'Resposta publicada').then(done)}><Send size={13} /> Responder</button>
          </div>
        </div>
      )}
      {c.status === 'replied' && c.reply && <div className="px-4 pb-4 pl-[60px] text-[13px] text-muted border-l-2 border-line2 ml-[60px] -mt-1">{c.reply}</div>}
    </div>
  )
}
