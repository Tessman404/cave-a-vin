/* Cave à vin — application web monopage, sans dépendance. */
"use strict";

const $ = (sel, el = document) => el.querySelector(sel);
const $$ = (sel, el = document) => [...el.querySelectorAll(sel)];
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const euros = (v) => v == null ? "—" : new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: v >= 1000 ? 0 : 2 }).format(v);
const nombre = (v) => new Intl.NumberFormat("fr-FR").format(v ?? 0);
const dateFr = (d) => d ? new Date(d.length === 10 ? d + "T12:00:00" : d).toLocaleDateString("fr-FR", { day: "numeric", month: "short", year: "numeric" }) : "";
const aujourdhui = () => new Date().toISOString().slice(0, 10);
const pluriel = (n, mot, motPluriel) => `${nombre(n)} ${n > 1 ? (motPluriel || mot + "s") : mot}`;
const COULEURS_CSS = ["rouge", "blanc", "rose", "effervescent", "liquoreux", "autre"];
const ICONES_STATUT = { trop_jeune: "⏳", a_boire: "✓", apogee: "★", urgent: "⚠", depasse: "✕", inconnu: "?" };

let REF = null;          // référentiel (couleurs, statuts, plats, autocomplétion…)
let CAPACITES = null;    // détourage, fonds, IA disponibles
let ajout = null;        // ajout en cours : { champs, code_barre, brouillon, fond, source }
let filtresVins = { q: "", couleur: "", statut: "", cave_id: "", stock: "1", tri: "nom" };

/* ------------------------------------------------------------------ API */

const cleAPI = {
  lire() { try { return localStorage.getItem("cave-api-key") || ""; } catch { return ""; } },
  ecrire(v) { try { v ? localStorage.setItem("cave-api-key", v) : localStorage.removeItem("cave-api-key"); } catch { /* navigation privée */ } },
};

async function api(methode, chemin, corps, brut) {
  const entetes = {};
  const cle = cleAPI.lire();
  if (cle) entetes["X-API-Key"] = cle;
  let body;
  if (brut !== undefined) { body = brut; entetes["Content-Type"] = "text/plain; charset=utf-8"; }
  else if (corps !== undefined) { body = JSON.stringify(corps); entetes["Content-Type"] = "application/json"; }
  const rep = await fetch("api/" + chemin, { method: methode, headers: entetes, body });
  if (rep.status === 401) {
    const saisie = prompt("Cette cave est protégée par une clé d'API. Saisissez-la :");
    if (saisie) { cleAPI.ecrire(saisie.trim()); return api(methode, chemin, corps, brut); }
  }
  const type = rep.headers.get("Content-Type") || "";
  const data = type.includes("json") ? await rep.json() : await rep.text();
  if (!rep.ok) throw new Error((data && data.erreur) || `Erreur ${rep.status}`);
  return data;
}

const avecCle = (url) => { const c = cleAPI.lire(); return c ? url + (url.includes("?") ? "&" : "?") + "cle=" + encodeURIComponent(c) : url; };
const urlPhoto = (vin) => avecCle(`api/vins/${vin.id}/photo?v=${encodeURIComponent(vin.updated_at || "")}`);

/* ------------------------------------------------------------------ petits composants */

function toast(message, erreur = false, duree) {
  const t = $("#toast");
  t.textContent = message;
  t.className = "visible" + (erreur ? " erreur" : "");
  clearTimeout(toast.minuteur);
  toast.minuteur = setTimeout(() => (t.className = ""), duree || (erreur ? 5000 : 2500));
}

const pastille = (couleur) => `<span class="pastille ${esc(couleur)}" title="${esc(REF.couleurs[couleur] || couleur)}"></span>`;
const badgeStatut = (s) => `<span class="statut ${esc(s)}"><span aria-hidden="true">${ICONES_STATUT[s] || ""}</span>${esc(REF.statuts[s] || s)}</span>`;
const etoiles = (n) => n == null ? "" : `<span class="etoiles" title="${n} / 5">${"★".repeat(Math.round(n))}${"☆".repeat(5 - Math.round(n))}</span>`;
const titreVin = (v) => `${esc(v.nom)}${v.millesime ? " " + esc(v.millesime) : ""}`;
const sousTitre = (v) => [...new Set([v.domaine, v.appellation, v.region].filter(Boolean))].map(esc).join(" · ");

function bouteilleSVG(couleur) {
  const c = COULEURS_CSS.includes(couleur) ? couleur : "autre";
  return `<svg viewBox="0 0 26 64" aria-hidden="true"><path d="M10 2h6v14c0 3 6 6 6 13v31a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V29c0-7 6-10 6-13z" fill="var(--c-${c})"/><rect x="4" y="34" width="18" height="13" rx="1" fill="var(--surface)" opacity=".85"/></svg>`;
}

function options(dict, selection, vide) {
  return (vide !== undefined ? `<option value="">${esc(vide)}</option>` : "") +
    Object.entries(dict).map(([k, v]) => `<option value="${esc(k)}"${String(k) === String(selection ?? "") ? " selected" : ""}>${esc(v)}</option>`).join("");
}

function datalist(id, valeurs) {
  return `<datalist id="${id}">${(valeurs || []).map((v) => `<option value="${esc(v)}">`).join("")}</datalist>`;
}

/** Barres horizontales étiquetées : le texte porte l'identité, la couleur la renforce. */
function barres(lignes, { couleur = false, lien } = {}) {
  if (!lignes.length) return `<p class="muted">Aucune donnée.</p>`;
  const max = Math.max(...lignes.map((l) => l.bouteilles), 1);
  return `<div class="barres">${lignes.map((l) => {
    const fond = couleur ? `background: var(--c-${COULEURS_CSS.includes(l.cle) ? l.cle : "autre"})` : "";
    const nom = `${couleur ? pastille(l.cle) : ""}<span class="tronque">${esc(l.label)}</span>`;
    return `<div class="barre-ligne" title="${esc(l.label)} : ${pluriel(l.bouteilles, "bouteille")}">
      <span class="nom">${lien ? `<a href="${lien(l)}">${nom}</a>` : nom}</span>
      <div class="piste"><div class="remplie" style="width:${(100 * l.bouteilles / max).toFixed(1)}%;${fond}"></div></div>
      <span class="nombre">${nombre(l.bouteilles)}</span></div>`;
  }).join("")}</div>`;
}

function histogramme(lignes) {
  const valides = lignes.filter((l) => l.cle !== "—");
  if (!valides.length) return `<p class="muted">Aucun millésime renseigné.</p>`;
  const max = Math.max(...valides.map((l) => l.bouteilles));
  const pas = Math.ceil(valides.length / 10);
  return `<div class="histogramme" role="img" aria-label="Bouteilles par millésime">${valides.map((l) =>
    `<div class="col" title="${esc(l.label)} : ${pluriel(l.bouteilles, "bouteille")}"><div style="height:${(100 * l.bouteilles / max).toFixed(1)}%"></div></div>`).join("")}</div>
    <div class="axe-x">${valides.map((l, i) => `<span>${i % pas === 0 ? esc(String(l.label).slice(-2) === String(l.label) ? l.label : "’" + String(l.label).slice(-2)) : ""}</span>`).join("")}</div>`;
}

/* ------------------------------------------------------------------ dialogues */

function dialogue(html, { onSubmit, large } = {}) {
  const d = $("#dialogue");
  d.innerHTML = `<form method="dialog">${html}</form>`;
  d.style.width = large ? "min(760px, calc(100% - 32px))" : "";
  const form = $("form", d);
  $$("[data-fermer]", d).forEach((b) => b.addEventListener("click", (e) => { e.preventDefault(); d.close(); }));
  if (onSubmit) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const bouton = $("button[type=submit]", form);
      if (bouton) bouton.disabled = true;
      try {
        await onSubmit(Object.fromEntries(new FormData(form)), form);
        d.close();
      } catch (err) {
        toast(err.message, true);
      } finally {
        if (bouton) bouton.disabled = false;
      }
    });
  }
  d.showModal();
  return d;
}

function confirmer(message, libelle = "Confirmer") {
  return new Promise((resolve) => {
    const d = dialogue(`<p>${esc(message)}</p><div class="actions">
      <button class="bouton" data-fermer>Annuler</button>
      <button class="bouton primaire" type="submit">${esc(libelle)}</button></div>`, { onSubmit: () => resolve(true) });
    d.addEventListener("close", () => resolve(false), { once: true });
  });
}

function champEtoiles(nom = "note") {
  return `<label>Note</label><input type="hidden" name="${nom}" value="">
    <div class="notes-etoiles" data-etoiles>${[1, 2, 3, 4, 5].map((n) => `<button type="button" data-n="${n}" aria-label="${n} sur 5">★</button>`).join("")}</div>`;
}

function activerEtoiles(form) {
  const zone = $("[data-etoiles]", form);
  if (!zone) return;
  const champ = zone.previousElementSibling;
  zone.addEventListener("click", (e) => {
    const n = e.target.dataset.n;
    if (!n) return;
    champ.value = champ.value === n ? "" : n;
    $$("button", zone).forEach((b) => b.classList.toggle("on", +b.dataset.n <= +champ.value));
  });
}

async function dialogueSortie(vin, bouteilleId, apres) {
  const d = dialogue(`<h2>Sortir ${titreVin(vin)}</h2>
    <div class="form">
      ${bouteilleId ? "" : `<label>Nombre de bouteilles<input type="number" name="quantite" min="1" max="${vin.stock}" value="1" required></label>`}
      <label>Raison<select name="raison">${options(REF.raisons_sortie, "bue")}</select></label>
      <label>Date<input type="date" name="date" value="${aujourdhui()}"></label>
      <div class="large">${champEtoiles()}</div>
      <label class="large">Commentaire de dégustation<textarea name="commentaire" placeholder="Robe, nez, bouche, accord du jour…"></textarea></label>
    </div>
    <div class="actions"><button class="bouton" data-fermer>Annuler</button><button class="bouton primaire" type="submit">Valider la sortie</button></div>`,
  {
    onSubmit: async (data) => {
      if (bouteilleId) data.bouteille_id = bouteilleId;
      await api("POST", `vins/${vin.id}/sortie`, data);
      toast("Bouteille sortie — santé ! 🍷");
      apres && apres();
    },
  });
  activerEtoiles($("form", d));
}

async function dialogueEntree(vin, apres) {
  const caves = await api("GET", "caves");
  dialogue(`<h2>Ajouter des bouteilles</h2><p class="muted">${titreVin(vin)}</p>
    <div class="form">
      <label>Nombre de bouteilles<input type="number" name="quantite" min="1" max="500" value="1" required></label>
      <label>Raison<select name="raison">${options(REF.raisons_entree, "achat")}</select></label>
      <label>Ranger dans<select name="cave_id"><option value="">Non rangées</option>${caves.map((c) =>
        `<option value="${c.id}">${esc(c.nom)}${c.capacite ? ` (${c.capacite - c.bouteilles} place(s) libre(s))` : ""}</option>`).join("")}</select></label>
      <label>Date<input type="date" name="date" value="${aujourdhui()}"></label>
      <label class="large">Commentaire<input name="commentaire" placeholder="Caviste, salon, prix payé…"></label>
    </div>
    <div class="actions"><button class="bouton" data-fermer>Annuler</button><button class="bouton primaire" type="submit">Ajouter</button></div>`,
  {
    onSubmit: async (data) => {
      await api("POST", `vins/${vin.id}/entree`, data);
      toast("Bouteilles ajoutées");
      apres && apres();
    },
  });
}

/* ------------------------------------------------------------------ pages */

async function pageAccueil(main) {
  const [s, climat] = await Promise.all([api("GET", "stats"), api("GET", "ha/climat").catch(() => null)]);
  if (!s.references) {
    main.innerHTML = `<div class="carte vide"><div style="width:60px;margin:0 auto 12px">${bouteilleSVG("rouge")}</div>
      <h1>Bienvenue dans votre cave</h1>
      <p>Commencez par décrire votre cave (casiers, armoire à vin…) puis ajoutez vos premières bouteilles.</p>
      <div class="actions" style="justify-content:center"><a class="bouton" href="#/caves">Créer une cave</a>
      <a class="bouton primaire" href="#/ajouter">Ajouter un vin</a></div></div>`;
    return;
  }
  const mesure = (m, unite, titre) => {
    if (!m) return "";
    if (m.erreur) return `<div><div class="muted petit-texte">${titre}</div><div class="alerte">${esc(m.erreur)}</div></div>`;
    const alerte = m.alerte ? `<div class="alerte petit-texte">⚠ trop ${m.alerte === "haute" ? "élevée" : "basse"} (idéal ${m.min ?? "?"}–${m.max ?? "?"} ${esc(m.unite || unite)})</div>` : `<div class="muted petit-texte">idéal ${m.min ?? "?"}–${m.max ?? "?"} ${esc(m.unite || unite)}</div>`;
    return `<div><div class="muted petit-texte">${titre}</div><div class="mesure${m.alerte ? " alerte" : ""}">${nombre(m.valeur)} ${esc(m.unite || unite)}</div>${alerte}</div>`;
  };
  const blocClimat = climat && climat.configure
    ? `<div class="carte"><h2>Climat de la cave</h2><div class="climat">${mesure(climat.temperature, "°C", "Température")}${mesure(climat.humidite, "%", "Humidité")}</div></div>`
    : "";
  const ligneVin = (v) => `<li>${pastille(v.couleur)}<div class="grandit"><a class="titre tronque" href="#/vins/${v.id}" style="display:block">${titreVin(v)}</a>
      <span class="muted petit-texte">${esc(v.domaine || "")}${v.garde_fin ? ` · jusqu'en ${v.garde_fin}` : ""}</span></div>
      ${badgeStatut(v.statut)}<span class="muted" title="bouteilles">×${v.stock}</span></li>`;
  const mouvement = (m) => `<li><span aria-hidden="true">${m.type === "entree" ? "📥" : "🍷"}</span>
      <div class="grandit"><span class="titre">${m.vin_id ? `<a href="#/vins/${m.vin_id}">${esc(m.vin_nom)}</a>` : esc(m.vin_nom)}${m.millesime ? " " + m.millesime : ""}</span>
      <div class="muted petit-texte">${m.type === "entree" ? "+" : "−"}${m.quantite} · ${esc((m.type === "entree" ? REF.raisons_entree : REF.raisons_sortie)[m.raison] || m.raison)} · ${dateFr(m.date)}</div></div>${etoiles(m.note)}</li>`;
  main.innerHTML = `
    <div class="entete"><h1>Tableau de bord</h1></div>
    <div class="grille g4" style="margin-bottom:16px">
      <div class="carte tuile"><div class="valeur">${nombre(s.bouteilles)}</div><div class="libelle">bouteilles en cave</div></div>
      <div class="carte tuile"><div class="valeur">${nombre(s.references)}</div><div class="libelle">références</div></div>
      <div class="carte tuile"><div class="valeur">${euros(s.valeur)}</div><div class="libelle">valeur estimée</div></div>
      <div class="carte tuile"><div class="valeur">${nombre(s.bues_annee)}</div><div class="libelle">bues en ${s.annee}</div></div>
    </div>
    <div class="grille g2">
      ${blocClimat}
      <div class="carte ${s.urgents.length ? "tuile alerte" : ""}"><h2>⚠ À boire vite</h2>
        ${s.urgents.length ? `<ul class="liste">${s.urgents.slice(0, 8).map(ligneVin).join("")}</ul>` : `<p class="muted">Rien d'urgent : toutes vos bouteilles sont dans leur fenêtre de garde.</p>`}
        ${s.urgents.length > 8 ? `<a href="#/vins" data-filtre-statut="urgent,depasse">Voir les ${s.urgents.length}</a>` : ""}</div>
      <div class="carte"><h2>Prêts à boire</h2>
        ${s.a_boire.length ? `<ul class="liste">${s.a_boire.slice(0, 8).map(ligneVin).join("")}</ul>` : `<p class="muted">Aucun vin dans sa fenêtre de dégustation.</p>`}
        ${s.a_boire.length > 8 ? `<a href="#/vins" data-filtre-statut="apogee,a_boire">Voir les ${s.a_boire.length}</a>` : ""}</div>
      <div class="carte"><h2>Par couleur</h2>${barres(s.par_couleur, { couleur: true })}</div>
      <div class="carte"><h2>Par garde</h2>${barres(s.par_statut.filter((l) => l.bouteilles))}</div>
      <div class="carte"><h2>Par région</h2>${barres(s.par_region)}</div>
      <div class="carte"><h2>Par millésime</h2>${histogramme(s.par_millesime)}</div>
      <div class="carte"><h2>Par cave</h2>${barres(s.par_cave.map((c) => ({ cle: c.id, label: c.capacite ? `${c.nom} (${c.bouteilles}/${c.capacite})` : c.nom, bouteilles: c.bouteilles })),
        { lien: (l) => l.cle ? `#/caves/${l.cle}` : "#/caves" })}</div>
      <div class="carte"><h2>Derniers mouvements</h2>
        <p class="muted petit-texte">Ce mois-ci : +${s.entrees_mois} / −${s.sorties_mois}</p>
        ${s.derniers_mouvements.length ? `<ul class="liste">${s.derniers_mouvements.map(mouvement).join("")}</ul>` : ""}
        <a href="#/historique">Tout l'historique</a></div>
    </div>`;
  $$("[data-filtre-statut]", main).forEach((a) => a.addEventListener("click", () => {
    filtresVins = { ...filtresVins, statut: a.dataset.filtreStatut, stock: "1" };
  }));
}

async function pageVins(main) {
  const caves = await api("GET", "caves");
  const statuts = { ...REF.statuts, "urgent,depasse": "⚠ À boire vite ou dépassés", "apogee,a_boire": "✓ Prêts à boire" };
  main.innerHTML = `
    <div class="entete"><h1>Mes vins</h1><a class="bouton primaire" href="#/ajouter">+ Ajouter un vin</a></div>
    <div class="filtres">
      <input type="search" name="q" placeholder="Rechercher : nom, domaine, cépage, millésime…" value="${esc(filtresVins.q)}" aria-label="Rechercher">
      <select name="couleur" aria-label="Couleur">${options(REF.couleurs, filtresVins.couleur, "Toutes couleurs")}</select>
      <select name="statut" aria-label="Garde">${options(statuts, filtresVins.statut, "Toutes gardes")}</select>
      <select name="cave_id" aria-label="Cave">${options(Object.fromEntries(caves.map((c) => [c.id, c.nom])), filtresVins.cave_id, "Toutes caves")}</select>
      <select name="stock" aria-label="Stock">${options({ 1: "En cave", 0: "Épuisés", all: "Tous" }, filtresVins.stock)}</select>
      <select name="tri" aria-label="Tri">${options({ nom: "Tri : nom", millesime: "Tri : millésime", region: "Tri : région", garde: "Tri : à boire en premier", stock: "Tri : quantité", valeur: "Tri : valeur", recent: "Tri : derniers ajouts" }, filtresVins.tri)}</select>
    </div>
    <p class="muted petit-texte" id="compte"></p>
    <div id="resultats" class="vins"></div>`;
  const charger = async () => {
    const qs = new URLSearchParams(Object.entries(filtresVins).filter(([, v]) => v !== "")).toString();
    const vins = await api("GET", "vins?" + qs);
    const total = vins.reduce((n, v) => n + v.stock, 0);
    $("#compte", main).textContent = `${pluriel(vins.length, "référence")} · ${pluriel(total, "bouteille")}`;
    $("#resultats", main).innerHTML = vins.length ? vins.map((v) => `
      <a class="carte vin" href="#/vins/${v.id}">
        <div class="vignette">${v.a_photo ? `<img src="${urlPhoto(v)}" alt="" loading="lazy">` : bouteilleSVG(v.couleur)}</div>
        <div class="infos"><span class="nom">${v.favori ? "♥ " : ""}${titreVin(v)}</span>
          <span class="muted petit-texte tronque">${sousTitre(v) || "&nbsp;"}</span>
          <span>${badgeStatut(v.statut)}</span></div>
        <div class="stock">${v.stock}<small>bout.</small></div>
      </a>`).join("") : `<div class="vide" style="grid-column:1/-1">Aucun vin ne correspond.</div>`;
  };
  let minuteur;
  $(".filtres", main).addEventListener("input", (e) => {
    filtresVins[e.target.name] = e.target.value;
    clearTimeout(minuteur);
    minuteur = setTimeout(() => charger().catch((err) => toast(err.message, true)), e.target.type === "search" ? 250 : 0);
  });
  await charger();
}

function frise(v, annee) {
  if (!v.garde_debut && !v.garde_fin) return "";
  const debut = v.garde_debut || v.garde_fin - 3, fin = v.garde_fin || v.garde_debut + 5;
  const min = Math.min(v.millesime || debut - 2, annee, debut) - 1, max = Math.max(fin, annee) + 2;
  const pos = (a) => ((a - min) / (max - min) * 100).toFixed(1) + "%";
  return `<div class="frise" aria-label="Fenêtre de dégustation de ${debut} à ${fin}">
    <div class="piste"></div><div class="zone" style="left:${pos(debut)};width:calc(${pos(fin + 1)} - ${pos(debut)})"></div>
    ${v.garde_apogee ? `<div class="etoile" style="left:${pos(v.garde_apogee + .5)}" title="Apogée ${v.garde_apogee}">★</div>` : ""}
    <div class="repere" style="left:${pos(annee + .5)}"><span>${annee}</span></div>
    <div class="borne" style="left:${pos(debut)}">${debut}</div><div class="borne" style="left:${pos(fin + 1)}">${fin}</div></div>
    <p class="muted petit-texte" style="margin:14px 0 0">À boire de ${debut} à ${fin}${v.garde_apogee ? ` · ★ apogée ${v.garde_apogee}` : ""}</p>`;
}

async function pageVin(main, id) {
  const v = await api("GET", `vins/${id}`);
  const recharger = () => route();
  const prop = (titre, valeur) => valeur || valeur === 0 ? `<div><dt>${titre}</dt><dd>${valeur}</dd></div>` : "";
  const emplacement = (b) => b.cave_id ? `${esc(b.cave_nom)}${b.rangee ? ` — rangée ${b.rangee}, colonne ${b.colonne}` : ""}` : "Non rangée";
  const groupes = {};
  v.bouteilles.forEach((b) => { const k = emplacement(b); groupes[k] = groupes[k] || { b, n: 0 }; groupes[k].n++; });
  main.innerHTML = `
    <p><a href="#/vins">← Mes vins</a></p>
    <div class="fiche">
      <div>
        <div class="photo">${v.a_photo ? `<img src="${urlPhoto(v)}" alt="Étiquette de ${esc(v.nom)}">` : bouteilleSVG(v.couleur)}</div>
        <div class="actions" style="margin-top:8px">
          <label class="bouton petit" style="color:var(--texte)">📷 ${v.a_photo ? "Changer" : "Photo de l'étiquette"}
            <input type="file" accept="image/*" capture="environment" hidden id="photo"></label>
          ${v.a_photo && CAPACITES.detourage ? `<button class="bouton petit" id="changer-fond">🎨 Fond</button>` : ""}
          ${v.a_photo ? `<button class="bouton petit danger" id="suppr-photo">Retirer</button>` : ""}
        </div>
      </div>
      <div class="grille">
        <div class="carte">
          <div class="entete" style="align-items:flex-start">
            <div><h1>${v.favori ? "♥ " : ""}${titreVin(v)}</h1>
              <div class="muted">${sousTitre(v)}</div>
              <div style="margin-top:8px;display:flex;gap:8px;align-items:center;flex-wrap:wrap">${pastille(v.couleur)} ${esc(v.couleur_label)} ${badgeStatut(v.statut)} ${v.note_moyenne != null ? etoiles(v.note_moyenne) : ""}</div></div>
            <div class="compteur">
              <button class="bouton rond" id="moins" ${v.stock ? "" : "disabled"} aria-label="Sortir une bouteille">−</button>
              <div class="valeur" aria-label="bouteilles en cave">${v.stock}</div>
              <button class="bouton rond" id="plus" aria-label="Ajouter une bouteille">+</button>
            </div>
          </div>
          ${frise(v, REF.annee)}
          <div class="actions" style="margin-top:14px">
            <button class="bouton primaire" id="sortir" ${v.stock ? "" : "disabled"}>🍷 Déguster / sortir</button>
            <button class="bouton" id="entrer">📥 Ajouter des bouteilles</button>
            <a class="bouton" href="#/vins/${v.id}/modifier">✎ Modifier</a>
            <button class="bouton" id="favori">${v.favori ? "♥ Retirer des favoris" : "♡ Favori"}</button>
            <button class="bouton danger" id="supprimer">Supprimer</button>
          </div>
        </div>
        <div class="carte"><h2>Caractéristiques</h2><dl class="proprietes">
          ${prop("Appellation", esc(v.appellation))}${prop("Région", esc(v.region))}${prop("Pays", esc(v.pays))}
          ${prop("Cépages", esc(v.cepages))}${prop("Format", esc(v.format))}${prop("Degré", v.degre != null ? v.degre + " %" : "")}
          ${prop("Prix d'achat", v.prix_achat != null ? euros(v.prix_achat) : "")}${prop("Valeur estimée", v.valeur != null ? euros(v.valeur) : "")}
          ${prop("Fournisseur", esc(v.fournisseur))}
          ${prop("À boire", v.garde_debut || v.garde_fin ? `${v.garde_debut || "?"} → ${v.garde_fin || "?"}` : "")}
          ${prop("Apogée", v.garde_apogee)}
        </dl>
        ${v.accords ? `<h3 style="margin-top:14px">Accords</h3><p>${esc(v.accords)}</p>` : ""}
        ${v.notes ? `<h3 style="margin-top:14px">Notes</h3><p style="white-space:pre-line">${esc(v.notes)}</p>` : ""}</div>
        <div class="carte"><h2>Emplacements</h2>
          ${v.bouteilles.length ? `<ul class="liste">${Object.entries(groupes).map(([k, g]) => `<li><span aria-hidden="true">📍</span><span class="grandit">${g.b.cave_id ? `<a href="#/caves/${g.b.cave_id}?vin=${v.id}">${k}</a>` : k}</span><span class="muted">×${g.n}</span></li>`).join("")}</ul>`
            : `<p class="muted">Plus aucune bouteille en cave.</p>`}</div>
        <div class="carte"><h2>Historique & dégustations</h2>
          ${v.mouvements.length ? `<div class="defile"><table class="tableau"><thead><tr><th>Date</th><th>Mouvement</th><th>Note</th><th>Commentaire</th></tr></thead><tbody>
          ${v.mouvements.map((m) => `<tr><td style="white-space:nowrap">${dateFr(m.date)}</td>
            <td style="white-space:nowrap">${m.type === "entree" ? "+" : "−"}${m.quantite} ${esc((m.type === "entree" ? REF.raisons_entree : REF.raisons_sortie)[m.raison] || m.raison)}</td>
            <td>${etoiles(m.note)}</td><td>${esc(m.commentaire)}</td></tr>`).join("")}</tbody></table></div>` : `<p class="muted">Aucun mouvement.</p>`}</div>
      </div>
    </div>`;
  $("#moins", main).onclick = () => dialogueSortie(v, null, recharger);
  $("#sortir", main).onclick = () => dialogueSortie(v, null, recharger);
  $("#plus", main).onclick = () => dialogueEntree(v, recharger);
  $("#entrer", main).onclick = () => dialogueEntree(v, recharger);
  $("#favori", main).onclick = async () => { await api("PUT", `vins/${v.id}`, { favori: !v.favori }); recharger(); };
  $("#supprimer", main).onclick = async () => {
    if (await confirmer(`Supprimer définitivement « ${v.nom} » et ses ${v.stock} bouteille(s) ? L'historique des dégustations est conservé.`, "Supprimer")) {
      await api("DELETE", `vins/${v.id}`);
      toast("Vin supprimé");
      location.hash = "#/vins";
    }
  };
  $("#photo", main).onchange = async (e) => {
    const fichier = e.target.files[0];
    if (!fichier) return;
    toast(CAPACITES.detourage ? "Détourage de la bouteille…" : "Envoi de la photo…", false, 60000);
    try {
      const r = await api("PUT", `vins/${v.id}/photo`, { image: await redimensionner(fichier, 1600), fond: CAPACITES.detourage ? CAPACITES.fond_defaut : "" });
      toast(r.avertissement || "Photo enregistrée", !!r.avertissement);
      recharger();
    } catch (err) { toast(err.message, true); }
  };
  const fond = $("#changer-fond", main);
  if (fond) fond.onclick = () => dialogueFond(async (choix) => {
    await api("POST", `vins/${v.id}/photo/fond`, { fond: choix });
    recharger();
  }, avecCle(`api/vins/${v.id}/photo?original=1&v=${encodeURIComponent(v.updated_at)}`));
  const suppr = $("#suppr-photo", main);
  if (suppr) suppr.onclick = async () => { await api("DELETE", `vins/${v.id}/photo`); recharger(); };
}

function redimensionner(fichier, max = 1200) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const r = Math.min(1, max / Math.max(img.width, img.height));
      const c = document.createElement("canvas");
      c.width = Math.round(img.width * r);
      c.height = Math.round(img.height * r);
      c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
      URL.revokeObjectURL(img.src);
      resolve(c.toDataURL("image/jpeg", 0.85));
    };
    img.onerror = () => reject(new Error("Image illisible"));
    img.src = URL.createObjectURL(fichier);
  });
}

/** Année de la première entrée en cave (sert de référence pour la garde d'un vin sans millésime). */
function anneeAchat(v) {
  const dates = (v.mouvements || []).filter((m) => m.type === "entree").map((m) => m.date).sort();
  return String(dates[0] || v.created_at || "").slice(0, 4);
}

async function pageFormulaire(main, id) {
  const defaut = { couleur: "rouge", pays: "France", format: "75 cl", ...(ajout?.champs || {}), code_barre: ajout?.code_barre || ajout?.champs?.code_barre || "" };
  const [v, caves] = await Promise.all([id ? api("GET", `vins/${id}`) : Promise.resolve(defaut), api("GET", "caves")]);
  const brouillon = !id && ajout?.brouillon ? ajout : null;
  const a = REF.autocompletion;
  const champ = (nom, libelle, attrs = "") => `<label>${libelle}<input name="${nom}" value="${esc(v[nom])}" ${attrs}></label>`;
  main.innerHTML = `
    <p><a href="${id ? `#/vins/${id}` : "#/vins"}">← Retour</a></p>
    <div class="carte"><h1>${id ? "Modifier le vin" : "Ajouter un vin"}</h1>
    ${!id && ajout?.source ? `<p class="muted">${{ off: "📦 Fiche pré-remplie depuis Open Food Facts", ia: "🔎 Fiche pré-remplie par l'IA à partir de l'étiquette", photo: "📷 Complétez la fiche de la bouteille photographiée" }[ajout.source] || ""} : vérifiez et complétez.</p>` : ""}
    ${brouillon ? `<div class="apercu-ajout"><img id="apercu" src="${avecCle(`api/brouillons/${brouillon.brouillon}/image?fond=${brouillon.fond || ""}`)}" alt="Photo de la bouteille">
      ${CAPACITES.detourage ? `<button class="bouton petit" type="button" id="fond-ajout">🎨 Changer de fond</button>` : ""}</div>` : ""}
    <form class="form" id="formulaire" autocomplete="off">
      <fieldset><legend>Identité</legend>
        ${champ("nom", "Nom de la cuvée *", 'required placeholder="Château Margaux, Clos des Mouches…"')}
        ${champ("domaine", "Domaine / producteur", 'list="l-domaines"')}
        ${champ("appellation", "Appellation", 'list="l-appellations"')}
        ${champ("region", "Région", 'list="l-regions"')}
        ${champ("pays", "Pays", 'list="l-pays"')}
        <label>Couleur<select name="couleur">${options(REF.couleurs, v.couleur)}</select></label>
        ${champ("millesime", "Millésime", `type="number" min="1800" max="${REF.annee + 1}" placeholder="Non millésimé"`)}
        ${champ("cepages", "Cépages", 'list="l-cepages" placeholder="Merlot, Cabernet franc"')}
        ${champ("format", "Format", 'list="l-formats"')}
        ${champ("degre", "Degré (%)", 'type="number" step="0.1" min="0" max="25"')}
        ${champ("code_barre", "Code-barres", 'inputmode="numeric" placeholder="Rempli par le scan"')}
      </fieldset>
      <fieldset><legend>Achat & valeur</legend>
        ${champ("prix_achat", "Prix d'achat (€ / bouteille)", 'type="number" step="0.01" min="0"')}
        ${champ("valeur", "Valeur actuelle estimée (€)", 'type="number" step="0.01" min="0"')}
        ${champ("fournisseur", "Fournisseur / caviste", 'list="l-fournisseurs"')}
      </fieldset>
      <fieldset><legend>Garde</legend>
        ${champ("garde_debut", "À boire à partir de", 'type="number" min="1800" max="2200"')}
        ${champ("garde_apogee", "Apogée", 'type="number" min="1800" max="2200"')}
        ${champ("garde_fin", "À boire avant (fin)", 'type="number" min="1800" max="2200"')}
        <div style="align-self:end"><button class="bouton" type="button" id="estimer">✨ Estimer</button></div>
        <p class="muted petit-texte large" style="margin:0">L'estimation est indicative (couleur, appellation, prix, millésime) : renseignez le prix pour qu'elle soit plus juste, et ajustez-la selon le producteur ou les conseils de votre caviste.</p>
      </fieldset>
      ${id ? "" : `<fieldset><legend>Bouteilles</legend>
        <label>Nombre de bouteilles<input type="number" name="quantite" min="0" max="500" value="1"></label>
        <label>Ranger dans<select name="cave_id"><option value="">Non rangées</option>${caves.map((c) => `<option value="${c.id}">${esc(c.nom)}</option>`).join("")}</select></label>
        <label>Raison<select name="raison">${options(REF.raisons_entree, "achat")}</select></label>
      </fieldset>`}
      <label class="large">Accords mets & vins<input name="accords" value="${esc(v.accords)}" placeholder="Agneau, fromages affinés…"></label>
      <label class="large">Notes<textarea name="notes">${esc(v.notes)}</textarea></label>
      <label class="case large"><input type="checkbox" name="favori" value="1" ${v.favori ? "checked" : ""}> ♥ Favori</label>
      <div class="actions large"><button class="bouton primaire" type="submit">${id ? "Enregistrer" : "Ajouter à ma cave"}</button>
        <a class="bouton" href="${id ? `#/vins/${id}` : "#/vins"}" id="annuler">Annuler</a></div>
    </form></div>
    ${datalist("l-domaines", a.domaines)}${datalist("l-appellations", a.appellations)}${datalist("l-regions", [...new Set([...a.regions, "Alsace", "Beaujolais", "Bordeaux", "Bourgogne", "Champagne", "Jura", "Languedoc", "Loire", "Provence", "Rhône", "Roussillon", "Savoie", "Sud-Ouest", "Corse"])].sort())}
    ${datalist("l-pays", [...new Set([...a.pays, "France", "Italie", "Espagne", "Portugal", "Allemagne", "Suisse", "États-Unis", "Argentine", "Chili", "Afrique du Sud", "Australie", "Nouvelle-Zélande"])])}
    ${datalist("l-cepages", a.cepages)}${datalist("l-fournisseurs", a.fournisseurs)}
    ${datalist("l-formats", [...new Set(["37,5 cl", "50 cl", "75 cl", "Magnum 1,5 L", "Jéroboam 3 L", "Clavelin 62 cl", ...a.formats])])}`;
  const form = $("#formulaire", main);
  $("#estimer", main).onclick = async () => {
    const qs = new URLSearchParams({ couleur: form.couleur.value, millesime: form.millesime.value, region: form.region.value,
      appellation: form.appellation.value, prix_achat: form.prix_achat.value, valeur: form.valeur.value,
      annee_achat: id ? anneeAchat(v) : "" });
    const g = await api("GET", "garde?" + qs);
    if (!g.garde_debut) return toast("Pas d'estimation pour cette couleur", true);
    form.garde_debut.value = g.garde_debut; form.garde_apogee.value = g.garde_apogee ?? ""; form.garde_fin.value = g.garde_fin;
    toast(g.reference === "achat"
      ? `Estimé comme ${g.niveau_label}. Sans millésime, la garde est comptée à partir de l'achat (${g.annee_reference})`
      : `Estimé comme ${g.niveau_label}`, false, g.reference === "achat" ? 5000 : undefined);
  };
  $("#annuler", main).onclick = () => { ajout = null; };
  const boutonFond = $("#fond-ajout", main);
  if (boutonFond) boutonFond.onclick = () => dialogueFond(async (choix) => {
    if (choix) await api("POST", `brouillons/${brouillon.brouillon}/rendu`, { fond: choix });
    brouillon.fond = choix;
    $("#apercu", main).src = avecCle(`api/brouillons/${brouillon.brouillon}/image?fond=${choix}`);
  }, avecCle(`api/brouillons/${brouillon.brouillon}/image`));
  // fiche pré-remplie sans garde : on propose tout de suite une estimation
  if (!id && ajout?.champs && !v.garde_fin) $("#estimer", main).click();
  form.onsubmit = async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(form));
    data.favori = !!data.favori;
    if (brouillon) data.photo = { brouillon: brouillon.brouillon, fond: brouillon.fond || "" };
    try {
      const vin = id ? await api("PUT", `vins/${id}`, data) : await api("POST", "vins", data);
      ajout = null;
      REF = await api("GET", "referentiel");
      toast(id ? "Modifications enregistrées" : "Vin ajouté à la cave");
      location.hash = `#/vins/${vin.id}`;
    } catch (err) { toast(err.message, true); }
  };
}

/* ------------------------------------------------------------------ ajout assisté : scan, photo, IA */

function dialogueFond(choisir, urlOriginal) {
  const vignettes = CAPACITES.fonds.map((f) => `<button type="button" class="vignette-fond" data-fond="${esc(f.id)}">
      <img src="fonds/${esc(f.id)}.jpg" alt=""><span>${esc(f.label)}</span></button>`).join("");
  const d = dialogue(`<h2>Choisir le fond</h2>
    <div class="fonds">${vignettes}<button type="button" class="vignette-fond" data-fond=""><img src="${urlOriginal}" alt=""><span>Photo d'origine</span></button></div>
    <p class="muted petit-texte" id="etat-fond"></p>
    <div class="actions"><button class="bouton" data-fermer>Fermer</button></div>`);
  $$("[data-fond]", d).forEach((b) => (b.onclick = async () => {
    $$("[data-fond]", d).forEach((x) => (x.disabled = true));
    $("#etat-fond", d).textContent = "Détourage et mise en scène…";
    try { await choisir(b.dataset.fond); d.close(); toast("Fond appliqué"); }
    catch (err) { $("#etat-fond", d).textContent = err.message; $$("[data-fond]", d).forEach((x) => (x.disabled = false)); }
  }));
}

function chargerScript(src) {
  return new Promise((resolve, reject) => {
    if ($(`script[src="${src}"]`)) return resolve();
    const s = document.createElement("script");
    s.src = src; s.onload = resolve; s.onerror = () => reject(new Error("Lecteur de code-barres indisponible"));
    document.head.appendChild(s);
  });
}

async function lecteurZXing() {
  await chargerScript("vendor/zxing-0.21.3.min.js");
  const Z = window.ZXing;
  const indices = new Map([[Z.DecodeHintType.POSSIBLE_FORMATS, [Z.BarcodeFormat.EAN_13, Z.BarcodeFormat.EAN_8, Z.BarcodeFormat.UPC_A, Z.BarcodeFormat.UPC_E]],
    [Z.DecodeHintType.TRY_HARDER, true]]);
  return new Z.BrowserMultiFormatReader(indices, 300);
}

const FORMATS_NATIFS = ["ean_13", "ean_8", "upc_a", "upc_e"];

async function decoderImage(fichier) {
  const img = new Image();
  img.src = URL.createObjectURL(fichier);
  await img.decode();
  try {
    if ("BarcodeDetector" in window) {
      const codes = await new BarcodeDetector({ formats: FORMATS_NATIFS }).detect(img);
      if (codes.length) return codes[0].rawValue;
    }
    const lecteur = await lecteurZXing();
    return (await lecteur.decodeFromImageElement(img)).getText();
  } catch { return null; } finally { URL.revokeObjectURL(img.src); }
}

/** Ouvre la caméra et renvoie le premier code-barres lu (ou null si l'on annule). */
function scannerEnDirect() {
  return new Promise((resolve) => {
    const d = dialogue(`<h2>Scanner le code-barres</h2>
      <div class="viseur"><video playsinline muted></video><div class="cadre"></div></div>
      <p class="muted petit-texte">Placez le code-barres de la contre-étiquette dans le cadre.</p>
      <div class="actions"><button class="bouton" data-fermer>Annuler</button></div>`);
    const video = $("video", d);
    let fini = false, flux = null, lecteur = null;
    const terminer = (code) => {
      if (fini) return;
      fini = true;
      flux?.getTracks().forEach((t) => t.stop());
      lecteur?.reset();
      if (d.open) d.close();
      resolve(code);
    };
    d.addEventListener("close", () => terminer(null), { once: true });
    (async () => {
      try {
        if ("BarcodeDetector" in window && (await BarcodeDetector.getSupportedFormats()).includes("ean_13")) {
          flux = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
          video.srcObject = flux;
          await video.play();
          const detecteur = new BarcodeDetector({ formats: FORMATS_NATIFS });
          while (!fini) {
            const codes = await detecteur.detect(video).catch(() => []);
            if (codes.length) return terminer(codes[0].rawValue);
            await new Promise((r) => setTimeout(r, 200));
          }
        } else {
          lecteur = await lecteurZXing();
          await lecteur.decodeFromConstraints({ video: { facingMode: "environment" } }, video, (resultat) => {
            if (resultat) terminer(resultat.getText());
          });
        }
      } catch (err) {
        toast("Caméra inaccessible : " + (err.message || err), true);
        terminer(null);
      }
    })();
  });
}

async function pageAjouter(main) {
  CAPACITES = await api("GET", "capacites");
  const direct = !!(navigator.mediaDevices?.getUserMedia && window.isSecureContext);
  main.innerHTML = `
    <div class="entete"><h1>Ajouter un vin</h1></div>
    <div class="tuiles-ajout">
      <button class="carte tuile-ajout" id="t-scan"><span class="icone">▥</span><b>Scanner le code-barres</b><span class="muted">La fiche se remplit toute seule si le vin est connu</span></button>
      <label class="carte tuile-ajout"><span class="icone">📷</span><b>Photographier la bouteille</b>
        <span class="muted">${CAPACITES.ia.possible ? "L'IA lit l'étiquette" : "Photo de la bouteille"}${CAPACITES.detourage ? ", la bouteille est détourée et posée sur un fond de cave" : ""}</span>
        <input type="file" accept="image/*" capture="environment" hidden id="t-photo"></label>
      <a class="carte tuile-ajout" href="#/vins/nouveau" id="t-main"><span class="icone">✎</span><b>Saisir à la main</b><span class="muted">Formulaire complet</span></a>
    </div>
    <form class="filtres" id="code-manuel" style="margin-top:16px;max-width:460px">
      <input name="code" inputmode="numeric" placeholder="… ou tapez le code-barres (13 chiffres)" aria-label="Code-barres">
      <button class="bouton" type="submit">Chercher</button>
    </form>
    <input type="file" accept="image/*" capture="environment" hidden id="photo-code">
    <div id="resultat"></div>`;
  ajout = null;
  const resultat = $("#resultat", main);
  $("#t-main", main).onclick = () => { ajout = null; };

  const montrer = () => resultat.scrollIntoView({ behavior: "smooth", block: "start" });
  const chercher = async (code) => {
    resultat.innerHTML = `<div class="carte chargement">Recherche du code ${esc(code)}…</div>`;
    montrer();
    let r;
    try { r = await api("GET", "scan/" + encodeURIComponent(code)); }
    catch (err) { resultat.innerHTML = `<div class="carte"><p>${esc(err.message)}</p></div>`; return; }
    if (r.local) {
      const v = r.local;
      resultat.innerHTML = `<div class="carte resultat-scan">${v.a_photo ? `<img src="${urlPhoto(v)}" alt="">` : bouteilleSVG(v.couleur)}
        <div><p class="muted">Déjà dans votre cave</p><h2>${titreVin(v)}</h2><p class="muted">${sousTitre(v)}</p><p>${badgeStatut(v.statut)} · ${pluriel(v.stock, "bouteille")}</p>
        <div class="actions"><button class="bouton primaire" id="r-entree">📥 Ajouter des bouteilles</button><a class="bouton" href="#/vins/${v.id}">Voir la fiche</a></div></div></div>`;
      $("#r-entree", resultat).onclick = () => dialogueEntree(v, () => (location.hash = `#/vins/${v.id}`));
      return;
    }
    if (r.externe) {
      const x = r.externe.vin;
      resultat.innerHTML = `<div class="carte resultat-scan">${r.externe.image_url ? `<img src="${esc(r.externe.image_url)}" alt="" referrerpolicy="no-referrer">` : bouteilleSVG(x.couleur || "autre")}
        <div><p class="muted">Trouvé dans Open Food Facts</p><h2>${titreVin(x)}</h2><p class="muted">${sousTitre(x)}</p>
        <div class="actions"><button class="bouton primaire" id="r-suite">Continuer</button>
        <label class="bouton">📷 Prendre ma photo<input type="file" accept="image/*" capture="environment" hidden id="r-photo"></label></div></div></div>`;
      $("#r-suite", resultat).onclick = async () => {
        ajout = { champs: x, code_barre: r.code, source: "off" };
        if (r.externe.image_url) {
          try { ajout.brouillon = (await api("POST", "brouillons", { url: r.externe.image_url })).id; ajout.fond = ""; } catch { /* sans photo */ }
        }
        location.hash = "#/vins/nouveau";
      };
      $("#r-photo", resultat).onchange = (e) => e.target.files[0] && traiterPhoto(e.target.files[0], { code_barre: r.code, champs: x });
      return;
    }
    resultat.innerHTML = `<div class="carte"><h2>Vin inconnu</h2>
      <p>${r.erreur ? esc(r.erreur) + ". " : "Ce code-barres n'est pas dans la base Open Food Facts. "}Prenez la bouteille en photo${CAPACITES.ia.possible ? " : l'IA lira l'étiquette pour remplir la fiche" : ""}.</p>
      <label class="bouton primaire">📷 Photographier la bouteille<input type="file" accept="image/*" capture="environment" hidden id="r-photo"></label></div>`;
    $("#r-photo", resultat).onchange = (e) => e.target.files[0] && traiterPhoto(e.target.files[0], { code_barre: r.code });
  };

  const traiterPhoto = async (fichier, base = {}) => {
    resultat.innerHTML = `<div class="carte traitement"><div class="apercu-ajout"><img id="apercu" alt="Photo de la bouteille"></div>
      <ul class="liste etapes"><li id="e-envoi">⏳ Envoi de la photo…</li>
      ${CAPACITES.detourage ? `<li id="e-detour">⏳ Détourage de la bouteille…</li>` : ""}
      ${CAPACITES.ia.possible ? `<li id="e-ia">⏳ Lecture de l'étiquette par l'IA…</li>` : ""}</ul>
      <div class="actions" id="e-actions" hidden>
        ${CAPACITES.detourage ? `<button class="bouton" id="e-fond">🎨 Changer de fond</button>` : ""}
        <button class="bouton primaire" id="e-suite">Continuer →</button></div></div>`;
    montrer();
    const etape = (id, texte) => { const li = $("#" + id, resultat); if (li) li.textContent = texte; };
    const image = await redimensionner(fichier, 1600);
    $("#apercu", resultat).src = image;
    let ident;
    try { ident = (await api("POST", "brouillons", { image })).id; etape("e-envoi", "✓ Photo reçue"); }
    catch (err) { etape("e-envoi", "✕ " + err.message); return; }
    ajout = { ...base, champs: { ...(base.champs || {}) }, brouillon: ident, fond: "", source: "photo" };
    const lent = setTimeout(() => etape("e-detour", "⏳ Détourage… (la première fois, le modèle de détourage est téléchargé : patientez une minute)"), 6000);
    await Promise.all([
      CAPACITES.detourage && api("POST", `brouillons/${ident}/rendu`, { fond: CAPACITES.fond_defaut })
        .then(() => { ajout.fond = CAPACITES.fond_defaut; $("#apercu", resultat).src = avecCle(`api/brouillons/${ident}/image?fond=${ajout.fond}`); etape("e-detour", "✓ Bouteille détourée"); })
        .catch((err) => etape("e-detour", "✕ Détourage impossible : " + err.message))
        .finally(() => clearTimeout(lent)),
      CAPACITES.ia.possible && api("POST", `brouillons/${ident}/lire`)
        .then((r) => {
          ajout.champs = { ...r.champs, ...ajout.champs };  // les données du code-barres priment
          ajout.source = "ia";
          const lu = [r.champs.nom, r.champs.millesime, r.champs.appellation].filter(Boolean).join(" · ");
          etape("e-ia", lu ? `✓ Étiquette lue : ${lu}` : "✕ L'IA n'a rien pu lire : complétez à la main");
        })
        .catch((err) => etape("e-ia", "✕ Lecture impossible : " + err.message)),
    ]);
    $("#e-actions", resultat).hidden = false;
    $("#e-suite", resultat).onclick = () => (location.hash = "#/vins/nouveau");
    const bf = $("#e-fond", resultat);
    if (bf) bf.onclick = () => dialogueFond(async (choix) => {
      if (choix) await api("POST", `brouillons/${ident}/rendu`, { fond: choix });
      ajout.fond = choix;
      $("#apercu", resultat).src = avecCle(`api/brouillons/${ident}/image?fond=${choix}`);
    }, avecCle(`api/brouillons/${ident}/image`));
  };

  $("#t-photo", main).onchange = (e) => e.target.files[0] && traiterPhoto(e.target.files[0]);
  $("#code-manuel", main).onsubmit = (e) => { e.preventDefault(); const c = e.target.code.value.replace(/\D/g, ""); if (c) chercher(c); };
  $("#photo-code", main).onchange = async (e) => {
    const f = e.target.files[0];
    if (!f) return;
    const code = await decoderImage(f);
    e.target.value = "";
    if (code) chercher(code); else toast("Aucun code-barres lisible sur la photo : réessayez de plus près", true);
  };
  $("#t-scan", main).onclick = async () => {
    if (!direct) return $("#photo-code", main).click();  // pas de caméra en direct (connexion non sécurisée) : photo du code
    const code = await scannerEnDirect();
    if (code) chercher(code);
  };
}

async function pageCaves(main, id, params) {
  const caves = await api("GET", "caves");
  if (!id && caves.length) { location.replace(`#/caves/${caves[0].id}`); return; }
  const onglets = `<nav class="onglets">${caves.map((c) => `<a href="#/caves/${c.id}" class="${c.id === id ? "actif" : ""}">${esc(c.nom)} <span class="muted">${c.bouteilles}</span></a>`).join("")}</nav>`;
  const entete = `<div class="entete"><h1>Plan de cave</h1><button class="bouton primaire" id="nouvelle">+ Nouvelle cave</button></div>`;
  if (!caves.length) {
    main.innerHTML = entete + `<div class="carte vide"><p>Décrivez votre cave : une armoire à vin, un casier, une pièce…<br>Indiquez le nombre de rangées et de colonnes pour obtenir un plan cliquable, ou 0 pour un rangement « en vrac ».</p></div>`;
    $("#nouvelle", main).onclick = () => dialogueCave();
    return;
  }
  const c = await api("GET", `caves/${id}`);
  const surligne = +new URLSearchParams(params).get("vin") || null;
  const parCase = {};
  c.bouteilles.forEach((b) => { if (b.rangee) parCase[`${b.rangee}-${b.colonne}`] = b; });
  let plan = "";
  if (c.capacite) {
    plan = `<div class="plan-conteneur"><div class="plan" style="grid-template-columns: 22px repeat(${c.colonnes}, 40px)"><span></span>`;
    for (let col = 1; col <= c.colonnes; col++) plan += `<span class="entete-col">${col}</span>`;
    for (let r = 1; r <= c.rangees; r++) {
      plan += `<span class="entete-rang">${String.fromCharCode(64 + ((r - 1) % 26) + 1)}${r > 26 ? Math.ceil(r / 26) : ""}</span>`;
      for (let col = 1; col <= c.colonnes; col++) {
        const b = parCase[`${r}-${col}`];
        plan += b
          ? `<button class="case-cave pleine ${esc(b.couleur)} ${esc(b.statut)}${b.vin_id === surligne ? " surligne" : ""}" data-b="${b.id}" title="${esc(b.nom)}${b.millesime ? " " + b.millesime : ""} — ${esc(REF.statuts[b.statut])}" aria-label="Rangée ${r} colonne ${col} : ${esc(b.nom)}"></button>`
          : `<button class="case-cave" data-r="${r}" data-c="${col}" aria-label="Rangée ${r} colonne ${col} : libre"></button>`;
      }
    }
    plan += `</div></div><div class="legende">${Object.entries(REF.couleurs).map(([k, l]) => `<span>${pastille(k)} ${esc(l)}</span>`).join("")}<span><b>!</b>&nbsp;à boire vite / dépassé</span><span>◌ case libre</span></div>`;
  }
  const vrac = c.bouteilles.filter((b) => !b.rangee);
  const groupesVrac = {};
  vrac.forEach((b) => { groupesVrac[b.vin_id] = groupesVrac[b.vin_id] || { ...b, n: 0 }; groupesVrac[b.vin_id].n++; });
  main.innerHTML = entete + onglets + `
    <div class="carte">
      <div class="entete"><div><h2 style="margin:0">${esc(c.nom)}</h2>
        <span class="muted">${c.capacite ? `${c.bouteilles.length} / ${c.capacite} emplacements occupés · ${c.rangees} rangées × ${c.colonnes} colonnes` : pluriel(c.bouteilles.length, "bouteille") + " (rangement libre)"}</span>
        ${c.description ? `<p class="muted">${esc(c.description)}</p>` : ""}</div>
        <div class="actions"><button class="bouton petit" id="modifier">✎ Modifier</button><button class="bouton petit danger" id="supprimer">Supprimer</button></div></div>
      <p id="mode-deplacement" class="muted" hidden>Choisissez la case de destination… <button class="bouton petit" id="annuler-depl">Annuler</button></p>
      ${plan}
      ${vrac.length ? `<h3 style="margin-top:16px">${c.capacite ? "Sans emplacement précis" : "Bouteilles"}</h3><ul class="liste">${Object.values(groupesVrac).map((b) =>
        `<li>${pastille(b.couleur)}<a class="grandit titre" href="#/vins/${b.vin_id}">${titreVin(b)}</a>${badgeStatut(b.statut)}<span class="muted">×${b.n}</span></li>`).join("")}</ul>` : ""}
      ${!c.bouteilles.length && !c.capacite ? `<p class="muted">Aucune bouteille. Ajoutez-en depuis la fiche d'un vin.</p>` : ""}
    </div>`;
  $("#nouvelle", main).onclick = () => dialogueCave();
  $("#modifier", main).onclick = () => dialogueCave(c);
  $("#supprimer", main).onclick = async () => {
    if (await confirmer(`Supprimer « ${c.nom} » ? Ses ${c.bouteilles.length} bouteille(s) resteront dans votre inventaire, sans emplacement.`, "Supprimer")) {
      await api("DELETE", `caves/${c.id}`);
      location.hash = "#/caves";
    }
  };
  let deplacement = null;
  const finDeplacement = () => {
    deplacement = null;
    $("#mode-deplacement", main).hidden = true;
    $$(".case-cave.cible", main).forEach((x) => x.classList.remove("cible"));
  };
  $("#annuler-depl", main).onclick = finDeplacement;
  $$(".case-cave", main).forEach((bouton) => bouton.addEventListener("click", async () => {
    if (bouton.dataset.b) {
      const b = c.bouteilles.find((x) => x.id === +bouton.dataset.b);
      const vin = { id: b.vin_id, nom: b.nom, millesime: b.millesime, stock: 1 };
      const d = dialogue(`<h2>${pastille(b.couleur)} ${titreVin(b)}</h2>
        <p class="muted">${esc(b.domaine || "")} · rangée ${b.rangee}, colonne ${b.colonne}</p><p>${badgeStatut(b.statut)}</p>
        <div class="actions" style="justify-content:flex-start">
          <button class="bouton primaire" type="button" data-action="sortir">🍷 Sortir cette bouteille</button>
          <button class="bouton" type="button" data-action="deplacer">↔ Déplacer</button>
          <a class="bouton" href="#/vins/${b.vin_id}" data-action="fiche">Voir la fiche</a></div>
        <div class="actions"><button class="bouton" data-fermer>Fermer</button></div>`);
      $("[data-action=sortir]", d).onclick = () => { d.close(); dialogueSortie(vin, b.id, () => route()); };
      $("[data-action=fiche]", d).onclick = () => d.close();
      $("[data-action=deplacer]", d).onclick = () => {
        d.close();
        deplacement = b.id;
        $("#mode-deplacement", main).hidden = false;
        $$(".case-cave:not(.pleine)", main).forEach((x) => x.classList.add("cible"));
      };
    } else if (deplacement) {
      try {
        await api("PUT", `bouteilles/${deplacement}`, { cave_id: c.id, rangee: +bouton.dataset.r, colonne: +bouton.dataset.c });
        toast("Bouteille déplacée");
        route();
      } catch (err) { toast(err.message, true); finDeplacement(); }
    } else {
      await dialogueRanger(c, +bouton.dataset.r, +bouton.dataset.c);
    }
  }));
  if (surligne) $(".case-cave.surligne", main)?.scrollIntoView({ block: "center", inline: "center" });
}

async function dialogueRanger(cave, rangee, colonne) {
  const [nonRangees, vins] = await Promise.all([api("GET", "bouteilles/non-rangees"), api("GET", "vins?stock=all&tri=nom")]);
  const groupes = {};
  nonRangees.forEach((b) => { groupes[b.vin_id] = groupes[b.vin_id] || { ...b, n: 0 }; groupes[b.vin_id].n++; });
  const ailleurs = Object.values(groupes);
  dialogue(`<h2>Rangée ${rangee}, colonne ${colonne}</h2>
    <div class="form">
      ${ailleurs.length ? `<label class="large">Ranger une bouteille déjà en stock (non rangée ou en vrac)
        <select name="bouteille_id"><option value="">—</option>${ailleurs.map((b) => `<option value="${b.id}">${titreVin(b)} (×${b.n}${b.cave_nom ? " — " + esc(b.cave_nom) : ""})</option>`).join("")}</select></label>
        <p class="large muted petit-texte" style="margin:0">… ou bien :</p>` : ""}
      <label class="large">Ajouter une nouvelle bouteille de
        <select name="vin_id"><option value="">—</option>${vins.map((v) => `<option value="${v.id}">${titreVin(v)}</option>`).join("")}</select></label>
      <p class="large muted petit-texte" style="margin:0">Vin absent de la liste ? <a href="#/vins/nouveau" data-fermer-lien>Créez-le d'abord</a>.</p>
    </div>
    <div class="actions"><button class="bouton" data-fermer>Annuler</button><button class="bouton primaire" type="submit">Ranger ici</button></div>`,
  {
    onSubmit: async (data) => {
      if (data.bouteille_id) await api("PUT", `bouteilles/${data.bouteille_id}`, { cave_id: cave.id, rangee, colonne });
      else if (data.vin_id) await api("POST", `vins/${data.vin_id}/entree`, { quantite: 1, cave_id: cave.id, rangee, colonne, raison: "achat" });
      else throw new Error("Choisissez une bouteille ou un vin");
      toast("Bouteille rangée");
      route();
    },
  });
  $("[data-fermer-lien]")?.addEventListener("click", () => $("#dialogue").close());
}

function dialogueCave(c) {
  dialogue(`<h2>${c ? "Modifier la cave" : "Nouvelle cave"}</h2>
    <div class="form">
      <label class="large">Nom<input name="nom" required value="${esc(c?.nom)}" placeholder="Cave du sous-sol, armoire à vin…"></label>
      <label>Rangées<input type="number" name="rangees" min="0" max="100" value="${c?.rangees ?? 6}"></label>
      <label>Colonnes<input type="number" name="colonnes" min="0" max="100" value="${c?.colonnes ?? 8}"></label>
      <p class="large muted petit-texte" style="margin:0">Mettez 0 rangée ou 0 colonne pour un rangement libre, sans plan.</p>
      <label class="large">Description<input name="description" value="${esc(c?.description)}" placeholder="Température, emplacement…"></label>
    </div>
    <div class="actions"><button class="bouton" data-fermer>Annuler</button><button class="bouton primaire" type="submit">Enregistrer</button></div>`,
  {
    onSubmit: async (data) => {
      const r = c ? await api("PUT", `caves/${c.id}`, data) : await api("POST", "caves", data);
      toast("Cave enregistrée");
      if (location.hash === `#/caves/${r.id}`) route(); else location.hash = `#/caves/${r.id}`;
    },
  });
}

async function pageCeSoir(main) {
  let plat = "", couleur = "";
  main.innerHTML = `<div class="entete"><h1>Que boire ce soir ?</h1></div>
    <div class="carte"><p class="muted">Choisissez ce que vous mangez : la cave propose les bouteilles qui s'accordent le mieux, en privilégiant celles à boire en priorité.</p>
    <div class="plats" id="plats"><button class="bouton actif" data-plat="">Peu importe</button>${Object.entries(REF.plats).map(([k, l]) => `<button class="bouton" data-plat="${k}">${esc(l)}</button>`).join("")}</div>
    <div class="filtres" style="margin:14px 0 0;max-width:280px"><select id="couleur" aria-label="Couleur">${options(REF.couleurs, "", "Toutes couleurs")}</select></div></div>
    <div id="suggestions" class="grille" style="margin-top:16px"></div>`;
  const charger = async () => {
    const res = await api("GET", "suggestion?" + new URLSearchParams({ plat, couleur, limite: 8 }));
    $("#suggestions", main).innerHTML = res.length ? res.map((s, i) => `
      <div class="carte suggestion"><span class="rang">${i + 1}</span>${pastille(s.vin.couleur)}
        <div class="grandit" style="flex:1;min-width:0"><a class="titre" href="#/vins/${s.vin.id}"><b>${titreVin(s.vin)}</b></a>
          <div class="muted petit-texte">${sousTitre(s.vin)}</div><div class="petit-texte">${s.raisons.map(esc).join(" · ")}</div></div>
        <span class="muted">×${s.vin.stock}</span><button class="bouton petit primaire" data-i="${i}">Ouvrir</button></div>`).join("")
      : `<div class="carte vide">Aucune bouteille prête à boire ne correspond. Essayez une autre couleur ou un autre plat.</div>`;
    $$("[data-i]", main).forEach((b) => (b.onclick = () => dialogueSortie(res[+b.dataset.i].vin, null, charger)));
  };
  $("#plats", main).addEventListener("click", (e) => {
    const b = e.target.closest("[data-plat]");
    if (!b) return;
    plat = b.dataset.plat;
    $$("#plats button", main).forEach((x) => x.classList.toggle("actif", x === b));
    charger();
  });
  $("#couleur", main).onchange = (e) => { couleur = e.target.value; charger(); };
  await charger();
}

async function pageEnvies(main) {
  const envies = await api("GET", "envies");
  main.innerHTML = `<div class="entete"><h1>Envies & liste d'achats</h1></div>
    <div class="carte">
      <form class="filtres" id="ajout" style="margin-bottom:8px">
        <input name="nom" placeholder="Vin à acheter ou à goûter…" required style="flex:2 1 200px" aria-label="Nom">
        <input name="details" placeholder="Détails (millésime, caviste, prix…)" style="flex:3 1 200px" aria-label="Détails">
        <button class="bouton primaire" type="submit">Ajouter</button></form>
      ${envies.length ? `<ul class="liste">${envies.map((e) => `<li>
        <input type="checkbox" data-id="${e.id}" ${e.fait ? "checked" : ""} aria-label="Fait">
        <div class="grandit" style="${e.fait ? "text-decoration:line-through;opacity:.6" : ""}"><span class="titre">${esc(e.nom)}</span>
        ${e.details ? `<div class="muted petit-texte">${esc(e.details)}</div>` : ""}</div>
        <button class="bouton petit danger" data-suppr="${e.id}" aria-label="Supprimer">✕</button></li>`).join("")}</ul>`
        : `<p class="muted">Votre liste est vide. Elle est aussi disponible dans Home Assistant (liste de tâches « Cave à vin – Envies »).</p>`}
    </div>`;
  $("#ajout", main).onsubmit = async (e) => {
    e.preventDefault();
    await api("POST", "envies", Object.fromEntries(new FormData(e.target)));
    route();
  };
  $$("[data-id]", main).forEach((c) => (c.onchange = async () => { await api("PUT", `envies/${c.dataset.id}`, { fait: c.checked }); route(); }));
  $$("[data-suppr]", main).forEach((b) => (b.onclick = async () => { await api("DELETE", `envies/${b.dataset.suppr}`); route(); }));
}

async function pageHistorique(main) {
  let type = "";
  main.innerHTML = `<div class="entete"><h1>Historique</h1>
    <select id="type" style="width:auto" aria-label="Type">${options({ entree: "Entrées", sortie: "Sorties" }, "", "Entrées et sorties")}</select></div>
    <div class="carte defile" id="table"></div>`;
  const charger = async () => {
    const ms = await api("GET", "mouvements?" + new URLSearchParams({ limite: 1000, ...(type ? { type } : {}) }));
    $("#table", main).innerHTML = ms.length ? `<table class="tableau"><thead><tr><th>Date</th><th>Vin</th><th>Mouvement</th><th>Note</th><th>Commentaire</th></tr></thead><tbody>
      ${ms.map((m) => `<tr><td style="white-space:nowrap">${dateFr(m.date)}</td>
        <td>${m.vin_id ? `<a href="#/vins/${m.vin_id}">${esc(m.vin_nom)}</a>` : esc(m.vin_nom)}${m.millesime ? " " + m.millesime : ""}</td>
        <td style="white-space:nowrap">${m.type === "entree" ? "📥 +" : "🍷 −"}${m.quantite} ${esc((m.type === "entree" ? REF.raisons_entree : REF.raisons_sortie)[m.raison] || m.raison)}</td>
        <td>${etoiles(m.note)}</td><td>${esc(m.commentaire)}</td></tr>`).join("")}</tbody></table>` : `<p class="vide">Aucun mouvement pour l'instant.</p>`;
  };
  $("#type", main).onchange = (e) => { type = e.target.value; charger(); };
  await charger();
}

async function pageReglages(main) {
  const [r, capteurs, entitesIA] = await Promise.all([api("GET", "reglages"), api("GET", "ha/capteurs").catch(() => []), api("GET", "ia/entites").catch(() => [])]);
  CAPACITES = await api("GET", "capacites");
  const choixCapteur = (nom, type) => {
    const liste = capteurs.filter((c) => c.type === type);
    if (!liste.length) return `<input name="${nom}" value="${esc(r[nom])}" placeholder="sensor.cave_${type === "temperature" ? "temperature" : "humidite"}">`;
    return `<select name="${nom}"><option value="">— Aucun —</option>${liste.map((c) => `<option value="${esc(c.entity_id)}"${c.entity_id === r[nom] ? " selected" : ""}>${esc(c.nom)} (${esc(c.etat)} ${esc(c.unite)})</option>`).join("")}
      ${r[nom] && !liste.some((c) => c.entity_id === r[nom]) ? `<option selected value="${esc(r[nom])}">${esc(r[nom])}</option>` : ""}</select>`;
  };
  let etatHA = "";
  if (r.addon || r.ha_url) {
    etatHA = capteurs.length
      ? `<p style="color:var(--ok)">✓ Connecté à Home Assistant (${capteurs.length} capteur(s) de température / humidité trouvé(s)).</p>`
      : `<p style="color:var(--danger)">Home Assistant ne répond pas, ou aucun capteur de température / humidité n'a été trouvé.</p>`;
  }
  main.innerHTML = `<div class="entete"><h1>Réglages</h1></div>
    <div class="grille g2">
      <div class="carte"><h2>🏠 Home Assistant — capteurs de la cave</h2>
        ${r.addon ? `<p class="muted">L'application tourne comme module complémentaire : la connexion à Home Assistant est automatique.</p>`
          : `<p class="muted">Pour afficher la température et l'humidité de la cave, indiquez l'adresse de Home Assistant et un jeton d'accès longue durée (Profil → Sécurité → Jetons d'accès longue durée).</p>`}
        ${etatHA}
        <form class="form" id="ha">
          ${r.addon ? "" : `<label class="large">Adresse de Home Assistant<input name="ha_url" value="${esc(r.ha_url)}" placeholder="http://homeassistant.local:8123"></label>
          <label class="large">Jeton d'accès<input name="ha_token" type="password" placeholder="${r.ha_token_defini ? "•••••• (inchangé)" : "eyJ0eXAiOi…"}" autocomplete="off"></label>`}
          <label class="large">Capteur de température ${choixCapteur("capteur_temperature", "temperature")}</label>
          <label>Température min (°C)<input name="temp_min" type="number" step="0.5" value="${esc(r.temp_min)}"></label>
          <label>Température max (°C)<input name="temp_max" type="number" step="0.5" value="${esc(r.temp_max)}"></label>
          <label class="large">Capteur d'humidité ${choixCapteur("capteur_humidite", "humidity")}</label>
          <label>Humidité min (%)<input name="hum_min" type="number" value="${esc(r.hum_min)}"></label>
          <label>Humidité max (%)<input name="hum_max" type="number" value="${esc(r.hum_max)}"></label>
          <div class="actions large"><button class="bouton primaire" type="submit">Enregistrer</button></div>
        </form></div>
      <div class="carte"><h2>📷 Photos & lecture d'étiquette</h2>
        <form class="form" id="photos">
          <label class="large">Lecture d'étiquette par l'IA de Home Assistant
            <select name="ia_active">${options({ 1: "Activée", 0: "Désactivée" }, r.ia_active)}</select></label>
          <label class="large">IA à utiliser
            <select name="ia_entite"><option value="">IA par défaut de Home Assistant</option>${entitesIA.map((e) => `<option value="${esc(e.entity_id)}"${e.entity_id === r.ia_entite ? " selected" : ""}>${esc(e.nom)}</option>`).join("")}</select></label>
          <p class="large petit-texte" style="margin:0;color:${CAPACITES.ia.possible ? "var(--ok)" : "var(--texte-2)"}">${CAPACITES.ia.possible ? "✓ Lecture d'étiquette disponible" : "Indisponible : " + esc(CAPACITES.ia.raison)}</p>
          <label class="large">Qualité du détourage
            <select name="detourage_qualite">${options({ rapide: "Rapide (modèle de 5 Mo)", standard: "Standard (45 Mo, recommandé)", precis: "Précis (180 Mo, plus lent, 2 Go de mémoire conseillés)" }, r.detourage_qualite)}</select></label>
          <label class="large">Fond par défaut
            <select name="fond_defaut">${options(Object.fromEntries(CAPACITES.fonds.map((f) => [f.id, f.label])), r.fond_defaut)}</select></label>
          ${CAPACITES.detourage ? "" : `<p class="large petit-texte muted" style="margin:0">Le détourage n'est pas disponible sur cette installation (bibliothèques de traitement d'image absentes) : les photos sont gardées telles quelles.</p>`}
          <div class="actions large"><button class="bouton primaire" type="submit">Enregistrer</button></div>
        </form>
        <p class="muted petit-texte">Le modèle de détourage est téléchargé une seule fois, au premier usage, puis tout se fait sur votre installation. Pour la lecture d'étiquette, la photo est envoyée à l'IA configurée dans Home Assistant.</p>
      </div>
      <div class="carte"><h2>🔌 Intégration Home Assistant</h2>
        <p>L'intégration <b>Cave à vin</b> (dossier <code>custom_components/cave_a_vin</code>) crée dans Home Assistant :</p>
        <ul><li>des capteurs : bouteilles, valeur, vins à boire, à boire vite…</li>
          <li>la liste de tâches <b>Envies</b> (utilisable avec Assist : « ajoute Chablis à Cave à vin Envies »)</li>
          <li>les actions <code>cave_a_vin.sortir_bouteille</code>, <code>ajouter_bouteilles</code> et <code>suggerer_vin</code>.</li></ul>
        <p class="muted">Adresse à saisir lors de l'ajout de l'intégration : ${r.addon ? "<code>http://&lt;nom d'hôte du module&gt;:8099</code> (visible dans l'onglet Info du module)" : `<code>${esc(location.origin)}</code>`}.</p>
      </div>
      <div class="carte"><h2>💾 Sauvegarde & import</h2>
        <div class="actions">
          <a class="bouton" href="${avecCle("api/export.csv")}" download>Exporter en CSV (Excel)</a>
          <a class="bouton" href="${avecCle("api/export.json")}" download>Sauvegarde complète (JSON)</a></div>
        <hr class="sep">
        <label>Importer des vins depuis un fichier CSV (colonnes : nom, domaine, appellation, region, couleur, millesime, quantite…)
          <input type="file" accept=".csv,text/csv" id="import-csv"></label>
        <label style="margin-top:12px">Restaurer une sauvegarde JSON (remplace toute la cave !)
          <input type="file" accept=".json,application/json" id="import-json"></label>
      </div>
      <div class="carte"><h2>ℹ️ À propos</h2>
        <p>Cave à vin version ${esc(REF.version)}${r.addon ? " — module complémentaire Home Assistant" : ""}.</p>
        ${cleAPI.lire() ? `<p>Une clé d'API est mémorisée sur cet appareil. <button class="bouton petit" id="oublier">Oublier la clé</button></p>` : ""}
      </div>
    </div>`;
  $("#ha", main).onsubmit = async (e) => {
    e.preventDefault();
    try {
      await api("PUT", "reglages", Object.fromEntries(new FormData(e.target)));
      toast("Réglages enregistrés");
      route();
    } catch (err) { toast(err.message, true); }
  };
  $("#photos", main).onsubmit = async (e) => {
    e.preventDefault();
    try {
      await api("PUT", "reglages", Object.fromEntries(new FormData(e.target)));
      toast("Réglages enregistrés");
      route();
    } catch (err) { toast(err.message, true); }
  };
  $("#import-csv", main).onchange = async (e) => {
    const f = e.target.files[0];
    if (!f) return;
    try {
      const res = await api("POST", "import.csv", undefined, await f.text());
      toast(`${res.vins_crees} vin(s) importé(s)${res.erreurs.length ? ` — ${res.erreurs.length} erreur(s)` : ""}`, !!res.erreurs.length);
      if (res.erreurs.length) console.warn(res.erreurs);
      REF = await api("GET", "referentiel");
    } catch (err) { toast(err.message, true); }
    e.target.value = "";
  };
  $("#import-json", main).onchange = async (e) => {
    const f = e.target.files[0];
    if (!f) return;
    if (await confirmer("Restaurer cette sauvegarde ? Toutes les données actuelles de la cave seront remplacées.", "Restaurer")) {
      try {
        const res = await api("POST", "import.json", JSON.parse(await f.text()));
        toast(`Sauvegarde restaurée : ${res.vins} vin(s), ${res.bouteilles} bouteille(s)`);
        REF = await api("GET", "referentiel");
      } catch (err) { toast(err.message, true); }
    }
    e.target.value = "";
  };
  const oublier = $("#oublier", main);
  if (oublier) oublier.onclick = () => { cleAPI.ecrire(""); route(); };
}

/* ------------------------------------------------------------------ routeur */

const ROUTES = [
  [/^$/, pageAccueil, "accueil"],
  [/^vins$/, pageVins, "vins"],
  [/^ajouter$/, pageAjouter, "vins"],
  [/^vins\/nouveau$/, (m) => pageFormulaire(m, null), "vins"],
  [/^vins\/(\d+)$/, (m, id) => pageVin(m, +id), "vins"],
  [/^vins\/(\d+)\/modifier$/, (m, id) => pageFormulaire(m, +id), "vins"],
  [/^caves$/, (m, _, p) => pageCaves(m, null, p), "caves"],
  [/^caves\/(\d+)$/, (m, id, p) => pageCaves(m, +id, p), "caves"],
  [/^ce-soir$/, pageCeSoir, "ce-soir"],
  [/^envies$/, pageEnvies, "envies"],
  [/^historique$/, pageHistorique, "historique"],
  [/^reglages$/, pageReglages, "reglages"],
];

async function route() {
  const [chemin, params = ""] = location.hash.replace(/^#\/?/, "").split("?");
  const main = $("#page");
  const d = $("#dialogue");
  if (d.open) d.close();
  for (const [motif, fn, menu] of ROUTES) {
    const m = chemin.match(motif);
    if (!m) continue;
    $$("#menu a").forEach((a) => a.classList.toggle("actif", a.dataset.page === menu));
    $("#menu a.actif")?.scrollIntoView({ block: "nearest", inline: "nearest" });
    try {
      if (!REF) [REF, CAPACITES] = await Promise.all([api("GET", "referentiel"), api("GET", "capacites")]);
      if (!main.childElementCount) main.innerHTML = `<div class="chargement">Chargement…</div>`;
      await fn(main, m[1], params);
    } catch (err) {
      main.innerHTML = `<div class="carte vide"><h2>Oups</h2><p>${esc(err.message)}</p><a class="bouton" href="#/">Retour à l'accueil</a></div>`;
    }
    return;
  }
  location.hash = "#/";
}

let derniereRoute = "";
window.addEventListener("hashchange", () => {
  const chemin = location.hash.split("?")[0];
  if (chemin !== derniereRoute) window.scrollTo(0, 0);
  derniereRoute = chemin;
  route();
});
route();
