import { AlertTriangle, ListVideo, CheckCircle2 } from 'lucide-react'
import { useApi } from '../api'
import { SectionTitle, Skeleton } from '../ui'
import { Bar } from './kit'
import { connectYoutube } from './Channels'

type Item = { key: string; label: string; count: number }
type Report = {
  total: number; planned: number; score: number | null; warnings: string[]; question_share: number
  structures: Item[]; hooks: Item[]; titles: Item[]; grades: Item[]; captions: Item[]; series: Item[]
  playlists_enabled: boolean; connected: boolean; playlists: Record<string, string>
}

const HOOK: Record<string, string> = { pergunta: 'Pergunta', numero: 'Número', contraintuitivo: 'Contraintuitivo', cena: 'Cena', desafio: 'Desafio', consequencia: 'Consequência' }
const GRADE: Record<string, string> = { neutro: 'Neutro', quente: 'Quente', frio: 'Frio', contraste: 'Contraste', sepia: 'Sépia', filme: 'Filme' }

function Bars({ items, total, names }: { items: Item[]; total: number; names?: Record<string, string> }) {
  if (!items.length) return <div className="text-[12.5px] text-faint">—</div>
  return (
    <div className="space-y-1.5">
      {items.slice(0, 5).map(i => (
        <div key={i.key} className="flex items-center gap-2 text-[12.5px]">
          <span className="w-36 truncate text-muted">{names?.[i.key] ?? i.label}</span>
          <Bar value={(i.count / Math.max(1, total)) * 100} className="flex-1" />
          <span className="w-5 text-right num text-muted">{i.count}</span>
        </div>
      ))}
    </div>
  )
}

export default function VarietyCard({ channelId }: { channelId: number }) {
  const { data: r } = useApi<Report>(`/channels/${channelId}/variety`)
  if (!r) return <Skeleton className="h-48" />
  const n = r.planned
  const tone = r.score == null ? 'text-muted' : r.score >= 75 ? 'text-ok' : r.score >= 50 ? 'text-warn' : 'text-bad'
  return (
    <section className="card overflow-hidden">
      <SectionTitle hint={`Últimos ${r.total} roteiros · evita que o canal pareça feito em série`}
        action={<div className="text-right"><div className={`text-[22px] font-semibold num leading-none ${tone}`}>{r.score ?? '—'}</div><div className="text-[11.5px] text-faint mt-0.5">índice de variedade</div></div>}>
        Variedade do canal
      </SectionTitle>
      <div className="p-4 space-y-4">
        {r.warnings.length > 0 ? (
          <div className="space-y-1.5">
            {r.warnings.map(w => <div key={w} className="flex items-center gap-2 text-[13px] rounded-md bg-warn/[0.05] border border-warn/20 px-2.5 py-1.5"><AlertTriangle size={14} className="text-warn shrink-0" />{w}</div>)}
          </div>
        ) : n > 0 && <div className="flex items-center gap-2 text-[13px] text-muted"><CheckCircle2 size={14} className="text-ok" />Nada se repetindo demais.</div>}
        {n === 0 ? (
          <p className="text-[13px] text-muted">Os próximos roteiros já saem com estrutura, gancho, título, visual e trilha sorteados. O índice aparece aqui conforme eles forem criados.</p>
        ) : (
          <div className="grid md:grid-cols-2 gap-x-6 gap-y-4">
            <div><div className="label">Estruturas narrativas</div><Bars items={r.structures} total={n} /></div>
            <div><div className="label">Ganchos</div><Bars items={r.hooks} total={n} names={HOOK} /></div>
            <div><div className="label">Tratamento de cor</div><Bars items={r.grades} total={n} names={GRADE} /></div>
            <div><div className="label">Títulos em pergunta</div>
              <div className="flex items-center gap-2 text-[12.5px]"><Bar value={r.question_share} className="flex-1" tone={r.question_share > 50 ? 'warn' : undefined} /><span className="num text-muted">{r.question_share}%</span></div>
            </div>
          </div>
        )}
        <div className="flex items-center gap-2 pt-3 border-t border-line text-[12.5px] text-muted">
          <ListVideo size={14} />
          <span className="flex-1">
            {r.playlists_enabled
              ? `Séries viram playlists no YouTube automaticamente${Object.keys(r.playlists).length ? ` · ${Object.keys(r.playlists).length} criada(s)` : ''}.`
              : 'Para criar as playlists das séries, reconecte o canal e aceite a permissão de gerenciar playlists.'}
          </span>
          {!r.playlists_enabled && r.connected && <button className="btn btn-sm" onClick={() => connectYoutube(channelId)}>Reconectar</button>}
        </div>
      </div>
    </section>
  )
}
