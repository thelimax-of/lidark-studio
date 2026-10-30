// Telas de rota para seções que existiam só dentro de outras páginas (Visão geral, Campanhas, Campeões, Modo foco).
// Reaproveitam os componentes das páginas; a aparência vem delas.
import { useNavigate } from 'react-router-dom'
import { Tv } from 'lucide-react'
import AllChannels from '../pages/Overview'
import CampaignsSection from '../pages/Campaigns'
import { ChampionsCard } from '../pages/Champions'
import FocusCard from '../pages/FocusMode'
import { ChannelScope, Empty, PageHeader, useChannel, useScope } from '../ui'

export function OverviewPage() {
  const { setChannelId } = useChannel()
  const nav = useNavigate()
  return <AllChannels scope={null} onOpen={id => {
    setChannelId(id)
    try { localStorage.setItem('scope:dashboard', 'one') } catch { /* noop */ }
    nav('/')
  }} />
}

const NoChannel = () => <Empty icon={<Tv size={18} />} title="Nenhum canal ainda" text="Conecte um canal do YouTube para começar." />

export function CampaignsPage() {
  const { channel } = useChannel()
  return (
    <>
      <PageHeader eyebrow={channel?.name} title="Campanhas" subtitle="Datas que puxam audiência viram séries: no período, parte da produção vai para o tema da campanha." />
      {channel ? <CampaignsSection key={channel.id} channelId={channel.id} /> : <NoChannel />}
    </>
  )
}

export function ChampionsPage() {
  const { channel } = useChannel()
  const [all, setAll] = useScope('champions', false)
  return (
    <>
      <PageHeader eyebrow="Crescer" title="Campeões" subtitle="Os Shorts que mais prenderam o público — e o atalho para virar vídeo longo."
        actions={<ChannelScope all={all} onChange={setAll} />} />
      <ChampionsCard channelId={all ? undefined : channel?.id} />
    </>
  )
}

export function FocusPage() {
  const { channels, channel } = useChannel()
  const list = channel ? [channel, ...channels.filter(c => c.id !== channel.id)] : channels
  return (
    <>
      <PageHeader eyebrow="Crescer" title="Modo foco" subtitle="Quanto o piloto automático produz em cada canal. Nada muda sozinho." />
      {!list.length ? <NoChannel /> : (
        <div className="grid gap-4 lg:grid-cols-2">
          {list.map(c => (
            <div key={c.id}>
              <div className="text-[12px] text-muted mb-1.5 px-1">{c.name}</div>
              <FocusCard channelId={c.id} />
            </div>
          ))}
        </div>
      )}
    </>
  )
}
