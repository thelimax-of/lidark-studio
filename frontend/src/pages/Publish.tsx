import { useMemo, useState } from 'react'
import { Send, ExternalLink, CalendarClock, CheckCircle2, AlertTriangle, Gauge, Languages, Smartphone } from 'lucide-react'
import { api, invalidate, mediaUrl, useApi, type Video } from '../api'
import { act, Empty, PageHeader, SectionTitle, Status, useChannel } from '../ui'
import { Bar, RowsSkeleton, StatTile, useProgressive } from './kit'
import StudioChecklist, { ChecklistChip, type ChecklistSummary } from '../components/StudioChecklist'

type Quota = { day: string; reset_at: string; settings: { daily_limit: number; upload_bucket: string; upload_limit: number }
  projects: { project: string; used: number; limit: number; pct: number; uploads: number; upload_limit: number; deferred: number
    kinds: Record<string, number>; allowed: string[] }[] }
type Prefs = { localize: boolean; captions: boolean; captions_langs: string[]; captions_shorts: boolean; phone_approval: boolean
  studio_checklist: boolean; sister_gap_hours: number }
type Approval = { running: boolean; url: string; ntfy_enabled: boolean; muted: boolean; pending: number; note: string }

const KIND_LABEL: Record<string, string> = { thumbnail: 'miniaturas', playlist: 'playlists', 'videos.update': 'edições',
  'captions.insert': 'legendas', comment: 'comentários', list: 'leituras', search: 'buscas' }

/** Medidor da cota diária da YouTube Data API (10.000 unidades/dia por projeto do Google Cloud). */
function QuotaCard() {
  const { data } = useApi<Quota>('/publish2/quota', { refetchInterval: 60_000 })
  const p = data?.projects?.[0]
  if (!p) return null
  const reset = new Date(data!.reset_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
  const spent = Object.entries(p.kinds).filter(([k, v]) => v > 0 && k !== 'upload' && k !== 'upload_count')
  return (
    <section className="card p-4 space-y-2.5">
      <div className="flex items-center gap-2 text-[13px] font-medium"><Gauge size={14} className="text-muted" /> Cota do YouTube hoje
        <span className="flex-1" /><span className="num text-muted">{p.used.toLocaleString('pt-BR')} / {p.limit.toLocaleString('pt-BR')}</span></div>
      <Bar value={p.pct} tone={p.pct >= 80 ? 'warn' : undefined} />
      <div className="text-[12px] text-muted leading-relaxed">
        {p.uploads} envio(s) de vídeo{data!.settings.upload_bucket === 'separate' ? ` (balde próprio, até ${p.upload_limit}/dia)` : ''}
        {spent.length ? ' · ' + spent.map(([k, v]) => `${KIND_LABEL[k] ?? k} ${v}`).join(' · ') : ''}
        {p.pct >= 80 ? ` · acima de 80%: legendas, comentários, métricas e buscas esperam a renovação (${reset})` : ` · renova às ${reset}`}
        {p.deferred ? ` · ${p.deferred} chamada(s) adiada(s)` : ''}
      </div>
    </section>
  )
}

/** Idiomas, legendas oficiais, checklist do Studio, aprovação pelo celular e espaço entre canais irmãos. */
function PublishPrefsCard({ channelId }: { channelId: number }) {
  const { data } = useApi<Prefs>(`/publish2/prefs/${channelId}`)
  const { data: ap } = useApi<Approval>('/publish2/approval')
  const save = (patch: Partial<Prefs>) => act(() => api(`/publish2/prefs/${channelId}`, { method: 'PUT', body: patch }), 'Salvo')
    .then(() => invalidate('/publish2/prefs'))
  if (!data) return null
  const Check = ({ k, label, hint }: { k: keyof Prefs; label: string; hint?: string }) => (
    <label className="flex items-start gap-2 text-[13px] cursor-pointer">
      <input type="checkbox" className="mt-0.5" checked={!!data[k]} onChange={e => save({ [k]: e.target.checked } as Partial<Prefs>)} />
      <span>{label}{hint && <span className="block text-[12px] text-muted">{hint}</span>}</span>
    </label>
  )
  return (
    <section className="card p-4 space-y-3">
      <div className="flex items-center gap-2 text-[13px] font-medium"><Languages size={14} className="text-muted" /> Ao publicar neste canal</div>
      <Check k="localize" label="Título e descrição também em inglês e espanhol" hint="Uma tradução barata por vídeo; o áudio sai marcado como pt-BR (libera a dublagem automática)." />
      <Check k="captions" label="Legendas oficiais (.srt) em PT, EN e ES" hint="Do texto exato do roteiro com os tempos das legendas do vídeo. 400 unidades de cota por idioma." />
      {data.captions && <div className="pl-6"><Check k="captions_shorts" label="Também nos Shorts" hint="Desligado por padrão: 20 Shorts/dia × 3 idiomas estourariam a cota diária." /></div>}
      <Check k="studio_checklist" label="Checklist do YouTube Studio depois de publicar" />
      <Check k="phone_approval" label="Aprovar roteiros e miniaturas pelo celular (ntfy)" />
      {ap && data.phone_approval && (
        <div className="pl-6 text-[12px] text-muted flex items-start gap-1.5"><Smartphone size={12} className="mt-0.5 shrink-0" />
          <span>{!ap.ntfy_enabled ? 'Ligue os avisos no celular em Configurações.' : ap.running ? `Respondendo em ${ap.url}.` : 'Servidor da rede local desligado — liga ao reiniciar.'} {ap.note}</span></div>
      )}
      <label className="flex items-center gap-2 text-[13px]">Espaço entre canais irmãos
        <select className="input h-8! w-24" value={String(data.sister_gap_hours)} onChange={e => save({ sister_gap_hours: Number(e.target.value) })}>
          {[0, 1, 1.5, 2, 3, 4].map(h => <option key={h} value={h}>{h ? `${String(h).replace('.', ',')} h` : 'livre'}</option>)}
        </select><span className="text-[12px] text-muted">(vale para todos)</span>
      </label>
    </section>
  )
}

type Pub = { id: number; video_id: number | null; title: string; status: string; scheduled_at: string | null; published_at: string | null
  url: string; thumbnail_url: string; error: string; privacy: string }

const dayKey = (iso: string) => new Date(iso).toLocaleDateString('pt-BR', { weekday: 'long', day: '2-digit', month: 'long' })
const when = (iso?: string | null) => iso ? new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : ''
const time = (iso?: string | null) => iso ? new Date(iso).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }) : '—'

export default function Publish() {
  const { channel } = useChannel()
  const { data = [], isLoading } = useApi<Pub[]>(channel ? `/publications?channel_id=${channel.id}` : null)
  // só a miniatura do vídeo é usada aqui: lista leve (mesma chave da tela de Vídeos)
  const { data: videos = [] } = useApi<Video[]>(channel ? `/videos?channel_id=${channel.id}&slim=1` : null)
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
  const [doneShown, doneMore] = useProgressive(done, 40, channel?.id)
  const { data: checks } = useApi<ChecklistSummary>(channel ? `/publish2/checklist?channel_id=${channel.id}` : null)
  const [check, setCheck] = useState<number | null>(null)

  const Row = ({ p, left, sub }: { p: Pub; left?: string; sub?: string }) => (
    <div className="flex items-center gap-3 px-4 py-2.5 border-b border-line last:border-0 hover:bg-white/[0.025] transition-colors group">
      {left && <span className="w-12 text-[13px] font-semibold num shrink-0">{left}</span>}
      <div className="w-[30px] h-[48px] rounded-md overflow-hidden bg-panel2 shrink-0 border border-line">
        {thumb(p) ? <img src={thumb(p)} referrerPolicy="no-referrer" loading="lazy" className="w-full h-full object-cover" alt="" /> : null}
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-[13.5px] font-medium truncate">{p.title.replace(/#Shorts/i, '').trim()}</div>
        <div className="text-[12px] text-muted truncate">{sub}{p.privacy && p.privacy !== 'public' ? ` · ${p.privacy}` : ''}</div>
        {p.error && <div className="text-[12px] text-bad truncate" title={p.error}>{p.error}</div>}
      </div>
      {p.status === 'published' && <ChecklistChip s={checks?.[String(p.id)]} onClick={() => setCheck(p.id)} />}
      <Status s={p.status} />
      {p.url && <a href={p.url} target="_blank" rel="noreferrer" className="btn btn-sm btn-icon btn-ghost opacity-60 group-hover:opacity-100" data-tip="Abrir no YouTube"><ExternalLink size={14} /></a>}
    </div>
  )

  return (
    <>
      <PageHeader eyebrow={channel?.name} title="Agenda" subtitle="Próximas postagens no YouTube e histórico do que já foi ao ar." />
      {isLoading && !data.length && <div className="card"><RowsSkeleton rows={5} h="h-12" /></div>}
      {!!data.length && (
        <div className="grid grid-cols-3 gap-3 mb-5">
          <StatTile label="Agendadas" icon={<CalendarClock size={14} />} value={upcoming.length} sub={upcoming[0]?.scheduled_at ? `próxima ${when(upcoming[0].scheduled_at)}` : 'nada na fila'} tone="accent" />
          <StatTile label="No ar" icon={<CheckCircle2 size={14} />} value={done.length} sub={done[0]?.published_at ? `última ${when(done[0].published_at)}` : '—'} />
          <StatTile label="Falharam" icon={<AlertTriangle size={14} />} value={failed.length} sub={failed.length ? 'tente de novo em Vídeos' : 'tudo certo'} tone={failed.length ? 'bad' : undefined} />
        </div>
      )}
      {!isLoading && !data.length && <Empty icon={<Send size={20} />} title="Nada publicado ainda" text="Em Vídeos, clique em “Publicar” — ou ligue o piloto automático para agendar sozinho." />}
      {!!data.length && (
        <div className="grid xl:grid-cols-5 gap-5 items-start">
          <div className="xl:col-span-3 space-y-5">
            <section className="card overflow-hidden">
              <SectionTitle hint={`${upcoming.length} agendada(s)`}>Próximas postagens</SectionTitle>
              {!upcoming.length && <div className="text-[13px] text-muted px-4 py-10 text-center flex flex-col items-center gap-2"><CalendarClock size={18} className="text-faint" />Nenhuma postagem agendada.</div>}
              {groups.map(([day, items]) => (
                <div key={day}>
                  <div className="px-4 py-1.5 text-[12px] font-medium text-muted bg-bg2/60 border-b border-line capitalize sticky top-0 backdrop-blur-sm z-[1]">{day}</div>
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
          <div className="xl:col-span-2 space-y-5">
            <section className="card overflow-hidden">
              <SectionTitle hint={`${done.length} vídeo(s) no ar`}>Publicados</SectionTitle>
              <div className="max-h-[70vh] overflow-y-auto">{doneShown.map(p => <Row key={p.id} p={p} sub={when(p.published_at)} />)}{doneMore}
                {!done.length && <div className="text-[13px] text-muted px-4 py-8 text-center">Nada publicado ainda.</div>}</div>
            </section>
            <QuotaCard />
            {channel && <PublishPrefsCard channelId={channel.id} />}
          </div>
        </div>
      )}
      {check && <StudioChecklist pubId={check} onClose={() => setCheck(null)} />}
    </>
  )
}
