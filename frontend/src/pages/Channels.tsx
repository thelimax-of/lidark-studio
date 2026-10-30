import { Link } from 'react-router-dom'
import { Plus, MonitorPlay as Youtube, Users, Eye, PlaySquare, Loader2, Link2, Sparkles } from 'lucide-react'
import { api, useApi, type Channel } from '../api'
import { act, fmtNum, PageHeader, Skeleton, toast, useChannel } from '../ui'
import { FocusPicker } from './FocusMode'

export async function connectYoutube(channelId?: number) {
  const r: any = await act(() => api(`/youtube/connect${channelId ? `?channel_id=${channelId}` : ''}`, { body: {} }))
  if (r?.auth_url) {
    window.open(r.auth_url, '_blank', 'width=520,height=720')
    toast.info('Escolha o canal na janela do Google. Ele aparece aqui sozinho quando terminar.')
  }
}

export default function Channels() {
  // mesma chave do seletor de canal do topo: já está em cache quando a tela abre
  const { data = [], isLoading } = useApi<(Channel & { connected: boolean })[]>('/channels')
  const { setChannelId } = useChannel()
  return (
    <>
      <PageHeader title="Canais" subtitle="Seus canais dark vêm direto do YouTube. Conecte e a IA monta a identidade de cada um."
        actions={<Link to="/canais/novo" className="btn btn-primary"><Sparkles size={15} /> Planejar novo canal</Link>} />
      <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-5">
        {isLoading && !data.length && [0, 1, 2].map(i => <Skeleton key={i} className="h-72" />)}
        {data.map(c => (
          <Link key={c.id} to={`/canais/${c.id}`} onClick={() => setChannelId(c.id)}
            className="card card-hover overflow-hidden group hover:-translate-y-0.5 hover:shadow-[var(--shadow-md)] transition-[transform,box-shadow,border-color] duration-200">
            <div className="h-24 relative overflow-hidden" style={{
              background: c.banner_url ? `center/cover url(${c.banner_url})`
                : `linear-gradient(135deg, ${c.theme?.bg_center ?? 'var(--elev)'}, ${c.theme?.bg_edge ?? 'var(--bg-2)'})`,
            }}>
              <div className="absolute inset-0 bg-gradient-to-t from-panel via-panel/20 to-transparent" />
              <span className="absolute top-0 left-0 right-0 h-[2px]" style={{ background: c.color || 'var(--accent)' }} />
            </div>
            <div className="px-5 pb-5 -mt-10 relative">
              <div className="flex items-end gap-3">
                <Avatar c={c} size={72} />
                <div className="min-w-0 pb-1">
                  <div className="font-semibold text-[15px] truncate">{c.name}</div>
                  <div className="text-sm text-muted truncate">{c.handle || 'sem @'}</div>
                </div>
              </div>
              <div className="text-[13px] text-muted mt-3 line-clamp-2 min-h-10">{c.niche || 'Nicho ainda não definido'}</div>
              <div className="flex items-center gap-4 mt-4 text-sm num">
                <span className="flex items-center gap-1.5" title="inscritos"><Users size={14} className="text-faint" />{fmtNum(c.stats?.subscribers ?? 0)}</span>
                <span className="flex items-center gap-1.5" title="views"><Eye size={14} className="text-faint" />{fmtNum(c.stats?.views ?? 0)}</span>
                <span className="flex items-center gap-1.5" title="vídeos"><PlaySquare size={14} className="text-faint" />{c.stats?.videos ?? c.counts?.published ?? 0}</span>
                <div className="flex-1" />
                <ChannelState c={c} />
              </div>
              <div className="flex items-center gap-2 mt-3 pt-3 border-t border-line text-[12px] text-muted">
                <span title="Quanto o piloto automático produz neste canal · ★ = sugerido pelos dados">Modo</span>
                <FocusPicker channelId={c.id} compact />
              </div>
            </div>
          </Link>
        ))}
        <button onClick={() => connectYoutube()} className="rounded-[var(--r-md)] border border-dashed border-line2 min-h-64 grid place-items-center hover:border-accent/50 hover:bg-accent/[0.04] transition-colors text-center p-6 group">
          <div className="flex flex-col items-center gap-3">
            <div className="w-14 h-14 rounded-2xl bg-bad/10 border border-bad/25 grid place-items-center group-hover:scale-105 transition-transform"><Youtube className="text-bad" size={26} /></div>
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
    ? <img src={c.avatar_url} alt="" referrerPolicy="no-referrer" className="rounded-full border-4 border-panel shrink-0 object-cover shadow-[var(--shadow-md)]" style={{ width: size, height: size }} />
    : <div className="rounded-full border-4 border-panel grid place-items-center font-semibold text-white shrink-0 shadow-[var(--shadow-md)]"
      style={{ width: size, height: size, background: c.color || 'var(--grad)', fontSize: size * 0.4 }}>{c.theme?.logo_letter ?? c.name?.[0] ?? '?'}</div>
}

export function ChannelState({ c }: { c: Channel & { connected?: boolean } }) {
  if (!c.connected)
    return <button className="badge badge-warn hover:brightness-125 transition" onClick={e => { e.preventDefault(); connectYoutube(c.id) }}><Link2 size={12} /> Conectar</button>
  if (c.setup_status === 'configuring' || c.setup_status === 'pending')
    return <span className="badge badge-accent"><Loader2 size={12} className="animate-spin" /> Configurando</span>
  return <span className="badge badge-ok"><span className="dot" />Conectado</span>
}
