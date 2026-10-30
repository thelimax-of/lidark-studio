import { useState } from 'react'
import clsx from 'clsx'
import { Bot, Play, Rocket, TrendingDown, ExternalLink } from 'lucide-react'
import { api, invalidate, useApi } from '../api'
import { act, ago, ChannelTag, PageHeader, SectionTitle, Skeleton, fmtNum, toast, useChannel } from '../ui'

type Auto = Record<string, { label: string; desc: string }>
type Settings = Record<string, boolean> & { enabled: boolean; enabled_default: boolean }
type ChanRow = {
  channel_id: number; name: string; auto_pilot: boolean; focus: string; settings: Settings; last_tick?: string
  breakouts: { publication_id: number; title: string; url?: string; views: number; ratio?: number; age_hours: number }[]
  flops: { publication_id: number; title: string; url?: string; views: number; ratio?: number; median?: number }[]
  week: Record<string, number>
}
type Overview = { automations: Auto; limits: Record<string, number>; channels: ChanRow[] }
type Action = { id: number; channel_id: number; kind: string; ref: string; title: string; data: Record<string, any>; status: string; created_at: string }

const STATUS: Record<string, [string, string]> = {
  done: ['feito', 'badge'], testing: ['medindo', 'badge badge-warn'], better: ['ajudou', 'badge badge-ok'],
  neutral: ['pouco efeito', 'badge'], worse: ['não ajudou', 'badge badge-bad'], failed: ['não feito', 'badge badge-bad'],
}
const WEEK: Record<string, string> = { followup: 'continuações', long: 'longos', seed: 'comentários', retitle: 'títulos trocados', trend_approve: 'tendências aprovadas' }

function Switch({ on, onChange, disabled }: { on: boolean; onChange: (v: boolean) => void; disabled?: boolean }) {
  return (
    <button role="switch" aria-checked={on} disabled={disabled} onClick={() => onChange(!on)}
      className={clsx('w-9 h-5 rounded-full relative transition shrink-0 disabled:opacity-40', on ? 'bg-[var(--accent)]' : 'bg-line2')}>
      <span className={clsx('absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all', on ? 'left-[18px]' : 'left-0.5')} />
    </button>
  )
}

export default function Autopilot() {
  const { data, isLoading } = useApi<Overview>('/autogrowth', { refetchInterval: 60000 })
  const { channel } = useChannel()
  const [only, setOnly] = useState(false)
  const { data: acts = [] } = useApi<Action[]>(`/autogrowth/actions?limit=80${only && channel ? `&channel_id=${channel.id}` : ''}`)
  const save = (cid: number, patch: Record<string, boolean>) =>
    act(() => api(`/autogrowth/${cid}`, { method: 'PUT', body: patch })).then(() => invalidate('/autogrowth'))
  const run = () => act(() => api<{ started: boolean }>('/autogrowth/run', { method: 'POST' }))
    .then(r => { if (r) toast.ok(r.started ? 'Rodada iniciada — as ações aparecem no histórico' : 'Já está rodando'); setTimeout(() => invalidate('/autogrowth'), 8000) })
  return (
    <div>
      <PageHeader eyebrow="Crescer" title="Piloto automático de crescimento"
        subtitle="A cada 30 min, por canal, o sistema age sozinho dentro de limites seguros — e registra tudo aqui e no sino. Cada automação liga e desliga por canal."
        actions={<button className="btn btn-sm btn-primary" onClick={run}><Play size={14} /> Rodar agora</button>} />
      {isLoading || !data ? <Skeleton className="h-96" /> : (
        <div className="grid gap-4 lg:grid-cols-2">
          {data.channels.map(c => (
            <section key={c.channel_id} className="card overflow-hidden">
              <SectionTitle hint={`${c.last_tick ? `Última rodada ${ago(c.last_tick)}` : 'Ainda não rodou'}${c.focus === 'pausado' ? ' · canal pausado (modo foco): só avisos' : ''}${c.settings.enabled_default ? ' · segue o piloto automático do canal' : ''}`}
                action={<Switch on={c.settings.enabled} onChange={v => save(c.channel_id, { enabled: v })} />}>
                <span className="inline-flex items-center gap-2"><Bot size={15} />{c.name}</span>
              </SectionTitle>
              <ul className="divide-y divide-line">
                {Object.entries(data.automations).map(([k, a]) => (
                  <li key={k} className={clsx('flex items-start gap-3 px-4 py-2.5', !c.settings.enabled && 'opacity-55')}>
                    <div className="min-w-0 flex-1">
                      <div className="text-[13px] font-medium">{a.label}</div>
                      <div className="text-[12px] text-muted">{a.desc}</div>
                    </div>
                    <Switch on={!!c.settings[k]} onChange={v => save(c.channel_id, { [k]: v })} />
                  </li>
                ))}
              </ul>
              {(c.breakouts.length > 0 || c.flops.length > 0) && (
                <div className="border-t border-line px-4 py-3 space-y-1.5">
                  {c.breakouts.map(b => (
                    <div key={b.publication_id} className="flex items-center gap-2 text-[12.5px]">
                      <Rocket size={13} className="text-ok shrink-0" />
                      <span className="truncate flex-1">{b.title.replace(/#shorts/i, '')}</span>
                      <span className="text-muted num shrink-0">{fmtNum(b.views)}{b.ratio ? ` · ${b.ratio}×` : ''}</span>
                      {b.url && <a href={b.url} target="_blank" rel="noreferrer" className="text-muted"><ExternalLink size={12} /></a>}
                    </div>
                  ))}
                  {c.flops.map(f => (
                    <div key={f.publication_id} className="flex items-center gap-2 text-[12.5px]">
                      <TrendingDown size={13} className="text-bad shrink-0" />
                      <span className="truncate flex-1 text-muted">{f.title.replace(/#shorts/i, '')}</span>
                      <span className="text-faint num shrink-0">{fmtNum(f.views)} · mediana {f.median}</span>
                    </div>
                  ))}
                </div>
              )}
              <div className="border-t border-line px-4 py-2 text-[11.5px] text-faint flex flex-wrap gap-x-3">
                <span>Nos últimos 7 dias:</span>
                {Object.entries(WEEK).map(([k, l]) => <span key={k}><b className="text-muted num">{c.week[k] ?? 0}</b> {l}</span>)}
              </div>
            </section>
          ))}
        </div>
      )}
      <section className="card overflow-hidden mt-4">
        <SectionTitle hint="Tudo o que o piloto fez — trocas de título trazem o antes/depois e o resultado medido 48 h depois"
          action={<label className="flex items-center gap-1.5 text-[12.5px] text-muted"><input type="checkbox" checked={only} onChange={e => setOnly(e.target.checked)} /> só {channel?.name}</label>}>
          Histórico de ações</SectionTitle>
        {!acts.length ? <div className="p-5 text-[13px] text-muted">Nenhuma ação ainda.</div> : (
          <ul className="divide-y divide-line">
            {acts.map(a => {
              const [label, cls] = STATUS[a.status] ?? [a.status, 'badge']
              return (
                <li key={a.id} className="px-4 py-2.5 flex items-start gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="text-[13px]">{a.title}</div>
                    {a.kind === 'retitle' && a.data.before && (
                      <div className="text-[12px] text-muted mt-0.5">
                        “{a.data.before}” → <b className="text-text">“{a.data.after}”</b>
                        {a.data.rate_before != null && <> · {a.data.rate_before} → {a.data.rate_after} views/h</>}
                      </div>
                    )}
                    {a.data.error && <div className="text-[12px] text-bad mt-0.5">{a.data.error}</div>}
                    <div className="flex items-center gap-2 mt-1 text-[11.5px] text-faint"><ChannelTag id={a.channel_id} /><span>{ago(a.created_at)}</span></div>
                  </div>
                  <span className={cls}>{label}</span>
                </li>
              )
            })}
          </ul>
        )}
      </section>
    </div>
  )
}
