import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { useParams, Link } from 'react-router-dom'
import clsx from 'clsx'
import {
  ArrowLeft, RefreshCw, Sparkles, Save, Undo2, Play, Pause, Users, Eye, PlaySquare, ExternalLink, Wand2,
  Image as ImageIcon, Palette, Mic, Bot, ChevronDown, Plus, X, Loader2, Type, Music, Upload, Trash2, Flame,
} from 'lucide-react'
import { api, invalidate, onJob, useApi, type Channel } from '../api'
import { act, ago, fmtNum, Skeleton, toast } from '../ui'
import { Callout, IconBox } from './kit'
import { Avatar, ChannelState, connectYoutube } from './Channels'
import CampaignsSection from './Campaigns'
import FocusCard from './FocusMode'

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
  if (!f) return (
    <div aria-busy="true" className="space-y-6">
      <Skeleton className="h-4 w-20" /><Skeleton className="h-64" />
      <div className="grid xl:grid-cols-[1fr_360px] gap-6"><div className="space-y-6"><Skeleton className="h-48" /><Skeleton className="h-72" /></div><Skeleton className="h-96" /></div>
    </div>
  )

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
      <Link to="/canais" className="text-[13px] text-muted hover:text-text inline-flex items-center gap-1 mb-4 transition-colors"><ArrowLeft size={14} /> Canais</Link>

      {/* cabeçalho com dados do YouTube */}
      <div className="card overflow-hidden mb-6">
        <div className="h-44 relative" style={{
          background: f.banner_url ? `center/cover url(${f.banner_url})` : `linear-gradient(135deg, ${f.theme?.bg_center ?? 'var(--elev)'}, ${f.theme?.bg_edge ?? 'var(--bg-2)'})`,
        }}><div className="absolute inset-0 bg-gradient-to-t from-panel via-panel/30 to-transparent" />
          <span className="absolute top-0 left-0 right-0 h-[2px]" style={{ background: f.color || 'var(--accent)' }} /></div>
        <div className="px-6 pb-5 -mt-12 relative flex flex-wrap items-end gap-4">
          <Avatar c={f} size={96} />
          <div className="flex-1 min-w-60 pb-1">
            <h1 className="text-[24px] font-semibold tracking-tight">{f.name}</h1>
            <div className="text-muted text-sm flex items-center gap-3 flex-wrap">
              <span>{f.handle || 'sem @'}</span>
              {f.synced_at && <span>· sincronizado {ago(f.synced_at)}</span>}
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm pb-1">
            <Stat icon={<Users size={15} />} v={fmtNum(f.stats?.subscribers ?? 0)} l="inscritos" />
            <Stat icon={<Eye size={15} />} v={fmtNum(f.stats?.views ?? 0)} l="views" />
            <Stat icon={<PlaySquare size={15} />} v={String(f.stats?.videos ?? 0)} l="vídeos" />
          </div>
          <div className="flex gap-2 pb-1">
            <ChannelState c={{ ...f, connected }} />
            {connected && <button className="btn" onClick={() => act(() => api(`/channels/${f.id}/sync`, { body: {} }), 'Sincronizando com o YouTube…')}><RefreshCw size={15} /> Sincronizar</button>}
            {f.handle && <a className="btn btn-icon" data-tip="Abrir no YouTube" href={`https://youtube.com/${f.handle}`} target="_blank" rel="noreferrer"><ExternalLink size={15} /></a>}
          </div>
        </div>
        {!connected && (
          <div className="mx-6 mb-5"><Callout tone="warn" action={<button className="btn btn-primary" onClick={() => connectYoutube(f.id)}>Conectar com Google</button>}>
            Este canal ainda não está conectado ao YouTube. Conecte para puxar dados, vídeos, métricas e publicar.
          </Callout></div>
        )}
      </div>

      {/* modo foco: quanto o piloto produz aqui + sugestão pelos dados */}
      <div className="mb-6"><FocusCard channelId={f.id} /></div>

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
              {[0, 35, 45, 60].map(s => <Toggle key={s} on={(f.short_seconds || 0) === s} label={s ? `${s}s` : 'Automático (testa faixas)'} onClick={() => set({ short_seconds: s })} />)}
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
                      <span className="w-full h-10 rounded-[var(--r-sm)] border border-line2 relative overflow-hidden shadow-[var(--shadow-sm)] hover:border-line3 transition-colors" style={{ background: f.theme?.[k] }}>
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
            <AudioOptions f={f} set={set} setTheme={setTheme} />
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
              <Callout tone="warn" className="mt-3">
                O YouTube recusou a miniatura deste canal (falta verificar por telefone em youtube.com/verify). Até lá, os vídeos longos saem com a capa no primeiro segundo.
              </Callout>
            )}
          </Section>

          <Section icon={<Bot size={18} />} title="Piloto automático" subtitle="Produz e agenda sozinho nos horários escolhidos.">
            <div className="flex items-center gap-3 mb-4">
              <Toggle on={f.auto_pilot} label={f.auto_pilot ? 'Ligado' : 'Desligado'} onClick={() => set({ auto_pilot: !f.auto_pilot })} />
              <span className="text-sm text-muted">Só produz pautas com nota ≥</span>
              <input type="range" min={50} max={95} step={5} value={f.min_score_to_produce} onChange={e => set({ min_score_to_produce: Number(e.target.value) })} />
              <span className="font-semibold w-8 num text-gradient">{f.min_score_to_produce}</span>
            </div>
            <ScheduleBox f={f} set={set} />
            <div className="flex flex-wrap items-center gap-3 mt-4 pt-4 border-t border-line">
              <Toggle on={!f.seed_comment_off} label="Comentário do canal" onClick={() => set({ seed_comment_off: !f.seed_comment_off })} />
              <span className="text-sm text-muted flex-1 min-w-60">Minutos depois de cada vídeo ir ao ar, o canal deixa um comentário que puxa conversa (pergunta, "A ou B?", próximo tema). Você fixa pela tela Comentários.</span>
            </div>
          </Section>

          <details className="card group">
            <summary className="px-5 py-4 cursor-pointer flex items-center gap-3 font-semibold list-none hover:bg-white/[0.02] rounded-[var(--r-md)] transition-colors">
              <IconBox><ChevronDown size={16} className="transition-transform group-open:rotate-180" /></IconBox> Avançado
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
        <div className="card p-4 xl:sticky xl:top-4">
          <div className="flex items-center justify-between mb-3">
            <div className="font-semibold">Prévia do vídeo</div>
            <button className="btn btn-sm" disabled={previewBusy} onClick={async () => { if (dirty) await save(); else refreshPreview() }}>
              {previewBusy ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />} Atualizar</button>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {['preview_a', 'preview_b'].map(n => (
              <img key={n} src={`/media/${f.slug}/${n}.jpg?v=${previewV}`} className={clsx('rounded-[var(--r-md)] border border-line w-full aspect-[9/16] object-cover bg-black transition-opacity', previewBusy && 'opacity-50')}
                onError={e => { (e.target as HTMLImageElement).style.opacity = '0.15' }} alt="" />
            ))}
          </div>
          <p className="text-xs text-muted mt-3">A prévia usa o banner do canal como imagem de exemplo. Salve as mudanças para atualizar.</p>
          <BrandKit channelId={f.id} beforeRun={dirty ? save : undefined} />
        </div>
      </div>

      {dirty && (
        <div className="fixed bottom-5 left-1/2 -translate-x-1/2 z-30 glass rounded-[var(--r-lg)] border border-line2 shadow-[var(--shadow-lg)] px-4 py-2.5 flex items-center gap-3 animate-pop">
          <span className="w-2 h-2 rounded-full bg-warn" /><span className="text-sm">Alterações não salvas</span>
          <button className="btn btn-sm" onClick={() => { setDirty(false); setF(data!) }}><Undo2 size={14} /> Descartar</button>
          <button className="btn btn-sm btn-primary" onClick={save}><Save size={14} /> Salvar</button>
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
          <IconBox>{icon}</IconBox>
          <div><h3 className="font-semibold">{title}</h3>{subtitle && <p className="text-[13px] text-muted mt-0.5">{subtitle}</p>}</div>
        </div>
        {action}
      </div>
      {children}
    </section>
  )
}

const Label = ({ children }: { children: ReactNode }) => <div className="label">{children}</div>
const Stat = ({ icon, v, l }: { icon: ReactNode; v: string; l: string }) => (
  <div className="surface-2 px-3 py-1.5 text-center min-w-20"><div className="flex items-center justify-center gap-1.5 font-semibold text-[15px] num"><span className="text-faint">{icon}</span>{v}</div><div className="text-[11px] text-muted">{l}</div></div>
)

function In({ label, v, on, ph }: { label: string; v: string; on: (v: string) => void; ph?: string }) {
  return <label className="block"><span className="label">{label}</span><input className="input" value={v ?? ''} placeholder={ph} onChange={e => on(e.target.value)} /></label>
}

function Toggle({ on, label, onClick }: { on: boolean; label: string; onClick: () => void }) {
  return <button onClick={onClick} aria-pressed={on} className={clsx('h-8 px-3 rounded-full text-[13px] border transition-colors inline-flex items-center gap-1.5', on ? 'bg-accent/15 border-accent/50 text-text font-medium' : 'border-line2 text-muted hover:text-text hover:border-line3')}>{on && <span className="w-1.5 h-1.5 rounded-full bg-grad" />}{label}</button>
}

function Choice({ on, onClick, title, text }: { on: boolean; onClick: () => void; title: string; text: string }) {
  return (
    <button onClick={onClick} aria-pressed={on} className={clsx('text-left p-4 rounded-[var(--r-md)] border transition-colors', on ? 'border-accent/55 bg-accent/[0.08] shadow-[0_0_0_3px_rgb(124_92_255/.12)]' : 'border-line bg-panel2 hover:border-line3')}>
      <div className="flex items-center gap-2 font-semibold"><span className={clsx('w-4 h-4 rounded-full border-2 grid place-items-center', on ? 'border-accent' : 'border-line3')}>{on && <span className="w-2 h-2 rounded-full bg-grad" />}</span>{title}</div>
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
            className={clsx('rounded-[var(--r-md)] overflow-hidden border-2 transition aspect-square', cur === m.id ? 'border-accent shadow-[0_0_0_3px_rgb(124_92_255/.18)]' : 'border-transparent opacity-70 hover:opacity-100')}>
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
            className={clsx('px-3 py-2 rounded-[var(--r-sm)] border text-left truncate transition-colors', cur === t.file ? 'border-accent/55 bg-accent/[0.08]' : 'border-line bg-panel2 hover:border-line3')}
            style={{ fontFamily: `"lk-${t.file}"`, fontWeight: 800 }}>{t.file.replace(/(-Regular|-ExtraBold)?\.ttf/, '')}</button>
        ))}
      </div>
      <div className="label mt-3">Fonte das legendas</div>
      <div className="flex flex-wrap gap-2">
        {(data?.caption ?? []).map(c => (
          <button key={c} onClick={() => onChange({ font_caption: c })} style={{ fontFamily: `"lk-${c}"`, fontWeight: 800 }}
            className={clsx('px-3 py-1.5 rounded-[var(--r-sm)] border text-sm transition-colors', (theme?.font_caption ?? 'FiraSans-ExtraBold.ttf') === c ? 'border-accent/55 bg-accent/[0.08]' : 'border-line bg-panel2 hover:border-line3')}>
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
          <div key={v.id} className={clsx('p-3 rounded-[var(--r-md)] border flex items-center gap-3 cursor-pointer transition-colors', f.voice_name === v.id && f.voice_provider === 'edge' ? 'border-accent/55 bg-accent/[0.08]' : 'border-line bg-panel2 hover:border-line3')}
            onClick={() => set({ voice_provider: 'edge', voice_name: v.id })}>
            <button className={clsx('w-9 h-9 rounded-full grid place-items-center shrink-0 transition', playing === v.id ? 'bg-grad text-white' : 'bg-elev border border-line3 text-text hover:bg-grad hover:text-white hover:border-transparent')} onClick={e => { e.stopPropagation(); play(v.id) }}>
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

function AudioOptions({ f, set, setTheme }: { f: Ch; set: (p: Partial<Ch>) => void; setTheme: (p: Record<string, string>) => void }) {
  const th = f.theme ?? {}
  const sfxOn = th.sfx !== 'off'
  const loopOn = th.loop_ok !== 'off'
  const local = f.voice_provider === 'local'
  return (
    <div className="mt-5 pt-4 border-t border-line2 space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Toggle on={sfxOn} label={`Efeitos sonoros: ${sfxOn ? 'ligados' : 'desligados'}`} onClick={() => setTheme({ sfx: sfxOn ? 'off' : 'on' })} />
        <Toggle on={loopOn} label={`Shorts em loop: ${loopOn ? 'permitido' : 'nunca'}`} onClick={() => setTheme({ loop_ok: loopOn ? 'off' : 'on' })} />
      </div>
      <p className="text-xs text-muted">Efeitos: whoosh nos cortes, impacto nas revelações e um “ding” no desfecho, sintetizados aqui mesmo (sem direitos autorais). A quantidade muda a cada vídeo.
        Loop: quando o roteiro pede, o fim do Short emenda no começo (sem tela final) — quem assiste vê de novo sem perceber o corte.</p>
      <div className={clsx('p-3 rounded-lg border', local ? 'border-warn/40 bg-warn/5' : 'border-line bg-panel2')}>
        <div className="flex flex-wrap items-center gap-2">
          <Toggle on={local} label={local ? 'Voz local (experimental): ligada' : 'Usar voz local (experimental)'}
            onClick={() => set(local ? { voice_provider: 'edge', voice_name: 'pt-BR-AntonioNeural' } : { voice_provider: 'local', voice_name: th.voice_ref ? 'ref' : 'default' })} />
        </div>
        <p className="text-xs text-muted mt-2">Gera a narração no seu computador (Chatterbox). Precisa ser ligada também em Configurações e instalada à parte; usa muita memória
          (≥ 4 GB de RAM e 3,5 GB de VRAM livres na hora). Se não houver folga, o vídeo sai com a voz Microsoft — nunca trava.</p>
        {local && (
          <div className="grid sm:grid-cols-2 gap-3 mt-3">
            <div><Label>Arquivo de voz de referência</Label>
              <input className="input" placeholder="minha_voz.wav (em data/voice_local/refs/)" value={th.voice_ref ?? ''}
                onChange={e => { set({ voice_provider: 'local', voice_name: e.target.value ? 'ref' : 'default', theme: { ...th, voice_ref: e.target.value } }) }} /></div>
            <div><Label>De quem é a voz?</Label>
              <select className="input" value={th.voice_ref_consent ?? ''} onChange={e => setTheme({ voice_ref_consent: e.target.value })}>
                <option value="">— escolha —</option>
                <option value="own">É a minha própria voz</option>
                <option value="licensed">Voz licenciada para este uso</option>
              </select></div>
            <p className="sm:col-span-2 text-xs text-warn">Nunca use a voz de outra pessoa (famosos, locutores, conhecidos) sem licença: clonar voz de terceiros é proibido pelo YouTube e pode ser crime.
              Sem arquivo ou sem marcar a origem, usa a voz padrão do modelo.</p>
          </div>
        )}
      </div>
    </div>
  )
}

const DAYS = [['', 'Todo dia'], ['seg', 'Seg'], ['ter', 'Ter'], ['qua', 'Qua'], ['qui', 'Qui'], ['sex', 'Sex'], ['sab', 'Sáb'], ['dom', 'Dom']]

function slotLabel(s: string) {
  const p = s.toLowerCase().split(/\s+/)
  const day = DAYS.find(([k]) => k && p.includes(k))?.[1] ?? 'Todo dia'
  const time = p.find(x => x.includes(':')) ?? s
  return `${day} ${time} · ${p.some(x => x.startsWith('long')) ? 'Longo' : 'Short'}`
}

type Suggestion = {
  slots: string[]; per_day: number; young: boolean; age_days: number; samples: number; uses_data: boolean; basis: string[]
  settings: { per_day: number; min_gap_hours: number; new_channel_cap: number; new_channel_days: number }
  hours: { hour: number; score: number; data_weight: number }[]
}

/** Horários de postagem: fixos ou "Automático (pelos dados)", com espaço mínimo e limite de canal novo. */
function ScheduleBox({ f, set }: { f: Ch; set: (p: Partial<Ch>) => void }) {
  const { data: sug } = useApi<Suggestion>(`/channels/${f.id}/posting-times`)
  const sc = f.schedule ?? {}
  const cfg = { ...sug?.settings, ...sc }
  const setSc = (p: NonNullable<Ch['schedule']>) => set({ schedule: { ...sc, ...p } })
  const auto = sc.mode === 'auto'
  const num = (label: string, v: number | undefined, on: (n: number) => void, min: number, max: number, step = 1, suf = '') => (
    <label className="flex items-center gap-2 text-sm text-muted">{label}
      <input type="number" className="input !w-20 !py-1" min={min} max={max} step={step} value={v ?? ''}
        onChange={e => on(Number(e.target.value))} />{suf}</label>
  )
  const best = sug ? Math.max(...sug.hours.map(h => h.score)) : 1
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Label>Horários de postagem</Label>
        <select className="input !w-auto !py-1 ml-auto" value={auto ? 'auto' : 'manual'} onChange={e => setSc({ mode: e.target.value as 'manual' | 'auto' })}>
          <option value="manual">Horários fixos</option>
          <option value="auto">Automático (pelos dados)</option>
        </select>
      </div>
      {auto ? (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            {(sug?.slots ?? []).map(s => <span key={s} className="badge badge-ok">{s}</span>)}
            {!sug && <Loader2 size={14} className="animate-spin text-muted" />}
            <span className="ml-2">{num('Shorts por dia', cfg.per_day, n => setSc({ per_day: n }), 1, 8)}</span>
          </div>
          <div className="text-xs text-muted">Vídeos longos continuam nos horários fixos abaixo (os marcados como “longo”).</div>
          <TimeChips slots={f.posting_slots.filter(s => s.includes('long'))} onChange={v => set({ posting_slots: [...f.posting_slots.filter(s => !s.includes('long')), ...v] })} />
        </div>
      ) : (
        <TimeChips slots={f.posting_slots} onChange={v => set({ posting_slots: v })} />
      )}
      <div className="flex flex-wrap items-center gap-4">
        {num('Espaço mínimo entre posts', cfg.min_gap_hours, n => setSc({ min_gap_hours: n }), 0, 12, 0.5, 'h')}
        {num('Canal novo: até', cfg.new_channel_cap, n => setSc({ new_channel_cap: n }), 1, 10, 1, 'Shorts/dia')}
        {num('nos primeiros', cfg.new_channel_days, n => setSc({ new_channel_days: n }), 0, 365, 1, 'dias')}
      </div>
      {sug && (
        <div className="p-3 rounded-[var(--r-md)] border border-line bg-bg2/50 text-sm space-y-2">
          <div className="font-medium">Sugestão pelos dados: {sug.slots.join(' · ') || '—'}
            <span className="text-muted font-normal"> · {sug.per_day}/dia{sug.young ? ` · canal novo (${Math.round(sug.age_days)} dia(s))` : ''}</span></div>
          <div className="flex items-end gap-[2px] h-10" title="Força de cada hora (Brasília), 0 h → 23 h">
            {sug.hours.map(h => (
              <div key={h.hour} className={clsx('flex-1 rounded-sm transition-colors', sug.slots.includes(`${String(h.hour).padStart(2, '0')}:00`) ? 'bg-grad' : 'bg-line3 hover:bg-faint')}
                style={{ height: `${Math.max(6, (h.score / best) * 100)}%` }} title={`${h.hour} h · força ${h.score} · dados ${Math.round(h.data_weight * 100)}%`} />
            ))}
          </div>
          <div className="flex justify-between text-[10px] text-muted"><span>0 h</span><span>6 h</span><span>12 h</span><span>18 h</span><span>23 h</span></div>
          <ul className="text-xs text-muted list-disc pl-4 space-y-0.5">{sug.basis.map(b => <li key={b}>{b}</li>)}</ul>
        </div>
      )}
    </div>
  )
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
          <span key={s} className={clsx('badge !h-7 !text-[13px] pr-1', s.includes('long') ? 'badge-accent' : '')}>
            {slotLabel(s)}<button className="w-5 h-5 grid place-items-center rounded hover:bg-white/10 text-muted hover:text-text" aria-label="Remover" onClick={() => onChange(slots.filter(x => x !== s))}><X size={12} /></button></span>
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
        <button className="btn btn-sm" onClick={add}><Plus size={14} /> Adicionar</button>
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
    <div className="surface p-3 transition-colors hover:border-line2" onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault(); if (e.dataTransfer.files.length) onFiles(e.dataTransfer.files) }}>
      <div className="flex items-center gap-2">
        <span className="font-medium text-[13px] flex-1">{label}</span>
        <span className={`badge ${count >= 3 ? 'badge-ok' : 'text-muted'}`}><span className="dot" /><span className="num">{count}</span></span>
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
          <span key={it} className="badge !h-7 !text-[13px] pr-1">{label ? label(it) : it}<button className="w-5 h-5 grid place-items-center rounded hover:bg-white/10 text-muted hover:text-text" aria-label="Remover" onClick={() => onChange(items.filter(x => x !== it))}><X size={12} /></button></span>
        ))}
        {!items.length && <span className="text-sm text-muted">Nenhum ainda.</span>}
      </div>
      <div className="flex gap-2">
        <input className="input" value={v} placeholder={placeholder} onChange={e => setV(e.target.value)} onKeyDown={e => e.key === 'Enter' && add()} />
        <button className="btn" onClick={add}><Plus size={14} /> Adicionar</button>
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
        <button className="btn btn-sm" disabled={busy} onClick={run}>
          {busy ? <Loader2 size={14} className="animate-spin" /> : <Wand2 size={14} />} {kit ? 'Gerar de novo' : 'Gerar'}</button>
      </div>
      <p className="text-xs text-muted">Foto de perfil, capa e marca d'água com o mascote e as cores do canal. Envie no YouTube Studio → Personalização.</p>
      {kit && (
        <div className="mt-3 space-y-2">
          <a href={kit.sheet} target="_blank" rel="noreferrer"><img src={kit.sheet} className="rounded-[var(--r-md)] border border-line w-full hover:border-line3 transition-colors" alt="" /></a>
          <div className="flex flex-wrap gap-2 text-xs">
            {([['avatar', 'Foto de perfil'], ['banner', 'Capa'], ['watermark', "Marca d'água"]] as const).map(([k, l]) => (
              <a key={k} className="btn btn-sm" href={kit[k]} download>{l}</a>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
