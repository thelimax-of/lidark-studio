import { useEffect, useState } from 'react'
import { CalendarRange, Plus, Trash2, Save, GraduationCap, Rocket, Sparkles } from 'lucide-react'
import { api, invalidate, useApi } from '../api'
import { act, toast } from '../ui'

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
      {list.some(c => c.id?.includes('enem')) && <EnemPack channelId={channelId} />}
    </section>
  )
}

type EnemItem = {
  key: string; format: 'short' | 'long'; title: string; angle: string; enem: string; weight: number
  structure: string | null; minutes: number | null; publish: string | null
  idea: { id: number; status: string; fact_status: string; score: number | null } | null
}
type EnemPackData = {
  campaign: Camp | null; enem_day: string; days_left: number; short_slots: number; campaign_slots: number
  suggested: number; auto_pilot: boolean; long_enabled: boolean; shorts: EnemItem[]; longs: EnemItem[]
}

const STRUCT: Record<string, string> = {
  mito_verdade: 'Mito × Verdade', pergunta: 'Pergunta direta', detalhe: 'Detalhe escondido', in_media_res: 'Começa no clímax',
  comparacao: 'Comparação', personagem: 'Personagem', contagem: 'Contagem regressiva', cronologia: 'Linha do tempo',
}
const ideaStatus = (i: EnemItem['idea']) => !i ? null
  : i.status === 'discarded' ? 'Descartada (fatos)' : i.status === 'produced' ? 'Produzida' : i.status === 'scripted' ? 'Em roteiro'
  : i.fact_status === 'verified' ? `Na fila${i.score != null ? ` · nota ${i.score}` : ''}` : 'Checando fatos'
const br = (d: string) => d.slice(8, 10) + '/' + d.slice(5, 7)

/** Pacote pronto da campanha ENEM: pautas de História que mais caem, com estrutura variada e SEO honesto. */
function EnemPack({ channelId }: { channelId: number }) {
  const path = `/channels/${channelId}/enem`
  const { data } = useApi<EnemPackData>(path)
  const [sel, setSel] = useState<Set<string>>(new Set())
  const [schedLongs, setSchedLongs] = useState(true)
  const [busy, setBusy] = useState(false)
  useEffect(() => {
    if (!data) return
    const fresh = (x: EnemItem) => !x.idea || x.idea.status === 'discarded'
    setSel(new Set([...data.shorts.filter(fresh).slice(0, data.suggested).map(x => x.key),
                    ...(data.long_enabled ? data.longs.filter(fresh).map(x => x.key) : [])]))
  }, [data])
  if (!data || data.days_left < 0) return null
  const toggle = (k: string) => setSel(s => { const n = new Set(s); if (n.has(k)) n.delete(k); else n.add(k); return n })
  const launch = async () => {
    setBusy(true)
    const r = await act(() => api<{ created: string[]; skipped: string[] }>(`${path}/launch`,
      { body: { keys: [...sel], schedule_longs: schedLongs } }))
    setBusy(false)
    if (r) {
      toast.ok(`${r.created.length} pauta(s) na campanha — checagem de fatos na fila` + (r.skipped.length ? ` · ${r.skipped.length} já existiam` : ''))
      invalidate(path); invalidate('/ideas')
    }
  }
  const more = () => act(() => api('/ideas/discover', { body: { channel_id: channelId, count: 6, campaign: data.campaign?.id ?? 'enem-revisao-2026' } }),
    'Buscando mais pautas da campanha com IA')
  const row = (x: EnemItem) => {
    const st = ideaStatus(x.idea)
    const locked = !!x.idea && x.idea.status !== 'discarded'
    return (
      <label key={x.key} className={`flex items-start gap-2.5 py-1.5 ${locked ? 'opacity-70' : 'cursor-pointer'}`}>
        <input type="checkbox" className="mt-1" disabled={locked} checked={locked || sel.has(x.key)} onChange={() => toggle(x.key)} />
        <div className="min-w-0 flex-1">
          <div className="text-[13.5px] font-medium">{x.title}</div>
          <div className="text-[12px] text-muted">{x.enem}
            {x.format === 'long' && <> · {x.minutes} min{x.publish && <> · publicar {br(x.publish)} {x.publish.slice(11)}</>}</>}</div>
        </div>
        <div className="flex gap-1.5 shrink-0 flex-wrap justify-end">
          <span className="badge">{x.structure ? STRUCT[x.structure] ?? x.structure : 'Estrutura sorteada'}</span>
          {st && <span className="badge"><span className={`dot ${st.startsWith('Descartada') ? 'text-bad' : st.startsWith('Checando') ? 'text-warn' : 'text-ok'}`} />{st}</span>}
        </div>
      </label>
    )
  }
  const nShorts = data.shorts.filter(x => sel.has(x.key)).length
  const nLongs = data.longs.filter(x => sel.has(x.key)).length
  return (
    <div className="mt-5 border border-line2 rounded-lg p-4 space-y-3">
      <div className="flex gap-3">
        <div className="w-9 h-9 rounded-lg bg-panel2 border border-line2 text-muted grid place-items-center shrink-0"><GraduationCap size={18} /></div>
        <div><h4 className="font-semibold">Pacote ENEM 2026 · {data.days_left === 0 ? 'é hoje' : `faltam ${data.days_left} dia(s)`} (prova em {br(data.enem_day)})</h4>
          <p className="text-sm text-muted">Pautas dos temas de História que mais caem em Ciências Humanas, com fatos conferidos e estruturas variadas.
            Até a véspera cabem <b className="text-text">{data.short_slots}</b> Shorts nos horários do canal (respeitando espaço mínimo e limite diário);
            ≈ <b className="text-text">{data.campaign_slots}</b> vão para a campanha. Cada pauta passa pela checagem de fatos e o roteiro ainda sorteia gancho, título, CTA e duração.</p></div>
      </div>
      {!data.auto_pilot && <div className="text-[12.5px] text-warn">Piloto automático desligado: as pautas ficam aprovadas em Pautas, mas só viram vídeo quando você ligar o piloto automático do canal ou mandar produzir cada uma.</div>}
      {!data.long_enabled && <div className="text-[12.5px] text-warn">O canal não tem o formato “vídeo longo” ativado — ative-o para produzir as revisões longas.</div>}
      <div>
        <div className="text-[12px] uppercase tracking-wide text-faint mb-1">Revisões longas · capítulos automáticos</div>
        {data.longs.map(row)}
        <label className="flex items-center gap-2 text-[12.5px] text-muted mt-1">
          <input type="checkbox" checked={schedLongs} onChange={e => setSchedLongs(e.target.checked)} />
          Já produzir e agendar os longos nas datas sugeridas (a data é ajustada se colidir com outro post)</label>
      </div>
      <div>
        <div className="text-[12px] uppercase tracking-wide text-faint mb-1">Shorts · ordenados pelo que mais cai</div>
        <div className="max-h-96 overflow-y-auto pr-1">{data.shorts.map(row)}</div>
      </div>
      <div className="flex flex-wrap gap-2 justify-end">
        <button className="btn btn-sm" onClick={more}><Sparkles size={14} /> Mais pautas da campanha (IA)</button>
        <button className="btn btn-sm btn-primary" disabled={busy || !sel.size} onClick={launch}>
          <Rocket size={14} /> Lançar {nShorts} Short(s){nLongs ? ` + ${nLongs} longo(s)` : ''}</button>
      </div>
    </div>
  )
}
