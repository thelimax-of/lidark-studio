import { useMemo } from 'react'
import { Send, ExternalLink } from 'lucide-react'
import { mediaUrl, useApi, type Video } from '../api'
import { Empty, PageHeader, SectionTitle, Status, useChannel } from '../ui'

type Pub = { id: number; video_id: number | null; title: string; status: string; scheduled_at: string | null; published_at: string | null
  url: string; thumbnail_url: string; error: string; privacy: string }

const dayKey = (iso: string) => new Date(iso).toLocaleDateString('pt-BR', { weekday: 'long', day: '2-digit', month: 'long' })
const when = (iso?: string | null) => iso ? new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : ''
const time = (iso?: string | null) => iso ? new Date(iso).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }) : '—'

export default function Publish() {
  const { channel } = useChannel()
  const { data = [] } = useApi<Pub[]>(channel ? `/publications?channel_id=${channel.id}` : null)
  const { data: videos = [] } = useApi<Video[]>(channel ? `/videos?channel_id=${channel.id}` : null)
  const thumb = (p: Pub) => {
    const v = videos.find(x => x.id === p.video_id)
    return v?.thumbnail_path ? mediaUrl(v.thumbnail_path) : p.thumbnail_url
  }
  const upcoming = data.filter(p => ['scheduled', 'uploading'].includes(p.status)).sort((a, b) => String(a.scheduled_at).localeCompare(String(b.scheduled_at)))
  const failed = data.filter(p => p.status === 'failed')
  const done = data.filter(p => p.status === 'published').sort((a, b) => String(b.published_at).localeCompare(String(a.published_at)))
  const groups = useMemo(() => {
    const g: Record<string, Pub[]> = {}
    upcoming.forEach(p => { const k = p.scheduled_at ? dayKey(p.scheduled_at) : 'Sem data'; (g[k] ??= []).push(p) })
    return Object.entries(g)
  }, [upcoming])

  const Row = ({ p, left, sub }: { p: Pub; left?: string; sub?: string }) => (
    <div className="flex items-center gap-3 px-4 py-2.5 border-b border-line last:border-0 hover:bg-white/[0.02]">
      {left && <span className="w-12 text-[12.5px] text-muted num shrink-0">{left}</span>}
      <div className="w-[30px] h-[48px] rounded overflow-hidden bg-black shrink-0 border border-line">
        {thumb(p) ? <img src={thumb(p)} referrerPolicy="no-referrer" className="w-full h-full object-cover" alt="" /> : null}
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-[13.5px] font-medium truncate">{p.title.replace(/#Shorts/i, '').trim()}</div>
        <div className="text-[12px] text-muted truncate">{sub}{p.privacy && p.privacy !== 'public' ? ` · ${p.privacy}` : ''}</div>
        {p.error && <div className="text-[12px] text-bad truncate" title={p.error}>{p.error}</div>}
      </div>
      <Status s={p.status} />
      {p.url && <a href={p.url} target="_blank" rel="noreferrer" className="btn btn-sm btn-icon btn-ghost" data-tip="Abrir no YouTube"><ExternalLink size={14} /></a>}
    </div>
  )

  return (
    <>
      <PageHeader title="Agenda" subtitle="Próximas postagens no YouTube e histórico do que já foi ao ar." />
      {!data.length && <Empty icon={<Send size={20} />} title="Nada publicado ainda" text="Em Vídeos, clique em “Publicar” — ou ligue o piloto automático para agendar sozinho." />}
      {!!data.length && (
        <div className="grid xl:grid-cols-5 gap-5 items-start">
          <div className="xl:col-span-3 space-y-5">
            <section className="card overflow-hidden">
              <SectionTitle hint={`${upcoming.length} agendada(s)`}>Próximas postagens</SectionTitle>
              {!upcoming.length && <div className="text-[13px] text-muted px-4 py-8 text-center">Nenhuma postagem agendada.</div>}
              {groups.map(([day, items]) => (
                <div key={day}>
                  <div className="px-4 py-1.5 text-[12px] font-medium text-muted bg-panel2 border-b border-line capitalize">{day}</div>
                  {items.map(p => <Row key={p.id} p={p} left={time(p.scheduled_at)} sub="YouTube" />)}
                </div>
              ))}
            </section>
            {failed.length > 0 && (
              <section className="card overflow-hidden">
                <SectionTitle hint="Tente publicar de novo pela tela de Vídeos"><span className="flex items-center gap-2"><span className="dot text-bad" /> Falharam</span></SectionTitle>
                {failed.map(p => <Row key={p.id} p={p} sub={when(p.scheduled_at)} />)}
              </section>
            )}
          </div>
          <section className="card overflow-hidden xl:col-span-2">
            <SectionTitle hint={`${done.length} vídeo(s) no ar`}>Publicados</SectionTitle>
            <div className="max-h-[70vh] overflow-y-auto">{done.map(p => <Row key={p.id} p={p} sub={when(p.published_at)} />)}</div>
          </section>
        </div>
      )}
    </>
  )
}
