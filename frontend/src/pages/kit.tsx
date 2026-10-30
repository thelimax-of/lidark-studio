// Peças visuais compartilhadas entre as páginas (tema dos gráficos, indicadores, avisos, listas longas).
// Tudo lê os tokens de index.css — nenhuma cor fixa aqui.
import { useEffect, useRef, useState, type ReactNode } from 'react'
import clsx from 'clsx'
import { AlertTriangle, CheckCircle2, Info, XCircle } from 'lucide-react'
import { Sparkline } from '../ui'

// ---------------------------------------------------------------- gráficos (recharts)

/** Props prontas para eixos/grade/tooltip do recharts no tema "obsidiana + aurora". */
export const chart = {
  grid: { stroke: 'var(--line)', strokeDasharray: '2 4', vertical: false } as const,
  axis: { tick: { fill: 'var(--faint)', fontSize: 11 }, axisLine: false, tickLine: false } as const,
  cursor: { stroke: 'var(--line-3)', strokeWidth: 1, strokeDasharray: '3 3' },
  dot: { r: 4.5, stroke: 'var(--panel)', strokeWidth: 2 },
  /** faixa dos dias estimados (sem Analytics ainda) */
  est: { fill: 'var(--accent-2)', fillOpacity: 0.06, stroke: 'none' } as const,
}

/** <defs> com o gradiente da marca para áreas (fill="url(#id)") e linhas (stroke="url(#id-line)"). */
export function ChartDefs({ id, color = 'var(--accent)', to = 'var(--accent-2)' }: { id: string; color?: string; to?: string }) {
  return (
    <defs>
      <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor={color} stopOpacity={0.32} />
        <stop offset="70%" stopColor={color} stopOpacity={0.06} />
        <stop offset="100%" stopColor={color} stopOpacity={0} />
      </linearGradient>
      <linearGradient id={`${id}-line`} x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stopColor={color} />
        <stop offset="100%" stopColor={to} />
      </linearGradient>
    </defs>
  )
}

type TipRow = { name: string; value: ReactNode; color?: string }
/** Conteúdo do Tooltip em vidro. Use: <Tooltip content={<ChartTip label={...} rows={...} />} /> */
export function ChartTip({ active, payload, label, fmtLabel, rows }: {
  active?: boolean; payload?: any[]; label?: any
  fmtLabel?: (l: any) => ReactNode; rows?: (payload: any[]) => TipRow[]
}) {
  if (!active || !payload?.length) return null
  const list: TipRow[] = rows ? rows(payload) : payload.map(p => ({ name: String(p.name ?? p.dataKey), value: p.value, color: p.color ?? p.stroke }))
  return (
    <div className="glass border border-line2 rounded-[10px] px-3 py-2 shadow-[var(--shadow-lg)] min-w-36 animate-pop">
      <div className="text-[11.5px] text-muted mb-1">{fmtLabel ? fmtLabel(label) : label}</div>
      {list.map((r, k) => (
        <div key={k} className="flex items-center gap-2 text-[12.5px] leading-6">
          {r.color && <span className="w-2 h-2 rounded-full shrink-0" style={{ background: r.color }} />}
          <span className="text-muted flex-1 truncate">{r.name}</span>
          <span className="num font-semibold text-text">{r.value}</span>
        </div>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------- indicadores

/** Cartão de indicador: rótulo, número grande, linha de apoio e (opcional) mini-gráfico. */
export function StatTile({ label, value, sub, spark, icon, tone, loading, className, onClick, hint }: {
  label: ReactNode; value: ReactNode; sub?: ReactNode; spark?: number[]; icon?: ReactNode
  tone?: 'ok' | 'warn' | 'bad' | 'accent'; loading?: boolean; className?: string; onClick?: () => void; hint?: string
}) {
  const Tag = onClick ? 'button' : 'div'
  return (
    <Tag onClick={onClick} title={hint} className={clsx('card card-hover p-4 text-left min-w-0 relative overflow-hidden', onClick && 'hover:bg-elev/40', className)}>
      <div className="flex items-center gap-2 stat-label">
        {icon && <span className="text-faint shrink-0">{icon}</span>}
        <span className="truncate">{label}</span>
      </div>
      {loading ? <div className="skeleton h-7 w-24 mt-2.5" /> : (
        <div className={clsx('stat-value mt-1.5 leading-none', tone === 'ok' && 'text-ok', tone === 'warn' && 'text-warn', tone === 'bad' && 'text-bad', tone === 'accent' && 'text-gradient')}>{value}</div>
      )}
      {sub && <div className="text-[11.5px] text-faint mt-2 truncate">{sub}</div>}
      {spark && <Sparkline data={spark} height={26} className="mt-2.5" />}
    </Tag>
  )
}

/** Ícone quadrado de seção (cabeçalhos de cartões). */
export function IconBox({ children, tone }: { children: ReactNode; tone?: 'accent' | 'warn' | 'ok' }) {
  return (
    <span className={clsx('w-8 h-8 rounded-[9px] grid place-items-center shrink-0 border shadow-[var(--shadow-sm)]',
      tone === 'accent' ? 'border-accent/40 bg-accent/10 text-accent' : tone === 'warn' ? 'border-warn/35 bg-warn/10 text-warn'
        : tone === 'ok' ? 'border-ok/35 bg-ok/10 text-ok' : 'border-line2 bg-panel2 text-muted')}>{children}</span>
  )
}

/** Faixa de aviso (substitui os vários "card border-warn/40" soltos). */
export function Callout({ tone = 'info', icon, children, action, className }: {
  tone?: 'info' | 'warn' | 'bad' | 'ok'; icon?: ReactNode; children: ReactNode; action?: ReactNode; className?: string
}) {
  const I = tone === 'warn' ? AlertTriangle : tone === 'bad' ? XCircle : tone === 'ok' ? CheckCircle2 : Info
  return (
    <div className={clsx('rounded-[var(--r-md)] border px-3.5 py-2.5 flex items-start gap-3 text-[13px]',
      tone === 'warn' && 'border-warn/30 bg-warn/[0.06]', tone === 'bad' && 'border-bad/30 bg-bad/[0.06]',
      tone === 'ok' && 'border-ok/30 bg-ok/[0.06]', tone === 'info' && 'border-accent/25 bg-accent/[0.06]', className)}>
      <span className={clsx('shrink-0 mt-px', tone === 'warn' ? 'text-warn' : tone === 'bad' ? 'text-bad' : tone === 'ok' ? 'text-ok' : 'text-accent')}>{icon ?? <I size={15} />}</span>
      <div className="flex-1 min-w-0 leading-relaxed">{children}</div>
      {action && <div className="shrink-0 self-center">{action}</div>}
    </div>
  )
}

/** Barra horizontal fina com o gradiente da marca (ou tom de status). */
export function Bar({ value, tone, className }: { value: number; tone?: 'ok' | 'warn' | 'bad' | 'muted'; className?: string }) {
  const p = Math.max(0, Math.min(100, value))
  return (
    <div className={clsx('h-1.5 rounded-full bg-line overflow-hidden', className)}>
      <div className={clsx('h-full rounded-full transition-[width] duration-500 ease-[var(--ease)]',
        tone === 'ok' ? 'bg-ok' : tone === 'warn' ? 'bg-warn' : tone === 'bad' ? 'bg-bad' : tone === 'muted' ? 'bg-line3' : 'bg-grad')}
        style={{ width: `${p}%` }} />
    </div>
  )
}

/** Linhas-esqueleto para listas carregando. */
export function RowsSkeleton({ rows = 5, h = 'h-12', className }: { rows?: number; h?: string; className?: string }) {
  return <div className={clsx('p-4 space-y-2.5', className)}>{Array.from({ length: rows }, (_, i) => <div key={i} className={clsx('skeleton', h)} style={{ opacity: 1 - i * 0.12 }} />)}</div>
}

// ---------------------------------------------------------------- listas longas

/** Renderiza a lista aos poucos (step itens por vez) e carrega mais quando o fim aparece na tela. */
export function useProgressive<T>(list: T[], step = 60, resetKey?: unknown): [T[], ReactNode] {
  const [n, setN] = useState(step)
  const ref = useRef<HTMLDivElement>(null)
  const more = list.length > n
  useEffect(() => { setN(step) }, [resetKey, step])  // volta ao início ao trocar de filtro/aba
  useEffect(() => {
    if (!more || !ref.current) return
    const io = new IntersectionObserver(e => { if (e[0]?.isIntersecting) setN(x => x + step) }, { rootMargin: '600px' })
    io.observe(ref.current)
    return () => io.disconnect()
  }, [more, step, n])
  const sentinel = more ? (
    <div ref={ref} className="py-3 text-center">
      <button className="btn btn-sm btn-ghost" onClick={() => setN(x => x + step)}>Mostrar mais ({list.length - n})</button>
    </div>
  ) : null
  return [list.slice(0, n), sentinel]
}
