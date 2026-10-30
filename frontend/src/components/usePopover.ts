import { useEffect, useRef, useState } from 'react'

/** Estado de um popover simples: fecha ao clicar fora e com Esc (devolvendo o foco ao gatilho). */
export function usePopover<T extends HTMLElement = HTMLDivElement>() {
  const [open, setOpen] = useState(false)
  const ref = useRef<T>(null)
  useEffect(() => {
    if (!open) return
    const down = (e: PointerEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false) }
    const key = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return
      setOpen(false)
      ref.current?.querySelector<HTMLElement>('[data-trigger]')?.focus()
    }
    document.addEventListener('pointerdown', down)
    document.addEventListener('keydown', key)
    return () => { document.removeEventListener('pointerdown', down); document.removeEventListener('keydown', key) }
  }, [open])
  return { open, setOpen, ref, toggle: () => setOpen(o => !o) }
}
