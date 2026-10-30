// Ações rápidas globais (mega-menu, paleta de comandos, barra do topo). Usam endpoints existentes.
import { api, invalidate } from '../api'
import { act, toast } from '../ui'

const queued = () => invalidate('/jobs')
const need = (id?: number) => { if (!id) toast.err('Selecione um canal primeiro'); return !!id }

export const produceVideo = (id?: number) => need(id) &&
  act(() => api(`/channels/${id}/autopilot`, { method: 'POST' }), 'Produzindo um vídeo com a melhor pauta').then(queued)

export const runRadar = (id?: number) => need(id) &&
  act(() => api(`/channels/${id}/radar`, { body: {} }), 'Radar de tendências rodando').then(queued)

export const discoverIdeas = (id?: number, format: 'short' | 'long' = 'short') => need(id) &&
  act(() => api('/ideas/discover', { body: { channel_id: id, count: 8, format } }), 'Buscando pautas na internet…').then(queued)

export const syncMetrics = (id?: number) => need(id) &&
  act(() => api(`/channels/${id}/metrics/sync`, { method: 'POST' }), 'Sincronizando métricas').then(queued)

export const syncChannel = (id?: number) => need(id) &&
  act(() => api(`/channels/${id}/sync`, { method: 'POST' }), 'Sincronizando dados do canal').then(queued)
