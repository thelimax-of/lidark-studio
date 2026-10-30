import { useEffect } from 'react'
import clsx from 'clsx'
import { Radar, RefreshCw, Flame, Search, TrendingUp, Users, Globe2, Plus, Clapperboard, ExternalLink, Loader2 } from 'lucide-react'
import { api, invalidate, onJob, useApi, type Job } from '../api'
import { act, ago, Empty, PageHeader, ScoreRing, SectionTitle, Skeleton, Status, fmtNum, useChannel } from '../ui'

type Ranked = { kind: 'rising' | 'competitor' | 'search' | 'google'; title: string; detail: string; url: string; thumbnail?: string; views?: number; vph?: number; short?: boolean; niche?: boolean; score: number; source: string }
type TIdea = { id: number; title: string; angle: string; summary: string; format: string; status: string; score: number | null; fact_status: string; evidence: string; urgency: string; created_at: string }
type Snap = { channel_id: number; at?: string; keywords: string[]; ranked?: Ranked[]; ideas: TIdea[]; job: Job | null }
type AllRow = { channel_id: number; name: string; at?: string; top: Ranked[]; ideas_new: number }

const KIND = {
  rising: { label: 'Subindo agora', icon: TrendingUp }, competitor: { label: 'Viral de concorrente', icon: Users },
  search: { label: 'Buscado no YouTube', icon: Search }, google: { label: 'Google Trends', icon: Globe2 },
}

export default function Trends() {
  const { channel } = useChannel()
  const cid = channel?.id
  const { data, isLoading } = useApi<Snap>(cid ? `/trends?channel_id=${cid}` : null)
  const { data: all } = useApi<AllRow[]>('/trends/all?top=3')
  useEffect(() => onJob(j => {
    if (['trend_radar', 'manual_idea', 'verify_idea', 'score_idea', 'write_script'].includes(j.kind) && ['done', 'failed'].includes(j.status)) invalidate('/trends')
  }), [])
  const refresh = (ideas: boolean) => cid && act(() => api(`/trends/${cid}/refresh`, { body: { ideas } }),
    ideas ? 'Radar rodando: tendências + pautas novas' : 'Atualizando o que está subindo').then(() => invalidate('/trends'))
  const toIdea = (r: Ranked) => cid && act(() => api(`/trends/${cid}/idea`, { body: { title: r.title, evidence: `${r.source}: ${r.detail}` } }),
    'Pauta criada — a IA pesquisa, checa os fatos e dá nota').then(() => invalidate('/trends'))
  const generate = (i: TIdea) => act(() => api(`/ideas/${i.id}/script`, { body: { auto_render: true, format: i.format } }),
    'Roteiro e vídeo na fila').then(() => invalidate('/trends'))
  const ranked = data?.ranked ?? []
  const running = !!data?.job
  return (
    <div>
      <PageHeader eyebrow="Crescer" title="Radar de tendências"
        subtitle="O que está subindo agora no YouTube Brasil (views por hora), o que o público busca, virais de concorrentes e Google Trends — ranqueado para este canal, cada um a um clique de virar vídeo."
        actions={<>
          <button className="btn btn-sm" disabled={running} onClick={() => refresh(false)}><RefreshCw size={14} className={clsx(running && 'animate-spin')} /> Atualizar</button>
          <button className="btn btn-sm btn-primary" disabled={running} onClick={() => refresh(true)}><Radar size={14} /> Radar + pautas novas</button>
        </>} />
      {!!all?.length && (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4 mb-4">
          {all.map(r => (
            <div key={r.channel_id} className={clsx('card p-3', r.channel_id === cid && 'ring-1 ring-[var(--accent)]')}>
              <div className="flex items-center justify-between text-[12.5px] mb-1.5"><b>{r.name}</b><span className="text-faint">{r.at ? ago(r.at) : 'sem radar'}</span></div>
              {r.top.length ? r.top.map((t, i) => <div key={i} className="text-[12px] text-muted truncate">🔥 {t.title}</div>)
                : <div className="text-[12px] text-faint">Rode o radar neste canal.</div>}
              {r.ideas_new > 0 && <div className="text-[11.5px] text-info mt-1">{r.ideas_new} pauta(s) de tendência em estoque</div>}
            </div>
          ))}
        </div>
      )}
      {running && <div className="card p-3 mb-4 text-[13px] flex items-center gap-2"><Loader2 size={14} className="animate-spin" /> {data?.job?.stage || 'Radar rodando…'}</div>}
      {isLoading ? <Skeleton className="h-96" /> : (
        <div className="grid gap-4 xl:grid-cols-[1fr_420px] items-start">
          <section className="card overflow-hidden">
            <SectionTitle hint={data?.at ? `Atualizado ${ago(data.at)} · palavras-chave: ${data.keywords.join(', ')}` : 'Ainda sem leitura — clique em Atualizar'}>
              <span className="inline-flex items-center gap-2"><Flame size={15} className="text-warn" />Em alta para {channel?.name}</span>
            </SectionTitle>
            {!ranked.length ? <div className="p-6 text-[13px] text-muted text-center">Nenhum sinal ainda.</div> : (
              <ul className="divide-y divide-line">
                {ranked.map((r, i) => {
                  const K = KIND[r.kind] ?? KIND.search
                  return (
                    <li key={i} className="flex items-center gap-3 px-4 py-2.5">
                      {r.thumbnail ? <img src={r.thumbnail} alt="" className="w-24 h-[54px] rounded object-cover bg-panel2 shrink-0" />
                        : <div className="w-24 h-[54px] rounded bg-panel2 grid place-items-center text-muted shrink-0"><K.icon size={16} /></div>}
                      <div className="min-w-0 flex-1">
                        <div className="text-[13px] font-medium line-clamp-2">{r.title}</div>
                        <div className="text-[11.5px] text-muted mt-0.5 flex flex-wrap gap-x-2">
                          <span>{K.label}</span><span>{r.detail}</span>{r.views ? <span>{fmtNum(r.views)} views</span> : null}
                          {r.kind === 'rising' && !r.niche && <span className="text-faint">fora do nicho</span>}
                        </div>
                      </div>
                      <ScoreRing score={r.score} size={34} />
                      <div className="flex gap-1 shrink-0">
                        {r.url && <a href={r.url} target="_blank" rel="noreferrer" className="btn btn-sm btn-icon btn-ghost" data-tip="Abrir"><ExternalLink size={14} /></a>}
                        <button className="btn btn-sm" onClick={() => toIdea(r)} data-tip="A IA cria uma pauta com ângulo próprio (sem copiar)"><Plus size={14} /> Pauta</button>
                      </div>
                    </li>
                  )
                })}
              </ul>
            )}
          </section>
          <section className="card overflow-hidden">
            <SectionTitle hint="Pautas que o radar criou — checadas e com nota. Gerar = roteiro + vídeo automático">Pautas de tendência</SectionTitle>
            {!data?.ideas.length ? <div className="p-5"><Empty icon={<Radar size={18} />} title="Sem pautas de tendência" text="Clique em “Radar + pautas novas”." /></div> : (
              <ul className="divide-y divide-line">
                {data.ideas.map(i => (
                  <li key={i.id} className="px-4 py-3">
                    <div className="flex items-start gap-3">
                      <ScoreRing score={i.score} size={34} />
                      <div className="min-w-0 flex-1">
                        <div className="text-[13px] font-medium">{i.title}</div>
                        {i.evidence && <div className="text-[11.5px] text-muted line-clamp-2 mt-0.5">🔥 {i.evidence}</div>}
                        <div className="flex flex-wrap items-center gap-1.5 mt-1.5">
                          <Status s={i.status} /><Status s={i.fact_status} />
                          {i.urgency === 'alta' && <span className="badge badge-warn">urgente</span>}
                        </div>
                      </div>
                      {['new', 'approved'].includes(i.status) && (
                        <button className="btn btn-sm btn-primary shrink-0" disabled={i.fact_status === 'disputed'} onClick={() => generate(i)}>
                          <Clapperboard size={14} /> Gerar</button>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}
    </div>
  )
}
