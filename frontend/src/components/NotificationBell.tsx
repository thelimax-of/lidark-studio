import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import clsx from 'clsx'
import { Bell, CheckCheck, BellOff } from 'lucide-react'
import { api, invalidate, onNotification, type Notification } from '../api'
import { ago, toast } from '../ui'
import { useNotifications } from './live'
import { usePopover } from './usePopover'

const markRead = (body: { ids: (number | string)[] } | { all: true }) =>
  api('/notifications/read', { body }).then(() => invalidate('/notifications')).catch(() => {})

const TONE: Record<string, string> = { error: 'bg-bad', failed: 'bg-bad', warn: 'bg-warn', warning: 'bg-warn', success: 'bg-ok', published: 'bg-ok', done: 'bg-ok' }

export default function NotificationBell() {
  const { available, items, unread } = useNotifications()
  const { open, setOpen, ref, toggle } = usePopover()
  const nav = useNavigate()

  // notificação nova chegando pelo SSE → aviso discreto
  useEffect(() => onNotification(n => toast.info(n.title + (n.body ? ` — ${n.body}` : ''))), [])

  const go = (n: Notification) => {
    setOpen(false)
    if (!n.read) void markRead({ ids: [n.id] })
    if (!n.link) return
    if (n.link.startsWith('/')) nav(n.link)
    else window.open(n.link, '_blank', 'noopener')
  }

  return (
    <div className="relative" ref={ref}>
      <button data-trigger className="btn btn-sm btn-icon btn-ghost relative" aria-label={`Notificações${unread ? ` (${unread} novas)` : ''}`}
        aria-expanded={open} onClick={toggle} data-tip={open ? undefined : 'Notificações'} data-tip-pos="bottom">
        <Bell size={16} />
        {unread > 0 && <span className="count-pill absolute -top-1 -right-1 ring-2 ring-bg">{unread > 99 ? '99+' : unread}</span>}
      </button>
      {open && (
        <div className="menu right-0 top-full mt-2 w-[380px] max-w-[calc(100vw-1.5rem)] p-0! overflow-hidden">
          <div className="flex items-center justify-between gap-2 px-4 py-3 border-b border-line">
            <div>
              <div className="card-title text-[13px]!">Notificações</div>
              <div className="text-[12px] text-muted num">{unread ? `${unread} não lidas` : 'Tudo em dia'}</div>
            </div>
            {unread > 0 && <button className="btn btn-sm btn-ghost" onClick={() => markRead({ all: true })}><CheckCheck size={14} /> Marcar todas</button>}
          </div>
          <div className="max-h-[420px] overflow-y-auto p-1">
            {!available ? (
              <div className="px-4 py-8 text-center text-[13px] text-muted flex flex-col items-center gap-2"><BellOff size={18} className="text-faint" />As notificações aparecem aqui assim que o motor começar a enviá-las.</div>
            ) : !items.length ? (
              <div className="px-4 py-8 text-center text-[13px] text-muted">Nenhuma notificação ainda.</div>
            ) : items.map(n => (
              <button key={n.id} onClick={() => go(n)} className={clsx('w-full text-left flex gap-3 px-3 py-2.5 rounded-lg transition-colors hover:bg-white/[0.05]', !n.read && 'bg-white/[0.025]')}>
                <span className={clsx('mt-1.5 w-1.5 h-1.5 rounded-full shrink-0', n.read ? 'bg-transparent' : TONE[n.kind] ?? 'bg-accent')} />
                <span className="min-w-0 flex-1">
                  <span className={clsx('block text-[13px] leading-snug', n.read ? 'text-muted' : 'text-text font-medium')}>{n.title}</span>
                  {n.body && <span className="block text-[12px] text-muted mt-0.5 line-clamp-2">{n.body}</span>}
                  <span className="block text-[11px] text-faint mt-1">{ago(n.created_at)}</span>
                </span>
              </button>
            ))}
          </div>
          <div className="border-t border-line p-1">
            <button className="menu-item justify-center text-muted" onClick={() => { setOpen(false); nav('/notificacoes') }}>Ver todas</button>
          </div>
        </div>
      )}
    </div>
  )
}
