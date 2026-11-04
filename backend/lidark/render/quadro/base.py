"""Traço e paleta do motor "quadro": a mesma mão do quadro aprovado (linha fina, cor chapada, luz planejada)."""
from __future__ import annotations

L = '#241c22'  # cor da linha, igual em tudo


def ln(w: float = 2.4, c: str = L) -> str:
    return f'stroke="{c}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round"'


DEFS = '''<defs>
<filter id="b3" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="3"/></filter>
<filter id="b6" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="6"/></filter>
<filter id="b14" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="14"/></filter>
<filter id="b9" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="9"/></filter>
<radialGradient id="fum"><stop offset="0" stop-color="#ffffff" stop-opacity=".9"/><stop offset=".55" stop-color="#ffffff" stop-opacity=".45"/><stop offset="1" stop-color="#ffffff" stop-opacity="0"/></radialGradient>
<radialGradient id="fumE"><stop offset="0" stop-color="#2b2730" stop-opacity=".9"/><stop offset=".55" stop-color="#3a3540" stop-opacity=".5"/><stop offset="1" stop-color="#3a3540" stop-opacity="0"/></radialGradient>
<linearGradient id="vidro" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".5"/><stop offset=".5" stop-color="#fff" stop-opacity="0"/></linearGradient>
<pattern id="chuva1" width="120" height="180" patternUnits="userSpaceOnUse"><path d="M12 10l-7 44M64 60l-7 44M100 120l-7 44M40 130l-5 30" stroke="#dbe9f6" stroke-width="2.2" stroke-opacity=".62" stroke-linecap="round"/></pattern>
<pattern id="chuva2" width="90" height="130" patternUnits="userSpaceOnUse"><path d="M10 6l-5 30M50 50l-5 30M78 90l-5 30" stroke="#c9dcef" stroke-width="1.4" stroke-opacity=".5" stroke-linecap="round"/></pattern>
</defs>'''
