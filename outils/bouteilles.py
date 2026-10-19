"""Génère les symboles SVG des bouteilles couchées du plan de cave (effet 3D). Résultat : symboles.svg.txt, à coller dans index.html."""
import math
SQ = math.sqrt(0.5)
# Vue presque de face (comme une vraie cave) : la bouteille fuit vers le haut-droite, raccourcie par la perspective.
THETA = math.radians(48)                     # inclinaison de l'axe à l'écran
ax = (math.cos(THETA), -math.sin(THETA))     # axe de la bouteille, de l'avant (bas-gauche) vers l'arrière (haut-droite)
n = (math.sin(THETA), math.cos(THETA))       # perpendiculaire à l'axe (vers le bas-droite)
F = 0.5                                      # raccourci de perspective des longueurs le long de l'axe
FC = 0.72                                    # le goulot, plus près de nous, est moins raccourci
ANGLE = -math.degrees(THETA)

def p(x, y): return f"{x:.2f},{y:.2f}"
def add(a, b, k=1): return (a[0] + k * b[0], a[1] + k * b[1])

def tube(a, b, r, arriere=True):
    """Cylindre de a (avant) à b (arrière), rayon r ; fond vu en ellipse (perspective) côté arrière."""
    a1, a2, b1, b2 = add(a, n, r), add(a, n, -r), add(b, n, r), add(b, n, -r)
    fin = f"A{r * F:.2f},{r:.2f} {ANGLE:.1f} 0 0 {p(*b2)}" if arriere else f"L{p(*b2)}"
    return f"M{p(*a1)} L{p(*b1)} {fin} L{p(*a2)} Z"

def grad_perp(id_, centre, r, stops):
    x1, y1 = add(centre, n, -r); x2, y2 = add(centre, n, r)
    s = "".join(f'<stop offset="{o}" stop-color="{c}" stop-opacity="{a}"/>' for o, c, a in stops)
    return f'<linearGradient id="{id_}" gradientUnits="userSpaceOnUse" x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}">{s}</linearGradient>'

# éclairage venant du haut-gauche : côté « -n » éclairé, côté « +n » dans l'ombre
VERRE = [(0, "#fff", .10), (.12, "#fff", .55), (.2, "#fff", .18), (.45, "#fff", 0), (.78, "#000", .25), (.9, "#fff", .10), (1, "#000", .6)]
METAL = [(0, "#fff", .25), (.18, "#fff", .75), (.32, "#fff", .1), (.65, "#000", .2), (1, "#000", .6)]

def cone(a, b, ra, rb):
    """Tronc de cône de a (rayon ra) à b (rayon rb) : épaule tombante des bourguignonnes et des flûtes."""
    return f"M{p(*add(a, n, ra))} L{p(*add(b, n, rb))} L{p(*add(b, n, -rb))} L{p(*add(a, n, -ra))} Z"

# rayon du corps, du goulot, longueur du goulot, épaule tombante (longueur du cône) — en unités du symbole
# (le diamètre d'une bordelaise fait 84 % d'une case : les bouteilles se touchent presque, comme en cave)
FORMES = {
    "bordelaise": (20.2, 6.2, 17, 0),
    "bourguignonne": (20.8, 6.3, 15, 8),
    "flute": (17.2, 5.6, 19, 9),
    "champagne": (21.4, 7.4, 15, 0),
}

def bouteille(id_, champagne=False, forme=None):
    forme = forme or ("champagne" if champagne else "bordelaise")
    rc, rn, lg, ep = FORMES[forme]
    S = (32, 36)                                     # centre de l'épaule (face avant du corps) = centre de la case
    B = add(S, ax, rc * 1.15)                        # fond de la bouteille, derrière (raccourci)
    C1 = add(S, ax, -(rc * .3 + ep * F))             # naissance du goulot sur l'épaule
    C0 = add(C1, ax, -lg * FC)                       # bout du goulot (vers nous)
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
    if ep:
        # épaule tombante (bourguignonne, flûte), vue de face : un dôme plus petit qui monte vers le goulot
        E = add(S, ax, -ep * F * .55)
        r1 = rc * .62
        d.append(grad_perp(f"{id_}-epaule", E, r1, VERRE))
        g.append(f'<circle cx="{E[0]:.2f}" cy="{E[1]:.2f}" r="{r1:.2f}" fill="currentColor"/>')
        g.append(f'<circle cx="{E[0]:.2f}" cy="{E[1]:.2f}" r="{r1:.2f}" fill="url(#epaule)" fill-opacity=".75"/>')
    hx, hy = add(add(S, n, -rc * .45), ax, rc * .1 * F)
    g.append(f'<ellipse cx="{hx:.2f}" cy="{hy:.2f}" rx="{rc*.32:.2f}" ry="{rc*.13:.2f}" transform="rotate({ANGLE:.1f} {hx:.2f} {hy:.2f})" fill="#fff" fill-opacity=".55"/>')
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
        Cm = add(C0, ax, lg * .55 * FC)
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


def fond(id_, forme="bordelaise"):
    """Bouteille couchée, le FOND tourné vers nous (rangement « arrière ») : on voit le cul de la bouteille et sa piqûre,
    le corps fuit vers le haut-droite et le goulot dépasse à peine derrière."""
    rc, rn, lg, ep = FORMES[forme]
    S = (32, 36)
    B = add(S, ax, rc * 1.15)
    N1 = add(B, ax, rc * .1)
    N2 = add(N1, ax, lg * F * .9)
    g, d = [], []
    d.append(grad_perp(f"{id_}-fond-corps", S, rc, VERRE))
    d.append(grad_perp(f"{id_}-fond-col", N1, rn, VERRE))
    # goulot qui dépasse derrière (dessiné d'abord, en partie caché par le corps)
    g.append(f'<path d="{tube(N1, N2, rn, False)}" fill="currentColor"/>')
    g.append(f'<path d="{tube(N1, N2, rn, False)}" fill="url(#{id_}-fond-col)"/>')
    capsule = "#c9a646" if forme == "champagne" else "var(--capsule, #5a0f20)"
    g.append(f'<circle cx="{N2[0]:.2f}" cy="{N2[1]:.2f}" r="{rn + .4:.2f}" fill="{capsule}"/>')
    g.append(f'<circle cx="{N2[0]:.2f}" cy="{N2[1]:.2f}" r="{rn + .4:.2f}" fill="url(#bout)"/>')
    # corps
    g.append(f'<path d="{tube(S, B, rc)}" fill="currentColor"/>')
    g.append(f'<path d="{tube(S, B, rc)}" fill="url(#{id_}-fond-corps)"/>')
    # le fond : disque plat au bord arrondi, piqûre creuse au centre
    g.append(f'<circle cx="{S[0]}" cy="{S[1]}" r="{rc}" fill="currentColor"/>')
    g.append(f'<circle cx="{S[0]}" cy="{S[1]}" r="{rc}" fill="url(#cul)"/>')
    g.append(f'<circle cx="{S[0]}" cy="{S[1]}" r="{rc * .58:.2f}" fill="url(#piqure)"/>')
    g.append(f'<circle cx="{S[0]}" cy="{S[1]}" r="{rc * .58:.2f}" fill="none" stroke="#fff" stroke-opacity=".22" stroke-width=".7"/>')
    hx, hy = add(S, n, -rc * .62)
    g.append(f'<ellipse cx="{hx:.2f}" cy="{hy:.2f}" rx="{rc*.36:.2f}" ry="{rc*.1:.2f}" transform="rotate({ANGLE:.1f} {hx:.2f} {hy:.2f})" fill="#fff" fill-opacity=".45"/>')
    return d, f'<symbol id="{id_}-fond" viewBox="8 12 48 48" overflow="visible"><g class="forme">{"".join(g)}</g></symbol>'


# vue de côté (rangement « allongé ») : longueur et silhouette selon la forme ; la case fait 3,2 bouteilles de large
LONGUEUR_COTE = 3.2
PROFILS = {  # (longueur du corps, longueur de l'épaule, longueur du goulot) en fractions de la longueur totale
    "bordelaise": (.62, .08, .30),
    "bourguignonne": (.52, .2, .28),
    "flute": (.44, .26, .30),
    "champagne": (.58, .14, .28),
}

def cote(id_, forme="bordelaise"):
    rc, rn, lg, ep = FORMES[forme]
    W = 48 * LONGUEUR_COTE
    cy, x0, x1 = 36, 4, W - 4
    L = x1 - x0
    fc, fe, fg = PROFILS[forme]
    xs = x0 + L * fc            # fin du corps, début de l'épaule
    xn = xs + L * fe            # début du goulot
    r = rc * .98
    haut, bas = cy - r, cy + r
    t, b = cy - rn, cy + rn
    k = (xn - xs)
    # silhouette : fond arrondi, corps, épaule, goulot, bague
    path = (f"M{x0 + 3:.2f},{haut:.2f} L{xs:.2f},{haut:.2f} C{xs + k * .55:.2f},{haut:.2f} {xn - k * .35:.2f},{t:.2f} {xn:.2f},{t:.2f} "
            f"L{x1 - 2.2:.2f},{t:.2f} L{x1 - 2.2:.2f},{t - .9:.2f} L{x1:.2f},{t - .9:.2f} L{x1:.2f},{b + .9:.2f} L{x1 - 2.2:.2f},{b + .9:.2f} "
            f"L{x1 - 2.2:.2f},{b:.2f} L{xn:.2f},{b:.2f} C{xn - k * .35:.2f},{b:.2f} {xs + k * .55:.2f},{bas:.2f} {xs:.2f},{bas:.2f} "
            f"L{x0 + 3:.2f},{bas:.2f} Q{x0:.2f},{bas:.2f} {x0:.2f},{bas - 3:.2f} L{x0:.2f},{haut + 3:.2f} Q{x0:.2f},{haut:.2f} {x0 + 3:.2f},{haut:.2f} Z")
    g, d = [], []
    stops = "".join(f'<stop offset="{o}" stop-color="{c}" stop-opacity="{a}"/>' for o, c, a in VERRE)
    d.append(f'<linearGradient id="{id_}-cote-verre" gradientUnits="userSpaceOnUse" x1="0" y1="{haut:.2f}" x2="0" y2="{bas:.2f}">{stops}</linearGradient>')
    mstops = "".join(f'<stop offset="{o}" stop-color="{c}" stop-opacity="{a}"/>' for o, c, a in METAL)
    d.append(f'<linearGradient id="{id_}-cote-metal" gradientUnits="userSpaceOnUse" x1="0" y1="{t - 1:.2f}" x2="0" y2="{b + 1:.2f}">{mstops}</linearGradient>')
    g.append(f'<path d="{path}" fill="currentColor"/>')
    g.append(f'<path d="{path}" fill="url(#{id_}-cote-verre)"/>')
    # léger arrondi du fond (bord gauche plus sombre)
    g.append(f'<rect x="{x0:.2f}" y="{haut:.2f}" width="5" height="{2 * r:.2f}" rx="2.5" fill="#000" fill-opacity=".18"/>')
    # capsule (ou coiffe dorée du champagne, qui descend sur l'épaule)
    if forme == "champagne":
        xc = xn - k * .45
        coiffe = (f"M{xc:.2f},{cy - rn - 3.2:.2f} C{xn - k * .1:.2f},{t - .4:.2f} {xn:.2f},{t - .4:.2f} {xn + 2:.2f},{t - .4:.2f} L{x1:.2f},{t - .9:.2f} "
                  f"L{x1:.2f},{b + .9:.2f} L{xn + 2:.2f},{b + .4:.2f} C{xn:.2f},{b + .4:.2f} {xn - k * .1:.2f},{b + .4:.2f} {xc:.2f},{cy + rn + 3.2:.2f} Z")
        g.append(f'<path d="{coiffe}" fill="#c9a646"/>')
        g.append(f'<path d="{coiffe}" fill="url(#{id_}-cote-metal)"/>')
    else:
        xcap = x1 - L * fg * .55
        cap = f"M{xcap:.2f},{t - .45:.2f} L{x1:.2f},{t - .9:.2f} L{x1:.2f},{b + .9:.2f} L{xcap:.2f},{b + .45:.2f} Z"
        g.append(f'<path d="{cap}" fill="var(--capsule, #5a0f20)"/>')
        g.append(f'<path d="{cap}" fill="url(#{id_}-cote-metal)"/>')
        g.append(f'<path d="M{xcap:.2f},{t - .45:.2f} L{xcap:.2f},{b + .45:.2f}" stroke="#000" stroke-opacity=".3" stroke-width=".6"/>')
    # reflet le long du corps
    g.append(f'<rect x="{x0 + 8:.2f}" y="{haut + r * .28:.2f}" width="{xs - x0 - 14:.2f}" height="{r * .16:.2f}" rx="{r * .08:.2f}" fill="#fff" fill-opacity=".38"/>')
    return d, f'<symbol id="{id_}-cote" viewBox="0 12 {W:.1f} 48" overflow="visible"><g class="forme">{"".join(g)}</g></symbol>'

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
<radialGradient id="cul" cx=".5" cy=".5" r=".5" fx=".35" fy=".32">
  <stop offset="0" stop-color="#fff" stop-opacity=".18"/><stop offset=".62" stop-color="#000" stop-opacity=".08"/>
  <stop offset=".86" stop-color="#fff" stop-opacity=".28"/><stop offset="1" stop-color="#000" stop-opacity=".55"/></radialGradient>
<radialGradient id="piqure" cx=".5" cy=".5" r=".5" fx=".6" fy=".62">
  <stop offset="0" stop-color="#000" stop-opacity=".55"/><stop offset=".7" stop-color="#000" stop-opacity=".25"/>
  <stop offset="1" stop-color="#fff" stop-opacity=".12"/></radialGradient>
<linearGradient id="or-plat" x1="0" y1="0" x2="1" y2="0">
  <stop offset="0" stop-color="#6e5317"/><stop offset=".3" stop-color="#f3dc8f"/><stop offset=".55" stop-color="#c9a646"/>
  <stop offset="1" stop-color="#5a4210"/></linearGradient>'''
IDS = {"bouteille-couchee": "bordelaise", "bouteille-champagne": "champagne", "bouteille-bourguignonne": "bourguignonne", "bouteille-flute": "flute"}
toutes_d, symboles = [], []
for id_, forme in IDS.items():
    for fabrique in (lambda: bouteille(id_, forme == "champagne", None if forme == "champagne" else forme), lambda: fond(id_, forme), lambda: cote(id_, forme)):
        dd, sy = fabrique()
        toutes_d += dd
        symboles.append(sy)
defs = "<defs>" + communs + "".join(toutes_d) + "</defs>"
open("symboles.svg.txt", "w").write(defs + "\n" + "\n".join(symboles))
vin, champ, bourg, flute = symboles[0], symboles[3], symboles[6], symboles[9]
vin = vin + champ + bourg + flute
champ = ""
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
