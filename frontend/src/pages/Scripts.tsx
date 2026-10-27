import { useNavigate } from 'react-router-dom'
import { FileText, AlertTriangle } from 'lucide-react'
import { useApi, type Script } from '../api'
import { ago, Empty, PageHeader, ScoreRing, Status, useChannel } from '../ui'

const STRUCT: Record<string, string> = {
  mito_verdade: 'Mito × Verdade', investigacao: 'Investigação', contagem: 'Contagem regressiva', cronologia: 'História acelerada',
  personagem: 'Personagem esquecido', detalhe: 'Detalhe escondido', in_media_res: 'Começa no clímax', pergunta: 'Pergunta direta',
  comparacao: 'Comparação de escala', e_se: 'E se...?',
}

export default function Scripts() {
  const { channel } = useChannel()
  const nav = useNavigate()
  const { data = [] } = useApi<Script[]>(channel ? `/scripts?channel_id=${channel.id}` : null)
  return (
    <>
      <PageHeader title="Roteiros" subtitle="Escritos com base em fontes e revisados por um editor-chefe de IA. Edite cena a cena antes de gerar o vídeo." />
      {!data.length && <Empty icon={<FileText size={20} />} title="Nenhum roteiro ainda" text="Abra uma pauta e clique em “Gerar roteiro”." />}
      {!!data.length && (
        <div className="card overflow-hidden"><div className="overflow-x-auto">
          <table className="tbl">
            <thead><tr><th className="w-14">Nota</th><th>Roteiro</th><th>Formato · estrutura</th><th>Checagem</th><th>Status</th><th className="right">Criado</th></tr></thead>
            <tbody>
              {data.map(s => (
                <tr key={s.id} className="cursor-pointer" onClick={() => nav(`/roteiros/${s.id}`)}>
                  <td><ScoreRing score={s.quality_score} size={34} /></td>
                  <td className="max-w-0 w-[52%]">
                    <div className="font-medium truncate">{s.title}</div>
                    <div className="text-[12.5px] text-muted truncate">{s.hook}</div>
                  </td>
                  <td className="text-muted whitespace-nowrap">
                    <div>{s.format === 'long' ? 'Longo' : 'Short'} · <span className="num">{s.scenes.length}</span> cenas</div>
                    {s.variety?.structure && <div className="text-[12px] text-faint">{STRUCT[s.variety.structure] ?? s.variety.structure}{s.variety.series ? ` · ${s.variety.series}` : ''}</div>}
                  </td>
                  <td>{s.fact_check?.length
                    ? <span className="badge"><AlertTriangle size={12} className="text-warn" /><span className="num">{s.fact_check.length}</span> alerta(s)</span>
                    : <span className="text-faint">—</span>}</td>
                  <td><Status s={s.status} /></td>
                  <td className="right text-muted whitespace-nowrap">{ago(s.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div></div>
      )}
    </>
  )
}
