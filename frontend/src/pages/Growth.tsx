import { useState } from 'react'
import { RefreshCw, FlaskConical, Trophy } from 'lucide-react'
import { api, invalidate, useApi } from '../api'
import { act, fmtNum, SectionTitle } from '../ui'

// ---------------------------------------------------------------- progresso para a monetização

type Tier = { label: string; subs: number; hours: number; shorts_views: number; eta_days: number | null; eta_date: string | null
  subs_eta: number | null; hours_eta: number | null; shorts_eta: number | null; shorts_per_day_needed: number }
type Ypp = { connected: boolean; error?: string; subs: number; hours_12m: number; shorts_views_90d: number
  rates: { subs_per_day: number; hours_per_day: number; shorts_views_per_day: number }; tiers: Record<'basic' | 'full', Tier>; updated_at?: string }

function Meter({ label, have, need, sub }: { label: string; have: number; need: number; sub: string }) {
  const p = Math.min(1, have / need)
  return (
    <div>
      <div className="flex items-baseline justify-between text-[12.5px]">
        <span className="text-muted">{label}</span>
        <span className="num"><b className="font-semibold">{fmtNum(Math.round(have))}</b><span className="text-faint"> / {fmtNum(need)}</span></span>
      </div>
      <div className="h-1.5 rounded-full bg-line overflow-hidden mt-1.5"><div className={`h-full rounded-full ${p >= 1 ? 'bg-ok' : 'bg-text/75'}`} style={{ width: `${Math.max(1.5, p * 100)}%` }} /></div>
      <div className="text-[11.5px] text-faint mt-1">{sub}</div>
    </div>
  )
}

const when = (d: number | null) => d === 0 ? 'atingido' : d == null ? 'fora do ritmo atual' : d > 730 ? 'mais de 2 anos no ritmo atual' : `~${d} dias no ritmo atual`

export function YppCard({ channelId, compact }: { channelId: number; compact?: boolean }) {
  const { data: y } = useApi<Ypp>(`/channels/${channelId}/ypp`)
  const [tier, setTier] = useState<'basic' | 'full'>('full')
  if (!y || !y.connected) return null
  if (!y.tiers) return <section className="card p-4 text-[13px] text-muted">Monetização: {y.error || 'sem dados ainda'}</section>
  const t = y.tiers[tier]
  const eta = t.eta_date ? new Date(t.eta_date + 'T12:00').toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' }) : null
  return (
    <section className="card overflow-hidden">
      <SectionTitle hint="Requisitos do Programa de Parcerias do YouTube"
        action={<div className="flex items-center gap-2">
          <div className="seg">
            <button data-active={tier === 'basic'} onClick={() => setTier('basic')}>Básico</button>
            <button data-active={tier === 'full'} onClick={() => setTier('full')}>Anúncios</button>
          </div>
          {!compact && <button className="btn btn-sm btn-icon btn-ghost" data-tip="Atualizar agora"
            onClick={() => act(() => api(`/channels/${channelId}/ypp?refresh=true`)).then(() => invalidate(`/channels/${channelId}/ypp`))}><RefreshCw size={14} /></button>}
        </div>}>
        Caminho para monetizar
      </SectionTitle>
      <div className="p-4 grid md:grid-cols-[1fr_1fr_1fr_auto] gap-5 items-start">
        <Meter label="Inscritos" have={y.subs} need={t.subs} sub={`+${y.rates.subs_per_day.toFixed(1)}/dia · ${when(t.subs_eta)}`} />
        <Meter label="Views de Shorts (90 dias)" have={y.shorts_views_90d} need={t.shorts_views}
          sub={`${fmtNum(y.rates.shorts_views_per_day)}/dia hoje · precisa ~${fmtNum(t.shorts_per_day_needed)}/dia`} />
        <Meter label="Horas em vídeos longos (12 meses)" have={y.hours_12m} need={t.hours} sub={`${y.rates.hours_per_day.toFixed(1)} h/dia · ${when(t.hours_eta)}`} />
        <div className="md:w-44 md:border-l md:border-line md:pl-5">
          <div className="text-[12px] text-muted">Previsão</div>
          <div className="text-[17px] font-semibold mt-0.5 capitalize">{eta ?? (t.eta_days === 0 ? 'Elegível!' : '—')}</div>
          <div className="text-[11.5px] text-faint mt-0.5 leading-snug">{eta ? 'no ritmo dos últimos 28 dias' : 'o ritmo atual ainda não chega lá; precisa acelerar'}</div>
        </div>
      </div>
      {!compact && <div className="px-4 pb-3 text-[11.5px] text-faint">Basta inscritos + UM dos caminhos (Shorts ou horas). As horas dos Shorts não contam para as horas dos vídeos longos.</div>}
    </section>
  )
}

// ---------------------------------------------------------------- laboratório de experimentos

type Opt = { key: string; label: string; n: number; perf: number; retention: number; views: number }
type Exp = { videos: number; base_perf?: number; base_retention?: number; lessons: string[]; dimensions: { key: string; label: string; winner: string | null; options: Opt[] }[] }

export function ExperimentsCard({ channelId }: { channelId: number }) {
  const { data: e } = useApi<Exp>(`/channels/${channelId}/experiments`)
  if (!e) return null
  return (
    <section className="card overflow-hidden">
      <SectionTitle hint="Cada vídeo testa combinações diferentes; aqui aparece o que de fato rende mais no seu canal">
        <span className="flex items-center gap-2"><FlaskConical size={15} className="text-muted" />Laboratório de experimentos</span>
      </SectionTitle>
      {e.videos < 3 ? (
        <div className="p-4 text-[13px] text-muted">
          {e.videos} vídeo(s) publicado(s) com o sistema de variedade. Os resultados aparecem a partir de ~6 vídeos
          (cada opção precisa de pelo menos 2 vídeos). Enquanto isso, o sistema segue testando combinações diferentes.
        </div>
      ) : (
        <>
          {e.lessons.length > 0 && (
            <div className="px-4 pt-4 space-y-1.5">
              {e.lessons.map(l => <div key={l} className="flex gap-2 text-[13px]"><Trophy size={14} className="text-warn shrink-0 mt-0.5" />{l}</div>)}
            </div>
          )}
          <div className="p-4 grid md:grid-cols-2 xl:grid-cols-3 gap-4">
            {e.dimensions.map(d => (
              <div key={d.key} className="border border-line rounded-lg overflow-hidden">
                <div className="px-3 py-2 text-[12.5px] font-medium border-b border-line bg-panel2">{d.label}</div>
                <table className="w-full text-[12.5px]">
                  <tbody>
                    {d.options.slice(0, 5).map(o => (
                      <tr key={o.key} className="border-b border-line last:border-0">
                        <td className="px-3 py-1.5 truncate max-w-[150px]">{o.key === d.winner && <Trophy size={11} className="inline text-warn mr-1 -mt-0.5" />}{o.label}</td>
                        <td className={`px-2 py-1.5 text-right num ${o.n < 2 ? 'text-faint' : ''}`}>{o.perf}</td>
                        <td className="px-2 py-1.5 text-right num text-muted">{o.retention}%</td>
                        <td className="px-3 py-1.5 text-right num text-faint">{o.n}×</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </div>
          <div className="px-4 pb-3 text-[11.5px] text-faint">Colunas: desempenho (0-100), retenção média, nº de vídeos. Média do canal: {e.base_perf} · retenção {e.base_retention}%.</div>
        </>
      )}
    </section>
  )
}
