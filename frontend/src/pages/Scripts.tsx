import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FileText, AlertTriangle, Search, Layers } from 'lucide-react'
import { prefetch, useApi, type Script } from '../api'
import { ago, Empty, PageHeader, ScoreRing, Status, useChannel } from '../ui'
import { RowsSkeleton, useProgressive } from './kit'

export const STRUCT: Record<string, string> = {
  mito_verdade: 'Mito × Verdade', investigacao: 'Investigação', contagem: 'Contagem regressiva', cronologia: 'História acelerada',
  personagem: 'Personagem esquecido', detalhe: 'Detalhe escondido', in_media_res: 'Começa no clímax', pergunta: 'Pergunta direta',
  comparacao: 'Comparação de escala', e_se: 'E se...?',
}

/** Item da lista leve (?slim=1): sem cenas/checagem, com as contagens. Com o servidor antigo vem completo — os dois funcionam. */
type ScriptRow = Script & { scenes_count?: number; fact_check_count?: number }
const nScenes = (s: ScriptRow) => s.scenes_count ?? s.scenes?.length ?? 0
const nAlerts = (s: ScriptRow) => s.fact_check_count ?? s.fact_check?.length ?? 0

export default function Scripts() {
  const { channel } = useChannel()
  const nav = useNavigate()
  const [q, setQ] = useState('')
  const [fmt, setFmt] = useState<'all' | 'short' | 'long'>('all')
  const { data = [], isLoading } = useApi<ScriptRow[]>(channel ? `/scripts?channel_id=${channel.id}&slim=1` : null)
  const list = useMemo(() => {
    const s = q.trim().toLowerCase()
    return data.filter(x => (fmt === 'all' || x.format === fmt) && (!s || (x.title + ' ' + (x.hook ?? '')).toLowerCase().includes(s)))
  }, [data, q, fmt])
  const [shown, more] = useProgressive(list, 60, q + fmt)

  return (
    <>
      <PageHeader eyebrow={channel?.name} title="Roteiros" subtitle="Escritos com base em fontes e revisados por um editor-chefe de IA. Edite cena a cena antes de gerar o vídeo."
        actions={<>
          <div className="relative">
            <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-faint" />
            <input className="input h-8! w-56 pl-8!" placeholder="Buscar roteiro…" value={q} onChange={e => setQ(e.target.value)} />
          </div>
          <div className="seg">
            {([['all', 'Todos'], ['short', 'Shorts'], ['long', 'Longos']] as const).map(([k, l]) =>
              <button key={k} data-active={fmt === k} onClick={() => setFmt(k)}>{l}</button>)}
          </div>
        </>} />
      {isLoading && !data.length && <div className="card"><RowsSkeleton rows={6} h="h-11" /></div>}
      {!isLoading && !list.length && <Empty icon={<FileText size={20} />} title={data.length ? 'Nada com esse filtro' : 'Nenhum roteiro ainda'}
        text={data.length ? 'Tente outra busca.' : 'Abra uma pauta e clique em “Gerar roteiro”.'} />}
      {!!list.length && (
        <div className="card overflow-hidden"><div className="overflow-x-auto">
          <table className="tbl">
            <thead><tr><th className="w-14">Nota</th><th>Roteiro</th><th>Formato · estrutura</th><th>Checagem</th><th>Status</th><th className="right">Criado</th></tr></thead>
            <tbody>
              {shown.map(s => (
                <tr key={s.id} className="cursor-pointer group" onClick={() => nav(`/roteiros/${s.id}`)} onMouseEnter={() => prefetch(`/scripts/${s.id}`)}>
                  <td><ScoreRing score={s.quality_score} size={34} /></td>
                  <td className="max-w-0 w-[50%]">
                    <div className="font-medium truncate">{s.title}</div>
                    <div className="text-[12.5px] text-muted truncate">{s.hook}</div>
                  </td>
                  <td className="text-muted whitespace-nowrap">
                    <div className="flex items-center gap-1.5"><span className={s.format === 'long' ? 'badge badge-accent' : 'badge'}>{s.format === 'long' ? 'Longo' : 'Short'}</span>
                      <span className="inline-flex items-center gap-1 text-[12.5px]"><Layers size={12} className="text-faint" /><span className="num">{nScenes(s)}</span> cenas</span></div>
                    {s.variety?.structure && <div className="text-[12px] text-faint mt-1">{STRUCT[s.variety.structure] ?? s.variety.structure}{s.variety.series ? ` · ${s.variety.series}` : ''}</div>}
                  </td>
                  <td>{nAlerts(s)
                    ? <span className="badge badge-warn"><AlertTriangle size={12} /><span className="num">{nAlerts(s)}</span> alerta(s)</span>
                    : <span className="text-faint">—</span>}</td>
                  <td><Status s={s.status} /></td>
                  <td className="right text-muted whitespace-nowrap">{ago(s.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {more}
        </div></div>
      )}
    </>
  )
}
