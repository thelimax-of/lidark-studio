import { useNavigate } from 'react-router-dom'
import clsx from 'clsx'
import { Cpu } from 'lucide-react'
import { useApi } from '../api'
import { Progress } from '../ui'
import { useActiveJobs } from './live'
import { usePopover } from './usePopover'

export const JOB_KIND: Record<string, string> = {
  discover_ideas: 'Pautas', score_idea: 'Nota', verify_idea: 'Checagem', manual_idea: 'Validação', write_script: 'Roteiro',
  review_script: 'Revisão', render_video: 'Vídeo', autopilot: 'Piloto', publish: 'Publicação', collect_metrics: 'Métricas',
  setup_channel: 'Canal', channel_identity: 'Identidade', trend_radar: 'Radar', inspect_video: 'Inspeção', import_youtube: 'Importação',
}

/** Anel de progresso do job principal + contagem. */
function Ring({ value, size = 16 }: { value: number; size?: number }) {
  const r = size / 2 - 2, c = 2 * Math.PI * r
  return (
    <svg width={size} height={size} className="-rotate-90 shrink-0" aria-hidden>
      <defs><linearGradient id="jr" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="var(--accent)" /><stop offset="1" stopColor="var(--accent-2)" /></linearGradient></defs>
      <circle cx={size / 2} cy={size / 2} r={r} stroke="var(--line-2)" strokeWidth="2" fill="none" />
      <circle cx={size / 2} cy={size / 2} r={r} stroke="url(#jr)" strokeWidth="2" fill="none" strokeLinecap="round"
        strokeDasharray={c} strokeDashoffset={c * (1 - Math.max(.04, value))} style={{ transition: 'stroke-dashoffset .5s var(--ease)' }} />
    </svg>
  )
}

export default function JobsIndicator({ connected }: { connected: boolean }) {
  const { active, running, queued } = useActiveJobs()
  const { data: health } = useApi<any>('/health', { refetchInterval: 60000 })
  const { open, setOpen, ref, toggle } = usePopover()
  const nav = useNavigate()
  const lead = running[0]
  return (
    <div className="relative" ref={ref}>
      <button data-trigger onClick={toggle} aria-expanded={open} className={clsx('btn btn-sm gap-2', !connected && 'text-bad')}
        aria-label={active.length ? `${active.length} tarefas em produção` : 'Produção ociosa'}>
        {!connected ? <span className="w-1.5 h-1.5 rounded-full bg-bad" /> : lead ? <Ring value={lead.progress} /> : active.length ? <span className="live-dot" /> : <span className="w-1.5 h-1.5 rounded-full bg-faint" />}
        <span className="num hidden md:inline">{!connected ? 'Motor offline' : active.length ? `${active.length} em produção` : 'Ocioso'}</span>
        {connected && active.length > 0 && <span className="num md:hidden">{active.length}</span>}
      </button>
      {open && (
        <div className="menu right-0 top-full mt-2 w-[380px] max-w-[calc(100vw-1.5rem)] p-0! overflow-hidden">
          <div className="flex items-center justify-between gap-2 px-4 py-3 border-b border-line">
            <span className="card-title text-[13px]!">Produção</span>
            <span className="text-[12px] text-muted num">{running.length} rodando · {queued.length} na fila</span>
          </div>
          {!active.length && <div className="text-[13px] text-muted px-4 py-7 text-center">Nenhuma tarefa rodando agora.</div>}
          <div className="max-h-80 overflow-y-auto p-1">
            {[...running, ...queued].slice(0, 8).map(j => (
              <button key={j.id} onClick={() => { setOpen(false); nav('/fila') }} className="w-full text-left px-3 py-2.5 rounded-lg hover:bg-white/[0.05] transition-colors">
                <div className="flex items-center justify-between gap-2 text-[12px] text-muted">
                  <span>{JOB_KIND[j.kind] ?? j.kind}</span>
                  <span className="num">{j.status === 'queued' ? 'na fila' : `${Math.round(j.progress * 100)}%`}</span>
                </div>
                <div className="text-[13px] truncate mt-0.5">{j.title}</div>
                {j.status === 'running' && <><Progress value={j.progress} className="mt-2" /><div className="text-[12px] text-muted mt-1 truncate">{j.stage}</div></>}
              </button>
            ))}
          </div>
          <div className="border-t border-line px-4 py-2.5 flex items-center gap-2 text-[12px] text-muted">
            <span className={clsx('w-1.5 h-1.5 rounded-full', connected ? 'bg-ok' : 'bg-bad')} />
            <span className="flex-1">{connected ? 'Motor local online' : 'Motor desconectado — reconectando…'}</span>
            {health && <span className="inline-flex items-center gap-1 text-faint"><Cpu size={12} />{health.ffmpeg?.nvenc ? 'NVENC' : 'CPU'}{health.llm?.gemini_keys ? ' · Gemini' : ''}{health.llm?.glm ? '+GLM' : ''}</span>}
          </div>
          <div className="border-t border-line p-1"><button onClick={() => { setOpen(false); nav('/fila') }} className="menu-item justify-center text-muted">Abrir fila de produção</button></div>
        </div>
      )}
    </div>
  )
}
