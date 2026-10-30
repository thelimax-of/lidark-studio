// Dados "ao vivo" compartilhados pela barra do topo (mesmas chaves de cache que as páginas usam → zero requisições extras).
import { useQuery } from '@tanstack/react-query'
import { api, ApiError, useApi, type Channel, type Job, type Notification } from '../api'
import { useChannel } from '../ui'

export function useActiveJobs() {
  const { data = [] } = useApi<Job[]>('/jobs?limit=25')
  const active = data.filter(j => j.status === 'running' || j.status === 'queued')
  const running = active.filter(j => j.status === 'running')
  return { all: data, active, running, queued: active.filter(j => j.status === 'queued') }
}

export function usePendingComments() {
  const { channel } = useChannel()
  const { data } = useApi<{ counts: Record<string, number> }>(channel ? `/comments?channel_id=${channel.id}&status=new` : null, { refetchInterval: 300000 })
  return data?.counts?.new ?? 0
}

export type NotifResp = { items: Notification[]; unread: number }
export const NOTIF_KEY = '/notifications?limit=30'

/** Notificações (o endpoint pode ainda não existir: 404 → vazio, sem novas tentativas nem polling). */
export function useNotifications() {
  const q = useQuery<NotifResp | null>({
    queryKey: [NOTIF_KEY],
    queryFn: async () => {
      try { return await api<NotifResp>(NOTIF_KEY) } catch (e) {
        if (e instanceof ApiError && e.status === 404) return null
        throw e
      }
    },
    refetchInterval: q => (q.state.data === null ? false : 120_000),
    staleTime: 30_000,
  })
  return { available: q.data !== null, items: q.data?.items ?? [], unread: q.data?.unread ?? 0, refetch: q.refetch }
}

export function ChannelAvatar({ c, size = 24, className = '' }: { c?: Partial<Channel> | null; size?: number; className?: string }) {
  const style = { width: size, height: size }
  if (!c) return <div className={'rounded-full bg-panel2 border border-line2 shrink-0 ' + className} style={style} />
  return c.avatar_url
    ? <img src={c.avatar_url} alt="" referrerPolicy="no-referrer" decoding="async" className={'rounded-full object-cover shrink-0 ring-1 ring-line2 ' + className} style={style} />
    : <div className={'rounded-full grid place-items-center font-semibold text-white shrink-0 ring-1 ring-white/10 ' + className}
      style={{ ...style, background: c.color ?? 'var(--accent)', fontSize: size * 0.42 }}>{c.theme?.logo_letter ?? c.name?.[0] ?? '?'}</div>
}
