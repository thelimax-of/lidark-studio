import type { MouseEvent } from 'react'
import { Crosshair, Lightbulb } from 'lucide-react'
import { api, invalidate, useApi } from '../api'
import { act, SectionTitle, Skeleton } from '../ui'

export type FocusMode = 'foco' | 'normal' | 'reduzido' | 'pausado'
export type FocusInfo = {
  channel_id: number; name: string; mode: FocusMode; label: string
  suggested: FocusMode; suggested_label: string; reason: string; confidence: 'baixa' | 'média' | 'alta'; matches: boolean
  stats: Record<string, number | null>
}
type FocusResp = { modes: { id: FocusMode; label: string; hint: string }[]; channels: FocusInfo[] }

export const FOCUS_TONE: Record<FocusMode, string> = { foco: 'text-ok', normal: 'text-muted', reduzido: 'text-warn', pausado: 'text-bad' }

/** Modo foco de todos os canais + a sugestão pelos dados (uma chamada só, compartilhada entre as telas). */
export const useFocus = () => useApi<FocusResp>('/focus')

export async function setFocus(channelId: number, mode: FocusMode, label?: string) {
  await act(() => api(`/channels/${channelId}/focus`, { method: 'PUT', body: { mode } }), `Modo ${label ?? mode} ativado`)
  invalidate('/focus')
  invalidate('/channels')
}

/** Selo do modo atual; se os dados sugerem outro, mostra a sugestão ao lado (o motivo fica no título). */
export function FocusBadge({ info }: { info?: FocusInfo }) {
  if (!info) return <span className="text-faint">—</span>
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap" title={`Sugestão (${info.confidence} confiança): ${info.suggested_label}\n${info.reason}`}>
      <span className={`badge ${FOCUS_TONE[info.mode]}`}><Crosshair size={11} /> {info.label}</span>
      {!info.matches && <span className={`text-[11.5px] ${FOCUS_TONE[info.suggested]}`}>→ sugerido {info.suggested_label}</span>}
    </span>
  )
}

/** Botões dos 4 modos. `compact` = só os botões (cartão da lista de canais, que é um link). */
export function FocusPicker({ channelId, compact }: { channelId: number; compact?: boolean }) {
  const { data } = useFocus()
  const info = data?.channels.find(c => c.channel_id === channelId)
  if (!data || !info) return null
  const stop = (e: MouseEvent) => { e.preventDefault(); e.stopPropagation() }
  return (
    <div className="seg" onClick={stop}>
      {data.modes.map(m => (
        <button key={m.id} data-active={info.mode === m.id} title={m.hint + (info.suggested === m.id ? `\n\nSugerido pelos dados: ${info.reason}` : '')}
          onClick={e => { stop(e); if (info.mode !== m.id) setFocus(channelId, m.id, m.label) }}>
          {m.label}{info.suggested === m.id ? (compact ? '★' : ' ★') : ''}
        </button>
      ))}
    </div>
  )
}

/** Cartão do canal: modo atual, o que cada modo faz e a sugestão pelos dados (o dono decide). */
export default function FocusCard({ channelId }: { channelId: number }) {
  const { data } = useFocus()
  const info = data?.channels.find(c => c.channel_id === channelId)
  if (!data) return <Skeleton className="h-36" />
  if (!info) return null
  const cur = data.modes.find(m => m.id === info.mode)
  return (
    <section className="card overflow-hidden">
      <SectionTitle hint="Quanto o piloto automático produz neste canal · nada muda sozinho" action={<FocusPicker channelId={channelId} />}>
        Modo foco
      </SectionTitle>
      <div className="p-4 space-y-2.5 text-[13px]">
        <div className="text-muted">{cur?.hint}</div>
        <div className={`flex items-start gap-2.5 rounded-[var(--r-md)] border px-3 py-2.5 ${info.matches ? 'border-line bg-bg2/40' : 'border-warn/35 bg-warn/[0.05]'}`}>
          <Lightbulb size={15} className={`shrink-0 mt-0.5 ${FOCUS_TONE[info.suggested]}`} />
          <div className="min-w-0">
            <div>Sugestão pelos dados: <b className={FOCUS_TONE[info.suggested]}>{info.suggested_label}</b>
              <span className="text-faint"> · confiança {info.confidence}</span>
              {info.matches && <span className="text-faint"> · já está neste modo</span>}</div>
            <div className="text-muted text-[12.5px] mt-0.5">{info.reason}</div>
          </div>
          {!info.matches && <button className="btn btn-sm btn-primary shrink-0" onClick={() => setFocus(channelId, info.suggested, info.suggested_label)}>Usar sugestão</button>}
        </div>
      </div>
    </section>
  )
}
