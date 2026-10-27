import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { useParams, Link } from 'react-router-dom'
import clsx from 'clsx'
import {
  ArrowLeft, RefreshCw, Sparkles, Save, Undo2, Play, Pause, Users, Eye, PlaySquare, ExternalLink, Wand2,
  Image as ImageIcon, Palette, Mic, Bot, ChevronDown, Plus, X, Loader2, Type, Music, Upload, Trash2, Flame,
} from 'lucide-react'
import { api, invalidate, onJob, useApi, type Channel } from '../api'
import { act, ago, fmtNum, toast } from '../ui'
import { Avatar, ChannelState, connectYoutube } from './Channels'
import CampaignsSection from './Campaigns'

type Ch = Channel & { connected?: boolean }

export default function ChannelDetail() {
  const { id } = useParams()
  const { data } = useApi<Ch>(`/channels/${id}`)
  const { data: list = [] } = useApi<Ch[]>('/channels')
  const [f, setF] = useState<Ch | null>(null)
  const [dirty, setDirty] = useState(false)
  const [previewV, setPreviewV] = useState(Date.now())
  const [previewBusy, setPreviewBusy] = useState(false)
  const connected = list.find(c => String(c.id) === id)?.connected
  useEffect(() => { if (data && !dirty) setF(data) }, [data, dirty])
  useEffect(() => onJob(j => {
    if (String(j.channel_id) === id && j.status === 'done' && ['channel_identity', 'setup_channel'].includes(j.kind)) {
      setDirty(false); invalidate(`/channels`); setPreviewV(Date.now())
    }
  }), [id])
  if (!f) return null

  const set = (p: Partial<Ch>) => { setF({ ...f, ...p }); setDirty(true) }
  const setTheme = (p: Record<string, string>) => set({ theme: { ...f.theme, ...p } })
  const save = async () => {
    const r = await act(() => api(`/channels/${f.id}`, { method: 'PUT', body: f }), 'Canal salvo')
    if (r) { setDirty(false); invalidate('/channels'); refreshPreview() }
  }
  const refreshPreview = async () => {
    setPreviewBusy(true)
    await act(() => api(`/channels/${f.id}/preview`, { body: {} }))
    setPreviewV(Date.now()); setPreviewBusy(false)
  }
  const ai = (parts: string, msg: string) => act(() => api(`/channels/${f.id}/identity`, { body: { parts } }), msg)

  return (
    <div className="pb-24">
      <Link to="/canais" className="text-sm text-muted hover:text-text flex items-center gap-1 mb-4"><ArrowLeft size={15} /> Canais</Link>

      {/* cabeçalho com dados do YouTube */}
      <div className="card overflow-hidden mb-6">
        <div className="h-40 relative" style={{
          background: f.banner_url ? `center/cover url(${f.banner_url})` : `linear-gradient(135deg, ${f.theme?.bg_center}, ${f.theme?.bg_edge})`,
        }}><div className="absolute inset-0 bg-gradient-to-t from-panel via-panel/30 to-transparent" /></div>
        <div className="px-6 pb-5 -mt-12 relative flex flex-wrap items-end gap-4">
          <Avatar c={f} size={96} />
          <div className="flex-1 min-w-60 pb-1">
            <h1 className="text-[22px] font-semibold">{f.name}</h1>
            <div className="text-muted text-sm flex items-center gap-3 flex-wrap">
              <span>{f.handle || 'sem @'}</span>
              {f.synced_at && <span>· sincronizado há {ago(f.synced_at)}</span>}
            </div>
          </div>
          <div className="flex items-center gap-5 text-sm pb-1">
            <Stat icon={<Users size={15} />} v={fmtNum(f.stats?.subscribers ?? 0)} l="inscritos" />
            <Stat icon={<Eye size={15} />} v={fmtNum(f.stats?.views ?? 0)} l="views" />
            <Stat icon={<PlaySquare size={15} />} v={String(f.stats?.videos ?? 0)} l="vídeos" />
          </div>
          <div className="flex gap-2 pb-1">
            <ChannelState c={{ ...f, connected }} />
            {connected && <button className="btn" onClick={() => act(() => api(`/channels/${f.id}/sync`, { body: {} }), 'Sincronizando com o YouTube…')}><RefreshCw size={15} /> Sincronizar</button>}
            {f.handle && <a className="btn" href={`https://youtube.com/${f.handle}`} target="_blank" rel="noreferrer"><ExternalLink size={15} /></a>}
          </div>
        </div>
        {!connected && (
          <div className="mx-6 mb-5 p-3 rounded-lg border border-warn/30 bg-warn/5 text-sm flex items-center gap-3">
            <span className="flex-1">Este canal ainda não está conectado ao YouTube. Conecte para puxar dados, vídeos, métricas e publicar.</span>
            <button className="btn btn-primary" onClick={() => connectYoutube(f.id)}>Conectar com Google</button>
          </div>
        )}
      </div>

      <div className="grid xl:grid-cols-[1fr_360px] gap-6 items-start">
        <div className="space-y-6">
          <Section icon={<Bot size={18} />} title="Sobre o conteúdo" subtitle="A IA usa isso em toda pauta e roteiro."
            action={<button className="btn" onClick={() => ai('text', 'IA analisando o canal…')}><Sparkles size={15} /> Sugerir com IA</button>}>
            <div className="grid md:grid-cols-3 gap-3">
              <In label="Nicho" v={f.niche} on={v => set({ niche: v })} ph="ex.: mistérios do espaço" />
              <In label="Público" v={f.audience} on={v => set({ audience: v })} ph="ex.: jovens curiosos 16-30" />
              <In label="Tom" v={f.tone} on={v => set({ tone: v })} ph="ex.: intrigante e rápido" />
            </div>
            <div className="flex flex-wrap gap-2 mt-4">
              {[['short', 'Shorts verticais'], ['long', 'Vídeos longos']].map(([k, l]) => (
                <Toggle key={k} on={f.formats.includes(k)} label={l} onClick={() => set({ formats: f.formats.includes(k) ? f.formats.filter(x => x !== k) : [...f.formats, k] })} />
              ))}
              <span className="text-sm text-muted self-center ml-2">Short com</span>
              {[60, 65, 75].map(s => <Toggle key={s} on={f.short_seconds === s} label={`${s}s`} onClick={() => set({ short_seconds: s })} />)}
              <span className="text-sm text-muted self-center ml-2">Longo com</span>
              {[5, 8, 12].map(m => <Toggle key={m} on={f.long_minutes === m} label={`${m} min`} onClick={() => set({ long_minutes: m })} />)}
            </div>
          </Section>

          <Section icon={<Palette size={18} />} title="Visual do vídeo" subtitle="Modelo, mascote, cores e fontes. Tudo próprio deste canal."
            action={<button className="btn" onClick={() => ai('visual', 'IA criando um visual novo…')}><Wand2 size={15} /> Novo visual com IA</button>}>
            <Label>Modelo</Label>
            <div className="grid sm:grid-cols-3 gap-3 mb-5">
              <Choice on={f.template === 'livre' && !((f.templates?.length ?? 0) > 1)} onClick={() => set({ template: 'livre', templates: [] })} title="Palco livre"
                text="Sem cartão. Fotos em tela cheia e polaroides, mascote andando pela tela." />
              <Choice on={f.template === 'ouro' && !((f.templates?.length ?? 0) > 1)} onClick={() => set({ template: 'ouro', templates: [] })} title="Cartão"
                text="Conteúdo dentro de um cartão central, mascote fixo embaixo. Mais organizado." />
              <Choice on={(f.templates?.length ?? 0) > 1} onClick={() => set({ templates: ['livre', 'ouro'] })} title="Alternar os dois"
                text="Mais variedade: cada vídeo novo usa o modelo que não foi usado no anterior." />
            </div>
            <Label>Mascote</Label>
            <MascotPicker theme={f.theme} onChange={setTheme} />
            <div className="grid md:grid-cols-2 gap-5 mt-5">
              <div>
                <Label>Cores</Label>
                <div className="grid grid-cols-5 gap-2">
                  {[['bg_center', 'Fundo'], ['bg_edge', 'Fundo 2'], ['gold', 'Destaque'], ['caption_hi', 'Legenda'], ['card', 'Papel']].map(([k, l]) => (
                    <label key={k} className="text-[11px] text-muted flex flex-col items-center gap-1 cursor-pointer">
                      <span className="w-full h-10 rounded-lg border border-line relative overflow-hidden" style={{ background: f.theme?.[k] }}>
                        <input type="color" className="absolute inset-0 opacity-0 cursor-pointer" value={f.theme?.[k] ?? '#000000'} onChange={e => setTheme({ [k]: e.target.value })} />
                      </span>{l}
                    </label>
                  ))}
                </div>
              </div>
              <FontPicker theme={f.theme} onChange={setTheme} />
            </div>
          </Section>

          <Section icon={<Mic size={18} />} title="Voz" subtitle="Ouça e escolha. Grátis e ilimitada.">
            <VoicePicker f={f} set={set} />
          </Section>

          <Section icon={<Flame size={18} />} title="Radar de tendências" subtitle="Todo dia às 7h o sistema vasculha buscas, vídeos virais e concorrentes e cria pautas do momento."
            action={<button className="btn" onClick={() => act(() => api(`/channels/${f.id}/radar`, { body: {} }), 'Radar rodando — veja em Pautas')}><Flame size={15} /> Rodar agora</button>}>
            <Label>Palavras-chave do nicho</Label>
            <ChipList items={f.radar?.keywords ?? []} placeholder="nova palavra-chave" onChange={v => set({ radar: { ...(f.radar ?? {}), keywords: v } })} />
            <div className="mt-4"><Label>Concorrentes monitorados</Label></div>
            <ChipList items={f.radar?.competitors ?? []} placeholder="@canal ou link do canal"
              label={c => f.radar?.competitor_names?.[c] ?? c.replace('https://www.youtube.com/', '')}
              onChange={v => set({ radar: { ...(f.radar ?? {}), competitors: v } })} />
            <p className="text-xs text-muted mt-2">Se ficar vazio, o radar descobre sozinho os canais que mais performam no nicho.</p>
          </Section>

          <CampaignsSection channelId={f.id} />

          <Section icon={<Music size={18} />} title="Trilhas sonoras" subtitle="Músicas deste canal (sem exigência de crédito). Sem trilhas, o sistema gera uma trilha ambiente própria.">
            <MusicLibrary channelId={f.id} />
          </Section>

          <Section icon={<ImageIcon size={18} />} title="Imagens">
            <div className="grid sm:grid-cols-3 gap-3">
              <Choice on={f.visual_mode === 'real'} onClick={() => set({ visual_mode: 'real' })} title="Fotos reais" text="Fotos da internet (Wikimedia, acervos), verificadas pela IA." />
              <Choice on={f.visual_mode === 'mixed'} onClick={() => set({ visual_mode: 'mixed' })} title="Misto" text="Foto real quando existir; IA cria o que não tem registro." />
              <Choice on={f.visual_mode === 'ai'} onClick={() => set({ visual_mode: 'ai' })} title="100% IA" text="Tudo gerado por IA, com controle de qualidade." />
            </div>
            <div className="flex flex-wrap items-center gap-2 mt-4">
              <Toggle on={!!f.footage} label="Filmagens reais (NASA/Commons)" onClick={() => set({ footage: !f.footage })} />
              <Toggle on={!!f.image_credit_ok} label="Aceitar fotos com crédito (CC BY)" onClick={() => set({ image_credit_ok: !f.image_credit_ok })} />
              <span className="text-sm text-muted ml-2">Categoria no YouTube</span>
              <select className="input !w-auto !py-1" value={f.yt_category ?? '27'} onChange={e => set({ yt_category: e.target.value })}>
                {[['27', 'Educação'], ['17', 'Esportes'], ['28', 'Ciência e tecnologia'], ['24', 'Entretenimento'], ['22', 'Pessoas e blogs'], ['19', 'Viagens e eventos'], ['25', 'Notícias e política']].map(([v, l]) =>
                  <option key={v} value={v}>{l}</option>)}
              </select>
            </div>
            <p className="text-xs text-muted mt-2">Filmagem entra quando a foto encontrada é fraca; sem filmagem boa, a cena vira gráfico animado. Fotos com crédito ganham a atribuição na descrição do vídeo.</p>
            {f.thumbs_blocked && (
              <div className="mt-3 p-3 rounded-lg border border-warn/30 bg-warn/5 text-sm">
                O YouTube recusou a miniatura deste canal (falta verificar por telefone em youtube.com/verify). Até lá, os vídeos longos saem com a capa no primeiro segundo.
              </div>
            )}
          </Section>

          <Section icon={<Bot size={18} />} title="Piloto automático" subtitle="Produz e agenda sozinho nos horários escolhidos.">
            <div className="flex items-center gap-3 mb-4">
              <Toggle on={f.auto_pilot} label={f.auto_pilot ? 'Ligado' : 'Desligado'} onClick={() => set({ auto_pilot: !f.auto_pilot })} />
              <span className="text-sm text-muted">Só produz pautas com nota ≥</span>
              <input type="range" min={50} max={95} step={5} value={f.min_score_to_produce} onChange={e => set({ min_score_to_produce: Number(e.target.value) })} />
              <span className="font-semibold w-8">{f.min_score_to_produce}</span>
            </div>
            <Label>Horários de postagem</Label>
            <TimeChips slots={f.posting_slots} onChange={v => set({ posting_slots: v })} />
          </Section>

          <details className="card group">
            <summary className="px-5 py-4 cursor-pointer flex items-center gap-2 font-semibold list-none">
              <ChevronDown size={18} className="transition group-open:rotate-180" /> Avançado
              <span className="text-sm text-muted font-normal">guia editorial, textos da marca, música</span>
            </summary>
            <div className="px-5 pb-5 grid md:grid-cols-2 gap-4">
              <div className="md:col-span-2"><Label>Guia editorial</Label>
                <textarea className="input min-h-40 font-mono text-xs" value={f.editorial_guide} onChange={e => set({ editorial_guide: e.target.value })} /></div>
              <In label="Chamada final (CTA)" v={f.cta} on={v => set({ cta: v })} />
              <In label="Hashtags padrão" v={f.default_hashtags.join(' ')} on={v => set({ default_hashtags: v.split(/\s+/).filter(Boolean) })} />
              <In label="Slogan (tela final)" v={f.theme?.slogan ?? ''} on={v => setTheme({ slogan: v })} />
              <In label="Título da tela final" v={f.theme?.outro_title ?? ''} on={v => setTheme({ outro_title: v })} />
              <In label="Rótulo das etapas" v={f.theme?.step_label ?? ''} on={v => setTheme({ step_label: v })} ph="PASSO, FATO, PISTA…" />
              <In label="Letra do logo" v={f.theme?.logo_letter ?? ''} on={v => setTheme({ logo_letter: v.slice(0, 1).toUpperCase() })} />
              <div className="md:col-span-2"><In label="Estilo das imagens de IA (inglês)" v={f.image_style} on={v => set({ image_style: v })} /></div>
              <In label="Estilo da música" v={f.music_mood} on={v => set({ music_mood: v })} />
              <div><Label>Volume da música</Label>
                <input type="range" min={0} max={0.3} step={0.01} className="w-full" value={f.music_volume} onChange={e => set({ music_volume: Number(e.target.value) })} /></div>
            </div>
          </details>
        </div>

        {/* prévia */}
        <div className="card p-4 xl:sticky xl:top-6">
          <div className="flex items-center justify-between mb-3">
            <div className="font-semibold">Prévia do vídeo</div>
            <button className="btn !py-1" disabled={previewBusy} onClick={async () => { if (dirty) await save(); else refreshPreview() }}>
              {previewBusy ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />} Atualizar</button>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {['preview_a', 'preview_b'].map(n => (
              <img key={n} src={`/media/${f.slug}/${n}.jpg?v=${previewV}`} className="rounded-lg border border-line w-full aspect-[9/16] object-cover bg-black"
                onError={e => { (e.target as HTMLImageElement).style.opacity = '0.15' }} alt="" />
            ))}
          </div>
          <p className="text-xs text-muted mt-3">A prévia usa o banner do canal como imagem de exemplo. Salve as mudanças para atualizar.</p>
          <BrandKit channelId={f.id} beforeRun={dirty ? save : undefined} />
        </div>
      </div>

      {dirty && (
        <div className="fixed bottom-5 left-1/2 -translate-x-1/2 z-30 card px-4 py-3 flex items-center gap-3 shadow-[0_16px_40px_-12px_#000c] border-line2! ">
          <span className="text-sm">Alterações não salvas</span>
          <button className="btn" onClick={() => { setDirty(false); setF(data!) }}><Undo2 size={15} /> Descartar</button>
          <button className="btn btn-primary" onClick={save}><Save size={15} /> Salvar</button>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------- peças

function Section({ icon, title, subtitle, action, children }: { icon: ReactNode; title: string; subtitle?: string; action?: ReactNode; children: ReactNode }) {
  return (
    <section className="card p-5">
      <div className="flex items-start justify-between gap-3 mb-4">
        <div className="flex gap-3">
          <div className="w-9 h-9 rounded-lg bg-panel2 border border-line2 text-muted grid place-items-center shrink-0">{icon}</div>
          <div><h3 className="font-semibold">{title}</h3>{subtitle && <p className="text-sm text-muted">{subtitle}</p>}</div>
        </div>
        {action}
      </div>
      {children}
    </section>
  )
}

const Label = ({ children }: { children: ReactNode }) => <div className="label">{children}</div>
const Stat = ({ icon, v, l }: { icon: ReactNode; v: string; l: string }) => (
  <div className="text-center"><div className="flex items-center gap-1.5 font-bold text-base">{icon}{v}</div><div className="text-[11px] text-muted">{l}</div></div>
)

function In({ label, v, on, ph }: { label: string; v: string; on: (v: string) => void; ph?: string }) {
  return <label className="block"><span className="label">{label}</span><input className="input" value={v ?? ''} placeholder={ph} onChange={e => on(e.target.value)} /></label>
}

function Toggle({ on, label, onClick }: { on: boolean; label: string; onClick: () => void }) {
  return <button onClick={onClick} className={clsx('px-3 py-1.5 rounded-full text-sm border transition', on ? 'bg-white/[0.08] border-text/50 text-text font-medium' : 'border-line text-muted hover:text-text')}>{label}</button>
}

function Choice({ on, onClick, title, text }: { on: boolean; onClick: () => void; title: string; text: string }) {
  return (
    <button onClick={onClick} className={clsx('text-left p-4 rounded-lg border transition', on ? 'border-text/60 bg-white/[0.05]' : 'border-line bg-panel2 hover:border-line2')}>
      <div className="flex items-center gap-2 font-semibold"><span className={clsx('w-4 h-4 rounded-full border-2', on ? 'border-text bg-text' : 'border-muted')} />{title}</div>
      <div className="text-sm text-muted mt-1">{text}</div>
    </button>
  )
}

function MascotPicker({ theme, onChange }: { theme: Record<string, string>; onChange: (p: Record<string, string>) => void }) {
  const { data = [] } = useApi<{ id: string; label: string; colors: [string, string] }[]>('/mascots')
  const cur = theme?.mascot ?? 'clock'
  const bg = (theme?.bg_center ?? '#16473a').replace('#', '')
  const q = (m: string) => {
    const c = m === cur ? (theme?.mascot_color ?? '') : ''
    const a = m === cur ? (theme?.mascot_accent ?? '') : ''
    return `/api/mascots/${m}.png?bg=${bg}${c ? `&color=${c.replace('#', '')}` : ''}${a ? `&accent=${a.replace('#', '')}` : ''}`
  }
  return (
    <>
      <div className="grid grid-cols-4 sm:grid-cols-6 lg:grid-cols-11 gap-2">
        {data.map(m => (
          <button key={m.id} title={m.label} onClick={() => onChange({ mascot: m.id, mascot_color: m.id === cur ? theme.mascot_color : '', mascot_accent: m.id === cur ? theme.mascot_accent : '' })}
            className={clsx('rounded-lg overflow-hidden border-2 transition aspect-square', cur === m.id ? 'border-text' : 'border-transparent opacity-70 hover:opacity-100')}>
            {m.id === 'none' ? <div className="w-full h-full grid place-items-center bg-panel2 text-muted"><X /></div>
              : <img src={q(m.id)} className="w-full h-full object-cover" alt={m.label} />}
          </button>
        ))}
      </div>
      {cur !== 'none' && (
        <div className="flex items-center gap-4 mt-3 text-sm">
          <span className="text-muted">{data.find(m => m.id === cur)?.label}</span>
          {cur !== 'clock' && ['mascot_color', 'mascot_accent'].map((k, i) => (
            <label key={k} className="flex items-center gap-2 text-muted cursor-pointer">{i ? 'Detalhe' : 'Cor'}
              <span className="w-8 h-6 rounded border border-line relative overflow-hidden" style={{ background: theme?.[k] || data.find(m => m.id === cur)?.colors[i] }}>
                <input type="color" className="absolute inset-0 opacity-0 cursor-pointer" value={theme?.[k] || data.find(m => m.id === cur)?.colors[i] || '#ffffff'} onChange={e => onChange({ [k]: e.target.value })} />
              </span>
            </label>
          ))}
        </div>
      )}
    </>
  )
}

function useFontFaces(files: string[]) {
  useEffect(() => {
    const id = 'lk-fonts'
    if (document.getElementById(id) || !files.length) return
    const st = document.createElement('style')
    st.id = id
    st.textContent = files.map(f => `@font-face{font-family:"lk-${f}";src:url(/fonts/${f});font-weight:100 900}`).join('\n')
    document.head.appendChild(st)
  }, [files])
}

function FontPicker({ theme, onChange }: { theme: Record<string, string>; onChange: (p: Record<string, string>) => void }) {
  const { data } = useApi<{ title: { file: string; label: string }[]; caption: string[] }>('/fonts')
  const files = useMemo(() => [...(data?.title ?? []).map(t => t.file), ...(data?.caption ?? [])], [data])
  useFontFaces(files)
  const cur = theme?.font_title ?? 'Cinzel.ttf'
  return (
    <div>
      <div className="label flex items-center gap-1"><Type size={12} /> Fonte dos títulos</div>
      <div className="grid grid-cols-2 gap-2 max-h-44 overflow-y-auto pr-1">
        {(data?.title ?? []).map(t => (
          <button key={t.file} title={t.label} onClick={() => onChange({ font_title: t.file })}
            className={clsx('px-3 py-2 rounded-lg border text-left truncate', cur === t.file ? 'border-text/60 bg-white/[0.05]' : 'border-line bg-panel2 hover:border-line2')}
            style={{ fontFamily: `"lk-${t.file}"`, fontWeight: 800 }}>{t.file.replace(/(-Regular|-ExtraBold)?\.ttf/, '')}</button>
        ))}
      </div>
      <div className="label mt-3">Fonte das legendas</div>
      <div className="flex flex-wrap gap-2">
        {(data?.caption ?? []).map(c => (
          <button key={c} onClick={() => onChange({ font_caption: c })} style={{ fontFamily: `"lk-${c}"`, fontWeight: 800 }}
            className={clsx('px-3 py-1.5 rounded-lg border text-sm', (theme?.font_caption ?? 'FiraSans-ExtraBold.ttf') === c ? 'border-text/60 bg-white/[0.05]' : 'border-line bg-panel2')}>
            {c.replace(/(-ExtraBold)?\.ttf/, '')}</button>
        ))}
      </div>
    </div>
  )
}

function VoicePicker({ f, set }: { f: Ch; set: (p: Partial<Ch>) => void }) {
  const { data: voices = [] } = useApi<{ id: string; label: string }[]>('/voices?provider=edge')
  const br = voices.filter(v => v.id.startsWith('pt-BR'))
  const [playing, setPlaying] = useState<string | null>(null)
  const audio = useRef<HTMLAudioElement | null>(null)
  const play = async (voice: string) => {
    if (playing === voice) { audio.current?.pause(); setPlaying(null); return }
    setPlaying(voice)
    try {
      const r = await api('/voices/preview', { body: { provider: 'edge', voice, rate: f.voice_rate, text: `Você sabia que existe uma história sobre ${f.niche || 'isso'} que quase ninguém conhece? Fica até o final.` } })
      audio.current?.pause()
      audio.current = new Audio(r.url + '?t=' + Date.now())
      audio.current.onended = () => setPlaying(null)
      await audio.current.play()
    } catch (e: any) { toast.err(e.message); setPlaying(null) }
  }
  return (
    <>
      <div className="grid sm:grid-cols-3 gap-3">
        {br.map(v => (
          <div key={v.id} className={clsx('p-3 rounded-lg border flex items-center gap-3 cursor-pointer', f.voice_name === v.id && f.voice_provider === 'edge' ? 'border-text/60 bg-white/[0.05]' : 'border-line bg-panel2')}
            onClick={() => set({ voice_provider: 'edge', voice_name: v.id })}>
            <button className="w-9 h-9 rounded-full bg-text text-bg grid place-items-center shrink-0" onClick={e => { e.stopPropagation(); play(v.id) }}>
              {playing === v.id ? <Pause size={15} /> : <Play size={15} />}</button>
            <div className="text-sm font-semibold">{v.label.replace(/\(pt-BR, /, '(')}</div>
          </div>
        ))}
      </div>
      <div className="flex items-center gap-2 mt-4 text-sm">
        <span className="text-muted mr-1">Velocidade</span>
        {['+0%', '+5%', '+10%', '+15%'].map(r => <Toggle key={r} on={f.voice_rate === r} label={r === '+0%' ? 'Normal' : r} onClick={() => set({ voice_rate: r })} />)}
      </div>
    </>
  )
}

const DAYS = [['', 'Todo dia'], ['seg', 'Seg'], ['ter', 'Ter'], ['qua', 'Qua'], ['qui', 'Qui'], ['sex', 'Sex'], ['sab', 'Sáb'], ['dom', 'Dom']]

function slotLabel(s: string) {
  const p = s.toLowerCase().split(/\s+/)
  const day = DAYS.find(([k]) => k && p.includes(k))?.[1] ?? 'Todo dia'
  const time = p.find(x => x.includes(':')) ?? s
  return `${day} ${time} · ${p.some(x => x.startsWith('long')) ? 'Longo' : 'Short'}`
}

function TimeChips({ slots, onChange }: { slots: string[]; onChange: (v: string[]) => void }) {
  const [t, setT] = useState('18:00')
  const [day, setDay] = useState('')
  const [fmt, setFmt] = useState('short')
  const add = () => {
    const v = [day, t, fmt === 'long' ? 'longo' : ''].filter(Boolean).join(' ')
    if (!slots.includes(v)) onChange([...slots, v].sort())
  }
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {slots.map(s => (
          <span key={s} className={clsx('chip !text-sm !py-1', s.includes('long') ? 'text-violet-300 border-violet-900' : 'text-text')}>
            {slotLabel(s)}<button onClick={() => onChange(slots.filter(x => x !== s))}><X size={13} /></button></span>
        ))}
        {!slots.length && <span className="text-sm text-muted">Nenhum horário definido.</span>}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <select className="input !w-auto !py-1" value={day} onChange={e => setDay(e.target.value)}>
          {DAYS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
        </select>
        <input type="time" className="input !w-28 !py-1" value={t} onChange={e => setT(e.target.value)} />
        <select className="input !w-auto !py-1" value={fmt} onChange={e => setFmt(e.target.value)}>
          <option value="short">Short</option><option value="long">Vídeo longo</option>
        </select>
        <button className="btn !py-1" onClick={add}><Plus size={14} /> Adicionar</button>
      </div>
    </div>
  )
}


type MusicRes = { moods: { key: string; label: string; yt: string }[]; files: { name: string; size: number; mood: string }[] }

function MusicLibrary({ channelId }: { channelId: number }) {
  const { data } = useApi<MusicRes>(`/channels/${channelId}/music`)
  const [busy, setBusy] = useState('')
  const upload = async (files: FileList, mood: string) => {
    setBusy(mood)
    const fd = new FormData()
    Array.from(files).forEach(f => fd.append('files', f))
    try {
      const r = await fetch(`/api/channels/${channelId}/music?mood=${mood}`, { method: 'POST', body: fd })
      const j = await r.json()
      toast.ok(`${j.saved?.length ?? 0} trilha(s) adicionada(s)`)
      invalidate(`/channels/${channelId}/music`)
    } catch (e: any) { toast.err(e.message) }
    setBusy('')
  }
  const files = data?.files ?? []
  return (
    <div className="space-y-3">
      <div className="text-[13px] text-muted leading-relaxed">
        Grátis e sem crédito: <b className="text-text">YouTube Studio → Biblioteca de áudio</b> → filtro <b className="text-text">“Atribuição não obrigatória”</b>,
        depois o clima/gênero indicado em cada grupo. Baixe ~4 músicas por clima e arraste aqui. Cada vídeo usa a trilha do clima da sua estrutura
        (investigação → mistério, contagem → energia...). Sem músicas num clima, o sistema usa outro parecido ou gera uma trilha.
      </div>
      <div className="grid md:grid-cols-2 gap-3">
        {(data?.moods ?? []).map(m => {
          const mine = files.filter(f => f.mood === m.key)
          return (
            <MoodDrop key={m.key} label={m.label} hint={m.yt} busy={busy === m.key} count={mine.length} onFiles={fs => upload(fs, m.key)}>
              {mine.map(f => (
                <div key={f.name} className="flex items-center gap-2 text-[12.5px] py-1">
                  <Music size={12} className="text-faint shrink-0" /><span className="flex-1 truncate">{f.name}</span>
                  <button className="btn btn-sm btn-icon btn-ghost" data-tip="Remover" onClick={() => act(() => api(`/channels/${channelId}/music/${encodeURIComponent(f.name)}?mood=${m.key}`, { method: 'DELETE' })).then(() => invalidate(`/channels/${channelId}/music`))}><Trash2 size={12} /></button>
                </div>
              ))}
            </MoodDrop>
          )
        })}
      </div>
      {files.some(f => !f.mood) && <div className="text-xs text-muted">Músicas antigas sem clima: {files.filter(f => !f.mood).map(f => f.name).join(', ')}</div>}
    </div>
  )
}

function MoodDrop({ label, hint, busy, count, onFiles, children }: { label: string; hint: string; busy: boolean; count: number; onFiles: (f: FileList) => void; children: ReactNode }) {
  const input = useRef<HTMLInputElement>(null)
  return (
    <div className="border border-line rounded-lg p-3" onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault(); if (e.dataTransfer.files.length) onFiles(e.dataTransfer.files) }}>
      <div className="flex items-center gap-2">
        <span className="font-medium text-[13px] flex-1">{label}</span>
        <span className={`badge ${count >= 3 ? 'text-ok' : 'text-muted'}`}><span className="dot" /><span className="num">{count}</span></span>
        <button className="btn btn-sm" onClick={() => input.current?.click()}>{busy ? <Loader2 size={13} className="animate-spin" /> : <Upload size={13} />} Adicionar</button>
        <input ref={input} type="file" multiple accept="audio/*" className="hidden" onChange={e => e.target.files && onFiles(e.target.files)} />
      </div>
      <div className="text-[11.5px] text-faint mt-1">{hint}</div>
      {count > 0 && <div className="mt-2 border-t border-line pt-1">{children}</div>}
    </div>
  )
}

function ChipList({ items, onChange, placeholder, label }: { items: string[]; onChange: (v: string[]) => void; placeholder: string; label?: (s: string) => string }) {
  const [v, setV] = useState('')
  const add = () => { const x = v.trim(); if (x && !items.includes(x)) onChange([...items, x]); setV('') }
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        {items.map(it => (
          <span key={it} className="chip !text-sm !py-1 text-text">{label ? label(it) : it}<button onClick={() => onChange(items.filter(x => x !== it))}><X size={13} /></button></span>
        ))}
        {!items.length && <span className="text-sm text-muted">Nenhum ainda.</span>}
      </div>
      <div className="flex gap-2">
        <input className="input !py-1.5" value={v} placeholder={placeholder} onChange={e => setV(e.target.value)} onKeyDown={e => e.key === 'Enter' && add()} />
        <button className="btn !py-1" onClick={add}><Plus size={14} /> Adicionar</button>
      </div>
    </div>
  )
}

type Kit = { avatar: string; banner: string; watermark: string; sheet: string }

function BrandKit({ channelId, beforeRun }: { channelId: number; beforeRun?: () => Promise<void> }) {
  const [kit, setKit] = useState<Kit | null>(null)
  const [busy, setBusy] = useState(false)
  const run = async () => {
    setBusy(true)
    if (beforeRun) await beforeRun()
    const r = await act(() => api<Kit>(`/channels/${channelId}/brandkit`, { body: {} }))
    if (r) setKit(Object.fromEntries(Object.entries(r).map(([k, v]) => [k, `${v}?v=${Date.now()}`])) as Kit)
    setBusy(false)
  }
  return (
    <div className="border-t border-line mt-4 pt-4">
      <div className="flex items-center justify-between mb-2">
        <div className="font-semibold">Kit de marca</div>
        <button className="btn !py-1" disabled={busy} onClick={run}>
          {busy ? <Loader2 size={14} className="animate-spin" /> : <Wand2 size={14} />} {kit ? 'Gerar de novo' : 'Gerar'}</button>
      </div>
      <p className="text-xs text-muted">Foto de perfil, capa e marca d'água com o mascote e as cores do canal. Envie no YouTube Studio → Personalização.</p>
      {kit && (
        <div className="mt-3 space-y-2">
          <a href={kit.sheet} target="_blank" rel="noreferrer"><img src={kit.sheet} className="rounded-lg border border-line w-full" alt="" /></a>
          <div className="flex flex-wrap gap-2 text-xs">
            {([['avatar', 'Foto de perfil'], ['banner', 'Capa'], ['watermark', "Marca d'água"]] as const).map(([k, l]) => (
              <a key={k} className="btn !py-1" href={kit[k]} download>{l}</a>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
