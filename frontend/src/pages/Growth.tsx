import { useState } from 'react'
import { RefreshCw, FlaskConical, Trophy } from 'lucide-react'
import { api, invalidate, useApi } from '../api'
import { act, fmtNum, SectionTitle } from '../ui'

// ---------------------------------------------------------------- progresso para a monetização

type Tier = { label: string; subs: number; hours: number; shorts_views: number; eta_days: number | null; eta_date: string | null
  subs_eta: number | null; hours_eta: number | null; shorts_eta: number | null; shorts_per_day_needed: number }
type TierKey = 'basic' | 'full' | 'full_2027'
// shorts_views_90d = views QUALIFICADAS (engajadas, sem anúncio pago); os campos *_raw/_engaged/_ads mostram de onde vem
type Ypp = { connected: boolean; error?: string; subs: number; hours_12m: number; shorts_views_90d: number
  shorts_raw_views_90d?: number; shorts_engaged_views_90d?: number; shorts_ads_views_90d?: number; shorts_feed_engaged_90d?: number
  engaged_rate?: number | null; engaged_estimated?: boolean; notes?: string[]
  rates: { subs_per_day: number; hours_per_day: number; shorts_views_per_day: number; shorts_raw_views_per_day?: number }
  tiers: Partial<Record<TierKey, Tier>>; updated_at?: string }

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
  const [tier, setTier] = useState<TierKey>('full')
  if (!y || !y.connected) return null
  if (!y.tiers) return <section className="card p-4 text-[13px] text-muted">Monetização: {y.error || 'sem dados ainda'}</section>
  // a regra "full" expira em 01/02/2027 (o backend deixa de mandar); cai na regra nova
  const t = y.tiers[tier] ?? y.tiers.full_2027 ?? y.tiers.full ?? y.tiers.basic
  if (!t) return null
  const raw = y.shorts_raw_views_90d
  const eta = t.eta_date ? new Date(t.eta_date + 'T12:00').toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' }) : null
  return (
    <section className="card overflow-hidden">
      <SectionTitle hint="Requisitos do Programa de Parcerias do YouTube"
        action={<div className="flex items-center gap-2">
          <div className="seg">
            <button data-active={tier === 'basic'} onClick={() => setTier('basic')}>Básico</button>
            {y.tiers.full && <button data-active={tier === 'full'} onClick={() => setTier('full')} data-tip={y.tiers.full.label}>Anúncios</button>}
            {y.tiers.full_2027 && <button data-active={tier === 'full_2027' || (!y.tiers.full && tier === 'full')} onClick={() => setTier('full_2027')}
              data-tip={y.tiers.full_2027.label}>Anúncios 2027</button>}
          </div>
          {!compact && <button className="btn btn-sm btn-icon btn-ghost" data-tip="Atualizar agora"
            onClick={() => act(() => api(`/channels/${channelId}/ypp?refresh=true`)).then(() => invalidate(`/channels/${channelId}/ypp`))}><RefreshCw size={14} /></button>}
        </div>}>
        Caminho para monetizar
      </SectionTitle>
      <div className="p-4 grid md:grid-cols-[1fr_1fr_1fr_auto] gap-5 items-start">
        <Meter label="Inscritos" have={y.subs} need={t.subs} sub={`+${y.rates.subs_per_day.toFixed(1)}/dia · ${when(t.subs_eta)}`} />
        <Meter label="Views engajadas de Shorts (90 dias)" have={y.shorts_views_90d} need={t.shorts_views}
          sub={`${fmtNum(y.rates.shorts_views_per_day)}/dia hoje · precisa ~${fmtNum(t.shorts_per_day_needed)}/dia`} />
        <Meter label="Horas em vídeos longos (12 meses)" have={y.hours_12m} need={t.hours} sub={`${y.rates.hours_per_day.toFixed(1)} h/dia · ${when(t.hours_eta)}`} />
        <div className="md:w-44 md:border-l md:border-line md:pl-5">
          <div className="text-[12px] text-muted">Previsão</div>
          <div className="text-[17px] font-semibold mt-0.5 capitalize">{eta ?? (t.eta_days === 0 ? 'Elegível!' : '—')}</div>
          <div className="text-[11.5px] text-faint mt-0.5 leading-snug">{eta ? 'no ritmo dos últimos 28 dias' : 'o ritmo atual ainda não chega lá; precisa acelerar'}</div>
        </div>
      </div>
      {raw != null && (
        <div className="px-4 pb-3 flex flex-wrap gap-x-4 gap-y-1 text-[12px] text-muted">
          <span>Shorts 90 dias: <b className="num font-semibold text-text">{fmtNum(raw)}</b> views</span>
          <span data-tip="Contam p/ monetizar (sem as vindas de anúncio pago)">
            <b className="num font-semibold text-text">{fmtNum(y.shorts_views_90d)}</b> views engajadas (contam p/ monetizar)
          </span>
          {y.engaged_rate != null && <span>taxa engajada <b className="num font-semibold text-text">{y.engaged_rate}%</b></span>}
          {!!y.shorts_ads_views_90d && <span className="text-warn">{fmtNum(y.shorts_ads_views_90d)} views de anúncio pago (não contam)</span>}
          {y.shorts_feed_engaged_90d != null && <span data-tip="Só o feed do Shorts divide receita de anúncios">feed do Shorts: {fmtNum(y.shorts_feed_engaged_90d)} engajadas</span>}
          {y.engaged_estimated && <span className="text-faint">(views engajadas indisponíveis — usando views brutas)</span>}
        </div>
      )}
      {!compact && <div className="px-4 pb-3 text-[11.5px] text-faint space-y-0.5">
        <div>Basta inscritos + UM dos caminhos (Shorts ou horas). As horas dos Shorts não contam para as horas dos vídeos longos.</div>
        {(y.notes || []).map(n => <div key={n}>{n}</div>)}
      </div>}
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
