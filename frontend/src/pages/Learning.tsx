import { useState } from 'react'
import { Brain, RefreshCw, Rocket, TrendingDown, Sparkles, FlaskConical, Target } from 'lucide-react'
import { api, invalidate, useApi } from '../api'
import { act, ChannelScope, ChannelTag, Empty, fmtNum, PageHeader, SectionTitle, Skeleton, useChannel, useScope } from '../ui'

// ---------------------------------------------------------------- tipos (ver backend/lidark/learning.py)

type Opt = { key: string; label: string; n: number; n_all: number; effect: number; lo: number; hi: number; p_pos: number; p_best: number; mult: number }
type Dim = { key: string; label: string; options: Opt[]; tested: number; n: number }
type Coef = { key: string; label: string; effect: number; se: number; p_pos: number }
type Loo = { r2: number; spearman: number | null; concordance: number | null; pairs: number; rmse: number; rmse_baseline: number
  null_r2?: number; null_spearman?: number; null_concordance?: number; p_value?: number; skill_r2?: number }
type VideoRow = { pub_id: number; channel_id: number; title: string; url: string; thumbnail: string; published_at: string; age_h: number
  format: string; duration: number; views: number; views_at: Record<string, number | null>; x_normal: number | null; x_pred: number | null
  trained: boolean; imported: boolean; hook: string
  retention: { hook?: number; mid?: number; end?: number; relative?: number }
  analytics: { engaged_ratio?: number; avg_view_pct?: number; subs_per_1k?: number }
  variety: Record<string, string | undefined> }
type ChannelSum = { id: number; name: string; videos: number; trained: number; typical_48h: number; typical_7d: number; effect_x: number
  best: { title: string; url: string; views: number } | null }
type Report = { computed_at: string; seconds: number; channel_id: number | null; channels: ChannelSum[]
  model: { ok: boolean; n: number; alpha?: number; loo?: Loo; verdict?: string; coefs: Coef[] }
  idea_score: { spearman: number | null; n: number }; lessons: string[]; dimensions: Dim[]; weights: Record<string, Record<string, number>>
  videos: VideoRow[]; pred_vs_actual: { title: string; channel_id: number; pred: number; actual: number }[]
  curve: { age_h: number; views: number }[]; topics?: { win: [string, number, number][]; lose: [string, number, number][] } | null
  method: string[]; audience?: Audience | null }
type Breakout = { pub_id: number; channel_id: number; channel: string; title: string; url: string; thumbnail: string; age_h: number; views: number
  expected_now: number; x_normal: number; z: number; status: string; views_per_h: number | null
  proj_7d: number; proj_7d_low: number; proj_7d_high: number; p_above: number; calibration_n: number }
type Prediction = { score: number; low: number; high: number; reasons: string[]; similar: { title: string; views: number; url: string; x: number }[]
  x_normal?: number; x_low?: number; x_high?: number; views_48h?: { mid: number; low: number; high: number }; confidence?: string }

// ---------------------------------------------------------------- formatação

const fx = (x: number | null | undefined) => x == null ? '—' : `${x < 10 ? x.toFixed(1).replace('.', ',') : Math.round(x)}x`
const pctEff = (e: number) => { const p = (Math.exp(e) - 1) * 100; return `${p >= 0 ? '+' : ''}${Math.round(p)}%` }
const pct = (v: number | null | undefined, d = 0) => v == null ? '—' : `${(v * 100).toFixed(d).replace('.', ',')}%`
const age = (h: number) => h < 48 ? `${Math.round(h)} h` : `${(h / 24).toFixed(1).replace('.', ',')} d`
const conf = (p: number) => { const q = Math.max(p, 1 - p); return q >= 0.95 ? 'forte' : q >= 0.85 ? 'boa' : q >= 0.7 ? 'moderada' : 'fraca' }
const confTone = (p: number) => { const q = Math.max(p, 1 - p); return q >= 0.85 ? (p > 0.5 ? 'badge-ok' : 'badge-bad') : q >= 0.7 ? 'badge-warn' : '' }

// ---------------------------------------------------------------- peças

/** Barra divergente: ponto = efeito estimado, faixa = intervalo de 80%, centro = normal do canal. */
function EffectBar({ o }: { o: Opt }) {
  const R = Math.log(2.2) // escala: de 0,45x a 2,2x
  const pos = (e: number) => 50 + 50 * Math.max(-1, Math.min(1, e / R))
  const good = o.effect >= 0
  return (
    <div className="relative h-4 w-full" data-tip={`${pctEff(o.effect)} (80%: ${pctEff(o.lo)} a ${pctEff(o.hi)}) · chance de ser positivo ${pct(o.p_pos)}`}>
      <div className="absolute inset-x-0 top-1/2 h-px bg-line" />
      <div className="absolute top-0 bottom-0 w-px bg-line2" style={{ left: '50%' }} />
      <div className={`absolute top-1/2 -translate-y-1/2 h-1.5 rounded-full ${good ? 'bg-ok/35' : 'bg-bad/35'}`}
        style={{ left: `${pos(o.lo)}%`, width: `${Math.max(1, pos(o.hi) - pos(o.lo))}%` }} />
      <div className={`absolute top-1/2 -translate-x-1/2 -translate-y-1/2 w-2.5 h-2.5 rounded-full border-2 border-panel ${good ? 'bg-ok' : 'bg-bad'} ${o.n ? '' : 'opacity-40'}`}
        style={{ left: `${pos(o.effect)}%` }} />
    </div>
  )
}

function DimCard({ d }: { d: Dim }) {
  const [open, setOpen] = useState(false)
  const rows = open ? d.options : d.options.filter(o => o.n > 0).slice(0, 5)
  return (
    <div className="card">
      <SectionTitle hint={`${d.n} vídeos · ${d.tested} de ${d.options.length} opções testadas`}
        action={d.options.length > rows.length || open ? <button className="btn btn-sm btn-ghost" onClick={() => setOpen(!open)}>{open ? 'Menos' : 'Todas'}</button> : undefined}>
        {d.label}
      </SectionTitle>
      <div className="p-3 space-y-2">
        {rows.length === 0 && <div className="text-[12.5px] text-faint px-1">Nenhum vídeo medido ainda.</div>}
        {rows.map(o => (
          <div key={o.key} className="grid grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)_auto] items-center gap-3 text-[12.5px]">
            <div className="min-w-0">
              <div className="truncate">{o.label}</div>
              <div className="text-[11px] text-faint num">{o.n} vídeo{o.n === 1 ? '' : 's'}{o.n_all > o.n ? ` · ${o.n_all} em todos` : ''}</div>
            </div>
            <EffectBar o={o} />
            <div className="text-right w-[92px]">
              <div className={`num font-medium ${o.n === 0 ? 'text-faint' : o.effect >= 0 ? 'text-ok' : 'text-bad'}`}>{pctEff(o.effect)}</div>
              <div className="text-[11px] text-faint num" data-tip="Peso no sorteio do próximo vídeo (1x = neutro; a anti-repetição continua valendo)">sorteio ×{o.mult.toFixed(2).replace('.', ',')}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function Stat({ label, value, sub, tone }: { label: string; value: string; sub?: string; tone?: string }) {
  return (
    <div className="min-w-0">
      <div className="text-[11.5px] text-muted">{label}</div>
      <div className={`text-[20px] font-semibold num leading-tight mt-0.5 ${tone ?? ''}`}>{value}</div>
      {sub && <div className="text-[11.5px] text-faint mt-0.5">{sub}</div>}
    </div>
  )
}

function ModelCard({ r }: { r: Report }) {
  const m = r.model, l = m.loo
  if (!m.ok || !l) return <section className="card p-4 text-[13px] text-muted">O modelo de previsão precisa de pelo menos 8 vídeos medidos ({m.n} até agora).</section>
  const good = (l.p_value ?? 1) <= 0.05 && l.r2 >= 0.1
  const weak = !good && l.r2 > 0 && (l.p_value ?? 1) <= 0.2
  const tone = good ? 'text-ok' : weak ? 'text-warn' : 'text-bad'
  const skill = Math.max(0, Math.min(1, l.r2 / 0.3))
  return (
    <section className="card">
      <SectionTitle hint="Validação leave-one-out aninhada: cada vídeo é previsto por um modelo que nunca o viu">Acurácia honesta da previsão</SectionTitle>
      <div className="p-4 space-y-4">
        <div className={`text-[14px] font-medium ${tone}`}>{m.verdict}</div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Stat label="Variância explicada (fora da amostra)" value={pct(l.r2, 1)} tone={tone}
            sub={`acaso: ${pct(l.null_r2 ?? null, 1)} · p = ${(l.p_value ?? 1).toFixed(2).replace('.', ',')}`} />
          <Stat label="Acerta qual de 2 pautas vai melhor" value={pct(l.concordance)} sub={`${l.pairs} pares do mesmo canal · acaso ${pct(l.null_concordance ?? 0.5)}`} />
          <Stat label="Correlação de ordem" value={l.spearman == null ? '—' : l.spearman.toFixed(2).replace('.', ',')} sub={`acaso ${(l.null_spearman ?? 0).toFixed(2).replace('.', ',')}`} />
          <Stat label="Nota 0-100 da IA nas pautas" value={r.idea_score.spearman == null ? '—' : r.idea_score.spearman.toFixed(2).replace('.', ',')}
            sub={`correlação com o real · ${r.idea_score.n} vídeos`} tone={(r.idea_score.spearman ?? 0) < 0.2 ? 'text-warn' : undefined} />
        </div>
        <div>
          <div className="flex justify-between text-[11.5px] text-faint mb-1"><span>sem sinal</span><span>útil (≥ 30%)</span></div>
          <div className="h-1.5 rounded-full bg-line overflow-hidden"><div className={`h-full rounded-full ${good ? 'bg-ok' : weak ? 'bg-warn' : 'bg-bad'}`} style={{ width: `${Math.max(2, skill * 100)}%` }} /></div>
        </div>
        {m.coefs.length > 0 && (
          <div className="text-[12.5px] space-y-1">
            <div className="text-muted">Traços que o modelo escolheu usar ({m.n} vídeos):</div>
            {m.coefs.map(c => (
              <div key={c.key} className="flex items-center justify-between gap-3">
                <span className="truncate">{c.label}</span>
                <span className="flex items-center gap-2 shrink-0"><span className="num">{pctEff(c.effect)}</span><span className={`badge ${confTone(c.p_pos)}`}>{conf(c.p_pos)}</span></span>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}

/** Previsto (LOO) × real, em escala log: perto da diagonal = acertou. */
function Scatter({ pts }: { pts: Report['pred_vs_actual'] }) {
  const { channels } = useChannel()
  if (pts.length < 3) return null
  const W = 320, H = 220, P = 26, R = 2.3
  const sx = (v: number) => P + ((Math.max(-R, Math.min(R, v)) + R) / (2 * R)) * (W - 2 * P)
  const sy = (v: number) => H - P - ((Math.max(-R, Math.min(R, v)) + R) / (2 * R)) * (H - 2 * P)
  const idx = (id: number) => Math.max(0, channels.findIndex(c => c.id === id))
  const COLORS = ['var(--color-info)', 'var(--color-ok)', 'var(--color-warn)', 'var(--color-accent)']
  return (
    <section className="card">
      <SectionTitle hint="Cada ponto é um vídeo; eixo x = previsão sem ver o vídeo, y = resultado real (vezes o normal do canal)">Previsto × real</SectionTitle>
      <div className="p-3">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto">
          <line x1={sx(-R)} y1={sy(-R)} x2={sx(R)} y2={sy(R)} stroke="var(--color-line2)" strokeDasharray="3 3" />
          <line x1={sx(0)} y1={P / 2} x2={sx(0)} y2={H - P} stroke="var(--color-line)" />
          <line x1={P} y1={sy(0)} x2={W - P / 2} y2={sy(0)} stroke="var(--color-line)" />
          {[-Math.log(4), Math.log(4)].map(v => <text key={v} x={sx(v)} y={H - 8} fontSize="9" textAnchor="middle" fill="var(--color-faint)">{v > 0 ? '4x' : '¼x'}</text>)}
          {[-Math.log(4), Math.log(4)].map(v => <text key={'y' + v} x={8} y={sy(v) + 3} fontSize="9" fill="var(--color-faint)">{v > 0 ? '4x' : '¼x'}</text>)}
          {pts.map((p, i) => <circle key={i} cx={sx(p.pred)} cy={sy(p.actual)} r={3.5} fill={COLORS[idx(p.channel_id) % COLORS.length]} fillOpacity={0.8}>
            <title>{`${p.title}\nprevisto ${fx(Math.exp(p.pred))} · real ${fx(Math.exp(p.actual))}`}</title></circle>)}
        </svg>
        <div className="text-[11.5px] text-faint mt-1">Pontos espalhados na vertical = o vídeo foi bem/mal por motivos que o modelo ainda não enxerga (o normal com poucos dados).</div>
      </div>
    </section>
  )
}

function CurveCard({ curve, typical }: { curve: Report['curve']; typical?: number }) {
  if (curve.length < 3) return null
  const W = 320, H = 120, P = 18
  const xs = curve.map(c => Math.log(c.age_h)), ys = curve.map(c => Math.log1p(c.views))
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y1 = Math.max(...ys)
  const px = (v: number) => P + ((v - x0) / (x1 - x0)) * (W - 2 * P)
  const py = (v: number) => H - P - (v / y1) * (H - 2 * P)
  const d = curve.map((_, i) => `${i ? 'L' : 'M'}${px(xs[i]).toFixed(1)} ${py(ys[i]).toFixed(1)}`).join(' ')
  const marks = curve.filter(c => [2, 24, 168].includes(c.age_h))
  return (
    <section className="card">
      <SectionTitle hint="Estimada comparando cada vídeo com ele mesmo em idades diferentes (chain-ladder)">Curva típica de views por idade</SectionTitle>
      <div className="p-3">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto">
          <path d={d} fill="none" stroke="var(--color-accent)" strokeWidth="2" vectorEffect="non-scaling-stroke" />
          {marks.map(c => <g key={c.age_h}>
            <circle cx={px(Math.log(c.age_h))} cy={py(Math.log1p(c.views))} r="3" fill="var(--color-accent)" />
            <text x={px(Math.log(c.age_h))} y={py(Math.log1p(c.views)) - 7} fontSize="9.5" textAnchor="middle" fill="var(--color-muted)">{fmtNum(c.views)}</text>
            <text x={px(Math.log(c.age_h))} y={H - 4} fontSize="9" textAnchor="middle" fill="var(--color-faint)">{c.age_h < 48 ? `${c.age_h} h` : `${c.age_h / 24} d`}</text>
          </g>)}
        </svg>
        {typical != null && <div className="text-[12px] text-muted">Vídeo típico deste canal: <b className="num text-text">{fmtNum(typical)}</b> views com 48 h.</div>}
      </div>
    </section>
  )
}

const STATUS: Record<string, { label: string; cls: string }> = {
  breakout: { label: 'Decolando', cls: 'badge-ok' }, acima: { label: 'Acima', cls: 'badge-ok' }, normal: { label: 'Normal', cls: '' },
  abaixo: { label: 'Abaixo', cls: 'badge-warn' }, flop: { label: 'Travado', cls: 'badge-bad' },
}

function Breakouts({ channelId }: { channelId?: number }) {
  const { data = [], isLoading } = useApi<Breakout[]>(`/learning/breakouts?hours=72${channelId ? `&channel_id=${channelId}` : ''}`, { refetchInterval: 300_000 })
  if (isLoading) return <Skeleton className="h-40" />
  return (
    <section className="card">
      <SectionTitle hint="Vídeos de até 3 dias comparados com a curva típica na mesma idade, com projeção para 7 dias">Sinais precoces</SectionTitle>
      {data.length === 0 ? <div className="p-4 text-[13px] text-muted">Nenhum vídeo recente.</div> : (
        <div className="divide-y divide-line">
          {data.slice(0, 10).map(b => {
            const st = STATUS[b.status] ?? STATUS.normal
            return (
              <div key={b.pub_id} className="px-4 py-2.5 flex items-center gap-3 text-[12.5px]">
                <span className={`badge shrink-0 ${st.cls}`}>{b.status === 'breakout' ? <Rocket size={12} /> : b.status === 'flop' ? <TrendingDown size={12} /> : null}{st.label}</span>
                <div className="min-w-0 flex-1">
                  <a href={b.url} target="_blank" rel="noreferrer" className="truncate block hover:underline">{b.title}</a>
                  <div className="text-[11.5px] text-faint num">{!channelId && `${b.channel} · `}{age(b.age_h)} no ar · {fmtNum(b.views)} views (normal ~{fmtNum(b.expected_now)}){b.views_per_h != null && ` · ${b.views_per_h}/h agora`}</div>
                </div>
                <div className="text-right shrink-0">
                  <div className={`num font-medium ${b.x_normal >= 1 ? 'text-ok' : 'text-bad'}`}>{fx(b.x_normal)}</div>
                  <div className="text-[11px] text-faint num" data-tip={`Faixa de 80%: ${fmtNum(b.proj_7d_low)} a ${fmtNum(b.proj_7d_high)} · calibrado em ${b.calibration_n} vídeos`}>7 d: ~{fmtNum(b.proj_7d)}</div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </section>
  )
}

function PredictBox({ channelId }: { channelId: number }) {
  const [title, setTitle] = useState('')
  const [hook, setHook] = useState('')
  const [fmt, setFmt] = useState<'short' | 'long'>('short')
  const [res, setRes] = useState<Prediction | null>(null)
  const [busy, setBusy] = useState(false)
  const run = async () => {
    if (!title.trim()) return
    setBusy(true)
    const r = await act(() => api<Prediction>('/learning/predict', { body: { channel_id: channelId, title, hook, format: fmt } }))
    setBusy(false)
    if (r) setRes(r)
  }
  return (
    <section className="card">
      <SectionTitle hint="Previsão com faixa de incerteza (80%) — com poucos dados a faixa é larga, e isso é honesto">Testar uma pauta</SectionTitle>
      <div className="p-4 space-y-3">
        <input className="input" placeholder="Título do vídeo" value={title} onChange={e => setTitle(e.target.value)} onKeyDown={e => e.key === 'Enter' && run()} />
        <textarea className="input" rows={2} placeholder="Gancho (primeira frase) — opcional" value={hook} onChange={e => setHook(e.target.value)} />
        <div className="flex items-center gap-2">
          <div className="seg">
            <button data-active={fmt === 'short'} onClick={() => setFmt('short')}>Short</button>
            <button data-active={fmt === 'long'} onClick={() => setFmt('long')}>Longo</button>
          </div>
          <button className="btn btn-primary btn-sm ml-auto" disabled={busy || !title.trim()} onClick={run}><Target size={14} />Prever</button>
        </div>
        {res && (
          <div className="pt-1 space-y-3">
            <div>
              <div className="flex items-baseline justify-between">
                <span className="text-[26px] font-semibold num">{res.score}</span>
                <span className="text-[12px] text-muted num">faixa {res.low}–{res.high} · confiança {res.confidence}</span>
              </div>
              <div className="relative h-2 rounded-full bg-line mt-1">
                <div className="absolute h-full rounded-full bg-accent/30" style={{ left: `${res.low}%`, width: `${Math.max(1, res.high - res.low)}%` }} />
                <div className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-3 h-3 rounded-full bg-accent" style={{ left: `${res.score}%` }} />
              </div>
              {res.views_48h && <div className="text-[12px] text-muted mt-1.5 num">≈ {fmtNum(res.views_48h.mid)} views em 48 h (80%: {fmtNum(res.views_48h.low)} a {fmtNum(res.views_48h.high)}) · {fx(res.x_normal)} o normal</div>}
            </div>
            <ul className="text-[12.5px] space-y-1 list-disc pl-4 text-muted">{res.reasons.map((x, i) => <li key={i}>{x}</li>)}</ul>
            {res.similar.length > 0 && <div className="text-[12px] space-y-1">
              <div className="text-faint">Vídeos parecidos</div>
              {res.similar.map(s => <a key={s.url} href={s.url} target="_blank" rel="noreferrer" className="flex justify-between gap-3 hover:underline">
                <span className="truncate">{s.title}</span><span className="num shrink-0 text-muted">{fmtNum(s.views)} · {fx(s.x)}</span></a>)}
            </div>}
          </div>
        )}
      </div>
    </section>
  )
}

function VideoTable({ rows, all }: { rows: VideoRow[]; all: boolean }) {
  const [sort, setSort] = useState<'recent' | 'best'>('best')
  const list = [...rows].sort((a, b) => sort === 'recent' ? b.published_at.localeCompare(a.published_at) : (b.x_normal ?? -1) - (a.x_normal ?? -1))
  return (
    <section className="card overflow-hidden">
      <SectionTitle hint="“x normal” = views ÷ views típicas do canal na mesma idade · retenção da curva do YouTube"
        action={<div className="seg"><button data-active={sort === 'best'} onClick={() => setSort('best')}>Melhores</button><button data-active={sort === 'recent'} onClick={() => setSort('recent')}>Recentes</button></div>}>
        Vídeos medidos
      </SectionTitle>
      <div className="overflow-x-auto">
        <table className="w-full text-[12.5px]">
          <thead className="text-muted text-left">
            <tr className="border-b border-line">
              <th className="px-4 py-2 font-medium">Vídeo</th>
              <th className="px-2 py-2 font-medium text-right">Idade</th>
              <th className="px-2 py-2 font-medium text-right">Views</th>
              <th className="px-2 py-2 font-medium text-right">24 h</th>
              <th className="px-2 py-2 font-medium text-right" data-tip="Vezes o normal do canal na mesma idade">x normal</th>
              <th className="px-2 py-2 font-medium text-right" data-tip="Previsão feita sem ver o vídeo (leave-one-out)">previsto</th>
              <th className="px-2 py-2 font-medium text-right" data-tip="Views engajadas ÷ views (estimativa: o Analytics atrasa ~2 dias)">engajadas</th>
              <th className="px-2 py-2 font-medium text-right">% assistido</th>
              <th className="px-4 py-2 font-medium text-right" data-tip="Retenção aos 3 s / no fim (curva do YouTube)">retenção</th>
            </tr>
          </thead>
          <tbody>
            {list.map(v => (
              <tr key={v.pub_id} className="border-b border-line/60 hover:bg-panel2">
                <td className="px-4 py-2 max-w-[340px]">
                  <a href={v.url} target="_blank" rel="noreferrer" className="truncate block hover:underline">{v.title}</a>
                  <div className="text-[11px] text-faint flex items-center gap-1.5 mt-0.5">
                    {all && <ChannelTag id={v.channel_id} />}
                    {v.format === 'long' && <span className="badge">longo</span>}
                    {v.imported && <span className="badge">importado</span>}
                    {v.variety?.structure && <span className="truncate">{v.variety.structure} · {v.variety.hook_style} · {v.variety.title_style}</span>}
                  </div>
                </td>
                <td className="px-2 py-2 text-right num text-muted">{age(v.age_h)}</td>
                <td className="px-2 py-2 text-right num">{fmtNum(v.views)}</td>
                <td className="px-2 py-2 text-right num text-muted">{v.views_at?.['24h'] == null ? '—' : fmtNum(v.views_at['24h'])}</td>
                <td className={`px-2 py-2 text-right num font-medium ${v.x_normal == null ? 'text-faint' : v.x_normal >= 1.25 ? 'text-ok' : v.x_normal <= 0.8 ? 'text-bad' : ''}`}>{fx(v.x_normal)}</td>
                <td className="px-2 py-2 text-right num text-muted">{fx(v.x_pred)}</td>
                <td className="px-2 py-2 text-right num text-muted">{pct(v.analytics?.engaged_ratio)}</td>
                <td className="px-2 py-2 text-right num text-muted">{v.analytics?.avg_view_pct == null ? '—' : `${Math.round(v.analytics.avg_view_pct)}%`}</td>
                <td className="px-4 py-2 text-right num text-muted">{v.retention?.hook == null ? '—' : `${Math.round(v.retention.hook)}% / ${Math.round(v.retention.end ?? 0)}%`}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function ChannelsGrid({ chans, onOpen }: { chans: ChannelSum[]; onOpen: (id: number) => void }) {
  return (
    <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-3">
      {chans.map(c => (
        <button key={c.id} className="card card-hover p-4 text-left space-y-2" onClick={() => onOpen(c.id)}>
          <ChannelTag id={c.id} />
          <div className="flex items-end justify-between gap-2">
            <Stat label="Típico com 48 h" value={fmtNum(c.typical_48h)} sub={`7 dias: ~${fmtNum(c.typical_7d)}`} />
            <div className="text-right text-[11.5px] text-faint num">{c.trained}/{c.videos} vídeos<br />no modelo</div>
          </div>
          {c.best && <div className="text-[12px] text-muted truncate">Melhor: {c.best.title}</div>}
        </button>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------- página

export default function Learning() {
  const { channel, setChannelId } = useChannel()
  const [all, setAll] = useScope('learning', false)
  const cid = all ? undefined : channel?.id
  const { data: r, isLoading } = useApi<Report>(all ? '/learning/report' : cid ? `/learning/report?channel_id=${cid}` : null)
  const [busy, setBusy] = useState(false)

  const refresh = async () => {
    setBusy(true)
    await act(() => api('/learning/refresh?wait=true', { method: 'POST' }), 'Aprendizado recalculado')
    setBusy(false)
    invalidate('/learning')
  }

  const header = (
    <PageHeader eyebrow="Crescimento" title={<span className="inline-flex items-center gap-2"><Brain size={20} />O que o sistema aprendeu</span>}
      subtitle="Views comparadas na mesma idade, efeitos com incerteza e previsões validadas fora da amostra. Com poucos vídeos, a maior parte ainda é palpite — e a página diz quando é."
      actions={<>
        <ChannelScope all={all} onChange={setAll} />
        <button className="btn btn-sm" disabled={busy} onClick={refresh}><RefreshCw size={14} className={busy ? 'animate-spin' : ''} />Recalcular</button>
      </>} />
  )

  if (isLoading || !r) return <div className="space-y-4">{header}<Skeleton className="h-28" /><Skeleton className="h-64" /></div>
  if (!r.videos.length) return <div>{header}<Empty icon={<Brain size={20} />} title="Ainda sem vídeos medidos" text="Assim que os vídeos publicados tiverem leituras de métricas, o aprendizado aparece aqui." /></div>

  const ch = r.channels.find(c => c.id === cid)
  const dims = [...r.dimensions].sort((a, b) => b.n - a.n)
  return (
    <div className="space-y-4">
      {header}

      {all && <ChannelsGrid chans={r.channels} onOpen={id => { setChannelId(id); setAll(false) }} />}

      <div className="grid lg:grid-cols-[1.4fr_1fr] gap-4 items-start">
        <ModelCard r={r} />
        <section className="card">
          <SectionTitle hint="Só achados com ≥ 75% de chance de não serem acaso, já descontada a idade de cada vídeo">
            <span className="inline-flex items-center gap-1.5"><Sparkles size={15} />Lições com evidência</span>
          </SectionTitle>
          <div className="p-4">
            {r.lessons.length === 0
              ? <p className="text-[13px] text-muted">Nenhuma diferença confiável ainda. O sorteio de variedade continua testando: cada vídeo novo estreita as faixas de incerteza.</p>
              : <ul className="space-y-2 text-[13px]">{r.lessons.map((t, i) => <li key={i} className="flex gap-2"><span className="text-accent mt-0.5">•</span><span>{t}</span></li>)}</ul>}
            {r.topics && (r.topics.win.length > 0 || r.topics.lose.length > 0) && (
              <div className="mt-4 pt-3 border-t border-line text-[12.5px] space-y-1.5">
                {r.topics.win.length > 0 && <div><span className="text-muted">Termos dos que foram bem: </span>{r.topics.win.map(t => <span key={t[0]} className="badge badge-ok mr-1">{t[0]}</span>)}</div>}
                {r.topics.lose.length > 0 && <div><span className="text-muted">Dos que foram mal: </span>{r.topics.lose.map(t => <span key={t[0]} className="badge badge-bad mr-1">{t[0]}</span>)}</div>}
              </div>
            )}
          </div>
        </section>
      </div>

      <div className="grid lg:grid-cols-[1.4fr_1fr] gap-4 items-start">
        <Breakouts channelId={cid} />
        {cid ? <PredictBox channelId={cid} /> : <CurveCard curve={r.curve} />}
      </div>

      <div>
        <div className="flex items-baseline justify-between mb-2 mt-2">
          <h2 className="text-[15px] font-semibold inline-flex items-center gap-1.5"><FlaskConical size={15} />Experimentos de variedade</h2>
          <span className="text-[11.5px] text-faint">ponto = efeito estimado · faixa = 80% de certeza · centro = normal do canal{all ? ' (todos os canais)' : ''}</span>
        </div>
        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-3">{dims.map(d => <DimCard key={d.key} d={d} />)}</div>
      </div>

      <AudienceCard a={r.audience} />

      <div className="grid lg:grid-cols-2 gap-4 items-start">
        <Scatter pts={r.pred_vs_actual} />
        {cid ? <CurveCard curve={r.curve} typical={ch?.typical_48h} /> : null}
      </div>

      <VideoTable rows={r.videos} all={all} />

      <details className="card p-4 text-[12.5px] text-muted">
        <summary className="cursor-pointer text-text">Como o aprendizado funciona</summary>
        <ul className="list-disc pl-5 mt-2 space-y-1">{r.method.map((m, i) => <li key={i}>{m}</li>)}</ul>
        <div className="mt-2 text-faint">Calculado {new Date(r.computed_at).toLocaleString('pt-BR')} em {r.seconds}s</div>
      </details>
    </div>
  )
}

// ---------------------------------------------------------------- público (origem, inscritos, aparelho, quem deslizou)

type AudFormat = { format: string; videos: number; engaged_ratio: number | null; with_performance: { key: string; rho: number; n: number }[] } & Record<string, any>
type AudOpt = { key: string; label: string; n_er: number; n_hook: number; engaged_ratio: number | null; engaged_raw: number | null; hook_3s: number | null; feed_engaged_ratio: number | null }
export type Audience = { formats: AudFormat[]; by_dimension: { key: string; label: string; options: AudOpt[] }[]
  channel_engaged_ratio: number | null; channel_hook_3s: number | null; videos_with_signals: number; note: string }

const SHARE_LABEL: Record<string, string> = {
  share_feed: 'Feed do Shorts', share_search: 'Busca', share_suggested: 'Sugeridos', share_browse: 'Inscritos/navegação',
  share_external: 'Externo/direto', share_ads: 'Anúncios pagos', share_other: 'Outras',
  share_subscribed: 'Inscritos (do total)', share_mobile: 'Celular', share_tv: 'TV', share_desktop: 'Computador',
}
const TRAFFIC_KEYS = ['share_feed', 'share_search', 'share_suggested', 'share_browse', 'share_external', 'share_ads', 'share_other']
const pct0 = (v: number | null | undefined) => v == null ? '—' : `${Math.round(v * 100)}%`

export function AudienceCard({ a }: { a?: Audience | null }) {
  if (!a) return null
  if (!a.videos_with_signals) return (
    <section className="card p-4 text-[13px] text-muted">
      <div className="text-sm font-semibold text-text mb-1">De onde vem o público</div>
      Ainda sem sinais do YouTube Analytics (origem do tráfego, inscritos, aparelho). Eles chegam com ~2 dias de atraso e são coletados a cada 3 h.
    </section>
  )
  const dims = a.by_dimension.filter(d => d.options.some(o => o.n_er > 0))
  return (
    <section className="card">
      <SectionTitle hint={a.note}>De onde vem o público e onde cada formato ganha</SectionTitle>
      <div className="p-4 grid lg:grid-cols-2 gap-5">
        {a.formats.map(f => (
          <div key={f.format}>
            <div className="text-[13px] font-semibold mb-2">{f.format === 'long' ? 'Vídeos longos' : 'Shorts'} <span className="text-muted font-normal">· {f.videos} vídeos · engajadas/views {pct0(f.engaged_ratio)}</span></div>
            <div className="space-y-1.5">
              {TRAFFIC_KEYS.filter(k => (f[k] ?? 0) >= 0.01).sort((x, y) => (f[y] ?? 0) - (f[x] ?? 0)).map(k => (
                <div key={k} className="flex items-center gap-2 text-[12.5px]">
                  <span className="w-36 text-muted truncate">{SHARE_LABEL[k]}</span>
                  <div className="flex-1 h-1.5 rounded-full bg-line overflow-hidden"><div className="h-full bg-grad rounded-full" style={{ width: `${Math.round((f[k] ?? 0) * 100)}%` }} /></div>
                  <span className="num w-10 text-right">{pct0(f[k])}</span>
                </div>
              ))}
            </div>
            <div className="flex flex-wrap gap-1.5 mt-2.5 text-[11.5px]">
              {['share_subscribed', 'share_mobile', 'share_tv', 'share_desktop'].filter(k => f[k] != null).map(k =>
                <span key={k} className="badge">{SHARE_LABEL[k]} {pct0(f[k])}</span>)}
            </div>
            {f.with_performance?.filter(w => Math.abs(w.rho) >= 0.4).slice(0, 2).map(w => (
              <div key={w.key} className="text-[11.5px] text-muted mt-1.5">
                {w.rho > 0 ? '↑' : '↓'} Mais {SHARE_LABEL[w.key]?.toLowerCase()} anda junto com vídeos {w.rho > 0 ? 'acima' : 'abaixo'} do normal
                (correlação {w.rho.toFixed(2).replace('.', ',')}, {w.n} vídeos — indício, não causa)
              </div>
            ))}
          </div>
        ))}
      </div>
      {!!dims.length && (
        <div className="px-4 pb-4">
          <div className="text-[13px] font-semibold mb-1">Quem desliza × quem fica, por escolha de variedade</div>
          <div className="text-[11.5px] text-muted mb-2">Engajadas ÷ views (orgânicas) e retenção aos 3s, encolhidas para a média do canal ({pct0(a.channel_engaged_ratio)}) quando há poucos vídeos</div>
          <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-3">
            {dims.map(d => (
              <div key={d.key} className="surface-2 p-3">
                <div className="text-[12.5px] font-medium mb-1.5">{d.label}</div>
                {d.options.map(o => (
                  <div key={o.key} className="flex items-center gap-2 text-[12px] leading-6">
                    <span className="flex-1 truncate">{o.label}</span>
                    <span className="num text-muted" title="engajadas ÷ views (encolhido)">{pct0(o.engaged_ratio)}</span>
                    <span className="num text-faint w-14 text-right" title="retenção aos 3s">{o.hook_3s != null ? `${Math.round(o.hook_3s)}% 3s` : ''}</span>
                    <span className="text-faint w-8 text-right">{o.n_er}v</span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}
