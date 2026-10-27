import { useEffect, useState } from 'react'
import { CalendarRange, Plus, Trash2, Save } from 'lucide-react'
import { api, invalidate, useApi } from '../api'
import { act } from '../ui'

type Camp = { id?: string; name: string; focus: string; start: string; end: string; share: number; active: boolean }

const today = () => new Date().toISOString().slice(0, 10)

export default function CampaignsSection({ channelId }: { channelId: number }) {
  const { data } = useApi<{ campaigns: Camp[]; active: string | null }>(`/channels/${channelId}/campaigns`)
  const [list, setList] = useState<Camp[]>([])
  const [dirty, setDirty] = useState(false)
  useEffect(() => { if (data) { setList(data.campaigns); setDirty(false) } }, [data])
  const upd = (i: number, p: Partial<Camp>) => { setList(l => l.map((c, k) => k === i ? { ...c, ...p } : c)); setDirty(true) }
  const save = () => act(() => api(`/channels/${channelId}/campaigns`, { method: 'PUT', body: { campaigns: list } }), 'Campanhas salvas')
    .then(() => invalidate(`/channels/${channelId}/campaigns`))
  const status = (c: Camp) => !c.active ? 'Pausada' : c.id && c.id === data?.active ? 'No ar agora'
    : c.end < today() ? 'Encerrada' : c.start > today() ? 'Agendada' : 'Ativa'

  return (
    <section className="card p-5">
      <div className="flex items-start justify-between gap-3 mb-4">
        <div className="flex gap-3">
          <div className="w-9 h-9 rounded-lg bg-panel2 border border-line2 text-muted grid place-items-center shrink-0"><CalendarRange size={18} /></div>
          <div><h3 className="font-semibold">Campanhas sazonais</h3>
            <p className="text-sm text-muted">Datas que puxam audiência (provas, aniversários, eventos). No período, parte dos vídeos do piloto automático vai para o tema da campanha e vira uma série/playlist.</p></div>
        </div>
        <div className="flex gap-2 shrink-0">
          <button className="btn btn-sm" onClick={() => { setList(l => [...l, { name: '', focus: '', start: today(), end: today(), share: 0.6, active: true }]); setDirty(true) }}><Plus size={14} /> Nova</button>
          {dirty && <button className="btn btn-sm btn-primary" onClick={save}><Save size={14} /> Salvar</button>}
        </div>
      </div>
      {!list.length && <div className="text-[13px] text-muted">Nenhuma campanha. Crie uma para datas importantes do seu nicho.</div>}
      <div className="space-y-3">
        {list.map((c, i) => (
          <div key={c.id ?? `n${i}`} className="border border-line rounded-lg p-3 space-y-2.5">
            <div className="flex flex-wrap items-center gap-2">
              <input className="input h-8! flex-1 min-w-48 font-medium" value={c.name} placeholder="Nome (vira a série/playlist)" onChange={e => upd(i, { name: e.target.value })} />
              <span className="badge"><span className={`dot ${status(c) === 'No ar agora' ? 'text-ok' : status(c) === 'Agendada' ? 'text-info' : 'text-faint'}`} />{status(c)}</span>
              <label className="flex items-center gap-1.5 text-[12.5px] text-muted"><input type="checkbox" checked={c.active} onChange={e => upd(i, { active: e.target.checked })} /> ativa</label>
              <button className="btn btn-sm btn-icon btn-ghost" data-tip="Remover" onClick={() => { setList(l => l.filter((_, k) => k !== i)); setDirty(true) }}><Trash2 size={14} /></button>
            </div>
            <textarea className="input min-h-14 text-[13px]" value={c.focus} placeholder="Sobre o que são os vídeos da campanha (a IA usa isso para buscar pautas)" onChange={e => upd(i, { focus: e.target.value })} />
            <div className="flex flex-wrap items-center gap-3 text-[12.5px] text-muted">
              <label className="flex items-center gap-1.5">De <input type="date" className="input h-8! w-auto!" value={c.start} onChange={e => upd(i, { start: e.target.value })} /></label>
              <label className="flex items-center gap-1.5">até <input type="date" className="input h-8! w-auto!" value={c.end} onChange={e => upd(i, { end: e.target.value })} /></label>
              <label className="flex items-center gap-2 flex-1 min-w-56">Fatia dos vídeos
                <input type="range" min={10} max={100} step={10} value={Math.round(c.share * 100)} onChange={e => upd(i, { share: Number(e.target.value) / 100 })} className="flex-1 accent-current" />
                <span className="num text-text w-9 text-right">{Math.round(c.share * 100)}%</span></label>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
