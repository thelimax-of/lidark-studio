// Ponte com o app de desktop (launcher/lidark_app.py, pywebview + WebView2).
// No navegador comum tudo isso cai para a Fullscreen API ou fica oculto.
import { useEffect, useState } from 'react'

type DesktopApi = {
  minimize: () => Promise<void>
  close: () => Promise<void>
  toggle_fullscreen: () => Promise<boolean>
  is_fullscreen: () => Promise<boolean>
}

declare global {
  interface Window { pywebview?: { api: DesktopApi } }
}

const bridge = () => (window.pywebview?.api?.minimize ? window.pywebview.api : null)

/** true quando rodando dentro da janela do Lidark Studio (pywebview). */
export function useDesktop() {
  const [on, setOn] = useState(() => !!bridge())
  useEffect(() => {
    if (on) return
    const h = () => setOn(!!bridge())
    window.addEventListener('pywebviewready', h)
    const t = window.setTimeout(h, 1500)
    return () => { window.removeEventListener('pywebviewready', h); window.clearTimeout(t) }
  }, [on])
  return on
}

export function useFullscreen(): [boolean, () => void] {
  const [fs, setFs] = useState(() => !!document.fullscreenElement)
  useEffect(() => {
    const b = bridge()
    if (b) b.is_fullscreen().then(setFs).catch(() => {})
    const h = () => setFs(!!document.fullscreenElement)
    document.addEventListener('fullscreenchange', h)
    window.addEventListener('pywebviewready', () => bridge()?.is_fullscreen().then(setFs).catch(() => {}), { once: true })
    return () => document.removeEventListener('fullscreenchange', h)
  }, [])
  const toggle = () => {
    const b = bridge()
    if (b) { b.toggle_fullscreen().then(setFs).catch(() => {}); return }
    if (document.fullscreenElement) void document.exitFullscreen()
    else void document.documentElement.requestFullscreen().catch(() => {})
  }
  return [fs, toggle]
}

export const toggleFullscreen = () => {
  const b = bridge()
  if (b) return void b.toggle_fullscreen()
  if (document.fullscreenElement) void document.exitFullscreen()
  else void document.documentElement.requestFullscreen().catch(() => {})
}
export const minimizeWindow = () => void bridge()?.minimize()
export const closeWindow = () => { const b = bridge(); if (b) void b.close(); else window.close() }
