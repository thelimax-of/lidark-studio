import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const API = 'http://127.0.0.1:8765'

/** Pré-carrega a fonte principal (latin) no <head>: o texto já pinta na fonte certa, sem troca/salto. */
const preloadFonts = (): Plugin => ({
  name: 'preload-fonts',
  apply: 'build',
  transformIndexHtml: {
    order: 'post',
    handler(_html, ctx) {
      const files = Object.keys(ctx.bundle ?? {}).filter(f => /geist-latin-wght-normal.*\.woff2$/.test(f))
      return files.map(f => ({ tag: 'link', injectTo: 'head-prepend' as const, attrs: { rel: 'preload', as: 'font', type: 'font/woff2', href: '/' + f, crossorigin: '' } }))
    },
  },
})

export default defineConfig({
  plugins: [react(), tailwindcss(), preloadFonts()],
  server: {
    port: 5173,
    proxy: { '/api': API, '/media': API, '/fonts': API },
  },
  build: {
    target: 'es2022',
    cssCodeSplit: true,
    modulePreload: { polyfill: false },
    chunkSizeWarningLimit: 900,
    rolldownOptions: {
      output: {
        // chunks estáveis: o vendor quase nunca muda (cache do navegador), gráficos só carregam nas páginas que usam
        codeSplitting: {
          includeDependenciesRecursively: false,  // senão o grupo de gráficos "puxa" react/clsx e vira dependência da entrada
          groups: [
            { name: 'charts', test: /node_modules[\\/](recharts|d3-[^\\/]+|victory-vendor|internmap|decimal\.js-light|es-toolkit|immer|reselect|@reduxjs|redux|react-redux|use-sync-external-store|eventemitter3|tiny-invariant)[\\/]/, priority: 20 },
            { name: 'react', test: /node_modules[\\/](react|react-dom|scheduler|react-router|react-router-dom|@tanstack|idb-keyval|cookie|set-cookie-parser)[\\/]/, priority: 15 },
            { name: 'icons', test: /node_modules[\\/]lucide-react[\\/]/, priority: 10 },
          ],
        },
      },
    },
  },
})
