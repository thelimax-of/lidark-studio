import { useEffect, useState } from 'react'
import { Save, Zap, Plus, Trash2, KeyRound, Cpu, ImageIcon, Send } from 'lucide-react'
import { api, invalidate, useApi } from '../api'
import { act, Field, PageHeader, toast } from '../ui'

export default function Settings() {
  const { data } = useApi<any>('/settings')
  const { data: health } = useApi<any>('/health')
  const [f, setF] = useState<any>(null)
  useEffect(() => { if (data) setF(data) }, [data])
  if (!f) return null
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
        actions={<button className="btn btn-primary" onClick={save}><Save size={16} /> Salvar</button>} />

      <div className="grid lg:grid-cols-2 gap-6">
        <section className="card p-5 space-y-4">
          <h3 className="font-semibold flex items-center gap-2"><KeyRound size={17} className="text-muted" /> Inteligência artificial</h3>
          <Field label="Chaves do Gemini (várias = mais cota grátis)" hint="Crie em aistudio.google.com/apikey. Quando uma estoura a cota, a próxima é usada.">
            <div className="space-y-2">
              {(f.gemini_api_keys as string[]).map((k, i) => (
                <div key={i} className="flex gap-2">
                  <input className="input font-mono" value={k} onChange={e => { const a = [...f.gemini_api_keys]; a[i] = e.target.value; set('gemini_api_keys', a) }} />
                  <button className="btn btn-danger !px-2" onClick={() => set('gemini_api_keys', f.gemini_api_keys.filter((_: any, j: number) => j !== i))}><Trash2 size={15} /></button>
                </div>
              ))}
              <button className="btn" onClick={() => set('gemini_api_keys', [...f.gemini_api_keys, ''])}><Plus size={15} /> Adicionar chave</button>
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
          <div className="flex gap-2">
            <button className="btn" onClick={() => test('gemini')}><Zap size={15} /> Testar Gemini</button>
            <button className="btn" onClick={() => test('glm')}><Zap size={15} /> Testar GLM</button>
            <button className="btn" onClick={() => test('ollama')}><Zap size={15} /> Testar Ollama</button>
          </div>
        </section>

        <div className="space-y-6">
          <section className="card p-5 space-y-4">
            <h3 className="font-semibold flex items-center gap-2"><ImageIcon size={17} className="text-muted" /> Imagens</h3>
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
            <h3 className="font-semibold flex items-center gap-2"><Cpu size={17} className="text-muted" /> Motor de vídeo</h3>
            <div className="text-sm flex justify-between"><span className="text-muted">FFmpeg</span><span className="truncate max-w-[60%] text-right">{health?.ffmpeg?.path?.split(/[\\/]/).pop()}</span></div>
            <div className="text-sm flex justify-between"><span className="text-muted">Aceleração NVIDIA (NVENC)</span><span className={health?.ffmpeg?.nvenc ? 'text-ok' : 'text-warn'}>{health?.ffmpeg?.nvenc ? 'Ativa ✓' : 'Indisponível'}</span></div>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={f.use_nvenc} onChange={e => set('use_nvenc', e.target.checked)} /> Usar GPU para codificar</label>
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

          <section className="card p-5 space-y-2">
            <h3 className="font-semibold flex items-center gap-2"><Send size={17} className="text-muted" /> YouTube</h3>
            <p className="text-sm text-muted">O arquivo <code>client_secret.json</code> do Google Cloud fica em <code>data/secrets/</code>. Conecte o canal em <b>Canais → Contas</b>.</p>
          </section>
        </div>
      </div>
    </>
  )
}
