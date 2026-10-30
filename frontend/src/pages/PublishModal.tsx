import { useState } from 'react'
import { Send, ShieldAlert } from 'lucide-react'
import { api, invalidate, mediaUrl, useApi, type Video } from '../api'
import { act, Field, Modal } from '../ui'

export default function PublishModal({ video, onClose }: { video: Video; onClose: () => void }) {
  const { data: accounts = [], isLoading } = useApi<any[]>(`/accounts?channel_id=${video.channel_id}`)
  const [sel, setSel] = useState<number[]>([])
  const [when, setWhen] = useState('')
  const [privacy, setPrivacy] = useState('public')
  const [force, setForce] = useState(false)
  const qaFail = video.assets?.qa && !video.assets.qa.passed
  const submit = () => act(() => api('/publications', {
    body: { video_id: video.id, account_ids: sel, scheduled_at: when ? new Date(when).toISOString() : null, privacy, force },
  }), when ? 'Publicação agendada' : 'Publicando…').then(r => { if (r) { invalidate('/publications'); invalidate('/videos'); onClose() } })

  return (
    <Modal open onClose={onClose} title="Publicar vídeo">
      <div className="space-y-4">
        <div className="flex items-center gap-3 surface-2 p-2.5">
          <div className={video.format === 'long' ? 'w-16 h-9 rounded-md overflow-hidden bg-black shrink-0' : 'w-8 h-14 rounded-md overflow-hidden bg-black shrink-0'}>
            {video.thumbnail_path && <img src={mediaUrl(video.thumbnail_path)} className="w-full h-full object-cover" alt="" />}
          </div>
          <div className="text-sm font-medium leading-snug line-clamp-2">{video.title}</div>
        </div>
        <Field label="Contas">
          {isLoading && <div className="skeleton h-11" />}
          {!isLoading && accounts.length === 0 && <div className="text-sm text-muted">Nenhuma conta conectada. Conecte em <b>Canais → Contas</b>.</div>}
          <div className="space-y-2">
            {accounts.map(a => (
              <label key={a.id} className={`flex items-center gap-3 px-3 h-11 rounded-[var(--r-md)] border text-sm cursor-pointer transition-colors ${sel.includes(a.id) ? 'border-accent/50 bg-accent/[0.08]' : 'border-line bg-panel2 hover:border-line3'}`}>
                <input type="checkbox" checked={sel.includes(a.id)} onChange={e => setSel(e.target.checked ? [...sel, a.id] : sel.filter(x => x !== a.id))} />
                <span className="capitalize font-semibold w-20">{a.platform}</span><span className="text-muted truncate">{a.display_name}</span>
              </label>
            ))}
          </div>
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Agendar (vazio = agora)"><input type="datetime-local" className="input" value={when} onChange={e => setWhen(e.target.value)} /></Field>
          <Field label="Visibilidade">
            <select className="input" value={privacy} onChange={e => setPrivacy(e.target.value)}>
              <option value="public">Público</option><option value="unlisted">Não listado</option><option value="private">Privado</option>
            </select>
          </Field>
        </div>
        {qaFail && (
          <label className="flex gap-2.5 items-start text-sm p-3 rounded-[var(--r-md)] border border-warn/30 bg-warn/[0.06] cursor-pointer">
            <ShieldAlert size={15} className="text-warn shrink-0 mt-0.5" />
            <input type="checkbox" className="mt-1" checked={force} onChange={e => setForce(e.target.checked)} />
            <span>Este vídeo foi <b>reprovado no inspetor de qualidade</b>. Marque para publicar mesmo assim.</span>
          </label>
        )}
        <button className="btn btn-primary btn-lg w-full" disabled={!sel.length || (qaFail && !force)} onClick={submit}><Send size={16} /> {when ? 'Agendar' : 'Publicar agora'}</button>
      </div>
    </Modal>
  )
}
