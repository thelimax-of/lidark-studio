// Modo História: séries ilustradas com HUD de missão (motion comic) — bíblia da série, personagens, banco de imagens,
// episódios e a cota grátis de imagens do dia (Cloudflare, GPU local, Hugging Face, Pollinations).
import { useEffect, useMemo, useState } from 'react'
import clsx from 'clsx'
import { BookOpen, Clapperboard, Cpu, Image as ImageIcon, Loader2, Play, RefreshCw, Save, Sparkles, Trash2, Users, Wand2 } from 'lucide-react'
import { api, invalidate, mediaUrl, onJob, useApi } from '../api'
import { act, Empty, Field, PageHeader, SectionTitle, Skeleton, Tabs, ago, fmtDur, useChannel } from '../ui'
import { Bar, Callout, StatTile } from './kit'

type Cap = Record<string, any>
type Overview = {
  channels: { id: number; name: string; slug: string; series_title: string; enabled: boolean; share: number; ready: boolean; why: string
    bank: { total: number; by_type: Record<string, number> }; episodes: number
    hero: { id: string; name: string; poses_have: number; poses_want: number }
    open_arc: { title: string; parts: number; max: number } | null }[]
  capacity: Cap; gpu: { owner: string; since: number } | null; conf: Record<string, any>
}
type Asset = { id: string; type: string; char: string; pose: string; tags: string[]; size: [number, number]; source: string; uses: number
  url: string; has_eyes: boolean; disabled?: boolean; created: number }
type Character = { id: string; name: string; role: string; desc: string; voice: string; pitch: string; rate: string; seed: number; eyes?: string }
type Bible = { series_title: string; premise: string; style: string; era: string; palette: string[]; characters: Character[]; poses: string[]
  missions: string[]; locations: string[]; enabled?: boolean; share?: number; hud: Record<string, any>; max_parts?: number
  voices?: Record<string, Voice> }
type Voice = { provider: 'edge' | 'gemini'; voice: string; rate?: string; pitch?: string; style?: string }
const ROLE_NAMES: Record<string, string> = { narrador: 'Narrador', tv: 'TV (âncora)', radio: 'Rádio (locutor)', phone: 'Celular (áudio)',
  comms: 'Rádio de bordo', newsboy: 'Jornaleiro', proclamation: 'Edital (arauto)' }
type Episode = { script_id: number; title: string; part: number; arc: string; mission: string; style: string; beats: number; words: number
  status: string; created_at: string
  video: { id: number; status: string; path: string; thumbnail: string; duration: number; qa?: boolean
    story?: { shots: number; new_images: number; reused: number; widgets: string[]; render_seconds: number } } | null }

type Tab = 'episodios' | 'personagens' | 'banco' | 'biblia' | 'config'
const STORY_JOBS = ['story_episode', 'story_assets', 'story_render', 'story_pregen', 'story_seed']

export default function StoryMode() {
  const { channel } = useChannel()
  const [tab, setTab] = useState<Tab>('episodios')
  const { data: ov, isLoading } = useApi<Overview>('/story/overview', { refetchInterval: 60_000 })
  const [busy, setBusy] = useState(false)
  useEffect(() => onJob(j => {
    if (!STORY_JOBS.includes(j.kind)) return
    setBusy(j.status === 'queued' || j.status === 'running')
    if (['done', 'failed', 'cancelled'].includes(j.status)) { invalidate('/story/') }
  }), [])
  const me = ov?.channels.find(c => c.id === channel?.id)
  const [fmt, setFmt] = useState<'short' | 'long'>('short')
  const gen = () => channel && act(() => api(`/story/${channel.id}/episode`, { body: { format: fmt } }),
    me?.open_arc ? `Gerando a parte ${me.open_arc.parts + 1} de “${me.open_arc.title}”…` : 'Gerando episódio…').then(() => setBusy(true))
  return (
    <div>
      <PageHeader eyebrow="Criar" title="Modo História"
        subtitle="Séries ilustradas com personagem recorrente e HUD de missão (estilo jogo). Fatos reais conferidos, moldura de ficção, imagens grátis: novas quando há cota, banco quando não há."
        actions={<>
          <div className="seg">
            <button data-active={fmt === 'short'} onClick={() => setFmt('short')}>Short</button>
            <button data-active={fmt === 'long'} onClick={() => setFmt('long')}>Longo</button>
          </div>
          <button className="btn btn-primary" disabled={!channel || busy} onClick={gen}>
            {busy ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} />} Gerar episódio
          </button>
        </>} />
      {isLoading || !ov ? <Skeleton className="h-28 mb-4" /> : <QuotaMeter ov={ov} />}
      {me && !me.ready && <Callout tone="warn" className="mb-4">{me.name}: {me.why}. A geração espera a cota da Cloudflare voltar (21:00) — ou configure a GPU local / um token do Hugging Face.</Callout>}
      {me?.open_arc && <Callout className="mb-4">Arco em andamento: <b>{me.open_arc.title}</b> — {me.open_arc.parts} de {me.open_arc.max} partes. O próximo episódio continua daqui.</Callout>}
      <Tabs value={tab} onChange={setTab} items={[
        { key: 'episodios', label: 'Episódios', count: me?.episodes },
        { key: 'personagens', label: 'Personagens' },
        { key: 'banco', label: 'Banco de imagens', count: me?.bank.total },
        { key: 'biblia', label: 'Bíblia da série' },
        { key: 'config', label: 'Fontes de imagem' },
      ]} />
      <div className="mt-4">
        {!channel ? <Empty icon={<BookOpen size={18} />} title="Nenhum canal" /> :
          tab === 'episodios' ? <Episodes cid={channel.id} /> :
          tab === 'personagens' ? <Characters cid={channel.id} /> :
          tab === 'banco' ? <BankGrid cid={channel.id} /> :
          tab === 'biblia' ? <BibleEditor cid={channel.id} /> : <Config ov={ov} />}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------- cota do dia

function QuotaMeter({ ov }: { ov: Overview }) {
  const c = ov.capacity
  const cf = c._cloudflare_day || {}
  const used = Number(cf.neurons_used || 0)
  const resets = cf.resets_at ? new Date(cf.resets_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }) : '21:00'
  const loc = c.local || {}
  const hf = c.hf_space || {}
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4 mb-4">
      <div className="card p-4">
        <div className="stat-label flex items-center gap-2"><Sparkles size={13} /> Cloudflare (grátis)</div>
        <div className="stat-value mt-1.5 leading-none">{cf.exhausted ? 'esgotada' : `${(10000 - used).toLocaleString('pt-BR')}`}<span className="text-[12px] text-faint font-normal"> {cf.exhausted ? '' : 'neurônios'}</span></div>
        <Bar value={cf.exhausted ? 100 : used / 100} tone={cf.exhausted ? 'bad' : used > 8000 ? 'warn' : undefined} className="mt-2.5" />
        <div className="text-[11.5px] text-faint mt-2">lucid ≈ {c.cf_lucid?.images_left ?? 0} · schnell ≈ {c.cf_schnell?.images_left ?? 0} imagens · zera às {resets}</div>
      </div>
      <StatTile icon={<Cpu size={13} />} label="GPU local" value={loc.available ? `${loc.images_per_hour || '?'}/h` : loc.configured ? 'offline' : 'não configurada'}
        tone={loc.available ? 'ok' : undefined} sub={loc.available ? `${loc.images_today} imagens hoje · ${Math.round((loc.seconds_today || 0) / 60)} min de GPU` : 'Volume: SD local no RTX 3050'} />
      <StatTile icon={<ImageIcon size={13} />} label="Hugging Face" value={hf.available ? 'disponível' : 'bloqueado'} tone={hf.available ? 'ok' : 'warn'}
        sub={`${hf.token ? 'com token' : 'anônimo (~3/dia)'} · ${hf.images_today ?? 0} hoje`} />
      <StatTile icon={<Wand2 size={13} />} label="Imagens novas possíveis hoje" value={c._today_new_images ?? 0}
        sub={ov.gpu ? `GPU ocupada: ${ov.gpu.owner}` : 'GPU livre'} />
    </div>
  )
}

// ---------------------------------------------------------------- episódios

function Episodes({ cid }: { cid: number }) {
  const { data, isLoading } = useApi<{ episodes: Episode[]; jobs: any[] }>(`/story/${cid}/episodes`)
  const last = data?.episodes.find(e => e.video?.status && ['ready', 'review', 'published'].includes(e.video.status))
  if (isLoading || !data) return <Skeleton className="h-60" />
  return (
    <div className="grid gap-4 xl:grid-cols-[1fr_340px] items-start">
      <section className="card overflow-hidden">
        <SectionTitle hint="Cada episódio: roteiro (1 pedido à IA) → checagem de fatos → imagens → render.">Episódios</SectionTitle>
        {data.jobs.length > 0 && <div className="px-4 pt-3 space-y-1.5">
          {data.jobs.map(j => <div key={j.id} className="text-[12.5px] flex items-center gap-2 text-muted">
            <Loader2 size={12} className="animate-spin" /> {j.title} — {j.stage || j.status} {j.progress ? `${Math.round(j.progress * 100)}%` : ''}</div>)}
        </div>}
        {!data.episodes.length ? <div className="p-6 text-[13px] text-muted">Nenhum episódio ainda — clique em “Gerar episódio”.</div> :
          <div className="divide-y divide-line">
            {data.episodes.map(e => (
              <div key={e.script_id} className="flex gap-3 p-3 items-center">
                {e.video?.thumbnail ? <img src={mediaUrl(e.video.thumbnail)} alt="" className="w-12 aspect-[9/16] object-cover rounded-md bg-panel2" />
                  : <div className="w-12 aspect-[9/16] rounded-md bg-panel2 grid place-items-center text-faint"><Clapperboard size={14} /></div>}
                <div className="min-w-0 flex-1">
                  <div className="text-[13.5px] font-medium truncate">{e.title}</div>
                  <div className="text-[12px] text-muted truncate">Parte {e.part ?? 1} · {e.arc || 'arco'} · missão {e.mission} · {e.style} · {e.words} palavras</div>
                  {e.video?.story && <div className="text-[11.5px] text-faint">{e.video.story.shots} tomadas · {e.video.story.new_images} imagens novas · {e.video.story.reused} do banco · render {Math.round(e.video.story.render_seconds)}s</div>}
                </div>
                <div className="text-right shrink-0">
                  <span className={clsx('badge', e.video?.status === 'ready' && 'badge-ok', e.video?.status === 'failed' && 'badge-bad')}>
                    {e.video ? e.video.status : e.status}</span>
                  <div className="text-[11px] text-faint mt-1">{e.video ? fmtDur(e.video.duration) : ago(e.created_at)}</div>
                </div>
                <button className="btn btn-sm btn-ghost btn-icon" title="Renderizar de novo" onClick={() => act(() => api(`/story/${cid}/episodes/${e.script_id}/render`, { method: 'POST' }), 'Render na fila')}>
                  <RefreshCw size={14} /></button>
              </div>
            ))}
          </div>}
      </section>
      <section className="card overflow-hidden xl:sticky xl:top-4">
        <SectionTitle>Último render</SectionTitle>
        {last?.video ? <div className="p-3">
          <video src={mediaUrl(last.video.path)} poster={mediaUrl(last.video.thumbnail)} controls className="w-full aspect-[9/16] rounded-lg bg-black" />
          <div className="text-[12.5px] mt-2 font-medium">{last.title}</div>
        </div> : <div className="p-6 text-[13px] text-muted flex items-center gap-2"><Play size={14} /> Nada renderizado ainda.</div>}
      </section>
    </div>
  )
}

// ---------------------------------------------------------------- personagens (folhas de pose)

function Characters({ cid }: { cid: number }) {
  const { data: bible } = useApi<Bible>(`/story/${cid}/bible`)
  const { data: bank } = useApi<{ items: Asset[] }>(`/story/${cid}/bank?type=pose`)
  const { data: por } = useApi<{ items: Asset[] }>(`/story/${cid}/bank?type=portrait`)
  if (!bible || !bank) return <Skeleton className="h-60" />
  const sheet = () => act(() => api(`/story/${cid}/sheet`, { body: { max: 24 } }), 'Gerando o que falta (quando houver cota)')
  return (
    <div className="space-y-4">
      {bible.characters.map(c => {
        const poses = bank.items.filter(a => a.char === c.id && !a.disabled)
        const missing = bible.poses.filter(p => !poses.some(a => a.pose === p))
        const face = por?.items.find(a => a.char === c.id)
        return (
          <section key={c.id} className="card overflow-hidden">
            <SectionTitle hint={c.desc} action={<button className="btn btn-sm" onClick={sheet}><Wand2 size={14} /> Gerar poses que faltam</button>}>
              <span className="inline-flex items-center gap-2">{face && <img src={face.url} alt="" className="w-7 h-7 rounded-full object-cover bg-panel2" />}{c.name} · {c.role}</span>
            </SectionTitle>
            <div className="grid grid-cols-3 sm:grid-cols-5 lg:grid-cols-8 gap-3 p-4">
              {poses.map(a => <AssetCard key={a.id} cid={cid} a={a} label={a.pose} />)}
              {missing.map(p => <div key={p} className="rounded-lg border border-dashed border-line2 aspect-[3/5] grid place-items-center text-[11.5px] text-faint text-center p-2">{p}<br />(falta)</div>)}
            </div>
            <div className="px-4 pb-3 text-[11.5px] text-faint">Voz: {c.voice} {c.pitch} {c.rate} · semente {c.seed} · cada pose é gerada em fundo verde e recortada; pose sem olhos detectados é refeita.</div>
          </section>
        )
      })}
      {!bible.characters.length && <Empty icon={<Users size={18} />} title="Sem personagens" text="Adicione personagens na Bíblia da série." />}
    </div>
  )
}

function AssetCard({ cid, a, label }: { cid: number; a: Asset; label?: string }) {
  const regen = () => act(() => api(`/story/${cid}/bank/${a.id}/regenerate`, { method: 'POST' }), 'Refazendo quando houver cota').then(() => invalidate(`/story/${cid}/bank`))
  const del = () => confirm('Apagar esta imagem do banco?') && act(() => api(`/story/${cid}/bank/${a.id}`, { method: 'DELETE' })).then(() => invalidate(`/story/${cid}/bank`))
  return (
    <div className={clsx('group relative rounded-lg overflow-hidden border border-line bg-[repeating-conic-gradient(#2a2a2a_0%_25%,#202020_0%_50%)] [background-size:16px_16px]', a.disabled && 'opacity-40')}>
      <img src={a.url} alt="" loading="lazy" className={clsx('w-full object-contain', a.type === 'pose' ? 'aspect-[3/5]' : a.size?.[0] > a.size?.[1] ? 'aspect-video object-cover' : 'aspect-[9/16] object-cover')} />
      <div className="absolute inset-x-0 bottom-0 p-1.5 bg-gradient-to-t from-black/85 to-transparent text-[10.5px] leading-tight">
        <div className="truncate">{label ?? a.tags.slice(0, 3).join(' · ')}</div>
        <div className="text-[#aaa]">{a.uses}× usada{a.has_eyes ? ' · pisca' : ''}</div>
      </div>
      <div className="absolute top-1 right-1 hidden group-hover:flex gap-1">
        <button className="btn btn-sm btn-icon !h-6 !w-6 bg-black/60" title="Refazer" onClick={regen}><RefreshCw size={12} /></button>
        <button className="btn btn-sm btn-icon !h-6 !w-6 bg-black/60 btn-danger" title="Apagar" onClick={del}><Trash2 size={12} /></button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------- banco

function BankGrid({ cid }: { cid: number }) {
  const [type, setType] = useState('scene')
  const { data } = useApi<{ items: Asset[]; stats: { by_type: Record<string, number> } }>(`/story/${cid}/bank?type=${type}`)
  const types = ['scene', 'location', 'insert', 'prop', 'portrait']
  const names: Record<string, string> = { scene: 'Cenas', location: 'Cenários vazios', insert: 'Detalhes', prop: 'Objetos', portrait: 'Retratos' }
  return (
    <section className="card overflow-hidden">
      <SectionTitle hint="O banco guarda a identidade da série e cobre os dias sem cota; com cota, cada episódio ganha imagens novas."
        action={<div className="seg">{types.map(t => <button key={t} data-active={type === t} onClick={() => setType(t)}>{names[t]} {data?.stats.by_type[t] ? `(${data.stats.by_type[t]})` : ''}</button>)}</div>}>
        Banco de imagens</SectionTitle>
      {!data ? <Skeleton className="h-60 m-4" /> : !data.items.length ? <div className="p-6 text-[13px] text-muted">Nada aqui ainda.</div> :
        <div className="grid grid-cols-3 sm:grid-cols-5 lg:grid-cols-8 gap-3 p-4">
          {data.items.map(a => <AssetCard key={a.id} cid={cid} a={a} />)}
        </div>}
    </section>
  )
}

// ---------------------------------------------------------------- bíblia

function BibleEditor({ cid }: { cid: number }) {
  const { data } = useApi<Bible>(`/story/${cid}/bible`)
  const [b, setB] = useState<Bible | null>(null)
  useEffect(() => { if (data) setB(structuredClone(data)) }, [data])
  const dirty = useMemo(() => JSON.stringify(b) !== JSON.stringify(data), [b, data])
  if (!b) return <Skeleton className="h-96" />
  const set = (k: keyof Bible, v: any) => setB({ ...b, [k]: v })
  const setChar = (i: number, k: keyof Character, v: any) => set('characters', b.characters.map((c, j) => j === i ? { ...c, [k]: v } : c))
  const save = () => act(() => api(`/story/${cid}/bible`, { method: 'PUT', body: b }), 'Bíblia salva').then(() => invalidate(`/story/${cid}`))
  return (
    <section className="card overflow-hidden">
      <SectionTitle hint="Mudar a descrição de um personagem muda o visual dele nas próximas poses geradas (as antigas continuam no banco)."
        action={<button className="btn btn-sm btn-primary" disabled={!dirty} onClick={save}><Save size={14} /> Salvar</button>}>Bíblia da série</SectionTitle>
      <div className="p-4 grid gap-4 lg:grid-cols-2">
        <Field label="Nome da série"><input className="input" value={b.series_title} onChange={e => set('series_title', e.target.value)} /></Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Ativo no piloto automático"><select className="input" value={b.enabled === false ? 'n' : 's'} onChange={e => set('enabled', e.target.value === 's')}><option value="s">Sim</option><option value="n">Não</option></select></Field>
          <Field label="Fração dos vídeos" hint="Freio: nunca mais de 1/3 dos últimos 10"><input className="input" type="number" min={0} max={0.34} step={0.05} value={b.share ?? 0.25} onChange={e => set('share', Number(e.target.value))} /></Field>
        </div>
        <Field label="Premissa"><textarea className="input min-h-[90px]" value={b.premise} onChange={e => set('premise', e.target.value)} /></Field>
        <Field label="Estilo de arte (prompt fixo, em inglês)"><textarea className="input min-h-[90px]" value={b.style} onChange={e => set('style', e.target.value)} /></Field>
        <Field label="Missões de exemplo (vírgula)"><input className="input" value={b.missions.join(', ')} onChange={e => set('missions', e.target.value.split(',').map(s => s.trim()).filter(Boolean))} /></Field>
        <Field label="Poses do banco (vírgula)"><input className="input" value={b.poses.join(', ')} onChange={e => set('poses', e.target.value.split(',').map(s => s.trim()).filter(Boolean))} /></Field>
        <Field label="Cenários recorrentes (um por linha, em inglês)"><textarea className="input min-h-[90px]" value={b.locations.join('\n')} onChange={e => set('locations', e.target.value.split('\n').map(s => s.trim()).filter(Boolean))} /></Field>
        <Field label="Cor de destaque do HUD"><input className="input" value={b.hud?.accent ?? ''} onChange={e => set('hud', { ...b.hud, accent: e.target.value })} /></Field>
      </div>
      <div className="px-4 pb-4">
        <div className="card-title mb-1">Vozes por papel</div>
        <div className="text-[12px] text-muted mb-2">O provedor vale para o episódio inteiro de cada papel: se a cota do Gemini não cobrir todas as falas do papel, ele vai todo em edge (nunca mistura). Aparelhos recebem filtro de som (TV, rádio, celular, rua).</div>
        <div className="space-y-2">
          {[...Object.keys(ROLE_NAMES).filter(r => r === 'narrador' || (b.hud?.devices ?? []).includes(r)), ...b.characters.map(c => c.id)].map(role => {
            const v: Voice = b.voices?.[role] ?? { provider: 'edge', voice: b.characters.find(c => c.id === role)?.voice ?? '', rate: b.characters.find(c => c.id === role)?.rate, pitch: b.characters.find(c => c.id === role)?.pitch }
            const setV = (k: keyof Voice, val: string) => set('voices', { ...(b.voices ?? {}), [role]: { ...v, [k]: val } })
            return (
              <div key={role} className="grid gap-2 md:grid-cols-[140px_100px_1fr_80px_80px_1.4fr] items-center">
                <div className="text-[13px]">{ROLE_NAMES[role] ?? b.characters.find(c => c.id === role)?.name ?? role}</div>
                <select className="input" value={v.provider} onChange={e => setV('provider', e.target.value)}><option value="edge">edge</option><option value="gemini">gemini</option></select>
                <input className="input" value={v.voice} placeholder={v.provider === 'gemini' ? 'Charon, Puck…' : 'pt-BR-AntonioNeural'} onChange={e => setV('voice', e.target.value)} />
                <input className="input" value={v.rate ?? ''} placeholder="-4%" onChange={e => setV('rate', e.target.value)} />
                <input className="input" value={v.pitch ?? ''} placeholder="-8Hz" onChange={e => setV('pitch', e.target.value)} />
                <input className="input" value={v.style ?? ''} placeholder="direção (Gemini)" onChange={e => setV('style', e.target.value)} />
              </div>)
          })}
        </div>
      </div>
      <div className="px-4 pb-4 space-y-3">
        {b.characters.map((c, i) => (
          <div key={c.id} className="surface p-3 grid gap-3 md:grid-cols-[160px_1fr_220px]">
            <div className="space-y-2">
              <input className="input" value={c.name} onChange={e => setChar(i, 'name', e.target.value)} />
              <input className="input" value={c.role} onChange={e => setChar(i, 'role', e.target.value)} />
              <div className="text-[11px] text-faint">id {c.id} · semente {c.seed}</div>
            </div>
            <textarea className="input min-h-[96px]" value={c.desc} onChange={e => setChar(i, 'desc', e.target.value)} />
            <div className="space-y-2">
              <input className="input" value={c.voice} onChange={e => setChar(i, 'voice', e.target.value)} />
              <div className="grid grid-cols-2 gap-2">
                <input className="input" value={c.pitch} onChange={e => setChar(i, 'pitch', e.target.value)} title="tom (ex.: +12Hz)" />
                <input className="input" value={c.rate} onChange={e => setChar(i, 'rate', e.target.value)} title="velocidade (ex.: +6%)" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

// ---------------------------------------------------------------- fontes de imagem

function Config({ ov }: { ov?: Overview }) {
  const [c, setC] = useState<Record<string, any> | null>(null)
  useEffect(() => { if (ov) setC(structuredClone(ov.conf)) }, [ov])
  if (!c) return <Skeleton className="h-60" />
  const save = () => act(() => api('/story/config', { method: 'PUT', body: c }), 'Configuração salva').then(() => invalidate('/story/overview'))
  const en = c.enabled || {}
  return (
    <section className="card overflow-hidden">
      <SectionTitle hint="Tudo grátis. Folhas de personagem e cenas-herói vão para o lucid (Cloudflare); volume vai para a GPU local e o schnell."
        action={<button className="btn btn-sm btn-primary" onClick={save}><Save size={14} /> Salvar</button>}>Fontes de imagem</SectionTitle>
      <div className="p-4 grid gap-4 lg:grid-cols-2">
        <Field label="GPU local — endereço do worker" hint="POST /generate e GET /capacity (ex.: http://127.0.0.1:8790)"><input className="input" value={c.local_url} onChange={e => setC({ ...c, local_url: e.target.value })} /></Field>
        <Field label="GPU local — imagens por hora (0 = pergunta ao worker)"><input className="input" type="number" value={c.local_images_per_hour} onChange={e => setC({ ...c, local_images_per_hour: Number(e.target.value) })} /></Field>
        <Field label="Token do Hugging Face (opcional)" hint="Aumenta a cota do FLUX.1-schnell no Space"><input className="input" value={c.hf_token} onChange={e => setC({ ...c, hf_token: e.target.value })} /></Field>
        <Field label="Token do Pollinations (opcional, último recurso)"><input className="input" value={c.pollinations_token} onChange={e => setC({ ...c, pollinations_token: e.target.value })} /></Field>
        <Field label="Imagens novas por Short (mín · máx)">
          <div className="grid grid-cols-2 gap-2">
            {[0, 1].map(k => <input key={k} className="input" type="number" value={(c.new_images_short || [12, 16])[k]}
              onChange={e => { const v = [...(c.new_images_short || [12, 16])]; v[k] = Number(e.target.value); setC({ ...c, new_images_short: v }) }} />)}
          </div>
        </Field>
        <Field label="Fontes ligadas">
          <div className="flex flex-wrap gap-3 text-[13px] pt-1">
            {['cf_lucid', 'cf_schnell', 'local', 'hf_space', 'pollinations'].map(k => (
              <label key={k} className="inline-flex items-center gap-1.5">
                <input type="checkbox" checked={en[k] !== false} onChange={e => setC({ ...c, enabled: { ...en, [k]: e.target.checked } })} /> {k}
              </label>))}
          </div>
        </Field>
      </div>
    </section>
  )
}
