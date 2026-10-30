"""Planejador de imagens do episódio: o que é NOVO (gera agora, dentro da cota grátis) e o que vem do banco.

Política (pedido do dono: imagens novas por vídeo, o banco é para identidade/velocidade):
- alvo de 12-16 imagens novas por Short quando há capacidade (local + Cloudflare + HF); longo: ~6 por minuto
- prioridade das novas: gancho (beat 1) → gancho final → cenas de ação → inserts → cenários → imagens alternativas
- pose de personagem que falta no banco é gerada como folha (fundo verde → recorte), com semente fixa do personagem
- sem cota: reaproveita do banco (tags iguais, menos usadas, fora dos episódios recentes) — o episódio nunca falha
  por falta de imagem enquanto houver banco; banco vazio + sem cota → a tarefa espera a cota voltar
"""
from __future__ import annotations

import hashlib
import random
from typing import Any

from . import bank, bible as B, providers


NEUTRAL_POSES = ("front", "worried", "talking", "thinking", "pointing", "surprised")


def _seed(*parts: Any) -> int:
    return int(hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:8], 16)


def sizes(fmt: str) -> dict[str, tuple[int, int]]:
    if fmt == "long":
        return {"scene": (1280, 720), "location": (1280, 720), "insert": (1280, 720), "pose": (768, 1024), "prop": (768, 768)}
    return {"scene": (720, 1280), "location": (720, 1280), "insert": (720, 1280), "pose": (768, 1024), "prop": (768, 768)}


def target_new(fmt: str, n_beats: int, minutes: float = 0) -> int:
    c = providers.conf()
    lo, hi = (c.get("new_images_short") or [12, 16])[:2]
    if fmt == "long":
        return int(max(20, minutes * float(c.get("new_images_long_per_min") or 6)))
    return max(lo, min(hi, n_beats + 4))


def plan(slug: str, b: dict[str, Any], ep: dict[str, Any], fmt: str, *, budget: int | None = None,
         recent_eps: set[int] | None = None, seed: int = 0) -> dict[str, Any]:
    """Monta a lista de necessidades por beat e decide quais viram imagem nova (até `budget`)."""
    rng = random.Random(seed)
    sz = sizes(fmt)
    orient = "h" if fmt == "long" else "v"
    chars = {c["id"]: c for c in b.get("characters") or []}
    beats = ep["beats"]
    needs: list[dict[str, Any]] = []
    for i, bt in enumerate(beats):
        v = bt.get("visual") or {}
        kind = v.get("kind", "scene")
        tags = list(dict.fromkeys((v.get("tags") or []) + ([v["place"].lower()] if v.get("place") else [])))
        cs = [chars[c["id"]] for c in v.get("chars") or [] if c["id"] in chars]
        pri = 100 if i == 0 else (90 if i == len(beats) - 1 else (60 if kind == "scene" else 50 if kind == "insert" else 40))
        if kind == "scene" and cs:
            needs.append({"beat": i, "role": "main", "type": "scene", "pri": pri, "tags": tags, "char": cs[0]["id"],
                          "pose": (v.get("chars") or [{}])[0].get("pose", ""), "size": sz["scene"],
                          "prompt": B.scene_prompt(b, v.get("desc") or bt["text"], cs), "kind": "hero" if i == 0 else "scene"})
        elif kind == "insert" or not cs:
            needs.append({"beat": i, "role": "main", "type": "insert" if kind == "insert" else "location", "pri": pri, "tags": tags,
                          "size": sz["insert"],
                          "prompt": (f"{b['style']}. Close-up detail shot, no people: {v.get('desc') or bt['text']}. No text, no letters"
                                     if kind == "insert" else B.location_prompt(b, v.get("desc") or v.get("place") or bt["text"])),
                          "kind": "insert" if kind == "insert" else "location"})
        else:  # layered: cenário vazio (por lugar) + poses do banco
            needs.append({"beat": i, "role": "main", "type": "location", "pri": pri - 5, "tags": tags, "size": sz["location"],
                          "place": (v.get("place") or "").lower(),
                          "prompt": B.location_prompt(b, f"{v.get('place') or ''}. {v.get('desc') or ''}"), "kind": "location"})
            for c in v.get("chars") or []:
                if c["id"] not in chars:
                    continue
                have = bank.find(slug, "pose", char=c["id"], pose=c.get("pose", ""), limit=1)
                if not have or have[0].get("pose") != c.get("pose"):
                    needs.append({"beat": i, "role": "pose", "type": "pose", "pri": 70, "char": c["id"], "pose": c.get("pose", "front"),
                                  "size": sz["pose"], "tags": [c["id"]], "prompt": B.pose_prompt(b, chars[c["id"]], c.get("pose", "front")),
                                  "kind": "sheet", "seed": int(chars[c["id"]].get("seed") or 1) + _seed(c.get("pose")) % 997})
        # imagem alternativa para beats longos (mais trocas visuais por segundo)
        if len(bt["text"].split()) >= 14:
            needs.append({"beat": i, "role": "alt", "type": "insert", "pri": 20 + rng.random() * 5, "tags": tags, "size": sz["insert"],
                          "prompt": f"{b['style']}. Atmospheric detail related to: {v.get('desc') or bt['text']}. No people, no text",
                          "kind": "insert"})
    # mesma pose pedida em vários beats = uma geração só
    seen, uniq = set(), []
    for n in needs:
        k = (n["type"], n.get("char"), n.get("pose")) if n["type"] == "pose" else (n["type"], n.get("place")) if n.get("place") else id(n)
        if k in seen:
            continue
        seen.add(k)
        uniq.append(n)
    if budget is None:
        budget = min(target_new(fmt, len(beats), (ep.get("seconds_target") or 0) / 60), providers.images_left_today() + _lucid_left())
    order = sorted(uniq, key=lambda n: -n["pri"])
    for n in order:
        n["generate"] = False
    left = budget
    for n in order:
        if left <= 0:
            break
        n["generate"] = True
        left -= 1
    return {"needs": uniq, "budget": budget, "new": sum(n["generate"] for n in uniq), "orient": orient}


def _lucid_left() -> int:
    c = providers.PROVIDERS["cf_lucid"].capacity()
    return int(c.get("images_left") or 0) if c.get("available") else 0


def generate_needs(slug: str, b: dict[str, Any], pl: dict[str, Any], *, log=None, check=None) -> dict[str, Any]:
    """Gera o que foi aprovado no plano e guarda no banco. Falhou/sem cota → marca para reaproveitar."""
    made, failed = 0, 0
    for n in pl["needs"]:
        if not n.get("generate"):
            continue
        if check:
            check()
        w, h = n["size"]
        seed = int(n.get("seed") or random.randint(1, 2 ** 31 - 2))
        rec = None
        for attempt in range(2 if n["type"] == "pose" else 1):
            p = providers.generate(n["prompt"], w, h, seed + attempt * 101, n["kind"], log_fn=log)
            if not p:
                break
            m = providers.meta(p)
            rec = bank.ingest(slug, p, n["type"], tags=n.get("tags"), char=n.get("char", ""), pose=n.get("pose", ""),
                              source=f"{m.get('provider', '')}:{m.get('model', '')}", prompt=n["prompt"], seed=seed + attempt * 101,
                              need_eyes=n["type"] == "pose" and n.get("pose") not in ("back", "running"))
            if rec and rec.get("rejected"):
                if log:
                    log(f"pose recusada ({', '.join(rec['rejected'])}) — tentando outra semente")
                rec = None
                continue
            break
        if rec:
            n["asset"] = rec["id"]
            made += 1
            if n["type"] == "pose" and rec.get("eyes") and not bank.find(slug, "portrait", char=n.get("char", ""), limit=1):
                bank.add_portrait_from(slug, rec)
        else:
            n["generate"] = False
            failed += 1
    return {"made": made, "failed": failed}


def resolve(slug: str, b: dict[str, Any], ep: dict[str, Any], pl: dict[str, Any], *, episode_no: int,
            recent_eps: set[int] | None = None, seed: int = 0) -> tuple[list[dict[str, Any]], list[str], list[dict[str, Any]]]:
    """Visual final de cada beat (para o diretor) usando o que foi gerado + banco. Devolve (visuals, ids usados, faltas)."""
    rng = random.Random(seed)
    used: list[str] = []
    missing: list[dict[str, Any]] = []
    by_beat: dict[int, list[dict[str, Any]]] = {}
    for n in pl["needs"]:
        by_beat.setdefault(n["beat"], []).append(n)
    place_loc: dict[str, str] = {}
    for n in pl["needs"]:
        if n["type"] == "location" and n.get("asset") and n.get("place"):
            place_loc[n["place"]] = n["asset"]
    orient = pl.get("orient", "v")
    taken: set[str] = set()

    def full(a: dict[str, Any] | None) -> dict[str, Any] | None:
        if not a:
            return None
        used.append(a["id"])
        return {**a, "file": str(bank.file_path(slug, a["file"]))}

    def pick(type_: str, tags: list[str], **kw: Any) -> dict[str, Any] | None:
        c = bank.find(slug, type_, tags=tags, orientation=orient, exclude=taken, recent_eps=recent_eps, limit=6, **kw)
        if not c:
            c = bank.find(slug, type_, tags=tags, orientation=orient, recent_eps=recent_eps, limit=6, **kw)
        if not c:
            return None
        a = c[0] if len(c) == 1 or rng.random() < 0.7 else c[1]
        taken.add(a["id"])
        return a

    visuals = []
    for i, bt in enumerate(ep["beats"]):
        v = bt.get("visual") or {}
        ns = by_beat.get(i, [])
        main = next((n for n in ns if n["role"] == "main"), None)
        tags = (main or {}).get("tags") or v.get("tags") or []
        a_main = bank.get(slug, main["asset"]) if main and main.get("asset") else None
        if main and not a_main and main.get("place") and main["place"] in place_loc:
            a_main = bank.get(slug, place_loc[main["place"]])
        if a_main:
            taken.add(a_main["id"])
        vis: dict[str, Any]
        want_chars = [c for c in v.get("chars") or []]
        if a_main and a_main["type"] in ("scene", "insert"):
            vis = {"mode": "scene", "bg": full(a_main)}
        else:
            loc = a_main or pick("location", tags)
            chars = []
            for c in want_chars:
                pz = bank.find(slug, "pose", char=c["id"], pose=c.get("pose", ""), limit=12, recent_eps=None)
                exact = [p for p in pz if p.get("pose") == c.get("pose")]
                if not exact:  # pose pedida não existe: só poses "neutras" (sem objeto na mão, de pé)
                    exact = [p for g in NEUTRAL_POSES for p in pz if p.get("pose") == g]
                if exact:
                    chars.append({"asset": full(rng.choice(exact[:2])), "id": c["id"]})
            if loc and chars:
                vis = {"mode": "layered", "bg": full(loc), "chars": chars}
            else:
                # sem cenário vazio ou sem pose: cena pronta do banco com as mesmas tags (ou qualquer uma)
                sc = pick("scene", tags, char=want_chars[0]["id"] if want_chars else "") or pick("scene", tags) or loc or pick("insert", tags)
                if not sc:
                    missing.append({"beat": i, "why": "banco sem imagem compatível"})
                    visuals.append(None)
                    continue
                vis = {"mode": "scene", "bg": full(sc)}
        alts = []
        for n in ns:
            if n["role"] == "alt" and n.get("asset"):
                a = bank.get(slug, n["asset"])
                if a:
                    alts.append({"mode": "scene", "bg": full(a)})
        if not alts and len(bt["text"].split()) >= 16:
            # sem alternativa nova: um close/insert do banco com as mesmas tags dá a segunda troca visual
            a = pick("insert", tags) or pick("scene", tags)
            if a and a["id"] != (vis.get("bg") or {}).get("id"):
                alts.append({"mode": "scene", "bg": full(a)})
        vis["alts"] = alts
        visuals.append(vis)
    # beats sem nada: herdam o visual do vizinho (com outro enquadramento) — nunca tela vazia
    for i, v in enumerate(visuals):
        if v is None:
            near = next((visuals[j] for j in list(range(i - 1, -1, -1)) + list(range(i + 1, len(visuals))) if visuals[j]), None)
            visuals[i] = dict(near) if near else None
    return visuals, used, missing
