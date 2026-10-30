import { CheckCircle2, Circle, Copy, ExternalLink, ListChecks } from 'lucide-react'
import clsx from 'clsx'
import { api, invalidate, mediaUrl, useApi } from '../api'
import { Modal, Skeleton, toast } from '../ui'

/** Checklist do YouTube Studio: o que a API não faz (Testar e comparar, vídeo relacionado, tela final, dublagem,
 *  fixar comentário, enquete), com link direto para a tela certa. Os itens marcados ficam salvos no servidor. */

type Item = {
  id: string; label: string; detail: string; link: string; done: boolean; done_at?: string | null; disabled?: boolean; hint?: string
  thumbs?: string[]; titles?: string[]; related?: { title: string; url: string; why?: string } | null
  poll?: { question?: string; options?: string[] }
}
export type Checklist = {
  publication: { id: number; title: string; url: string; external_id: string; studio: string; format: string; video_id: number | null }
  items: Item[]; done: number; total: number
}
export type ChecklistSummary = Record<string, { done: number; total: number; video_id: number | null }>

const copy = (t: string) => navigator.clipboard?.writeText(t).then(() => toast.ok('Copiado'), () => toast.err('Não deu para copiar'))

export function ChecklistChip({ s, onClick }: { s?: { done: number; total: number }; onClick: () => void }) {
  if (!s || !s.total) return null
  const full = s.done >= s.total
  return (
    <button onClick={onClick} className={clsx('badge transition-colors', full ? 'badge-ok' : 'text-muted hover:text-text hover:border-line3')}
      data-tip="Checklist do YouTube Studio">
      <ListChecks size={12} /><span className="num">{s.done}/{s.total}</span>
    </button>
  )
}

export default function StudioChecklist({ pubId, videoId, onClose }: { pubId?: number | null; videoId?: number | null; onClose: () => void }) {
  const path = pubId ? `/publish2/checklist/${pubId}` : videoId ? `/publish2/checklist/by-video/${videoId}` : null
  const { data, isLoading, error, refetch } = useApi<Checklist>(path, { keepPrevious: false })
  const toggle = (it: Item) => data && api(`/publish2/checklist/${data.publication.id}/toggle`, { body: { item: it.id, done: !it.done } })
    .then(() => { refetch(); invalidate('/publish2/checklist?') }).catch(e => toast.err(String(e.message ?? e)))

  return (
    <Modal open onClose={onClose} title="Checklist do YouTube Studio" wide>
      {isLoading && <Skeleton className="h-64" />}
      {error && <p className="text-[13px] text-muted">{String((error as Error).message || 'Vídeo ainda não publicado')}</p>}
      {data && <>
        <div className="flex items-center gap-3 mb-4">
          <div className="min-w-0 flex-1">
            <div className="text-[13.5px] font-medium truncate">{data.publication.title}</div>
            <div className="text-[12px] text-muted">O que a API do YouTube não faz — feito à mão no Studio. {data.done}/{data.total} feito(s).</div>
          </div>
          {data.publication.studio && <a className="btn btn-sm" href={data.publication.studio} target="_blank" rel="noreferrer"><ExternalLink size={13} /> Abrir no Studio</a>}
        </div>
        <ul className="space-y-2.5">
          {data.items.map(it => (
            <li key={it.id} className={clsx('surface-2 p-3 flex gap-3', it.disabled && 'opacity-60')}>
              <button onClick={() => !it.disabled && toggle(it)} disabled={it.disabled} className="shrink-0 mt-0.5" aria-label={it.done ? 'Desmarcar' : 'Marcar como feito'}>
                {it.done ? <CheckCircle2 size={18} className="text-ok" /> : <Circle size={18} className="text-faint hover:text-text" />}
              </button>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={clsx('text-[13.5px] font-medium', it.done && 'line-through text-muted')}>{it.label}</span>
                  <div className="flex-1" />
                  {it.link && <a className="btn btn-sm btn-ghost" href={it.link} target="_blank" rel="noreferrer"><ExternalLink size={13} /> Abrir</a>}
                </div>
                <p className="text-[12.5px] text-muted mt-0.5 leading-relaxed">{it.detail}</p>
                {it.hint && <p className="text-[12px] text-warn mt-1">{it.hint}</p>}
                {!!it.thumbs?.length && (
                  <div className="grid grid-cols-3 gap-2 mt-2.5">
                    {it.thumbs.map((t, i) => (
                      <a key={t} href={mediaUrl(t)} download={`miniatura_${'abc'[i]}.jpg`} className="block group" data-tip="Baixar">
                        <img src={mediaUrl(t)} className="w-full rounded-md border border-line group-hover:border-line3" alt={`Opção ${'ABC'[i]}`} loading="lazy" />
                      </a>
                    ))}
                  </div>
                )}
                {!!it.titles?.length && (
                  <div className="mt-2.5 space-y-1">
                    {it.titles.map((t, i) => (
                      <div key={t} className="flex items-center gap-2 text-[12.5px]">
                        <span className="text-faint w-4">{'ABC'[i]}</span><span className="flex-1 truncate">{t}</span>
                        <button className="btn btn-sm btn-icon btn-ghost" onClick={() => copy(t)} aria-label="Copiar título"><Copy size={12} /></button>
                      </div>
                    ))}
                  </div>
                )}
                {it.related?.url && (
                  <div className="flex items-center gap-2 text-[12.5px] mt-2">
                    <a href={it.related.url} target="_blank" rel="noreferrer" className="truncate flex-1 hover:text-accent2">{it.related.title}</a>
                    <button className="btn btn-sm btn-ghost" onClick={() => copy(it.related!.url)}><Copy size={12} /> Link</button>
                  </div>
                )}
                {it.poll?.question && (
                  <div className="mt-2.5 rounded-md border border-line p-2.5 text-[12.5px]">
                    <div className="flex items-start gap-2"><span className="font-medium flex-1">{it.poll.question}</span>
                      <button className="btn btn-sm btn-icon btn-ghost" aria-label="Copiar enquete"
                        onClick={() => copy([it.poll!.question, ...(it.poll!.options ?? [])].join('\n'))}><Copy size={12} /></button></div>
                    <ul className="mt-1 text-muted">{it.poll.options?.map(o => <li key={o}>○ {o}</li>)}</ul>
                  </div>
                )}
              </div>
            </li>
          ))}
        </ul>
      </>}
    </Modal>
  )
}
