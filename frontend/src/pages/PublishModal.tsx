import { useState } from 'react'
import { Send } from 'lucide-react'
import { api, invalidate, useApi, type Video } from '../api'
import { act, Field, Modal } from '../ui'

export default function PublishModal({ video, onClose }: { video: Video; onClose: () => void }) {
  const { data: accounts = [] } = useApi<any[]>(`/accounts?channel_id=${video.channel_id}`)
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
        <div className="text-sm font-medium">{video.title}</div>
        <Field label="Contas">
          {accounts.length === 0 && <div className="text-sm text-muted">Nenhuma conta conectada. Conecte em <b>Canais → Contas</b>.</div>}
          <div className="space-y-2">
            {accounts.map(a => (
              <label key={a.id} className="flex items-center gap-3 p-2 rounded-lg bg-panel2 border border-line text-sm">
                <input type="checkbox" checked={sel.includes(a.id)} onChange={e => setSel(e.target.checked ? [...sel, a.id] : sel.filter(x => x !== a.id))} />
                <span className="capitalize font-semibold w-20">{a.platform}</span>{a.display_name}
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
          <label className="flex gap-2 items-start text-sm p-3 rounded-lg border border-warn/30 bg-warn/5">
            <input type="checkbox" className="mt-1" checked={force} onChange={e => setForce(e.target.checked)} />
            <span>Este vídeo foi <b>reprovado no inspetor de qualidade</b>. Marque para publicar mesmo assim.</span>
          </label>
        )}
        <button className="btn btn-primary w-full justify-center" disabled={!sel.length || (qaFail && !force)} onClick={submit}><Send size={16} /> {when ? 'Agendar' : 'Publicar agora'}</button>
      </div>
    </Modal>
  )
}
