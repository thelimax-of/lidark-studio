import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import clsx from 'clsx'
import { Image as ImageIcon, Sparkles, Check, RotateCcw, Smartphone, Monitor, Loader2, MoreVertical } from 'lucide-react'
import { api, invalidate, mediaUrl, onJob, useApi, type Video } from '../api'
import { act, Empty, PageHeader, SectionTitle, Skeleton, fmtDur, fmtNum, toast, useChannel } from '../ui'

type Opt = { path: string; text: string; variant: number; photo?: string; ring?: boolean; ab?: boolean }
type State = {
  video: { id: number; format: string; status: string; thumbnail_path: string; duration: number; title: string; thumbnail_text: string }
  channel: { id: number; name: string; avatar_url: string; handle: string; subscribers?: number; thumbs_blocked: boolean }
  original: string; picked?: string; options: Opt[]; ab: Opt[]; published: { url: string; external_id: string } | null
}

const norm = (p?: string) => (p ?? '').replace(/\\/g, '/')

export default function ThumbStudio() {
  const { channel } = useChannel()
  const [params, setParams] = useSearchParams()
  const { data: videos = [] } = useApi<Video[]>(channel ? `/videos?channel_id=${channel.id}` : null)
  const list = videos.filter(v => ['ready', 'review', 'published'].includes(v.status))
  const vid = Number(params.get('video')) || list[0]?.id || null
  return (
    <div>
      <PageHeader eyebrow="Criar" title="Estúdio de miniaturas"
        subtitle="Gere versões com fotos, textos e layouts diferentes, veja como aparecem no feed do YouTube (celular e computador) e troque com um clique — se o vídeo já estiver no ar, a miniatura nova vai direto para o YouTube."
        actions={<select className="input !w-auto max-w-[360px] !py-1.5 text-sm" value={vid ?? ''} onChange={e => setParams({ video: e.target.value })}>
          {!list.length && <option value="">Nenhum vídeo pronto</option>}
          {list.map(v => <option key={v.id} value={v.id}>{(v.title ?? `Vídeo #${v.id}`).replace(/#shorts/i, '')} · {v.status === 'published' ? 'no ar' : 'pronto'}</option>)}
        </select>} />
      {vid ? <Studio vid={vid} /> : <Empty icon={<ImageIcon size={18} />} title="Nenhum vídeo" text="Quando um vídeo ficar pronto, ele aparece aqui." />}
    </div>
  )
}

function Studio({ vid }: { vid: number }) {
  const { data: st, isLoading } = useApi<State>(`/thumbs/${vid}`)
  const [texts, setTexts] = useState('')
  const [sel, setSel] = useState<string | null>(null)
  const [view, setView] = useState<'mobile' | 'desktop'>('mobile')
  const [working, setWorking] = useState(false)
  useEffect(() => onJob(j => {
    if (j.kind !== 'thumb_studio' || j.ref_id !== vid) return
    setWorking(j.status === 'queued' || j.status === 'running')
    if (j.status === 'done' || j.status === 'failed') invalidate(`/thumbs/${vid}`)
  }), [vid])
  useEffect(() => { setSel(null) }, [vid])
  const all = useMemo(() => st ? [
    ...(st.original ? [{ path: st.original, text: 'Original', variant: -2 } as Opt] : []),
    ...st.options, ...st.ab.filter(a => !st.options.some(o => norm(o.path) === norm(a.path))),
  ] : [], [st])
  if (isLoading || !st) return <Skeleton className="h-96" />
  const current = norm(st.video.thumbnail_path)
  const shown = sel ?? st.video.thumbnail_path
  const vertical = st.video.format === 'short'
  const gen = () => act(() => api(`/thumbs/${vid}/generate`, { body: { count: 6, texts: texts.split(/[,;\n]/).map(t => t.trim()).filter(Boolean) } }),
    'Gerando variações…').then(() => setWorking(true))
  const pick = (p: string) => act(() => api<{ youtube: { ok: boolean; error?: string } | null }>(`/thumbs/${vid}/pick`, { body: { path: p } }))
    .then(r => {
      if (!r) return
      invalidate(`/thumbs/${vid}`); invalidate('/videos')
      if (r.youtube?.ok === false) toast.err(`Trocada no painel, mas o YouTube recusou: ${r.youtube.error}`)
      else toast.ok(r.youtube?.ok ? 'Miniatura trocada no YouTube' : 'Miniatura escolhida (vai no envio)')
    })
  return (
    <div className="grid gap-4 xl:grid-cols-[1fr_460px] items-start">
      <section className="card overflow-hidden">
        <SectionTitle hint={vertical ? 'Shorts: no feed de Shorts o YouTube mostra um quadro do vídeo; a miniatura aparece na busca, no canal e nas sugestões.' : 'Vídeo longo: a miniatura é o que decide o clique.'}
          action={<div className="flex items-center gap-2">
            <input className="input h-8! w-56" placeholder="Textos (opcional, separe por vírgula)" value={texts} onChange={e => setTexts(e.target.value)} />
            <button className="btn btn-sm btn-primary" disabled={working} onClick={gen}>{working ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />} Gerar variações</button>
          </div>}>Versões</SectionTitle>
        <div className={clsx('grid gap-3 p-4', vertical ? 'grid-cols-3 md:grid-cols-4 lg:grid-cols-6' : 'grid-cols-2 md:grid-cols-3')}>
          {all.map(o => {
            const isCur = norm(o.path) === current
            return (
              <button key={o.path} onClick={() => setSel(o.path)} className={clsx('relative rounded-lg overflow-hidden border text-left transition',
                norm(shown) === norm(o.path) ? 'border-[var(--accent)] ring-2 ring-[var(--accent)]/40' : 'border-line hover:border-line2')}>
                <img src={mediaUrl(o.path)} alt="" className={clsx('w-full object-cover bg-panel2', vertical ? 'aspect-[9/16]' : 'aspect-video')} loading="lazy" />
                <div className="absolute inset-x-0 bottom-0 p-1.5 bg-gradient-to-t from-black/80 to-transparent text-[11px] truncate">
                  {o.variant === -2 ? 'Original' : o.ab ? 'Teste A/B' : o.text}
                </div>
                {isCur && <span className="absolute top-1.5 left-1.5 badge badge-ok !h-5 text-[10.5px]"><Check size={11} /> em uso</span>}
              </button>
            )
          })}
        </div>
        {!st.options.length && <div className="px-4 pb-4 text-[13px] text-muted">Nenhuma variação ainda — clique em “Gerar variações”.</div>}
      </section>
      <section className="card overflow-hidden xl:sticky xl:top-4">
        <SectionTitle action={<div className="seg">
          <button data-active={view === 'mobile'} onClick={() => setView('mobile')}><Smartphone size={13} /> Celular</button>
          <button data-active={view === 'desktop'} onClick={() => setView('desktop')}><Monitor size={13} /> Computador</button>
        </div>}>Prévia no feed</SectionTitle>
        <div className="p-4 bg-[#0f0f0f]">
          {view === 'mobile' ? <MobileFeed st={st} thumb={shown} /> : <DesktopFeed st={st} thumb={shown} others={all.filter(o => norm(o.path) !== norm(shown)).map(o => o.path)} />}
        </div>
        <div className="p-4 flex flex-wrap gap-2 border-t border-line">
          <button className="btn btn-primary btn-sm" disabled={norm(shown) === current} onClick={() => pick(shown)}>
            <Check size={14} /> {st.published ? 'Usar esta (troca no YouTube)' : 'Usar esta'}</button>
          {st.original && norm(st.original) !== current && <button className="btn btn-sm" onClick={() => act(() => api(`/thumbs/${vid}/restore`, { method: 'POST' }), 'Original restaurada').then(() => invalidate(`/thumbs/${vid}`))}>
            <RotateCcw size={14} /> Voltar à original</button>}
          {st.channel.thumbs_blocked && <div className="text-[12px] text-warn w-full">O YouTube recusou miniaturas deste canal: verifique o canal por telefone em youtube.com/verify.</div>}
        </div>
      </section>
    </div>
  )
}

function Avatar({ st, size = 36 }: { st: State; size?: number }) {
  return st.channel.avatar_url ? <img src={st.channel.avatar_url} alt="" className="rounded-full shrink-0" style={{ width: size, height: size }} />
    : <div className="rounded-full bg-[#333] shrink-0" style={{ width: size, height: size }} />
}

const title = (st: State) => st.video.title.replace(/#shorts/i, '').trim()

function MobileFeed({ st, thumb }: { st: State; thumb: string }) {
  if (st.video.format === 'short') {
    return (
      <div className="mx-auto w-[300px] text-white">
        <div className="text-[13px] font-semibold mb-2 flex items-center gap-1.5"><span className="text-[#f00]">▶</span> Shorts</div>
        <div className="grid grid-cols-2 gap-2">
          {[thumb, null].map((t, i) => (
            <div key={i}>
              {t ? <img src={mediaUrl(t)} alt="" className="w-full aspect-[9/16] object-cover rounded-xl" /> : <div className="w-full aspect-[9/16] rounded-xl bg-[#272727]" />}
              <div className="text-[12px] leading-tight mt-1.5 line-clamp-2">{t ? title(st) : ' '}</div>
              {t && <div className="text-[11px] text-[#aaa]">{fmtNum(12000)} visualizações</div>}
            </div>
          ))}
        </div>
      </div>
    )
  }
  return (
    <div className="mx-auto w-[340px] text-white">
      <div className="relative">
        <img src={mediaUrl(thumb)} alt="" className="w-full aspect-video object-cover" />
        <span className="absolute bottom-1.5 right-1.5 bg-black/80 text-[11px] px-1 rounded">{fmtDur(st.video.duration)}</span>
      </div>
      <div className="flex gap-3 p-3">
        <Avatar st={st} />
        <div className="min-w-0 flex-1">
          <div className="text-[13.5px] leading-snug line-clamp-2">{title(st)}</div>
          <div className="text-[11.5px] text-[#aaa] mt-0.5">{st.channel.name} · 12 mil visualizações · há 3 horas</div>
        </div>
        <MoreVertical size={16} className="text-[#aaa]" />
      </div>
    </div>
  )
}

function DesktopFeed({ st, thumb, others }: { st: State; thumb: string; others: string[] }) {
  const vertical = st.video.format === 'short'
  const cells = [thumb, ...others.slice(0, 2)]
  return (
    <div className="text-white">
      <div className={clsx('grid gap-3', vertical ? 'grid-cols-4' : 'grid-cols-3')}>
        {cells.map((t, i) => (
          <div key={i} className={clsx(i > 0 && 'opacity-40')}>
            <div className="relative">
              <img src={mediaUrl(t)} alt="" className={clsx('w-full object-cover rounded-lg', vertical ? 'aspect-[9/16]' : 'aspect-video')} />
              {!vertical && <span className="absolute bottom-1 right-1 bg-black/80 text-[10px] px-1 rounded">{fmtDur(st.video.duration)}</span>}
            </div>
            <div className="flex gap-2 mt-2">
              {!vertical && <Avatar st={st} size={24} />}
              <div className="min-w-0">
                <div className="text-[11.5px] leading-tight line-clamp-2 font-medium">{i === 0 ? title(st) : 'Outro vídeo'}</div>
                <div className="text-[10.5px] text-[#aaa] mt-0.5 truncate">{st.channel.name}</div>
              </div>
            </div>
          </div>
        ))}
        {vertical && <div className="rounded-lg bg-[#272727] aspect-[9/16]" />}
      </div>
      <div className="text-[11px] text-[#777] mt-3">As outras posições mostram as demais versões apagadas, para comparar o contraste lado a lado.</div>
    </div>
  )
}
