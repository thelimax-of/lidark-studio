import { useState } from 'react'
import { Clapperboard, Download, Trash2, Send, Loader2, ShieldCheck, ShieldAlert, RotateCcw, Check, Play, ExternalLink, List, LayoutGrid, FileText, Search, Images, ListOrdered, Scissors } from 'lucide-react'
import clsx from 'clsx'
import { Link, useNavigate } from 'react-router-dom'
import { api, invalidate, mediaUrl, useApi, type Video } from '../api'
import { act, ago, Empty, fmtDur, Menu, Modal, PageHeader, Status, Tabs, useChannel } from '../ui'
import PublishModal from './PublishModal'
import { RowsSkeleton, useProgressive } from './kit'

type Filter = 'all' | 'ready' | 'review' | 'published' | 'failed'
const playable = (v: Video) => ['ready', 'published', 'review'].includes(v.status)

export default function Videos() {
  const { channel } = useChannel()
  const nav = useNavigate()
  // versão leve: assets só com qa/thumbs_ab/duração/modelo/capítulos — é tudo o que esta tela lê
  const { data = [], isLoading } = useApi<Video[]>(channel ? `/videos?channel_id=${channel.id}&slim=1` : null)
  const [pub, setPub] = useState<Video | null>(null)
  const [qa, setQa] = useState<Video | null>(null)
  const [play, setPlay] = useState<Video | null>(null)
  const [ab, setAb] = useState<Video | null>(null)
  const [filter, setFilter] = useState<Filter>('all')
  const [q, setQ] = useState('')
  const [view, setView] = useState<'list' | 'grid'>(() => { try { return (localStorage.getItem('videos.view') as any) || 'list' } catch { return 'list' } })
  const setViewP = (v: 'list' | 'grid') => { setView(v); try { localStorage.setItem('videos.view', v) } catch { /* noop */ } }
  const count = (k: string) => data.filter(v => v.status === k).length
  const list = data.filter(v => (filter === 'all' || v.status === filter) && (v.title ?? '').toLowerCase().includes(q.toLowerCase()))
  const [shown, more] = useProgressive(list, view === 'grid' ? 48 : 60, filter + q + view)

  const remove = (v: Video) => confirm(`Excluir “${v.title}”?`) && act(() => api(`/videos/${v.id}`, { method: 'DELETE' }), 'Vídeo excluído').then(() => invalidate('/videos'))
  const menu = (v: Video) => [
    { label: 'Assistir', icon: <Play size={15} />, onClick: () => setPlay(v), disabled: !playable(v) },
    { label: 'Relatório de qualidade', icon: <ShieldCheck size={15} />, onClick: () => setQa(v) },
    { label: 'Abrir roteiro', icon: <FileText size={15} />, onClick: () => nav(`/roteiros/${v.script_id}`), disabled: !v.script_id },
    ...(v.path ? [{ label: 'Baixar MP4', icon: <Download size={15} />, href: mediaUrl(v.path) }] : []),
    ...(v.publications?.[0]?.url ? [{ label: 'Abrir no YouTube', icon: <ExternalLink size={15} />, href: v.publications[0].url }] : []),
    { label: 'Reinspecionar', icon: <RotateCcw size={15} />, onClick: () => act(() => api(`/videos/${v.id}/inspect`, { body: {} }), 'Inspeção iniciada'), disabled: !v.path },
    ...(v.format === 'long' && v.path ? [
      'sep' as const,
      { label: 'Miniaturas para teste A/B', icon: <Images size={15} />, onClick: () => v.assets?.thumbs_ab?.length ? setAb(v)
        : act(() => api(`/videos/${v.id}/thumbs-ab`, { body: {} }), 'Criando 3 miniaturas — aparecem aqui em instantes').then(() => invalidate('/jobs')) },
      { label: 'Capítulos no YouTube', icon: <ListOrdered size={15} />, disabled: v.status !== 'published',
        onClick: () => act(() => api(`/videos/${v.id}/chapters`, { body: {} }), 'Gerando capítulos e atualizando a descrição').then(() => invalidate('/jobs')) },
      { label: 'Criar Shorts deste vídeo', icon: <Scissors size={15} />,
        onClick: () => act(() => api(`/videos/${v.id}/shorts-from-long`, { body: {} }), 'Escrevendo Shorts a partir do vídeo longo').then(() => invalidate('/jobs')) },
    ] : []),
    'sep' as const,
    { label: 'Excluir', icon: <Trash2 size={15} />, danger: true, onClick: () => remove(v) },
  ]
  const primary = (v: Video) =>
    (v.status === 'ready' || v.status === 'review') ? <button className="btn btn-sm btn-primary" onClick={() => setPub(v)}><Send size={13} /> Publicar</button>
      : v.status === 'published' && v.publications?.[0]?.url ? <a className="btn btn-sm" href={v.publications[0].url} target="_blank" rel="noreferrer"><ExternalLink size={13} /> Ver</a>
        : null

  return (
    <>
      <PageHeader eyebrow={channel?.name} title="Vídeos" subtitle="Tudo que foi produzido. Assista, confira a qualidade e publique." />
      <div className="flex flex-wrap items-end justify-between gap-3 mb-4">
        <Tabs value={filter} onChange={setFilter} items={[
          { key: 'all', label: 'Todos', count: data.length }, { key: 'ready', label: 'Prontos', count: count('ready') },
          { key: 'review', label: 'Revisar', count: count('review') }, { key: 'published', label: 'Publicados', count: count('published') },
          { key: 'failed', label: 'Falharam', count: count('failed') },
        ]} />
        <div className="flex items-center gap-2 pb-1.5">
          <div className="relative">
            <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-faint" />
            <input className="input h-8! w-56 pl-8!" placeholder="Buscar vídeo…" value={q} onChange={e => setQ(e.target.value)} />
          </div>
          <div className="seg">
            <button data-active={view === 'list'} onClick={() => setViewP('list')} aria-label="Lista"><List size={14} /></button>
            <button data-active={view === 'grid'} onClick={() => setViewP('grid')} aria-label="Grade"><LayoutGrid size={14} /></button>
          </div>
        </div>
      </div>

      {isLoading && !data.length && <div className="card"><RowsSkeleton rows={6} h="h-14" /></div>}
      {!isLoading && !list.length && <Empty icon={<Clapperboard size={20} />} title={q ? 'Nada com essa busca' : 'Nenhum vídeo aqui'} text={q ? 'Tente outra palavra.' : 'Produza a partir de uma pauta ou de um roteiro.'}
        action={!q && filter === 'all' ? <Link to="/pautas" className="btn btn-primary">Ir para Pautas</Link> : undefined} />}

      {!!list.length && view === 'list' && (
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="tbl">
              <thead><tr>
                <th>Vídeo</th><th>Status</th><th>Qualidade</th><th>Formato</th><th className="right">Duração</th><th>Criado</th><th className="right w-[140px]"><span className="sr-only">Ações</span></th>
              </tr></thead>
              <tbody>
                {shown.map(v => (
                  <tr key={v.id} className="group">
                    <td className="max-w-0 w-[44%]">
                      <div className="flex items-center gap-3 min-w-0">
                        <Thumb v={v} onPlay={() => setPlay(v)} />
                        <div className="min-w-0">
                          <Link to={`/roteiros/${v.script_id}`} className="font-medium truncate block hover:text-accent2 transition-colors">{v.title}</Link>
                          {v.status === 'failed'
                            ? <div className="text-[12.5px] text-bad truncate" title={v.error}>{v.error || 'Falhou ao renderizar'}</div>
                            : <div className="text-[12.5px] text-muted truncate"><span className="num text-faint">#{v.id}</span>{v.publications?.[0]?.url ? ' · no YouTube' : ''}</div>}
                        </div>
                      </div>
                    </td>
                    <td><Status s={v.status} /></td>
                    <td><QaBadge v={v} onClick={() => setQa(v)} /></td>
                    <td><span className={v.format === 'long' ? 'badge badge-accent' : 'badge text-muted'}>{v.format === 'long' ? 'Longo 16:9' : 'Short 9:16'}</span></td>
                    <td className="right num text-muted">{v.duration ? fmtDur(v.duration) : '—'}</td>
                    <td className="text-muted whitespace-nowrap">{ago(v.created_at)}</td>
                    <td className="right">
                      <div className="flex items-center justify-end gap-1">{primary(v)}<Menu items={menu(v)} /></div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {more}
          </div>
        </div>
      )}

      {!!list.length && view === 'grid' && (
        <>
        <div className="grid grid-cols-[repeat(auto-fill,minmax(210px,1fr))] gap-4">
          {shown.map(v => (
            <div key={v.id} className="card overflow-hidden flex flex-col card-hover group">
              <button className={clsx('relative bg-black overflow-hidden', v.format === 'long' ? 'aspect-video' : 'aspect-[9/16]')} onClick={() => playable(v) && setPlay(v)}>
                {v.thumbnail_path && v.status !== 'rendering'
                  ? <img src={mediaUrl(v.thumbnail_path)} loading="lazy" className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-[1.03]" alt="" />
                  : <div className="w-full h-full grid place-items-center text-muted text-[13px] p-4 text-center">
                    {v.status === 'failed' ? <span className="text-bad text-xs line-clamp-6">{v.error}</span> : <span className="flex flex-col items-center gap-2"><Loader2 className="animate-spin" size={18} />Renderizando…</span>}
                  </div>}
                {v.duration ? <span className="absolute bottom-2 right-2 text-[11.5px] num px-1.5 py-0.5 rounded-md bg-black/75 backdrop-blur-sm">{fmtDur(v.duration)}</span> : null}
                {playable(v) && v.thumbnail_path && (
                  <div className="absolute inset-0 grid place-items-center bg-black/30 opacity-0 group-hover:opacity-100 transition">
                    <div className="w-12 h-12 rounded-full bg-grad text-white grid place-items-center shadow-lg"><Play size={18} fill="currentColor" /></div>
                  </div>
                )}
              </button>
              <div className="p-3 flex flex-col gap-2.5 flex-1">
                <div className="text-[13px] font-medium leading-snug line-clamp-2 min-h-[2.6em]" title={v.title}>{v.title}</div>
                <div className="flex items-center gap-1.5 flex-wrap"><Status s={v.status} /><QaBadge v={v} onClick={() => setQa(v)} compact /></div>
                <div className="flex items-center gap-1 mt-auto pt-2 border-t border-line">
                  <span className="text-[12px] text-muted flex-1">{ago(v.created_at)}</span>
                  {primary(v)}<Menu items={menu(v)} />
                </div>
              </div>
            </div>
          ))}
        </div>
        {more}
        </>
      )}

      {pub && <PublishModal video={pub} onClose={() => setPub(null)} />}
      {ab && <AbModal v={data.find(x => x.id === ab.id) ?? ab} onClose={() => setAb(null)} />}
      {qa && <QaModal v={data.find(x => x.id === qa.id) ?? qa} onClose={() => setQa(null)} />}
      {play && (
        <div className="fixed inset-0 z-[70] backdrop !bg-black/80 grid place-items-center p-6 animate-[enter_.2s_ease_both]" onMouseDown={() => setPlay(null)}>
          <div className="relative animate-pop" onMouseDown={e => e.stopPropagation()}>
            <video src={mediaUrl(play.path)} poster={mediaUrl(play.thumbnail_path)} controls autoPlay
              className={clsx('rounded-[var(--r-lg)] bg-black shadow-[var(--shadow-lg)] ring-1 ring-white/10', play.format === 'long' ? 'max-w-[85vw] max-h-[80vh]' : 'h-[86vh] aspect-[9/16]')} />
            <div className="text-center text-[13px] mt-3 text-muted max-w-[60ch] mx-auto">{play.title}</div>
          </div>
        </div>
      )}
    </>
  )
}

function Thumb({ v, onPlay }: { v: Video; onPlay: () => void }) {
  const long = v.format === 'long'
  return (
    <button onClick={() => playable(v) && onPlay()} className={clsx('relative shrink-0 rounded-md overflow-hidden bg-black border border-line group/t hover:border-line3 transition-colors', long ? 'w-[72px] h-[40px]' : 'w-[34px] h-[60px]')}>
      {v.thumbnail_path && v.status !== 'rendering'
        ? <img src={mediaUrl(v.thumbnail_path)} loading="lazy" className="w-full h-full object-cover" alt="" />
        : <div className="w-full h-full grid place-items-center text-faint">{v.status === 'failed' ? <Clapperboard size={14} /> : <Loader2 size={14} className="animate-spin" />}</div>}
      {playable(v) && <div className="absolute inset-0 grid place-items-center bg-black/50 opacity-0 group-hover/t:opacity-100 transition"><Play size={14} fill="white" className="text-white" /></div>}
    </button>
  )
}

type QA = { passed: boolean; score: number; manual?: boolean; checks: { name: string; level: string; detail: string }[]; visual?: { scene: number; severity: number; problem: string }[] }

function QaBadge({ v, onClick, compact }: { v: Video; onClick: () => void; compact?: boolean }) {
  const qa = v.assets?.qa as QA | undefined
  if (!qa) return v.status === 'ready' ? <button onClick={onClick} className="badge text-muted hover:border-line3 hover:text-text transition-colors">Sem inspeção</button> : <span className="text-faint">—</span>
  return (
    <button onClick={onClick} className={clsx('badge transition-colors', qa.passed ? 'badge-ok' : 'badge-warn')} data-tip="Ver relatório">
      {qa.passed ? <ShieldCheck size={13} /> : <ShieldAlert size={13} />}
      {qa.passed ? (qa.manual ? 'Aprovado' : <span className="num">{qa.score}{compact ? '' : '/100'}</span>) : 'Reprovado'}
    </button>
  )
}

function QaModal({ v, onClose }: { v: Video; onClose: () => void }) {
  const qa = v.assets?.qa as QA | undefined
  const icon = (l: string) => l === 'ok' ? <Check size={14} className="text-ok" /> : l === 'warn' ? <ShieldAlert size={14} className="text-warn" /> : <ShieldAlert size={14} className="text-bad" />
  return (
    <Modal open onClose={onClose} title="Inspetor de qualidade">
      <div className="text-[13px] text-muted mb-3">{v.title}</div>
      {!qa && <p className="text-[13px] text-muted">Este vídeo ainda não foi inspecionado.</p>}
      {qa && <>
        <div className={clsx('flex items-center gap-2 px-3 h-10 rounded-[var(--r-md)] mb-4 text-[13px] font-medium border', qa.passed ? 'border-ok/30 bg-ok/10 text-ok' : 'border-warn/30 bg-warn/10 text-warn')}>
          {qa.passed ? <ShieldCheck size={15} /> : <ShieldAlert size={15} />}
          {qa.passed ? `Aprovado${qa.manual ? ' manualmente' : ''} — nota ${qa.score}` : 'Reprovado — não será publicado automaticamente'}
        </div>
        <div className="divide-y divide-line border border-line rounded-[var(--r-md)] overflow-hidden">
          {qa.checks.map((c, k) => (
            <div key={k} className="flex gap-3 px-3 py-2 text-[13px] hover:bg-white/[0.02]"><span className="pt-0.5">{icon(c.level)}</span><span className="font-medium w-40 shrink-0">{c.name}</span><span className="text-muted">{c.detail}</span></div>
          ))}
        </div>
        {!!qa.visual?.filter(x => x.severity >= 2).length && (
          <div className="mt-4"><div className="label">Problemas visuais</div>
            {qa.visual.filter(x => x.severity >= 2).map(x => <div key={x.scene} className="text-[12.5px] text-muted">Cena {x.scene}: {x.problem}</div>)}</div>
        )}
      </>}
      <div className="flex gap-2 mt-5 pt-4 border-t border-line">
        <button className="btn btn-sm" onClick={() => act(() => api(`/videos/${v.id}/inspect`, { body: {} }), 'Inspeção iniciada').then(onClose)}><RotateCcw size={14} /> Reinspecionar</button>
        <div className="flex-1" />
        {qa && !qa.passed && <button className="btn btn-sm btn-primary" onClick={() => act(() => api(`/videos/${v.id}/approve`, { body: {} }), 'Vídeo liberado').then(() => { invalidate('/videos'); onClose() })}><Check size={14} /> Aprovar mesmo assim</button>}
      </div>
    </Modal>
  )
}

function AbModal({ v, onClose }: { v: Video; onClose: () => void }) {
  const thumbs: string[] = v.assets?.thumbs_ab ?? []
  return (
    <Modal open onClose={onClose} title="Miniaturas para teste A/B" wide>
      <p className="text-[13px] text-muted mb-4">
        No YouTube Studio, abra o vídeo → <b className="text-text">Miniatura → Testar e comparar</b> e envie as 3. O YouTube mostra
        cada uma para parte do público e fica com a que gera mais tempo assistido.
      </p>
      <div className="grid sm:grid-cols-3 gap-3">
        {thumbs.map((t, i) => (
          <div key={t} className="space-y-2">
            <img src={mediaUrl(t) + `?v=${Date.now() % 100000}`} className="w-full rounded-[var(--r-md)] border border-line" alt="" />
            <div className="flex items-center justify-between text-[12.5px]"><span className="text-muted">Opção {'ABC'[i]}</span>
              <a className="btn btn-sm" href={mediaUrl(t)} download={`miniatura_${'abc'[i]}.jpg`}><Download size={13} /> Baixar</a></div>
          </div>
        ))}
      </div>
      <div className="flex justify-end mt-4 pt-4 border-t border-line">
        <button className="btn btn-sm" onClick={() => act(() => api(`/videos/${v.id}/thumbs-ab`, { body: {} }), 'Gerando novas opções…').then(onClose)}><RotateCcw size={13} /> Gerar outras</button>
      </div>
    </Modal>
  )
}
