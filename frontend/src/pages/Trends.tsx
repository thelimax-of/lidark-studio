import { useEffect, useState } from 'react'
import clsx from 'clsx'
import { Radar, RefreshCw, Flame, Search, TrendingUp, Users, Globe2, Plus, Clapperboard, ExternalLink, Loader2, Zap } from 'lucide-react'
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
      {cid && <OutliersCard cid={cid} />}
    </div>
  )
}

// ---------------------------------------------------------------- radar de outliers (método "1 em 10")

type Outlier = { id: string; lang: 'pt' | 'en'; title: string; channel: string; channel_avg: number; channel_subs: number; views: number
  ratio: number; short: boolean; age_days: number; thumbnail: string; url: string
  theme?: string; idea_title?: string; angle?: string; query_pt?: string
  pt_coverage?: { query: string; best_views: number; covered: boolean; results: number } }
type OutSnap = { at?: string; pt?: Outlier[]; en?: Outlier[]; gaps?: string[]; notes?: string[]; error?: string
  min_ratio?: number; days?: number; running: boolean; age_hours: number | null }

function OutliersCard({ cid }: { cid: number }) {
  const { data } = useApi<OutSnap>(`/learning/outliers?channel_id=${cid}`, { refetchInterval: 20_000 })
  const [tab, setTab] = useState<'pt' | 'en' | 'gaps'>('pt')
  const refresh = () => act(() => api(`/learning/outliers?channel_id=${cid}&refresh=true`), 'Radar de outliers atualizando (2 buscas na API)')
    .then(() => invalidate('/learning/outliers'))
  const toIdea = (o: Outlier) => act(() => api('/learning/outliers/idea', { body: { channel_id: cid, video_id: o.id } }),
    'Pauta criada com o TEMA (ângulo próprio, pesquisa própria) — a IA checa os fatos e dá nota').then(() => invalidate('/trends'))
  const gaps = new Set(data?.gaps ?? [])
  const list = tab === 'pt' ? data?.pt ?? [] : tab === 'en' ? data?.en ?? [] : (data?.en ?? []).filter(o => gaps.has(o.id))
  return (
    <section className="card overflow-hidden mt-4">
      <SectionTitle hint={`Vídeos do nicho com views ≥ ${data?.min_ratio ?? 5}x a média do PRÓPRIO canal (últimos ${data?.days ?? 21} dias) — o tema puxou, não o tamanho do canal. Só números públicos; cada um vira um TEMA para adaptar com pesquisa própria, nunca cópia.${data?.at ? ` · atualizado ${ago(data.at)}` : ''}`}
        action={<div className="flex items-center gap-2">
          <div className="seg">
            <button data-active={tab === 'pt'} onClick={() => setTab('pt')}>PT-BR ({data?.pt?.length ?? 0})</button>
            <button data-active={tab === 'en'} onClick={() => setTab('en')}>EN ({data?.en?.length ?? 0})</button>
            <button data-active={tab === 'gaps'} onClick={() => setTab('gaps')}>Lacunas ({gaps.size})</button>
          </div>
          <button className="btn btn-sm" disabled={data?.running} onClick={refresh}><RefreshCw size={14} className={clsx(data?.running && 'animate-spin')} /></button>
        </div>}>
        <span className="inline-flex items-center gap-2"><Zap size={15} className="text-warn" />Outliers do nicho</span>
      </SectionTitle>
      {data?.running && <div className="px-4 py-2 text-[12.5px] text-muted flex items-center gap-2 border-b border-line"><Loader2 size={13} className="animate-spin" /> Buscando outliers (PT e EN) e checando o que já existe em português…</div>}
      {data?.error && <div className="px-4 py-2 text-[12.5px] text-warn">{data.error}</div>}
      {!!data?.notes?.length && <div className="px-4 py-2 text-[12px] text-muted">{data.notes.join(' · ')}</div>}
      {tab === 'gaps' && <div className="px-4 pt-3 text-[12px] text-muted">Temas em alta em inglês com pouca cobertura no YouTube brasileiro (busca em português sem vídeo com 100 mil+ views).</div>}
      {!list.length ? <div className="p-6 text-[13px] text-muted text-center">{data?.at ? 'Nenhum outlier nesta lista.' : data?.running ? 'Primeira leitura em andamento…' : 'Ainda sem leitura.'}</div> : (
        <ul className="divide-y divide-line">
          {list.map(o => (
            <li key={o.id} className="flex items-center gap-3 px-4 py-2.5">
              {o.thumbnail ? <img src={o.thumbnail} alt="" referrerPolicy="no-referrer" className="w-24 h-[54px] rounded object-cover bg-panel2 shrink-0" />
                : <div className="w-24 h-[54px] rounded bg-panel2 shrink-0" />}
              <div className="min-w-0 flex-1">
                <div className="text-[13px] font-medium line-clamp-1">{o.idea_title || o.theme || o.title}</div>
                <div className="text-[11.5px] text-muted line-clamp-1">ref.: “{o.title}” · {o.channel}</div>
                <div className="text-[11.5px] text-muted mt-0.5 flex flex-wrap gap-x-2">
                  <span className="text-warn font-semibold num">{o.ratio.toFixed(1).replace('.', ',')}x a média</span>
                  <span>{fmtNum(o.views)} views · canal faz ~{fmtNum(o.channel_avg)}</span>
                  <span>{o.short ? 'Short' : 'longo'} · {Math.round(o.age_days)} dias</span>
                  {o.pt_coverage && <span className={o.pt_coverage.covered ? 'text-faint' : 'text-ok'}>{o.pt_coverage.covered ? `já coberto em PT (${fmtNum(o.pt_coverage.best_views)})` : 'pouco coberto em PT'}</span>}
                </div>
                {o.angle && <div className="text-[11.5px] text-text/80 mt-0.5 line-clamp-1">Ângulo: {o.angle}</div>}
              </div>
              <div className="flex gap-1 shrink-0">
                <a href={o.url} target="_blank" rel="noreferrer" className="btn btn-sm btn-icon btn-ghost" data-tip="Ver a referência"><ExternalLink size={14} /></a>
                <button className="btn btn-sm" disabled={!o.idea_title && !o.theme} onClick={() => toIdea(o)}
                  data-tip="Cria a pauta com o tema e um ângulo próprio — pesquisa própria, sem copiar título nem roteiro"><Plus size={14} /> Pauta</button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
