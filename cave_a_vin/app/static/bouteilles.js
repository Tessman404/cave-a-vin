/* Tessvine — dessin des bouteilles en SVG.
 *
 * Deux vues :
 *  - Bouteilles.debout(vin, taille) : la bouteille vue de face, avec une étiquette générée à partir des vraies
 *    informations du vin (listes, fiches, suggestions) ;
 *  - Bouteilles.couchee(vin) : les couleurs à appliquer à la bouteille couchée du plan de cave (symboles de index.html).
 *
 * Chaque forme est décrite par son profil réel (hauteur, demi-largeur) de la bague au culot ; la silhouette est une
 * courbe lisse passant par ces points. Le verre et le vin visible dépendent du type de bouteille et de la couleur du vin.
 */
const Bouteilles = (() => {
  const CX = 60;           // axe de la bouteille dans le repère 120 × 360
  let compteur = 0;        // identifiants uniques des découpes (une page peut contenir beaucoup de bouteilles)

  // Profils : [y, demi-largeur] de haut en bas. « capsule » : bas de la capsule ; « epaule » : début du corps plein ;
  // « etiquette » : [haut, bas, largeur relative] ; « niveau » : hauteur du vin dans une bouteille en verre blanc.
  const FORMES = {
    bordelaise: {
      profil: [[11, 9.4], [17, 9.6], [19, 8.1], [26, 8], [60, 8.3], [86, 9.4], [98, 13.5], [108, 21], [117, 27.8], [126, 30.6], [134, 31],
        [340, 31], [347, 30], [352, 27]],
      capsule: 64, epaule: 134, etiquette: [176, 292, 0.94], niveau: 112, coin: 3,
    },
    bourguignonne: {
      profil: [[11, 10], [17, 10.2], [19, 8.6], [26, 8.5], [62, 9.4], [92, 12.6], [122, 19.5], [150, 26.5], [174, 31.4], [192, 33.2], [204, 33.5],
        [341, 33.5], [348, 32], [352, 29]],
      capsule: 68, epaule: 204, etiquette: [212, 300, 0.92], niveau: 120, coin: 3,
    },
    champagne: {
      profil: [[7, 10.6], [12, 11.2], [19, 11.2], [22, 9.6], [30, 9.6], [72, 10.6], [100, 14.2], [128, 21.5], [156, 29.5], [178, 34], [194, 35.6],
        [204, 35.8], [340, 35.8], [348, 34], [352, 30.5]],
      capsule: 122, epaule: 204, etiquette: [216, 308, 0.86], niveau: 130, coin: 14,
    },
    flute: {
      profil: [[13, 8.3], [18, 8.5], [20, 7.4], [27, 7.3], [64, 8], [104, 11.4], [146, 17.6], [184, 22.8], [212, 25.2], [226, 25.6],
        [343, 25.6], [349, 24.2], [353, 21.5]],
      capsule: 62, epaule: 226, etiquette: [238, 330, 0.98], niveau: 120, coin: 3,
    },
    clavelin: {
      profil: [[74, 9.4], [79, 9.6], [81, 8.2], [88, 8.1], [112, 8.6], [122, 13], [132, 22], [142, 30], [150, 33.4], [158, 34.2],
        [341, 34.2], [348, 32.6], [352, 29]],
      capsule: 112, epaule: 158, etiquette: [186, 290, 0.9], niveau: 140, coin: 3,
    },
  };

  const sans = (t) => String(t || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  const contient = (t, mots) => mots.some((m) => t.includes(m));

  /** Forme de la bouteille d'après l'appellation, la région, les cépages et la couleur. */
  function forme(vin) {
    const t = sans([vin.appellation, vin.region, vin.cepages, vin.nom, vin.format].join(" "));
    if (vin.couleur === "effervescent" || contient(t, ["champagne", "cremant", "prosecco", "cava", "blanquette", "petillant"])) return "champagne";
    if (contient(t, ["clavelin", "vin jaune", "chateau-chalon", "chateau chalon"])) return "clavelin";
    if (contient(t, ["alsace", "riesling", "gewurz", "sylvaner", "pinot gris", "muscat d'alsace", "moselle", "mosel", "rheingau", "tokaj"])) return "flute";
    if (contient(t, ["bourgogne", "chablis", "beaujolais", "morgon", "fleurie", "brouilly", "julienas", "moulin-a-vent", "pommard", "meursault",
      "gevrey", "nuits", "volnay", "beaune", "pouilly-fuisse", "macon", "rhone", "cote-rotie", "cote rotie", "hermitage", "chateauneuf",
      "gigondas", "cornas", "saint-joseph", "crozes", "condrieu", "vacqueyras", "pinot noir", "chardonnay", "loire", "sancerre", "chinon",
      "bourgueil", "vouvray", "savennieres", "jura", "savoie", "languedoc", "minervois", "corbieres", "fitou", "faugeres", "pic saint-loup",
      "bandol", "cotes du rhone", "cotes-du-rhone", "gamay", "syrah", "grenache"])) return "bourguignonne";
    return "bordelaise";
  }

  // Couleurs : verre, vin (visible si le verre est blanc), capsule, encre et papier de l'étiquette.
  function couleurs(vin, f) {
    const c = vin.couleur || "rouge";
    const verreBlanc = { teinte: "#dfe6dc", blanc: true };
    let verre, vinC, capsule, capsule2, papier = "#f1e9d8", encre = "#2a1f1c", accent = "#7c1630";
    if (c === "rouge") {
      verre = f === "bourguignonne" ? { teinte: "#2f2c17" } : f === "flute" ? { teinte: "#2c3c1f" } : { teinte: "#1c261d" };
      vinC = "#4a0f1d"; capsule = f === "bourguignonne" ? "#2a2424" : "#6d1328"; capsule2 = "#b8954f";
    } else if (c === "blanc") {
      if (f === "bourguignonne") { verre = { teinte: "#4d5626" }; capsule = "#c9a24b"; }
      else if (f === "flute") { verre = { teinte: "#3f6a2c" }; capsule = "#a8b35a"; }
      else { verre = verreBlanc; capsule = "#e7dcbc"; }
      vinC = "#e2c55e"; capsule2 = "#9c7b2a"; accent = "#8a6a18";
    } else if (c === "rose") {
      verre = verreBlanc; vinC = "#f0a0a6"; capsule = "#f4ece6"; capsule2 = "#d48b98"; papier = "#fbf6f2"; accent = "#b04a68";
    } else if (c === "liquoreux") {
      verre = verreBlanc; vinC = "#d6952a"; capsule = "#b58628"; capsule2 = "#6f4f12"; accent = "#8a5a10";
    } else if (c === "effervescent") {
      verre = { teinte: "#14231a" }; vinC = "#e8d38a"; capsule = "#c9a646"; capsule2 = "#6e5317";
      papier = "#191717"; encre = "#e9d9a6"; accent = "#d8b860";
    } else {
      verre = { teinte: "#2a2338" }; vinC = "#5b3a6e"; capsule = "#3a3348"; capsule2 = "#a99bc4";
    }
    return { verre, vin: vinC, capsule, capsule2, papier, encre, accent };
  }

  /* --- silhouette : spline lisse passant par les points du profil --------------------------------------------- */
  function cote(pts, signe) {
    // côté droit (signe +1) de haut en bas ou gauche (signe -1) de bas en haut, en Catmull-Rom converti en Bézier
    const p = pts.map(([y, r]) => [CX + signe * r, y]);
    const ordre = signe > 0 ? p : p.slice().reverse();
    let d = "";
    for (let i = 0; i < ordre.length - 1; i++) {
      const p0 = ordre[Math.max(0, i - 1)], p1 = ordre[i], p2 = ordre[i + 1], p3 = ordre[Math.min(ordre.length - 1, i + 2)];
      const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
      const c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
      d += ` C${c1[0].toFixed(2)},${c1[1].toFixed(2)} ${c2[0].toFixed(2)},${c2[1].toFixed(2)} ${p2[0].toFixed(2)},${p2[1].toFixed(2)}`;
    }
    return d;
  }
  const cache = {};
  function silhouette(f) {
    if (cache[f]) return cache[f];
    const pts = FORMES[f].profil;
    const [y0, r0] = pts[0], [yn, rn] = pts[pts.length - 1];
    // haut arrondi (bague), culot légèrement creusé
    const d = `M${CX - r0},${y0} Q${CX},${y0 - 3.5} ${CX + r0},${y0}${cote(pts, 1)} Q${CX},${yn + 2.2} ${CX - rn},${yn}${cote(pts, -1)} Z`;
    return (cache[f] = d);
  }
  function rayonA(f, y) {
    const p = FORMES[f].profil;
    for (let i = 0; i < p.length - 1; i++) if (y >= p[i][0] && y <= p[i + 1][0]) {
      const t = (y - p[i][0]) / (p[i + 1][0] - p[i][0]);
      return p[i][1] + t * (p[i + 1][1] - p[i][1]);
    }
    return p[p.length - 1][1];
  }

  const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));

  /** Coupe un texte en lignes d'au plus `max` caractères (au plus `lignes` lignes, la dernière abrégée). */
  function lignes(texte, max, n) {
    // un mot composé trop long se coupe après un trait d'union (Entre-deux- / Mers)
    const mots = String(texte || "").split(/\s+/).filter(Boolean)
      .flatMap((m) => (m.length > max && m.includes("-") ? m.split(/(?<=-)/) : [m]));
    const res = [];
    let cour = "";
    for (const m of mots) {
      const suite = cour.endsWith("-") ? cour + m : (cour + " " + m).trim();
      if (suite.length <= max) cour = suite;
      else { if (cour) res.push(cour); cour = m; }
    }
    if (cour) res.push(cour);
    if (res.length > n) { res.length = n; res[n - 1] = res[n - 1].slice(0, max - 1).replace(/[\s-]+$/, "") + "…"; }
    return res;  // un mot seul trop long reste entier : il est resserré à l'affichage
  }

  /* --- étiquette ------------------------------------------------------------------------------------------- */
  function etiquette(vin, f, col, detail, id) {
    const [haut, bas, larg] = FORMES[f].etiquette;
    const r = rayonA(f, (haut + bas) / 2) * larg;
    const x = CX - r, w = 2 * r, h = bas - haut;
    const champagne = f === "champagne";
    const fond = `<rect x="${x.toFixed(1)}" y="${haut}" width="${w.toFixed(1)}" height="${h}" rx="${FORMES[f].coin}" fill="${col.papier}"/>`
      + `<rect x="${(x + 3).toFixed(1)}" y="${haut + 3}" width="${(w - 6).toFixed(1)}" height="${h - 6}" rx="${Math.max(1, FORMES[f].coin - 2)}" fill="none" stroke="${col.accent}" stroke-opacity=".55" stroke-width=".8"/>`;
    let texte = "";
    if (detail === "silhouette") {
      // trop petit pour être lu : on suggère une étiquette (bandeau et filet)
      texte = `<rect x="${(x + 8).toFixed(1)}" y="${(haut + h * 0.4).toFixed(1)}" width="${(w - 16).toFixed(1)}" height="${(h * 0.13).toFixed(1)}" fill="${col.accent}" opacity=".85"/>`
        + `<rect x="${(x + 14).toFixed(1)}" y="${(haut + h * 0.66).toFixed(1)}" width="${(w - 28).toFixed(1)}" height="2.5" fill="${col.encre}" opacity=".35"/>`;
    } else if (detail === "mini") {
      // vignette : le millésime (ou l'initiale) en grand, lisible même petit
      const grand = vin.millesime ? String(vin.millesime) : String(vin.nom || "?").trim().charAt(0).toUpperCase();
      const taille = vin.millesime ? Math.min(30, (w - 6) / 2.15) : 44;
      texte = `<rect x="${(x + 6).toFixed(1)}" y="${haut + 9}" width="${(w - 12).toFixed(1)}" height="2" fill="${col.accent}" opacity=".75"/>`
        + `<text x="${CX}" y="${(haut + h / 2 + taille * 0.34).toFixed(1)}" class="b-mil" font-size="${taille.toFixed(1)}" fill="${col.encre}">${esc(grand)}</text>`
        + `<rect x="${(x + 6).toFixed(1)}" y="${bas - 11}" width="${(w - 12).toFixed(1)}" height="2" fill="${col.accent}" opacity=".75"/>`;
    } else {
      // mise en page : le nom d'abord, le millésime en pied ; domaine et appellation seulement s'il reste de la place.
      // La taille des textes s'adapte à la largeur de l'étiquette : un mot long est réduit, jamais coupé.
      const utile = w - 10;
      const t = [];
      const ajuste = (texte, taille, facteur, min) => {
        const tt = Math.max(min, Math.min(taille, utile / Math.max(1, texte.length * facteur)));
        return { texte, taille: tt, trop: texte.length * facteur * tt > utile };
      };
      const ligne = (o, y, classe, couleur) => `<text x="${CX}" y="${y.toFixed(1)}" class="${classe}" font-size="${o.taille.toFixed(1)}" fill="${couleur}"`
        + `${o.trop ? ` textLength="${utile}" lengthAdjust="spacingAndGlyphs"` : ""}>${esc(o.texte)}</text>`;
      // nom : 1 ou 2 lignes, taille réglée sur le mot le plus long
      const motMax = Math.max(...String(vin.nom || "Sans nom").split(/\s+/).map((m) => m.length));
      let tNom = Math.max(9, Math.min(13, utile / (motMax * 0.5)));
      const parLigne = Math.max(4, Math.floor(utile / (tNom * 0.5)));
      const nom = lignes(vin.nom || "Sans nom", parLigne, 2).map((l) => ajuste(l, tNom, 0.5, 8.5));
      const dom = detail === "grand" && vin.domaine && sans(vin.domaine) !== sans(vin.nom) ? ajuste(vin.domaine.toUpperCase(), 6.6, 0.78, 5.2) : null;
      const app = detail === "grand" && (vin.appellation || vin.region) && sans(vin.appellation || vin.region) !== sans(vin.nom)
        ? ajuste(vin.appellation || vin.region, 9.5, 0.44, 7.5) : null;
      const pied = vin.millesime || champagne ? 32 : 10;
      const dispo = h - 12 - pied;
      const hNom = nom.reduce((n, l) => n + l.taille * 1.08, 0);
      let blocs = [dom && { o: dom, h: 13, c: "b-dom" }, { nom: true, h: hNom }, app && { o: app, h: 13, c: "b-app" }].filter(Boolean);
      const total = () => blocs.reduce((n, b) => n + b.h, 0);
      if (total() > dispo) blocs = blocs.filter((b) => b.c !== "b-app");
      if (total() > dispo) blocs = blocs.filter((b) => b.c !== "b-dom");
      if (total() > dispo && nom.length > 1) { nom.length = 1; nom[0].texte = nom[0].texte.replace(/…?$/, "…"); blocs = [{ nom: true, h: nom[0].taille * 1.08 }]; }
      let y = haut + 6 + (dispo - total()) / 2;
      for (const b of blocs) {
        if (b.nom) nom.forEach((l) => { y += l.taille * 1.08; t.push(ligne(l, y - l.taille * 0.18, "b-nom", col.encre)); });
        else { y += b.h; t.push(ligne(b.o, y - 3.5, b.c, col.encre)); }
      }
      if (vin.millesime || champagne) {
        t.push(`<rect x="${CX - 9}" y="${bas - 30}" width="18" height=".8" fill="${col.accent}" opacity=".8"/>`);
        t.push(vin.millesime ? `<text x="${CX}" y="${bas - 11}" class="b-mil" font-size="15" fill="${col.accent}">${esc(vin.millesime)}</text>`
          : `<text x="${CX}" y="${bas - 13}" class="b-dom" font-size="6.6" fill="${col.accent}">BRUT</text>`);
      }
      texte = `<g clip-path="url(#${id}-et)">${t.join("")}</g>`;
    }
    // ombre de courbure : l'étiquette suit le cylindre
    const galbe = `<rect x="${x.toFixed(1)}" y="${haut}" width="${w.toFixed(1)}" height="${h}" rx="${FORMES[f].coin}" fill="url(#b-galbe)"/>`;
    const clip = `<clipPath id="${id}-et"><rect x="${(x + 4).toFixed(1)}" y="${haut + 3}" width="${(w - 8).toFixed(1)}" height="${h - 6}"/></clipPath>`;
    return { defs: clip, svg: fond + texte + galbe };
  }

  /* --- bouteille vue de face --------------------------------------------------------------------------------- */
  /** taille : "silhouette" (icône, sans texte), "mini" (vignette : millésime en grand), "moyen" (nom et millésime),
   *  "grand" (fiche : domaine, nom, appellation, millésime). */
  function debout(vin, taille = "moyen") {
    const f = forme(vin);
    const F = FORMES[f];
    const col = couleurs(vin, f);
    const id = `b${++compteur}`;
    const d = silhouette(f);
    const parts = [];
    // ombre portée au sol
    parts.push(`<ellipse cx="${CX}" cy="354" rx="${(F.profil[F.profil.length - 2][1] * 1.25).toFixed(1)}" ry="5" fill="url(#b-sol)"/>`);
    // verre
    parts.push(`<path d="${d}" fill="${col.verre.teinte}"${col.verre.blanc ? ' fill-opacity=".3"' : ""}/>`);
    if (col.verre.blanc) {
      // verre blanc : on voit le vin, sous un léger voile de verre
      parts.push(`<g clip-path="url(#${id}-s)"><rect x="0" y="${F.niveau}" width="120" height="${360 - F.niveau}" fill="${col.vin}"/>`
        + `<rect x="0" y="${F.niveau}" width="120" height="3" fill="#fff" opacity=".35"/></g>`);
      parts.push(`<path d="${d}" fill="#fff" opacity=".1"/>`);
    } else {
      // verre teinté : un reflet de vin très discret dans la masse
      parts.push(`<g clip-path="url(#${id}-s)"><rect x="0" y="${F.niveau}" width="120" height="${360 - F.niveau}" fill="${col.vin}" opacity="${col.vin === "#4a0f1d" ? ".3" : ".2"}"/></g>`);
    }
    // modelé du cylindre
    parts.push(`<path d="${d}" fill="url(#b-modele)"/>`);
    // étiquette
    const et = taille === "aucune" ? null : etiquette(vin, f, col, taille, id);
    if (et) parts.push(et.svg);
    // capsule (collerette dorée et col étiqueté pour le champagne)
    const rCap = Math.max(...F.profil.filter(([y]) => y <= F.capsule).map(([, r]) => r), rayonA(f, F.capsule)) + 1;
    const xCap = (CX - rCap).toFixed(1), wCap = (2 * rCap).toFixed(1);
    parts.push(`<g clip-path="url(#${id}-s)"><rect x="${xCap}" y="0" width="${wCap}" height="${F.capsule}" fill="${col.capsule}"/>`
      + `<rect x="${xCap}" y="0" width="${wCap}" height="${F.capsule}" fill="url(#b-metal)"/>`
      + `<rect x="0" y="${F.capsule - 2}" width="120" height="2" fill="#000" opacity=".28"/>`
      + (f === "champagne" ? `<rect x="0" y="${F.capsule - 16}" width="120" height="7" fill="${col.capsule2}" opacity=".55"/>` : "")
      + `<rect x="0" y="${F.profil[0][0] + 4}" width="120" height="1.2" fill="${col.capsule2}" opacity=".6"/></g>`);
    // reflets : un filet net à gauche, un reflet doux d'épaule, un liseré clair à droite
    const rCorps = F.profil[F.profil.length - 3][1];
    parts.push(`<rect x="${(CX - rCorps * 0.62).toFixed(1)}" y="${F.epaule + 6}" width="${(rCorps * 0.13).toFixed(1)}" height="${(340 - F.epaule - 16).toFixed(1)}" rx="2" fill="url(#b-reflet)"/>`);
    parts.push(`<path d="M${(CX - rCorps * 0.55).toFixed(1)},${F.epaule - 4} Q${(CX - rCorps * 0.2).toFixed(1)},${F.epaule - (F.epaule - F.capsule) * 0.55} ${(CX - 4).toFixed(1)},${F.capsule + 10}" fill="none" stroke="#fff" stroke-opacity=".28" stroke-width="2.4" stroke-linecap="round"/>`);
    parts.push(`<rect x="${(CX + rCorps * 0.78).toFixed(1)}" y="${F.epaule + 4}" width="1.4" height="${(340 - F.epaule - 12).toFixed(1)}" fill="#fff" opacity=".14"/>`);
    // culot
    parts.push(`<ellipse cx="${CX}" cy="349" rx="${(rCorps * 0.8).toFixed(1)}" ry="2.2" fill="#000" opacity=".28"/>`);
    const defs = `<defs><clipPath id="${id}-s"><path d="${d}"/></clipPath>${et ? et.defs : ""}</defs>`;
    const titre = [vin.nom, vin.millesime].filter(Boolean).join(" ");
    return `<svg class="bouteille-debout forme-${f}" viewBox="0 0 120 362" role="img" aria-label="${esc(titre)}">${defs}${parts.join("")}</svg>`;
  }

  /** Couleurs de la bouteille couchée du plan : verre (ou vin visible pour un verre blanc) et capsule.
   *  La couleur du vin reste reconnaissable d'un coup d'œil : un rouge reste grenat, un blanc reste doré. */
  const SYMBOLES = { bordelaise: "bouteille-couchee", bourguignonne: "bouteille-bourguignonne", flute: "bouteille-flute",
    champagne: "bouteille-champagne", clavelin: "bouteille-bourguignonne" };
  function couchee(vin) {
    const f = forme(vin);
    const col = couleurs(vin, f);
    const c = vin.couleur || "rouge";
    let verre;
    if (c === "rouge") verre = f === "bourguignonne" ? "#44141f" : "#3a0f1c";
    else if (c === "effervescent") verre = "#1d3526";
    else if (c === "autre") verre = "#4a3d78";
    else verre = col.verre.blanc ? melange(col.vin, "#ffffff", 0.12) : melange(col.verre.teinte, col.vin, 0.65);
    return { forme: f, verre, capsule: col.capsule, symbole: SYMBOLES[f] };
  }
  function melange(a, b, t) {
    const h = (s) => [1, 3, 5].map((i) => parseInt(s.slice(i, i + 2), 16));
    const [x, y] = [h(a), h(b)];
    return "#" + x.map((v, i) => Math.round(v + (y[i] - v) * t).toString(16).padStart(2, "0")).join("");
  }

  return { debout, couchee, forme, couleurs };
})();
