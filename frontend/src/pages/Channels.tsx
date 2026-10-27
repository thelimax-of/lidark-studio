import { Link } from 'react-router-dom'
import { Plus, MonitorPlay as Youtube, Users, Eye, PlaySquare, Loader2, Link2 } from 'lucide-react'
import { api, useApi, type Channel } from '../api'
import { act, fmtNum, PageHeader, toast, useChannel } from '../ui'

export async function connectYoutube(channelId?: number) {
  const r: any = await act(() => api(`/youtube/connect${channelId ? `?channel_id=${channelId}` : ''}`, { body: {} }))
  if (r?.auth_url) {
    window.open(r.auth_url, '_blank', 'width=520,height=720')
    toast.info('Escolha o canal na janela do Google. Ele aparece aqui sozinho quando terminar.')
  }
}

export default function Channels() {
  const { data = [] } = useApi<(Channel & { connected: boolean })[]>('/channels')
  const { setChannelId } = useChannel()
  return (
    <>
      <PageHeader title="Canais" subtitle="Seus canais dark vêm direto do YouTube. Conecte e a IA monta a identidade de cada um." />
      <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-5">
        {data.map(c => (
          <Link key={c.id} to={`/canais/${c.id}`} onClick={() => setChannelId(c.id)}
            className="card overflow-hidden group hover:border-line2 transition">
            <div className="h-24 relative" style={{
              background: c.banner_url ? `center/cover url(${c.banner_url})`
                : `linear-gradient(135deg, ${c.theme?.bg_center ?? '#16473a'}, ${c.theme?.bg_edge ?? '#061915'})`,
            }}>
              <div className="absolute inset-0 bg-gradient-to-t from-panel to-transparent" />
            </div>
            <div className="px-5 pb-5 -mt-10 relative">
              <div className="flex items-end gap-3">
                <Avatar c={c} size={72} />
                <div className="min-w-0 pb-1">
                  <div className="font-semibold text-[15px] truncate ">{c.name}</div>
                  <div className="text-sm text-muted truncate">{c.handle || 'sem @'}</div>
                </div>
              </div>
              <div className="text-sm text-text/70 mt-3 line-clamp-2 min-h-10">{c.niche || 'Nicho ainda não definido'}</div>
              <div className="flex items-center gap-4 mt-4 text-sm">
                <span className="flex items-center gap-1.5"><Users size={15} className="text-muted" />{fmtNum(c.stats?.subscribers ?? 0)}</span>
                <span className="flex items-center gap-1.5"><Eye size={15} className="text-muted" />{fmtNum(c.stats?.views ?? 0)}</span>
                <span className="flex items-center gap-1.5"><PlaySquare size={15} className="text-muted" />{c.stats?.videos ?? c.counts?.published ?? 0}</span>
                <div className="flex-1" />
                <ChannelState c={c} />
              </div>
            </div>
          </Link>
        ))}
        <button onClick={() => connectYoutube()} className="card border-dashed min-h-64 grid place-items-center hover:border-line2 hover:bg-white/[0.02] transition text-center p-6">
          <div className="flex flex-col items-center gap-3">
            <div className="w-14 h-14 rounded-full bg-[#ff3b3b]/15 grid place-items-center"><Youtube className="text-[#ff5c5c]" size={28} /></div>
            <div className="font-semibold">Adicionar canal do YouTube</div>
            <div className="text-sm text-muted max-w-60">Entre com o Google e escolha o canal. Dados, vídeos e métricas são puxados automaticamente.</div>
            <span className="btn btn-primary mt-1"><Plus size={16} /> Conectar</span>
          </div>
        </button>
      </div>
    </>
  )
}

export function Avatar({ c, size = 40 }: { c: Partial<Channel>; size?: number }) {
  return c.avatar_url
    ? <img src={c.avatar_url} alt="" referrerPolicy="no-referrer" className="rounded-full border-4 border-panel shrink-0 object-cover" style={{ width: size, height: size }} />
    : <div className="rounded-full border-4 border-panel grid place-items-center font-semibold text-[#1a1405] shrink-0"
      style={{ width: size, height: size, background: c.color ?? '#d9a53a', fontSize: size * 0.4 }}>{c.theme?.logo_letter ?? c.name?.[0] ?? '?'}</div>
}

export function ChannelState({ c }: { c: Channel & { connected?: boolean } }) {
  if (!c.connected)
    return <button className="chip text-warn " onClick={e => { e.preventDefault(); connectYoutube(c.id) }}><Link2 size={12} /> Conectar</button>
  if (c.setup_status === 'configuring' || c.setup_status === 'pending')
    return <span className="chip text-text"><Loader2 size={12} className="animate-spin" /> Configurando</span>
  return <span className="chip text-ok ">Conectado</span>
}
