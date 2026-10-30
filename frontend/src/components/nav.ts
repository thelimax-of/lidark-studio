// Mapa único de navegação: rotas (com code-splitting) + grupos do mega-menu + paleta de comandos.
import { lazy, type ComponentType } from 'react'
import {
  LayoutDashboard, Globe2, Bell, Lightbulb, FileText, Clapperboard, Image as ImageIcon, FlaskConical, Send, Activity,
  MessageSquare, BarChart3, GraduationCap, Radar, Bot, CalendarRange, CalendarDays, Trophy, Crosshair, Tv, Plus, Settings as Cog, SlidersHorizontal,
  type LucideIcon,
} from 'lucide-react'
import { prefetch } from '../api'

type Loader = () => Promise<{ default: ComponentType<any> }>
const named = <K extends string>(p: Promise<Record<K, ComponentType<any>>>, k: K) => p.then(m => ({ default: m[k] }))

/** Importadores das páginas. Chamar de novo é barato (o módulo fica em cache) — é assim que o hover pré-carrega. */
export const LOADERS = {
  dashboard: () => import('../pages/Dashboard'),
  overview: () => named(import('./Sections'), 'OverviewPage'),
  notifications: () => import('../pages/Notifications'),
  ideas: () => import('../pages/Ideas'),
  scripts: () => import('../pages/Scripts'),
  script: () => import('../pages/ScriptEditor'),
  videos: () => import('../pages/Videos'),
  thumbs: () => import('../pages/ThumbStudio'),
  viral: () => import('../pages/ViralLab'),
  publish: () => import('../pages/Publish'),
  jobs: () => import('../pages/Jobs'),
  comments: () => import('../pages/Comments'),
  metrics: () => import('../pages/Metrics'),
  learning: () => import('../pages/Learning'),
  trends: () => import('../pages/Trends'),
  autopilot: () => import('../pages/Autopilot'),
  campaigns: () => named(import('./Sections'), 'CampaignsPage'),
  calendar: () => import('../pages/Calendar'),
  champions: () => named(import('./Sections'), 'ChampionsPage'),
  focus: () => named(import('./Sections'), 'FocusPage'),
  channels: () => import('../pages/Channels'),
  newChannel: () => import('../pages/NewChannel'),
  channel: () => import('../pages/ChannelDetail'),
  settings: () => import('../pages/Settings'),
} satisfies Record<string, Loader>
export type PageKey = keyof typeof LOADERS

export const PAGES = Object.fromEntries(Object.entries(LOADERS).map(([k, l]) => [k, lazy(l as Loader)])) as unknown as Record<PageKey, ComponentType<any>>

export const ROUTES: { path: string; page: PageKey }[] = [
  { path: '/', page: 'dashboard' },
  { path: '/visao-geral', page: 'overview' },
  { path: '/notificacoes', page: 'notifications' },
  { path: '/pautas', page: 'ideas' },
  { path: '/roteiros', page: 'scripts' },
  { path: '/roteiros/:id', page: 'script' },
  { path: '/videos', page: 'videos' },
  { path: '/thumbs', page: 'thumbs' },
  { path: '/laboratorio-viral', page: 'viral' },
  { path: '/publicacao', page: 'publish' },
  { path: '/fila', page: 'jobs' },
  { path: '/comentarios', page: 'comments' },
  { path: '/metricas', page: 'metrics' },
  { path: '/aprendizado', page: 'learning' },
  { path: '/tendencias', page: 'trends' },
  { path: '/piloto-automatico', page: 'autopilot' },
  { path: '/campanhas', page: 'campaigns' },
  { path: '/calendario', page: 'calendar' },
  { path: '/campeoes', page: 'champions' },
  { path: '/modo-foco', page: 'focus' },
  { path: '/canais', page: 'channels' },
  { path: '/canais/novo', page: 'newChannel' },
  { path: '/canais/:id', page: 'channel' },
  { path: '/config', page: 'settings' },
]

export type NavItem = {
  to: string; label: string; desc: string; icon: LucideIcon; page: PageKey
  /** dados da API pré-carregados no hover (cid = canal selecionado) */
  data?: (cid?: number) => (string | null)[]
  badge?: 'jobs' | 'comments' | 'notifications'
  keywords?: string
}
export type NavGroup = { id: string; label: string; items: NavItem[]; columns?: number }

export const NAV: NavGroup[] = [
  { id: 'inicio', label: 'Início', items: [
    { to: '/', label: 'Painel', desc: 'O dia do canal: próximos passos, produção e números', icon: LayoutDashboard, page: 'dashboard', keywords: 'dashboard home inicio' },
    { to: '/visao-geral', label: 'Visão geral', desc: 'Todos os canais lado a lado', icon: Globe2, page: 'overview', data: () => ['/overview?days=28'], keywords: 'todos canais overview' },
    { to: '/notificacoes', label: 'Notificações', desc: 'Avisos do sistema, publicações e alertas', icon: Bell, page: 'notifications', badge: 'notifications', data: () => ['/notifications?limit=30'] },
  ] },
  { id: 'criar', label: 'Criar', items: [
    { to: '/pautas', label: 'Pautas', desc: 'Ideias pesquisadas, com nota e checagem de fatos', icon: Lightbulb, page: 'ideas', keywords: 'ideias' },
    { to: '/roteiros', label: 'Roteiros', desc: 'Textos, cenas, ganchos e revisão', icon: FileText, page: 'scripts', data: cid => [cid ? `/scripts?channel_id=${cid}&slim=1` : null] },
    { to: '/videos', label: 'Vídeos', desc: 'Renders prontos, em produção e revisão', icon: Clapperboard, page: 'videos', data: cid => [cid ? `/videos?channel_id=${cid}&slim=1` : null] },
    { to: '/thumbs', label: 'Estúdio de thumbs', desc: 'Miniaturas e variações para teste', icon: ImageIcon, page: 'thumbs', keywords: 'thumbnail miniatura capa' },
    { to: '/laboratorio-viral', label: 'Laboratório viral', desc: 'Ganchos, títulos e formatos que viralizam', icon: FlaskConical, page: 'viral', keywords: 'hook gancho viral' },
  ] },
  { id: 'publicar', label: 'Publicar', items: [
    { to: '/publicacao', label: 'Publicação', desc: 'Agenda e horários de postagem', icon: Send, page: 'publish', data: cid => [cid ? `/videos?channel_id=${cid}&slim=1` : null], keywords: 'agenda postar youtube' },
    { to: '/fila', label: 'Fila de produção', desc: 'Tarefas rodando, na fila e falhas', icon: Activity, page: 'jobs', badge: 'jobs', data: () => ['/jobs?limit=100'], keywords: 'jobs producao tarefas' },
    { to: '/comentarios', label: 'Comentários', desc: 'Responder o público com ajuda da IA', icon: MessageSquare, page: 'comments', badge: 'comments', data: cid => [cid ? `/comments?channel_id=${cid}&status=new` : null] },
  ] },
  { id: 'crescer', label: 'Crescer', columns: 2, items: [
    { to: '/metricas', label: 'Métricas', desc: 'Views, retenção, experimentos e YPP', icon: BarChart3, page: 'metrics', data: cid => [cid ? `/channels/${cid}/performance` : null], keywords: 'analytics views retencao' },
    { to: '/aprendizado', label: 'Aprendizado', desc: 'O que os dados ensinaram ao sistema', icon: GraduationCap, page: 'learning', keywords: 'insights' },
    { to: '/tendencias', label: 'Radar de tendências', desc: 'Assuntos subindo agora no nicho', icon: Radar, page: 'trends', keywords: 'trends radar' },
    { to: '/piloto-automatico', label: 'Piloto automático', desc: 'Produção e postagem sem você', icon: Bot, page: 'autopilot', keywords: 'autopilot automatico' },
    { to: '/campanhas', label: 'Campanhas', desc: 'Datas sazonais que puxam audiência', icon: CalendarRange, page: 'campaigns' },
    { to: '/calendario', label: 'Calendário de efemérides', desc: 'Datas que vêm por aí, prontas para virar pauta', icon: CalendarDays, page: 'calendar', keywords: 'almanaque efemerides datas aniversario eclipse' },
    { to: '/campeoes', label: 'Campeões', desc: 'Short campeão → vídeo longo', icon: Trophy, page: 'champions' },
    { to: '/modo-foco', label: 'Modo foco', desc: 'Quanto cada canal produz', icon: Crosshair, page: 'focus', data: () => ['/focus'] },
  ] },
  { id: 'canais', label: 'Canais', items: [
    { to: '/canais', label: 'Todos os canais', desc: 'Conectar, sincronizar e organizar', icon: Tv, page: 'channels', data: () => ['/channels'] },
    { to: '/canais/:current', label: 'Canal atual', desc: 'Identidade, voz, visual e agenda', icon: SlidersHorizontal, page: 'channel' },
    { to: '/canais/novo', label: 'Novo canal', desc: 'Criar um canal com marca e nicho', icon: Plus, page: 'newChannel' },
    { to: '/config', label: 'Configurações', desc: 'Chaves de IA, backup e sistema', icon: Cog, page: 'settings', data: () => ['/settings'] },
  ] },
]

export const ALL_ITEMS = NAV.flatMap(g => g.items.map(i => ({ ...i, group: g.label })))

/** Resolve o destino de um item (o "canal atual" depende do canal selecionado). */
export const hrefOf = (i: NavItem, cid?: number) => (i.to.includes(':current') ? (cid ? i.to.replace(':current', String(cid)) : '/canais') : i.to)

/** Grupo ativo para a rota atual. */
export function activeGroup(pathname: string) {
  for (const g of NAV) for (const i of g.items) {
    const t = i.to.replace('/:current', '')
    if (t === '/' ? pathname === '/' : pathname === t || pathname.startsWith(t + '/')) return g.id
  }
  return null
}
export const isActiveItem = (i: NavItem, pathname: string, cid?: number) => {
  const h = hrefOf(i, cid)
  if (h === '/') return pathname === '/'
  if (h === '/canais') return pathname === '/canais'
  return pathname === h || pathname.startsWith(h + '/')
}

const warmed = new Set<string>()
/** Intenção de navegar: baixa o chunk da página e os dados principais. */
export function warm(i: NavItem, cid?: number) {
  const key = i.page + ':' + cid
  if (warmed.has(key)) return
  warmed.add(key)
  void LOADERS[i.page]().catch(() => warmed.delete(key))
  i.data?.(cid).forEach(p => prefetch(p))
}

/** Depois da primeira pintura, baixa em segundo plano todos os chunks (app local: custo quase zero). */
export function warmAllWhenIdle() {
  const run = () => Object.values(LOADERS).forEach(l => void l().catch(() => {}))
  const ric = (window as any).requestIdleCallback as ((cb: () => void, o?: any) => number) | undefined
  if (ric) ric(run, { timeout: 4000 }); else window.setTimeout(run, 2500)
}
