import { Maximize2, Minimize2, Minus, X } from 'lucide-react'
import { closeWindow, minimizeWindow, useDesktop, useFullscreen } from './desktop'

/** Tela cheia sempre; minimizar/fechar só dentro do app de desktop (no navegador o próprio navegador cuida). */
export default function WindowControls() {
  const desktop = useDesktop()
  const [fs, toggle] = useFullscreen()
  return (
    <div className="flex items-center gap-0.5 no-drag">
      <button className="win-btn" onClick={toggle} aria-label={fs ? 'Sair da tela cheia' : 'Tela cheia'} data-tip={fs ? 'Sair da tela cheia (F11)' : 'Tela cheia (F11)'} data-tip-pos="bottom">
        {fs ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
      </button>
      {desktop && <>
        <button className="win-btn" onClick={minimizeWindow} aria-label="Minimizar"><Minus size={16} /></button>
        <button className="win-btn close" onClick={closeWindow} aria-label="Fechar"><X size={16} /></button>
      </>}
    </div>
  )
}
