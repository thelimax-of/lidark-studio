import { useEffect, useState } from 'react'
import { Save, Zap, Plus, Trash2, KeyRound, Cpu, ImageIcon, Send, CloudUpload, Bell, Volume2 } from 'lucide-react'
import { api, invalidate, useApi } from '../api'
import { act, Field, PageHeader, Skeleton, toast } from '../ui'
import { IconBox } from './kit'

export default function Settings() {
  const { data } = useApi<any>('/settings')
  const { data: health } = useApi<any>('/health')
  const [f, setF] = useState<any>(null)
  useEffect(() => { if (data) setF(data) }, [data])
  if (!f) return (
    <div aria-busy="true"><Skeleton className="h-7 w-56 mb-7" />
      <div className="grid lg:grid-cols-2 gap-6"><Skeleton className="h-[420px]" /><div className="space-y-6"><Skeleton className="h-56" /><Skeleton className="h-56" /></div></div></div>
  )
  const set = (k: string, v: any) => setF({ ...f, [k]: v })
  const save = () => act(() => api('/settings', { method: 'PUT', body: f }), 'Configurações salvas').then(() => { invalidate('/settings'); invalidate('/health') })
  const test = async (p: string) => {
    await save()
    const r = await api(`/settings/test-llm?provider=${p}`, { method: 'POST' })
    r.ok ? toast.ok(`${r.provider} (${r.model}) respondeu: ${r.text}`) : toast.err(r.error)
  }

  return (
    <>
      <PageHeader title="Configurações" subtitle="Chaves e motores. Tudo fica salvo só no seu computador (pasta data/)."
        actions={<button className="btn btn-primary" onClick={save}><Save size={15} /> Salvar</button>} />

      <div className="grid lg:grid-cols-2 gap-6">
        <section className="card p-5 space-y-4">
          <h3 className="font-semibold flex items-center gap-3"><IconBox><KeyRound size={15} /></IconBox> Inteligência artificial</h3>
          <Field label="Chaves do Gemini (várias = mais cota grátis)" hint="Crie em aistudio.google.com/apikey. Quando uma estoura a cota, a próxima é usada.">
            <div className="space-y-2">
              {(f.gemini_api_keys as string[]).map((k, i) => (
                <div key={i} className="flex gap-2">
                  <input className="input font-mono" value={k} onChange={e => { const a = [...f.gemini_api_keys]; a[i] = e.target.value; set('gemini_api_keys', a) }} />
                  <button className="btn btn-icon btn-danger shrink-0" aria-label="Remover chave" onClick={() => set('gemini_api_keys', f.gemini_api_keys.filter((_: any, j: number) => j !== i))}><Trash2 size={15} /></button>
                </div>
              ))}
              <button className="btn btn-sm btn-ghost" onClick={() => set('gemini_api_keys', [...f.gemini_api_keys, ''])}><Plus size={14} /> Adicionar chave</button>
            </div>
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Modelo Gemini (texto)"><input className="input" value={f.gemini_model} onChange={e => set('gemini_model', e.target.value)} /></Field>
            <Field label="Modelo Gemini (voz)"><input className="input" value={f.gemini_tts_model} onChange={e => set('gemini_tts_model', e.target.value)} /></Field>
          </div>
          <Field label="Chave GLM (reserva)" hint="z.ai — o modelo glm-4.5-flash é gratuito.">
            <input className="input font-mono" value={f.glm_api_key} onChange={e => set('glm_api_key', e.target.value)} />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Modelo GLM"><input className="input" value={f.glm_model} onChange={e => set('glm_model', e.target.value)} /></Field>
            <Field label="URL GLM"><input className="input" value={f.glm_base_url} onChange={e => set('glm_base_url', e.target.value)} /></Field>
          </div>
          <Field label="Ordem de uso (fallback)" hint="Ex.: gemini, glm, ollama">
            <input className="input" value={f.llm_order.join(', ')} onChange={e => set('llm_order', e.target.value.split(',').map((x: string) => x.trim()).filter(Boolean))} />
          </Field>
          <div className="flex flex-wrap gap-2 pt-3 border-t border-line">
            <button className="btn" onClick={() => test('gemini')}><Zap size={15} /> Testar Gemini</button>
            <button className="btn" onClick={() => test('glm')}><Zap size={15} /> Testar GLM</button>
            <button className="btn" onClick={() => test('ollama')}><Zap size={15} /> Testar Ollama</button>
          </div>
        </section>

        <div className="space-y-6">
          <section className="card p-5 space-y-4">
            <h3 className="font-semibold flex items-center gap-3"><IconBox><ImageIcon size={15} /></IconBox> Imagens</h3>
            <Field label="Gerador de imagens por IA">
              <select className="input" value={f.image_ai_provider} onChange={e => set('image_ai_provider', e.target.value)}>
                <option value="pollinations">Pollinations (Flux grátis, nuvem)</option>
                <option value="gemini">Gemini Imagen (usa cota do Gemini)</option>
                <option value="none">Somente imagens reais</option>
              </select>
            </Field>
            <Field label="Nota mínima de qualidade da imagem (0-100)" hint="Cada imagem é avaliada por IA de visão (relevância, nitidez, marca d'água, erros de IA).">
              <input type="number" className="input" value={f.image_min_quality} onChange={e => set('image_min_quality', Number(e.target.value))} />
            </Field>
            <Field label="Chave Pexels (opcional)"><input className="input font-mono" value={f.pexels_api_key} onChange={e => set('pexels_api_key', e.target.value)} /></Field>
          </section>

          <section className="card p-5 space-y-3">
            <h3 className="font-semibold flex items-center gap-3"><IconBox><Cpu size={15} /></IconBox> Motor de vídeo</h3>
            <div className="text-sm flex justify-between"><span className="text-muted">FFmpeg</span><span className="truncate max-w-[60%] text-right">{health?.ffmpeg?.path?.split(/[\\/]/).pop()}</span></div>
            <div className="text-sm flex justify-between items-center"><span className="text-muted">Aceleração NVIDIA (NVENC)</span><span className={health?.ffmpeg?.nvenc ? 'badge badge-ok' : 'badge badge-warn'}>{health?.ffmpeg?.nvenc ? 'Ativa' : 'Indisponível'}</span></div>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={f.use_nvenc} onChange={e => set('use_nvenc', e.target.checked)} /> Usar GPU para codificar</label>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={!!f.trend_radar_enabled} onChange={e => set('trend_radar_enabled', e.target.checked)} /> Radar de tendências diário (7h) cria pautas sozinho</label>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={!!f.auto_ideas_on_setup} onChange={e => set('auto_ideas_on_setup', e.target.checked)} /> Canal recém-conectado ganha 8 pautas automaticamente</label>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Modelo Whisper (legendas)">
                <select className="input" value={f.whisper_model} onChange={e => set('whisper_model', e.target.value)}>
                  {['base', 'small', 'medium', 'large-v3-turbo'].map(m => <option key={m}>{m}</option>)}
                </select>
              </Field>
              <Field label="Dispositivo Whisper">
                <select className="input" value={f.whisper_device} onChange={e => set('whisper_device', e.target.value)}>
                  <option value="cpu">CPU</option><option value="cuda">GPU (CUDA)</option>
                </select>
              </Field>
            </div>
          </section>

          <section className="card p-5 space-y-3">
            <h3 className="font-semibold flex items-center gap-2"><Volume2 size={17} className="text-muted" /> Áudio e voz</h3>
            <Field label="Volume final do vídeo (LUFS integrado)" hint="O YouTube toca tudo em -14 LUFS: mixar no mesmo nível evita o vídeo soar baixo ou ser abaixado. Pico real fica sempre em -1 dBTP ou menos.">
              <select className="input" value={String(f.loudness_target ?? -14)} onChange={e => set('loudness_target', Number(e.target.value))}>
                <option value="-14">-14 LUFS (padrão YouTube)</option>
                <option value="-13">-13 LUFS (um pouco mais alto)</option>
                <option value="-16">-16 LUFS (mais dinâmico)</option>
              </select>
            </Field>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={f.sfx_enabled !== false} onChange={e => set('sfx_enabled', e.target.checked)} /> Efeitos sonoros (whoosh nos cortes, impacto nas revelações, ding no desfecho) — cada canal pode desligar</label>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={f.loop_enabled !== false} onChange={e => set('loop_enabled', e.target.checked)} /> Shorts em loop quando o roteiro pede (fim emenda no começo, sem tela final)</label>
            <div className={`p-3 rounded-lg border ${f.local_voice_enabled ? 'border-warn/40 bg-warn/5' : 'border-line'}`}>
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={!!f.local_voice_enabled} onChange={e => set('local_voice_enabled', e.target.checked)} /> Voz local (Chatterbox) — experimental</label>
              <p className="text-xs text-muted mt-1.5">Roda no seu PC num ambiente separado (instalação manual de ~6 GB: veja <code>backend/lidark/voice_local.py</code>). Só é usada nos canais
                que escolherem “voz local” e só quando houver ≥ 4 GB de RAM e 3,5 GB de VRAM livres; senão o vídeo sai com a voz Microsoft. Com 8 GB de RAM, renderizar e gerar voz ao mesmo tempo pode deixar o PC lento.</p>
              <p className="text-xs text-warn mt-1">Voz de referência: só a sua própria ou uma voz licenciada. Nunca clone a voz de outra pessoa.</p>
            </div>
          </section>

          <section className="card p-5 space-y-2">
            <h3 className="font-semibold flex items-center gap-3"><IconBox><Send size={15} /></IconBox> YouTube</h3>
            <p className="text-sm text-muted">O arquivo <code>client_secret.json</code> do Google Cloud fica em <code>data/secrets/</code>. Conecte o canal em <b>Canais → Contas</b>.</p>
          </section>
        </div>
      </div>
      <div className="grid lg:grid-cols-2 gap-6 mt-6">
        <BackupCard />
        <NotifyCard enabled={!!f.ntfy_enabled} muted={f.ntfy_muted ?? []} onChange={(k, v) => { set(k, v); act(() => api('/settings', { method: 'PUT', body: { ...f, [k]: v } })).then(() => invalidate('/settings')) }} />
      </div>
    </>
  )
}

function BackupCard() {
  const { data: st } = useApi<any>('/backup/status', { refetchInterval: 15000 })
  const connect = async () => {
    const r: any = await act(() => api('/backup/drive/connect', { body: {} }))
    if (r?.auth_url) { window.open(r.auth_url, '_blank', 'width=520,height=720'); toast.info('Autorize na janela do Google. O primeiro backup começa sozinho.') }
  }
  return (
    <section className="card p-5 space-y-3">
      <h3 className="font-semibold flex items-center gap-3"><IconBox><CloudUpload size={15} /></IconBox> Backup na nuvem</h3>
      <p className="text-sm text-muted">Todo dia às 3h20 um .zip com o banco, configurações, chaves e a identidade dos canais vai para o seu Google Drive
        (guarda os 14 últimos). O código fica no GitHub (repositório privado). Os vídeos não entram — dá para refazer.</p>
      {!st?.connected ? (
        <button className="btn btn-primary" onClick={connect}><CloudUpload size={15} /> Conectar Google Drive</button>
      ) : (
        <div className="space-y-2 text-sm">
          <div className="flex items-center gap-2"><span className={`live-dot ${st.last_error ? '!bg-bad' : st.last_ok ? '' : '!bg-faint'}`} />
            {st.last_ok ? <>Último backup: <b>{new Date(st.last_ok).toLocaleString('pt-BR')}</b> · {Math.round((st.last_size ?? 0) / 1024)} KB · {st.count} cópias</> : 'Conectado — aguardando o primeiro backup'}</div>
          {st.last_error && <div className="text-xs text-bad break-words">{st.last_error}</div>}
          <div className="flex gap-2">
            <button className="btn btn-sm" onClick={() => act(() => api('/backup/now', { body: {} }), 'Backup enviado ao Google Drive').then(() => invalidate('/backup/status'))}><CloudUpload size={13} /> Fazer backup agora</button>
            {st.folder_url && <a className="btn btn-sm btn-ghost" href={st.folder_url} target="_blank" rel="noreferrer">Abrir pasta no Drive</a>}
          </div>
        </div>
      )}
    </section>
  )
}

const EVENTS: [string, string][] = [['ready', 'Vídeo pronto'], ['review', 'Vídeo para revisar'], ['failed', 'Falhas'], ['published', 'Publicado no YouTube'], ['comments', 'Comentários novos'], ['daily', 'Resumo das 21h']]

function NotifyCard({ enabled, muted, onChange }: { enabled: boolean; muted: string[]; onChange: (k: string, v: any) => void }) {
  const { data: t } = useApi<{ topic: string; server: string }>('/notify/topic')
  return (
    <section className="card p-5 space-y-3">
      <h3 className="font-semibold flex items-center gap-3"><IconBox><Bell size={15} /></IconBox> Avisos no celular</h3>
      <ol className="text-sm text-muted list-decimal pl-5 space-y-1">
        <li>Instale o app grátis <b className="text-text">ntfy</b> (Play Store ou App Store) — não precisa de conta.</li>
        <li>No app, toque em <b className="text-text">+</b> e assine o tópico: <code className="kbd text-[13px]! select-all text-text!">{t?.topic ?? '…'}</code></li>
        <li>Ligue abaixo e toque em “Testar”.</li>
      </ol>
      <p className="text-xs text-faint">O nome do tópico é secreto e aleatório: só quem tiver ele recebe os avisos. Os avisos levam títulos de vídeos, nunca senhas ou chaves.</p>
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={enabled} onChange={e => onChange('ntfy_enabled', e.target.checked)} /> Avisos ligados</label>
      <div className="flex flex-wrap gap-x-4 gap-y-1.5">
        {EVENTS.map(([k, l]) => (
          <label key={k} className={`flex items-center gap-1.5 text-[13px] ${enabled ? '' : 'opacity-50'}`}>
            <input type="checkbox" disabled={!enabled} checked={!muted.includes(k)}
              onChange={e => onChange('ntfy_muted', e.target.checked ? muted.filter(x => x !== k) : [...muted, k])} /> {l}</label>
        ))}
      </div>
      <button className="btn btn-sm" onClick={() => act(() => api('/notify/test', { body: {} }), 'Aviso de teste enviado — confira o celular')}><Bell size={13} /> Testar</button>
    </section>
  )
}
