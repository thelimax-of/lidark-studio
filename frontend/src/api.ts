import { QueryClient, useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

export const qc = new QueryClient({
  defaultOptions: { queries: { refetchOnWindowFocus: false, staleTime: 5_000 } },
})

export async function api<T = any>(path: string, opts: { method?: string; body?: unknown } = {}): Promise<T> {
  const r = await fetch('/api' + path, {
    method: opts.method ?? (opts.body !== undefined ? 'POST' : 'GET'),
    headers: opts.body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
  })
  if (!r.ok) {
    let msg = r.statusText
    try { msg = (await r.json()).detail ?? msg } catch { /* noop */ }
    throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg))
  }
  return r.json()
}

export const useApi = <T = any>(path: string | null, opts: { refetchInterval?: number } = {}) =>
  useQuery<T>({ queryKey: [path], queryFn: () => api<T>(path!), enabled: !!path, ...opts })

export const invalidate = (prefix: string) =>
  qc.invalidateQueries({ predicate: q => String(q.queryKey[0] ?? '').startsWith(prefix) })

// ---------------------------------------------------------------- tipos

export type Channel = {
  id: number; name: string; slug: string; niche: string; audience: string; language: string
  description: string; editorial_guide: string; tone: string; formats: string[]
  short_seconds: number; long_minutes: number
  voice_provider: string; voice_name: string; voice_style: string; voice_rate: string
  visual_mode: string; image_style: string; template: string; templates?: string[]; theme: Record<string, string>
  music_mood: string; music_volume: number; default_hashtags: string[]; cta: string
  auto_pilot: boolean; min_score_to_produce: number; posting_slots: string[]; color: string
  youtube_id: string; handle: string; avatar_url: string; banner_url: string; yt_description: string
  stats: { subscribers?: number; views?: number; videos?: number; country?: string }
  synced_at: string | null; setup_status: string; connected?: boolean
  radar?: { keywords?: string[]; competitors?: string[]; competitor_names?: Record<string, string> }
  counts?: { ideas: number; scripts: number; videos: number; published: number }
  footage?: boolean; image_credit_ok?: boolean; yt_category?: string; thumbs_blocked?: boolean
}

export type Idea = {
  id: number; channel_id: number; title: string; angle: string; summary: string; format: string
  origin: string; status: string; score: number | null; score_reason: string
  score_breakdown: { criteria?: Record<string, number>; improvements?: string[]; better_title?: string; raw?: number }
  fact_status: string; facts: { claim: string; verdict: string; sources: string[]; note?: string }[]
  sources: { title: string; url: string; kind?: string }[]; tags: string[]; created_at: string
}

export type Scene = { text: string; visual: { kind: string; query?: string; query_pt?: string; prompt?: string }; emphasis?: string[] }

export type Claim = { scene: number; claim: string; verdict: string; source?: string; note?: string }

export type Script = {
  id: number; channel_id: number; idea_id: number | null; format: string; title: string; hook: string
  scenes: Scene[]; description: string; tags: string[]; hashtags: string[]; thumbnail_text: string
  status: string; quality_score: number | null; review_notes: string
  variety?: { series?: string; structure?: string; hook_style?: string; title_style?: string; seconds?: number; template?: string }
  fact_check: { scene?: number; claim: string; problem: string; fix: string }[]
  claims?: { items: Claim[]; fixed?: number; unresolved?: Claim[]; sources?: number }
  sources: { title: string; url: string }[]; version: number; created_at: string
}

export type Video = {
  id: number; channel_id: number; script_id: number; format: string; status: string; path: string
  thumbnail_path: string; duration: number; error: string; created_at: string; title?: string
  assets: Record<string, any>; publications?: any[]
}

export type Job = {
  id: number; kind: string; channel_id: number | null; ref_id: number | null; title: string
  status: string; priority?: number; progress: number; stage: string; error: string; result: any
  created_at: string; started_at: string | null; finished_at: string | null; log?: string
}

export const mediaUrl = (p: string) => (p ? '/media/' + p.replace(/\\/g, '/').split('/media/').pop() : '')

// ---------------------------------------------------------------- eventos ao vivo

const listeners = new Set<(j: Job) => void>()

export function useLiveEvents() {
  const [connected, setConnected] = useState(false)
  useEffect(() => {
    let es: EventSource | null = null
    let retry: number | undefined
    const connect = () => {
      es = new EventSource('/api/events')
      es.addEventListener('hello', () => setConnected(true))
      es.addEventListener('job', (e) => {
        const job = JSON.parse((e as MessageEvent).data) as Job
        listeners.forEach(l => l(job))
        invalidate('/jobs')
        if (job.status === 'done' || job.status === 'failed') {
          ;['/ideas', '/scripts', '/videos', '/dashboard', '/channels', '/publications'].forEach(invalidate)
        }
      })
      es.onerror = () => { setConnected(false); es?.close(); retry = window.setTimeout(connect, 3000) }
    }
    connect()
    return () => { es?.close(); window.clearTimeout(retry) }
  }, [])
  return connected
}

export function onJob(fn: (j: Job) => void) {
  listeners.add(fn)
  return () => { listeners.delete(fn) }
}
