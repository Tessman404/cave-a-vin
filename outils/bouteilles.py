"""Génère les symboles SVG des bouteilles couchées du plan de cave (effet 3D). Résultat : symboles.svg.txt, à coller dans index.html."""
import math
SQ = math.sqrt(0.5)
n = (SQ, SQ)          # perpendiculaire à l'axe (vers le bas-droite)
ax = (SQ, -SQ)        # axe de la bouteille, de l'avant (bas-gauche) vers l'arrière (haut-droite)

def p(x, y): return f"{x:.2f},{y:.2f}"
def add(a, b, k=1): return (a[0] + k * b[0], a[1] + k * b[1])

def tube(a, b, r, arriere=True):
    """Cylindre de a (avant) à b (arrière), rayon r ; fond arrondi côté arrière."""
    a1, a2, b1, b2 = add(a, n, r), add(a, n, -r), add(b, n, r), add(b, n, -r)
    fin = f"A{r:.2f},{r:.2f} 0 0 0 {p(*b2)}" if arriere else f"L{p(*b2)}"
    return f"M{p(*a1)} L{p(*b1)} {fin} L{p(*a2)} Z"

def grad_perp(id_, centre, r, stops):
    x1, y1 = add(centre, n, -r); x2, y2 = add(centre, n, r)
    s = "".join(f'<stop offset="{o}" stop-color="{c}" stop-opacity="{a}"/>' for o, c, a in stops)
    return f'<linearGradient id="{id_}" gradientUnits="userSpaceOnUse" x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}">{s}</linearGradient>'

# éclairage venant du haut-gauche : côté « -n » éclairé, côté « +n » dans l'ombre
VERRE = [(0, "#fff", .10), (.12, "#fff", .55), (.2, "#fff", .18), (.45, "#fff", 0), (.78, "#000", .25), (.9, "#fff", .10), (1, "#000", .6)]
METAL = [(0, "#fff", .25), (.18, "#fff", .75), (.32, "#fff", .1), (.65, "#000", .2), (1, "#000", .6)]

def bouteille(id_, champagne=False):
    rc = 16 if champagne else 14.5          # rayon du corps
    rn = 5.6 if champagne else 4.6          # rayon du goulot
    S = (28.5, 35.5)                        # centre de l'épaule (face avant du corps)
    B = add(S, ax, 30)                      # fond de la bouteille, loin derrière
    C1 = add(S, ax, -rc * .42)              # naissance du goulot sur l'épaule
    C0 = add(S, ax, -(rc * .42 + (11.5 if champagne else 13)))  # bout du goulot (vers nous)
    g = []
    d = []
    d.append(grad_perp(f"{id_}-corps", S, rc, VERRE))
    d.append(grad_perp(f"{id_}-col", C0, rn, VERRE))
    d.append(grad_perp(f"{id_}-cap", C0, rn + .6, METAL))
    # corps qui s'enfonce dans le casier
    g.append(f'<path d="{tube(S, B, rc)}" fill="currentColor"/>')
    g.append(f'<path d="{tube(S, B, rc)}" fill="url(#{id_}-corps)"/>')
    # épaule bombée : sphère éclairée en haut à gauche
    g.append(f'<circle cx="{S[0]}" cy="{S[1]}" r="{rc}" fill="currentColor"/>')
    g.append(f'<circle cx="{S[0]}" cy="{S[1]}" r="{rc}" fill="url(#epaule)"/>')
    hx, hy = add(add(S, n, -rc * .45), ax, rc * .1)
    g.append(f'<ellipse cx="{hx:.2f}" cy="{hy:.2f}" rx="{rc*.32:.2f}" ry="{rc*.13:.2f}" transform="rotate(-45 {hx:.2f} {hy:.2f})" fill="#fff" fill-opacity=".55"/>')
    # goulot
    if champagne:
        # collerette dorée qui couvre le goulot et mord sur l'épaule
        # collerette : disque doré évasé sur l'épaule, vu de face
        g.append(f'<circle cx="{C1[0]:.2f}" cy="{C1[1]:.2f}" r="{rn + 4.2:.2f}" fill="url(#or-collerette)"/>')
        g.append(f'<circle cx="{C1[0]:.2f}" cy="{C1[1]:.2f}" r="{rn + 4.2:.2f}" fill="none" stroke="#5e4512" stroke-opacity=".5" stroke-width=".5" stroke-dasharray="1.2 1"/>')
        g.append(f'<path d="{tube(C0, C1, rn + .4, False)}" fill="url(#{id_}-cap)"/>')
        g.append(f'<path d="{tube(C0, C1, rn + .4, False)}" fill="#c9a646" fill-opacity=".55" style="mix-blend-mode:multiply"/>')
    else:
        g.append(f'<path d="{tube(C0, C1, rn, False)}" fill="currentColor"/>')
        g.append(f'<path d="{tube(C0, C1, rn, False)}" fill="url(#{id_}-col)"/>')
        # capsule sur la moitié avant du goulot
        Cm = add(C0, ax, 7.5)
        g.append(f'<path d="{tube(C0, Cm, rn + .35, False)}" fill="var(--capsule, #5a0f20)"/>')
        g.append(f'<path d="{tube(C0, Cm, rn + .35, False)}" fill="url(#{id_}-cap)"/>')
        a1, a2 = add(Cm, n, rn + .35), add(Cm, n, -(rn + .35))
        g.append(f'<path d="M{p(*a1)} L{p(*a2)}" stroke="#000" stroke-opacity=".35" stroke-width=".6"/>')
    # bout du goulot vers nous : disque de la capsule
    rb = rn + (1.4 if champagne else .5)
    if champagne:
        g.append(f'<circle cx="{C0[0]:.2f}" cy="{C0[1]:.2f}" r="{rb:.2f}" fill="url(#or-sphere)"/>')
        # muselet : fils en croix et plaque centrale
        for k in (-1, 1):
            q1, q2 = add(C0, (SQ * k, SQ), -rb * .92), add(C0, (SQ * k, SQ), rb * .92)
            g.append(f'<path d="M{p(*q1)} L{p(*q2)}" stroke="#e6e6e6" stroke-width=".7"/>')
        g.append(f'<circle cx="{C0[0]:.2f}" cy="{C0[1]:.2f}" r="{rb*.42:.2f}" fill="#f3e6b8" stroke="#7a5d1a" stroke-width=".45"/>')
    else:
        g.append(f'<circle cx="{C0[0]:.2f}" cy="{C0[1]:.2f}" r="{rb:.2f}" fill="var(--capsule, #5a0f20)"/>')
        g.append(f'<circle cx="{C0[0]:.2f}" cy="{C0[1]:.2f}" r="{rb:.2f}" fill="url(#bout)"/>')
        g.append(f'<circle cx="{C0[0]:.2f}" cy="{C0[1]:.2f}" r="{rb*.62:.2f}" fill="none" stroke="#000" stroke-opacity=".28" stroke-width=".6"/>')
    return d, f'<symbol id="{id_}" viewBox="8 12 48 48" overflow="visible"><g class="forme">{"".join(g)}</g></symbol>'

communs = '''<radialGradient id="epaule" cx=".5" cy=".5" r=".5" fx=".3" fy=".28">
  <stop offset="0" stop-color="#fff" stop-opacity=".55"/><stop offset=".35" stop-color="#fff" stop-opacity=".08"/>
  <stop offset=".75" stop-color="#000" stop-opacity=".18"/><stop offset="1" stop-color="#000" stop-opacity=".55"/></radialGradient>
<radialGradient id="bout" cx=".5" cy=".5" r=".5" fx=".32" fy=".3">
  <stop offset="0" stop-color="#fff" stop-opacity=".55"/><stop offset=".5" stop-color="#fff" stop-opacity=".05"/>
  <stop offset="1" stop-color="#000" stop-opacity=".5"/></radialGradient>
<radialGradient id="or-sphere" cx=".5" cy=".5" r=".5" fx=".32" fy=".3">
  <stop offset="0" stop-color="#fff6d2"/><stop offset=".35" stop-color="#e3c46a"/><stop offset=".75" stop-color="#a8852c"/>
  <stop offset="1" stop-color="#5e4512"/></radialGradient>
<radialGradient id="or-collerette" cx=".5" cy=".5" r=".5" fx=".38" fy=".36">
  <stop offset="0" stop-color="#8f6d20"/><stop offset=".45" stop-color="#d9b85a"/><stop offset=".7" stop-color="#f6e3a1"/>
  <stop offset=".9" stop-color="#b08b2e"/><stop offset="1" stop-color="#5e4512"/></radialGradient>
<linearGradient id="or-plat" x1="0" y1="0" x2="1" y2="0">
  <stop offset="0" stop-color="#6e5317"/><stop offset=".3" stop-color="#f3dc8f"/><stop offset=".55" stop-color="#c9a646"/>
  <stop offset="1" stop-color="#5a4210"/></linearGradient>'''
d1, vin = bouteille("bouteille-couchee")
d2, champ = bouteille("bouteille-champagne", True)
defs = "<defs>" + communs + "".join(d1 + d2) + "</defs>"
open("symboles.svg.txt", "w").write(defs + "\n" + vin + "\n" + champ)
html = f'''<!doctype html><html><body style="margin:0;background:#eef0ea">
<svg width="0" height="0" style="position:absolute">{defs}{vin}{champ}</svg>
<div style="display:flex;gap:30px;padding:20px;flex-wrap:wrap">
''' + "".join(f'<svg width="200" height="200" style="color:{c};--capsule:{k}"><use href="#{s}"/></svg>' for c, k, s in [
    ("#3d0b18", "#7d1530", "bouteille-couchee"), ("#a9963c", "#ece0b4", "bouteille-couchee"), ("#ec9aac", "#e9e4e6", "bouteille-couchee"),
    ("#1f3d2c", "#c9a646", "bouteille-champagne"), ("#d9ddd5", "#c5cbc2", "bouteille-couchee")]) + '''</div>
<div style="display:grid;grid-template-columns:repeat(4,58px);padding:20px 40px">''' + "".join(
    f'<svg width="58" height="58" style="margin-top:{-10 if r else 0}px;z-index:{10-r};position:relative;color:{c};--capsule:{k}"><use href="#{s}"/></svg>'
    for r in range(5) for (c, k, s) in [("#3d0b18", "#7d1530", "bouteille-couchee"), ("#d9ddd5", "#c5cbc2", "bouteille-couchee"),
                                         ("#1f3d2c", "#c9a646", "bouteille-champagne"), ("#a9963c", "#ece0b4", "bouteille-couchee")]) + '''</div></body></html>'''
open("essai.html", "w").write(html)
