import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ExternalLink, Film, Loader2, Trophy } from 'lucide-react'
import { api, invalidate, onJob, useApi, type Job } from '../api'
import { act, ChannelTag, fmtNum, SectionTitle, Skeleton, toast } from '../ui'

export type Champion = {
  key: string; channel_id: number; channel_name?: string; title: string; url?: string; thumbnail?: string; published_at?: string
  views: number; engaged_views?: number | null; retention: number; likes: number; comments: number; shares: number; subs: number
  score: number; parts: Record<string, number>; reasons: string[]; confidence: 'alta' | 'média' | 'baixa'
  early: boolean; champion: boolean; age_hours: number
  long_status?: 'working' | 'idea' | 'script' | 'video' | 'published' | 'discarded'; job_id?: number
  idea_id?: number; long_title?: string; script_id?: number | null; long_video_id?: number | null
}

const STATUS: Record<string, string> = {
  working: 'Pesquisando e planejando…', idea: 'Pauta longa criada', script: 'Roteiro longo pronto para revisar',
  video: 'Vídeo longo gerado', published: 'Vídeo longo publicado', discarded: 'Fontes não sustentaram — descartado',
}

/** Short campeão → vídeo longo: pesquisa fontes, planeja 8-12 min em capítulos, checa, dá nota e escreve o roteiro. */
export async function toLong(channelId: number, key: string, title?: string) {
  const j = await act(() => api<Job>(`/channels/${channelId}/champions/long`, { body: { key, title } }),
    'Na fila: pesquisa de fontes, capítulos e roteiro longo (você revisa antes de gerar o vídeo)')
  invalidate('/champions')
  return j
}

/** Atualiza a lista quando a transformação termina (e avisa se o tema não rendeu um longo). */
function useChampionJobs() {
  useEffect(() => onJob(j => {
    if (!['champion_long', 'write_script'].includes(j.kind)) return
    if (['done', 'failed', 'cancelled'].includes(j.status) || j.status === 'running') invalidate('/champions')
    if (j.kind === 'champion_long' && j.status === 'failed') toast.err(`Vídeo longo não criado: ${j.error || 'erro desconhecido'}`)
    if (j.kind === 'champion_long' && j.status === 'done') toast.ok(`Pauta longa pronta: ${j.result?.title ?? ''} — roteiro na fila`)
  }), [])
}

/** Sugestões de vídeo longo a partir dos Shorts que mais performaram (horas assistidas para o YPP vêm dos longos). */
export function ChampionsCard({ channelId }: { channelId?: number }) {
  const { data = [], isLoading } = useApi<Champion[]>(channelId ? `/champions?channel_id=${channelId}` : '/champions?limit=3')
  const [busy, setBusy] = useState<string | null>(null)
  useChampionJobs()
  const champs = data.filter(c => c.champion)
  const rest = data.filter(c => !c.champion).slice(0, Math.max(0, 3 - champs.length))
  const list = [...champs, ...rest]
  const go = async (c: Champion) => {
    setBusy(c.key)
    await toLong(c.channel_id, c.key, c.title)
    setBusy(null)
  }
  return (
    <section className="card overflow-hidden">
      <SectionTitle hint="Horas assistidas (4.000 h em 12 meses) vêm dos vídeos longos — Shorts não contam. O Short que prendeu o público vira um longo de 8-12 min com fontes.">
        <span className="inline-flex items-center gap-2"><Trophy size={15} className="text-warn" />Short campeão → vídeo longo</span>
      </SectionTitle>
      {isLoading ? <div className="p-4"><Skeleton className="h-24" /></div> : !list.length ? (
        <div className="p-6 text-center text-[13px] text-muted">Nenhum Short publicado com métricas ainda.</div>
      ) : (
        <ul className="divide-y divide-line">
          {!champs.length && <li className="px-4 py-2.5 text-[12.5px] text-muted">Ainda sem campeão claro (precisa de 24 h no ar e views acima da mediana do canal). Os melhores até agora:</li>}
          {list.map(c => {
            const working = c.long_status === 'working' || busy === c.key
            const done = c.long_status && c.long_status !== 'working' && c.long_status !== 'discarded'
            return (
              <li key={`${c.channel_id}-${c.key}`} className="px-4 py-3 flex flex-wrap items-center gap-3">
                {c.thumbnail ? <img src={c.thumbnail} referrerPolicy="no-referrer" className="w-10 h-14 rounded object-cover bg-black shrink-0" alt="" />
                  : <div className="w-10 h-14 rounded bg-panel2 shrink-0" />}
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="font-medium truncate">{c.title}</span>
                    {c.url && <a href={c.url} target="_blank" rel="noreferrer" className="text-muted hover:text-text shrink-0"><ExternalLink size={13} /></a>}
                  </div>
                  <div className="text-[12px] text-muted flex flex-wrap items-center gap-x-2 gap-y-1 mt-0.5">
                    {!channelId && <ChannelTag id={c.channel_id} />}
                    <span className="num">{fmtNum(c.views)} views</span>
                    {c.engaged_views != null && <span className="num">· {fmtNum(c.engaged_views)} engajadas</span>}
                    {c.retention > 0 && <span className="num">· retenção {c.retention.toFixed(0)}%</span>}
                    <span title="Confiança dos dados (retenção e views engajadas chegam com ~2 dias de atraso)">· dados {c.confidence}</span>
                  </div>
                  {!!c.reasons.length && <div className="text-[12px] text-text/75 mt-1">{c.reasons.join(' · ')}</div>}
                  {c.long_status && <div className={`text-[12px] mt-1 ${c.long_status === 'discarded' ? 'text-warn' : 'text-ok'}`}>
                    {STATUS[c.long_status]}{c.long_title && c.long_status !== 'working' ? `: ${c.long_title}` : ''}
                    {c.long_status === 'script' && c.script_id && <> · <Link to={`/roteiros/${c.script_id}`} className="underline">abrir roteiro</Link></>}
                  </div>}
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <div className="text-right" title={Object.entries(c.parts).map(([k, v]) => `${k}: ${v}`).join(' · ')}>
                    <div className={`text-[18px] font-semibold num leading-none ${c.champion ? 'text-ok' : ''}`}>{c.score}</div>
                    <div className="text-[11px] text-faint mt-1">{c.champion ? 'campeão' : c.early ? 'menos de 24 h' : 'nota'}</div>
                  </div>
                  <button className={`btn btn-sm ${c.champion && !done ? 'btn-primary' : ''}`} disabled={working || !!done || c.early}
                    title={c.early ? 'Espere 24 h no ar para as métricas firmarem' : done ? 'Este Short já virou vídeo longo' : 'Pesquisa fontes, planeja capítulos e escreve o roteiro longo'}
                    onClick={() => go(c)}>
                    {working ? <Loader2 size={14} className="animate-spin" /> : <Film size={14} />}
                    {working ? 'Criando…' : done ? 'Feito' : 'Transformar em vídeo longo'}
                  </button>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
