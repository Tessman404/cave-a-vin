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
const ICONES_STATUT = { trop_jeune: "⏳", a_boire: "✓", apogee: "★", declin: "↘", urgent: "⚠", depasse: "✕", inconnu: "?" };

let REF = null;          // référentiel (couleurs, statuts, plats, autocomplétion…)
let CAPACITES = null;    // détourage, fonds, IA disponibles
let ajout = null;        // ajout en cours : { champs, code_barre, brouillon, fond, source }
let rangement = null;    // case du plan où ranger le vin en cours d'ajout : { cave_id, cave_nom, rangee, colonne }
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
  const place = rangement;
  dialogue(`<h2>Ajouter des bouteilles</h2><p class="muted">${titreVin(vin)}</p>
    <div class="form">
      <label>Nombre de bouteilles<input type="number" name="quantite" min="1" max="500" value="1" required></label>
      <label>Raison<select name="raison">${options(REF.raisons_entree, "achat")}</select></label>
      ${place ? `<p class="large" style="margin:0">📍 Rangée ${place.rangee}, colonne ${place.colonne} de <b>${esc(place.cave_nom)}</b> (les bouteilles suivantes dans les cases libres)</p>`
        : `<label>Ranger dans<select name="cave_id"><option value="">Non rangées</option>${caves.map((c) =>
        `<option value="${c.id}">${esc(c.nom)}${c.capacite ? ` (${c.capacite - c.bouteilles} place(s) libre(s))` : ""}</option>`).join("")}</select></label>`}
      <label>Date<input type="date" name="date" value="${aujourdhui()}"></label>
      <label class="large">Commentaire<input name="commentaire" placeholder="Caviste, salon, prix payé…"></label>
    </div>
    <div class="actions"><button class="bouton" data-fermer>Annuler</button><button class="bouton primaire" type="submit">Ajouter</button></div>`,
  {
    onSubmit: async (data) => {
      if (place) Object.assign(data, { cave_id: place.cave_id, rangee: place.rangee, colonne: place.colonne });
      await api("POST", `vins/${vin.id}/entree`, data);
      toast(place ? "Bouteille rangée dans le plan" : "Bouteilles ajoutées");
      apres && apres();
    },
  });
}

/* ------------------------------------------------------------------ pages */

/** Le casier vivant : une alvéole par bouteille, colorée selon le vin. */
function casierVivant(s) {
  const MAX = 96;
  const pastilles = [];
  s.par_couleur.forEach((l) => {
    const c = COULEURS_CSS.includes(l.cle) ? l.cle : "autre";
    for (let i = 0; i < l.bouteilles; i++) pastilles.push(c);
  });
  const montrees = pastilles.slice(0, MAX);
  const colonnes = Math.min(12, Math.max(6, Math.ceil(Math.sqrt(montrees.length * 1.6))));
  const rangs = Math.max(2, Math.ceil(montrees.length / colonnes));
  const vides = rangs * colonnes - montrees.length;
  const legende = s.par_couleur.filter((l) => l.bouteilles).map((l) => `${nombre(l.bouteilles)} ${esc(String(l.label).toLowerCase())}`).join(", ");
  return `<section class="casier" aria-label="Votre cave : ${pluriel(s.bouteilles, "bouteille")}, dont ${legende}">
    <div>
      <div class="total">${nombre(s.bouteilles)}</div>
      <div class="sous-total">${s.bouteilles > 1 ? "bouteilles dans votre cave" : "bouteille dans votre cave"}</div>
      <div class="chiffres">
        <div><strong>${nombre(s.references)}</strong><span>${s.references > 1 ? "références" : "référence"}</span></div>
        <div><strong>${euros(s.valeur)}</strong><span>valeur estimée</span></div>
        <div><strong>${nombre(s.bues_annee)}</strong><span>${s.bues_annee > 1 ? "bues" : "bue"} en ${s.annee}</span></div>
      </div>
    </div>
    <div class="alveoles" aria-hidden="true" style="--colonnes:${colonnes};--colonnes-mobile:${Math.min(colonnes, 10)}">
      ${montrees.map((c, i) => `<i style="--c:var(--c-${c});--i:${i}"></i>`).join("")}${"<i class=\"libre\"></i>".repeat(vides)}
      ${pastilles.length > MAX ? `<span class="reste">et ${nombre(pastilles.length - MAX)} de plus</span>` : ""}
    </div>
  </section>`;
}

function feuillePlus() {
  const lien = (page, icone, titre) => `<a href="#/${page}"><svg><use href="#i-${icone}"/></svg>${titre}</a>`;
  dialogue(`<h2>Plus</h2><nav class="feuille-plus">
    ${lien("envies", "envies", "Envies")}${lien("historique", "historique", "Historique")}${lien("reglages", "reglages", "Réglages")}</nav>
    <div class="actions"><button class="bouton" data-fermer>Fermer</button></div>`);
}

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
    ${casierVivant(s)}
    <div class="actions raccourcis"><button class="bouton" id="sortie-scan">▥ Sortir une bouteille par son code-barres</button></div>
    <div class="grille tableau-bord">
      ${blocClimat}
      <div class="carte ${s.urgents.length ? "alerte-carte" : ""}"><div class="titre-carte"><h2>À boire vite</h2>
        ${s.urgents.length > 8 ? `<a href="#/vins" data-filtre-statut="urgent,depasse">Voir les ${s.urgents.length}</a>` : ""}</div>
        ${s.urgents.length ? `<ul class="liste">${s.urgents.slice(0, 8).map(ligneVin).join("")}</ul>` : `<p class="muted">Rien d'urgent : toutes vos bouteilles sont dans leur fenêtre de garde.</p>`}</div>
      <div class="carte"><div class="titre-carte"><h2>Prêts à boire</h2>
        ${s.a_boire.length > 8 ? `<a href="#/vins" data-filtre-statut="declin,apogee,a_boire">Voir les ${s.a_boire.length}</a>` : ""}</div>
        ${s.a_boire.length ? `<ul class="liste">${s.a_boire.slice(0, 8).map(ligneVin).join("")}</ul>` : `<p class="muted">Aucun vin dans sa fenêtre de dégustation.</p>`}</div>
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
  $("#sortie-scan", main).onclick = sortirParCodeBarres;
  $$("[data-filtre-statut]", main).forEach((a) => a.addEventListener("click", () => {
    filtresVins = { ...filtresVins, statut: a.dataset.filtreStatut, stock: "1" };
  }));
}

async function pageVins(main) {
  const caves = await api("GET", "caves");
  const statuts = { ...REF.statuts, "urgent,depasse": "⚠ À boire vite ou dépassés", "declin,apogee,a_boire": "✓ Prêts à boire" };
  main.innerHTML = `
    <div class="entete"><h1>Mes vins</h1><div class="actions"><button class="bouton" id="sortie-scan">▥ Sortir par code-barres</button><a class="bouton primaire" href="#/ajouter">+ Ajouter un vin</a></div></div>
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
  $("#sortie-scan", main).onclick = sortirParCodeBarres;
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
    ${v.garde_apogee ? (() => { const fp = v.garde_apogee + Math.max(1, Math.round(((fin) - v.garde_apogee) * 0.4)) - 1;
      return `<div class="zone plateau" style="left:${pos(v.garde_apogee)};width:calc(${pos(fp + 1)} - ${pos(v.garde_apogee)})" title="Apogée : ${v.garde_apogee}${fp > v.garde_apogee ? " à " + fp : ""}"></div>`; })() : ""}
    ${v.garde_apogee ? `<div class="etoile" style="left:${pos(v.garde_apogee + .5)}" title="Apogée ${v.garde_apogee}">★</div>` : ""}
    <div class="repere" style="left:${pos(annee + .5)}"><span>${annee}</span></div>
    <div class="borne" style="left:${pos(debut)}">${debut}</div><div class="borne" style="left:${pos(fin + 1)}">${fin}</div></div>
    <p class="muted petit-texte" style="margin:14px 0 0">À boire de ${debut} à ${fin}${v.garde_apogee ? ` · ★ apogée ${v.garde_apogee}` : ""}</p>`;
}

/** D'où vient la garde (IA, estimation, saisie) et ce que l'IA suggère si elle n'a pas pu l'appliquer. */
function origineGarde(v) {
  const dateIA = v.garde_ia_date ? dateFr(v.garde_ia_date.slice(0, 10)) : "";
  let html = "";
  if (v.garde_source === "ia") {
    html = `🤖 Garde estimée par l'IA le ${dateIA}${v.garde_ia_note ? " : " + esc(v.garde_ia_note) : ""}`;
  } else if (v.garde_source === "manuel") {
    html = "✎ Garde saisie à la main : l'IA ne la modifie pas.";
    const differe = v.garde_ia_fin && (v.garde_ia_debut !== v.garde_debut || v.garde_ia_fin !== v.garde_fin);
    if (differe) html += ` L'IA suggère ${v.garde_ia_debut} → ${v.garde_ia_fin}${v.garde_ia_apogee ? ` (apogée ${v.garde_ia_apogee})` : ""}${v.garde_ia_note ? " : " + esc(v.garde_ia_note) : ""}`;
  } else if (v.garde_source === "estimation") {
    html = "✨ Garde estimée automatiquement (règle générale)" + (CAPACITES?.ia_texte?.possible ? " : l'IA l'affinera." : ".");
  } else if (v.garde_debut || v.garde_fin) {
    html = CAPACITES?.ia_texte?.possible ? "Garde importée : l'IA l'affinera lors de son prochain passage." : "";
  }
  return html ? `<p class="petit-texte origine-garde">${html}</p>` : "";
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
        <div class="photo">${v.a_photo ? `<img src="${urlPhoto(v)}" alt="Étiquette de ${esc(v.nom)}" id="photo-vin" title="Agrandir">` : bouteilleSVG(v.couleur)}</div>
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
          ${origineGarde(v)}
          <div class="actions" style="margin-top:14px">
            <button class="bouton primaire" id="sortir" ${v.stock ? "" : "disabled"}>🍷 Déguster / sortir</button>
            <button class="bouton" id="entrer">📥 Ajouter des bouteilles</button>
            <a class="bouton" href="#/vins/${v.id}/modifier">✎ Modifier</a>
            <button class="bouton" id="garde-ia">🤖 Demander la garde à l'IA</button>
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
  const boutonIA = $("#garde-ia", main);
  if (boutonIA) boutonIA.onclick = async () => {
    if (!CAPACITES.ia_texte?.possible) {
      return toast(`IA indisponible : ${CAPACITES.ia_texte?.raison || "inconnue"}. Voir Réglages → IA.`, true, 7000);
    }
    if (v.garde_source === "manuel" && !(await confirmer("Remplacer la garde saisie à la main par l'estimation de l'IA ?", "Remplacer"))) return;
    boutonIA.disabled = true;
    boutonIA.textContent = "🤖 L'IA réfléchit…";
    try {
      const r = await api("POST", `vins/${v.id}/garde-ia`, {});
      toast(`Garde estimée par l'IA : ${r.garde_debut} → ${r.garde_fin}`);
      recharger();
    } catch (err) { toast(err.message, true); boutonIA.disabled = false; boutonIA.textContent = "🤖 Demander la garde à l'IA"; }
  };
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
      const r = await api("PUT", `vins/${v.id}/photo`, { image: await redimensionner(fichier, 1600), fond: CAPACITES.detourage ? CAPACITES.fond_defaut : "", cadrage: CAPACITES.cadrage_defaut });
      toast(r.avertissement || "Photo enregistrée", !!r.avertissement);
      recharger();
    } catch (err) { toast(err.message, true); }
  };
  const photoVin = $("#photo-vin", main);
  if (photoVin) photoVin.onclick = () => plein_ecran(urlPhoto(v),
    v.a_photo_originale ? avecCle(`api/vins/${v.id}/photo?original=1&v=${encodeURIComponent(v.updated_at)}`) : null, titreVin(v));
  const fond = $("#changer-fond", main);
  if (fond) fond.onclick = () => dialogueFond(async (choix, cadrage) => {
    await api("POST", `vins/${v.id}/photo/fond`, { fond: choix, cadrage });
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
    ${brouillon ? `<div class="apercu-ajout"><img id="apercu" src="${avecCle(`api/brouillons/${brouillon.brouillon}/image?fond=${brouillon.fond || ""}&cadrage=${brouillon.cadrage || ""}`)}" alt="Photo de la bouteille">
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
        <input type="hidden" name="garde_source" value="${esc(v.garde_source ?? "")}">
        <p class="muted petit-texte large" style="margin:0">✨ Estimer applique une règle générale (couleur, appellation, prix, millésime).${CAPACITES.ia_texte?.possible ? " L'IA de Home Assistant l'affinera ensuite, puis chaque mois." : ""} Une garde corrigée à la main n'est jamais modifiée par l'IA.</p>
      </fieldset>
      ${id ? "" : `<fieldset><legend>Bouteilles</legend>
        <label>Nombre de bouteilles<input type="number" name="quantite" min="0" max="500" value="1"></label>
        ${rangement ? `<p style="margin:0;align-self:end">📍 ${esc(rangement.cave_nom)}, rangée ${rangement.rangee}, colonne ${rangement.colonne}</p>
          <input type="hidden" name="cave_id" value="${rangement.cave_id}"><input type="hidden" name="rangee" value="${rangement.rangee}">
          <input type="hidden" name="colonne" value="${rangement.colonne}">`
        : `<label>Ranger dans<select name="cave_id"><option value="">Non rangées</option>${caves.map((c) => `<option value="${c.id}">${esc(c.nom)}</option>`).join("")}</select></label>`}
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
    form.garde_source.value = "estimation";
    toast(g.reference === "achat"
      ? `Estimé comme ${g.niveau_label}. Sans millésime, la garde est comptée à partir de l'achat (${g.annee_reference})`
      : `Estimé comme ${g.niveau_label}`, false, g.reference === "achat" ? 5000 : undefined);
  };
  $("#annuler", main).onclick = () => { ajout = null; };
  ["garde_debut", "garde_apogee", "garde_fin"].forEach((c) => form[c].addEventListener("input", () => (form.garde_source.value = "manuel")));
  const boutonFond = $("#fond-ajout", main);
  if (boutonFond) boutonFond.onclick = () => dialogueFond(async (choix, cadrage) => {
    if (choix) await api("POST", `brouillons/${brouillon.brouillon}/rendu`, { fond: choix, cadrage });
    brouillon.fond = choix;
    brouillon.cadrage = cadrage;
    $("#apercu", main).src = avecCle(`api/brouillons/${brouillon.brouillon}/image?fond=${choix}&cadrage=${cadrage}`);
  }, avecCle(`api/brouillons/${brouillon.brouillon}/image`), brouillon.cadrage);
  // fiche pré-remplie sans garde : on propose tout de suite une estimation
  if (!id && ajout?.champs && !v.garde_fin) $("#estimer", main).click();
  form.onsubmit = async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(form));
    data.favori = !!data.favori;
    if (brouillon) data.photo = { brouillon: brouillon.brouillon, fond: brouillon.fond || "", cadrage: brouillon.cadrage || "" };
    try {
      const vin = id ? await api("PUT", `vins/${id}`, data) : await api("POST", "vins", data);
      ajout = null;
      REF = await api("GET", "referentiel");
      toast(id ? "Modifications enregistrées" : rangement ? "Vin ajouté et rangé dans le plan" : "Vin ajouté à la cave");
      if (id) location.hash = `#/vins/${vin.id}`; else apresAjout(vin.id);
    } catch (err) { toast(err.message, true); }
  };
}

/* ------------------------------------------------------------------ ajout assisté : scan, photo, IA */

/** Photo en grand (pour lire l'étiquette), avec bascule vers la photo d'origine. */
function plein_ecran(url, urlOriginal, titre) {
  const d = dialogue(`<div class="plein-ecran"><img src="${url}" alt="${titre}" id="pe-image"></div>
    <div class="actions">${urlOriginal ? `<button type="button" class="bouton" id="pe-original">Photo d'origine</button>` : ""}
    <button class="bouton" data-fermer>Fermer</button></div>`, { large: true });
  const bascule = $("#pe-original", d);
  if (bascule) bascule.onclick = () => {
    const img = $("#pe-image", d);
    const original = img.src.includes("original=1");
    img.src = original ? url : urlOriginal;
    bascule.textContent = original ? "Photo d'origine" : "Photo mise en scène";
  };
}

function dialogueFond(choisir, urlOriginal, cadrageActuel) {
  let cadrage = cadrageActuel || CAPACITES.cadrage_defaut || "etiquette";
  const vignettes = CAPACITES.fonds.map((f) => `<button type="button" class="vignette-fond" data-fond="${esc(f.id)}">
      <img src="fonds/${esc(f.id)}.jpg" alt=""><span>${esc(f.label)}</span></button>`).join("");
  const d = dialogue(`<h2>Choisir le fond</h2>
    <div class="plats cadrages" role="radiogroup" aria-label="Cadrage">${(CAPACITES.cadrages || []).map((c) =>
      `<button type="button" class="bouton petit${c.id === cadrage ? " actif" : ""}" data-cadrage="${esc(c.id)}">${c.id === "etiquette" ? "🔍" : "🍾"} ${esc(c.label)}</button>`).join("")}</div>
    <div class="fonds">${vignettes}<button type="button" class="vignette-fond" data-fond=""><img src="${urlOriginal}" alt=""><span>Photo d'origine</span></button></div>
    <p class="muted petit-texte" id="etat-fond"></p>
    <div class="actions"><button class="bouton" data-fermer>Fermer</button></div>`);
  $$("[data-cadrage]", d).forEach((b) => (b.onclick = () => {
    cadrage = b.dataset.cadrage;
    $$("[data-cadrage]", d).forEach((x) => x.classList.toggle("actif", x === b));
    $("#etat-fond", d).textContent = "Choisissez maintenant un fond.";
  }));
  $$("[data-fond]", d).forEach((b) => (b.onclick = async () => {
    $$("[data-fond]", d).forEach((x) => (x.disabled = true));
    $("#etat-fond", d).textContent = "Détourage et mise en scène…";
    try { await choisir(b.dataset.fond, cadrage); d.close(); toast("Photo mise à jour"); }
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

/* Lecture des codes-barres : BarcodeDetector natif quand il existe (Android), sinon ZXing.
   L'image est essayée telle quelle puis tournée d'un quart de tour : sur une bouteille debout,
   le code-barres de la contre-étiquette est souvent vertical. */
const FORMATS_NATIFS = ["ean_13", "ean_8", "upc_a", "upc_e"];
let lecteurZX = null;
let detecteurNatif;

async function zxing() {
  await chargerScript("vendor/zxing-0.21.3.min.js");
  const Z = window.ZXing;
  if (!lecteurZX) {
    lecteurZX = new Z.MultiFormatReader();
    lecteurZX.setHints(new Map([[Z.DecodeHintType.POSSIBLE_FORMATS, [Z.BarcodeFormat.EAN_13, Z.BarcodeFormat.EAN_8,
      Z.BarcodeFormat.UPC_A, Z.BarcodeFormat.UPC_E]], [Z.DecodeHintType.TRY_HARDER, true]]));
  }
  return Z;
}

async function natif() {
  if (detecteurNatif !== undefined) return detecteurNatif;
  detecteurNatif = null;
  try {
    if ("BarcodeDetector" in window && (await BarcodeDetector.getSupportedFormats()).includes("ean_13")) {
      detecteurNatif = new BarcodeDetector({ formats: FORMATS_NATIFS });
    }
  } catch { /* non pris en charge */ }
  return detecteurNatif;
}

function quartDeTour(source) {
  const c = document.createElement("canvas");
  c.width = source.height;
  c.height = source.width;
  const ctx = c.getContext("2d");
  ctx.translate(c.width / 2, c.height / 2);
  ctx.rotate(Math.PI / 2);
  ctx.drawImage(source, -source.width / 2, -source.height / 2);
  return c;
}

/** Cherche un code-barres dans un canvas ; renvoie ses chiffres ou null. */
async function lireCanvas(canvas) {
  const detecteur = await natif();
  if (detecteur) {
    try {
      const codes = await detecteur.detect(canvas);
      if (codes.length) return codes[0].rawValue;
    } catch { /* on tente ZXing */ }
  }
  const Z = await zxing();
  for (const c of [canvas, quartDeTour(canvas)]) {
    try {
      return lecteurZX.decode(new Z.BinaryBitmap(new Z.HybridBinarizer(new Z.HTMLCanvasElementLuminanceSource(c)))).getText();
    } catch { /* pas de code dans ce sens */ } finally { lecteurZX.reset(); }
  }
  return null;
}

function versCanvas(source, largeurSource, hauteurSource, max) {
  const r = Math.min(1, max / Math.max(largeurSource, hauteurSource));
  const c = document.createElement("canvas");
  c.width = Math.round(largeurSource * r);
  c.height = Math.round(hauteurSource * r);
  c.getContext("2d").drawImage(source, 0, 0, c.width, c.height);
  return c;
}

/** Lit le code-barres d'une photo : plusieurs tailles et un recadrage central, dans les deux sens. */
async function decoderImage(fichier) {
  const img = new Image();
  img.src = URL.createObjectURL(fichier);
  try {
    await img.decode();
    for (const max of [1600, 1000, 2400]) {
      const code = await lireCanvas(versCanvas(img, img.naturalWidth, img.naturalHeight, max));
      if (code) return code;
    }
    // code-barres petit au milieu de la photo : on recadre le centre
    const [w, h] = [img.naturalWidth, img.naturalHeight];
    const centre = document.createElement("canvas");
    centre.width = Math.round(w * 0.6);
    centre.height = Math.round(h * 0.6);
    centre.getContext("2d").drawImage(img, w * 0.2, h * 0.2, centre.width, centre.height, 0, 0, centre.width, centre.height);
    return await lireCanvas(versCanvas(centre, centre.width, centre.height, 1600));
  } catch {
    return null;
  } finally {
    URL.revokeObjectURL(img.src);
  }
}

/** Fenêtre de scan : caméra en direct si possible, sinon (ou en plus) photo du code ou saisie des chiffres.
    Renvoie le code lu, ou null si l'on annule. */
function scanner() {
  return new Promise((resolve) => {
    const d = dialogue(`<h2>Scanner le code-barres</h2>
      <div class="viseur" hidden><video playsinline muted></video><div class="cadre"></div></div>
      <p class="petit-texte" id="scan-etat">Ouverture de la caméra…</p>
      <div class="actions" style="justify-content:flex-start;margin-top:8px">
        <label class="bouton primaire">📷 Photographier le code-barres<input type="file" accept="image/*" capture="environment" hidden id="scan-photo"></label>
      </div>
      <div class="filtres" style="margin:12px 0 0">
        <input id="scan-chiffres" inputmode="numeric" placeholder="… ou tapez les chiffres" aria-label="Chiffres du code-barres">
        <button class="bouton" type="button" id="scan-ok">OK</button>
      </div>
      <div class="actions"><button class="bouton" data-fermer>Annuler</button></div>`);
    const video = $("video", d);
    const etat = $("#scan-etat", d);
    let fini = false, flux = null;
    const terminer = (code) => {
      if (fini) return;
      fini = true;
      flux?.getTracks().forEach((t) => t.stop());
      if (d.open) d.close();
      resolve(code);
    };
    d.addEventListener("close", () => terminer(null), { once: true });
    $("#scan-ok", d).onclick = () => { const c = $("#scan-chiffres", d).value.replace(/\D/g, ""); if (c) terminer(c); };
    $("#scan-chiffres", d).addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); $("#scan-ok", d).click(); } });
    $("#scan-photo", d).onchange = async (e) => {
      const f = e.target.files[0];
      e.target.value = "";
      if (!f) return;
      etat.textContent = "Lecture de la photo…";
      const code = await decoderImage(f);
      if (code) terminer(code);
      else etat.textContent = "Aucun code-barres lisible sur cette photo. Rapprochez-vous (le code doit remplir une bonne partie de l'image), évitez les reflets, puis réessayez.";
    };
    (async () => {
      if (!navigator.mediaDevices?.getUserMedia || !window.isSecureContext) {
        etat.textContent = "La caméra en direct n'est pas disponible sur cette connexion : photographiez le code-barres ou tapez ses chiffres.";
        return;
      }
      try {
        flux = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: "environment" }, width: { ideal: 1920 }, height: { ideal: 1080 } }, audio: false });
      } catch (err) {
        const raisons = { NotAllowedError: "accès refusé, ou bloqué dans le panneau Home Assistant", SecurityError: "bloquée par le navigateur",
          NotFoundError: "aucune caméra trouvée", NotReadableError: "caméra déjà utilisée par une autre application",
          OverconstrainedError: "caméra non compatible" };
        etat.textContent = `Caméra en direct indisponible (${raisons[err.name] || err.message || err.name}) : photographiez le code-barres ou tapez ses chiffres.`;
        return;
      }
      if (fini) return flux.getTracks().forEach((t) => t.stop());
      const piste = flux.getVideoTracks()[0];
      try { await piste.applyConstraints({ advanced: [{ focusMode: "continuous" }] }); } catch { /* mise au point non réglable */ }
      video.srcObject = flux;
      $(".viseur", d).hidden = false;
      await video.play().catch(() => {});
      etat.textContent = "Visez le code-barres, de près, sans reflet (horizontal ou vertical).";
      const canvas = document.createElement("canvas");
      while (!fini) {
        if (video.videoWidth) {
          const max = 1280;
          const r = Math.min(1, max / Math.max(video.videoWidth, video.videoHeight));
          canvas.width = Math.round(video.videoWidth * r);
          canvas.height = Math.round(video.videoHeight * r);
          canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
          const code = await lireCanvas(canvas);
          if (code) {
            navigator.vibrate?.(80);
            return terminer(code);
          }
        }
        await new Promise((r) => setTimeout(r, 250));
      }
    })();
  });
}

async function pageAjouter(main) {
  CAPACITES = await api("GET", "capacites");
  main.innerHTML = `
    <div class="entete"><h1>Ajouter un vin</h1></div>
    ${rangement ? `<div class="carte bandeau-rangement">📍 La bouteille sera rangée dans <b>${esc(rangement.cave_nom)}</b>, rangée ${rangement.rangee}, colonne ${rangement.colonne}.
      <button class="bouton petit" id="annuler-rangement">Ne pas la ranger</button></div>` : ""}
    <div class="tuiles-ajout">
      <label class="carte tuile-ajout"><span class="icone">📷</span><b>Photographier la bouteille</b>
        <span class="muted">D'abord l'étiquette, puis le verso${CAPACITES.ia.possible ? " : l'IA remplit la fiche et trouve le code-barres" : ""}${CAPACITES.detourage ? ". La bouteille est détourée et posée sur un fond de cave" : ""}</span>
        <input type="file" accept="image/*" capture="environment" hidden id="t-photo"></label>
      <a class="carte tuile-ajout" href="#/vins/nouveau" id="t-main"><span class="icone">✎</span><b>Saisir à la main</b><span class="muted">Formulaire complet</span></a>
    </div>
    <div id="resultat"></div>`;
  ajout = null;
  const resultat = $("#resultat", main);
  $("#t-main", main).onclick = () => { ajout = null; };
  const annulerRangement = $("#annuler-rangement", main);
  if (annulerRangement) annulerRangement.onclick = () => { rangement = null; route(); };
  const montrer = () => resultat.scrollIntoView({ behavior: "smooth", block: "start" });

  /** Demande la photo du verso ; renvoie le fichier, ou null si l'utilisateur l'ignore. */
  const demanderVerso = () => new Promise((resolve) => {
    const zone = $("#e-verso-choix", resultat);
    zone.hidden = false;
    $("#v-photo", zone).onchange = (e) => { zone.hidden = true; resolve(e.target.files[0] || null); };
    $("#v-ignorer", zone).onclick = () => { zone.hidden = true; resolve(null); };
  });

  const traiterPhoto = async (fichier) => {
    resultat.innerHTML = `<div class="carte traitement"><div class="apercu-ajout"><img id="apercu" alt="Photo de la bouteille"></div>
      <ul class="liste etapes"><li id="e-envoi">⏳ Envoi de la photo…</li>
      ${CAPACITES.detourage ? `<li id="e-detour">⏳ Détourage de la bouteille…</li>` : ""}
      <li id="e-verso">↻ Verso de la bouteille</li>
      ${CAPACITES.ia.possible ? `<li id="e-ia">⏳ Lecture de l'étiquette par l'IA…</li>` : ""}</ul>
      <div class="carte verso-choix" id="e-verso-choix" hidden>
        <b>Photographiez maintenant le verso</b>
        <p class="muted petit-texte">La contre-étiquette donne plus d'informations (cépages, degré…) et le code-barres, qui servira à sortir la bouteille d'un simple scan.</p>
        <div class="actions"><label class="bouton primaire">📷 Photographier le verso<input type="file" accept="image/*" capture="environment" hidden id="v-photo"></label>
          <button class="bouton" id="v-ignorer">Ignorer</button></div></div>
      <div id="e-existe"></div>
      <div class="actions" id="e-actions" hidden>
        ${CAPACITES.detourage ? `<button class="bouton" id="e-fond">🎨 Changer de fond</button>` : ""}
        <button class="bouton primaire" id="e-suite">Continuer</button></div></div>`;
    montrer();
    const etape = (id, texte) => { const li = $("#" + id, resultat); if (li) li.textContent = texte; };
    const image = await redimensionner(fichier, 1600);
    $("#apercu", resultat).src = image;
    let ident;
    try { ident = (await api("POST", "brouillons", { image })).id; etape("e-envoi", "✓ Photo reçue"); }
    catch (err) { etape("e-envoi", "✕ " + err.message); return; }
    ajout = { champs: {}, brouillon: ident, fond: "", source: "photo" };
    const lent = setTimeout(() => etape("e-detour", "⏳ Détourage… (la première fois, le modèle de détourage est téléchargé : patientez une minute)"), 6000);
    const detourage = CAPACITES.detourage && api("POST", `brouillons/${ident}/rendu`, { fond: CAPACITES.fond_defaut, cadrage: CAPACITES.cadrage_defaut })
      .then(() => {
        ajout.fond = CAPACITES.fond_defaut;
        ajout.cadrage = CAPACITES.cadrage_defaut;
        $("#apercu", resultat).src = avecCle(`api/brouillons/${ident}/image?fond=${ajout.fond}&cadrage=${ajout.cadrage}`);
        etape("e-detour", "✓ Bouteille détourée");
      })
      .catch((err) => etape("e-detour", "✕ Détourage impossible : " + err.message))
      .finally(() => clearTimeout(lent));

    // le verso pendant que le détourage tourne
    const fichierVerso = await demanderVerso();
    let verso = null, codeVerso = null;
    if (fichierVerso) {
      etape("e-verso", "⏳ Lecture du verso…");
      [verso, codeVerso] = await Promise.all([redimensionner(fichierVerso, 1600), decoderImage(fichierVerso).catch(() => null)]);
      etape("e-verso", codeVerso ? `✓ Verso reçu, code-barres ${codeVerso}` : "✓ Verso reçu");
    } else {
      etape("e-verso", "– Verso ignoré");
    }

    const lecture = CAPACITES.ia.possible && api("POST", `brouillons/${ident}/lire`, verso ? { verso } : {})
      .then((r) => {
        ajout.champs = { ...r.champs, ...ajout.champs };
        ajout.source = "ia";
        const libelles = { nom: "nom", domaine: "domaine", appellation: "appellation", region: "région", couleur: "couleur",
          millesime: "millésime", cepages: "cépages", degre: "degré", valeur: "valeur", accords: "accords", notes: "description" };
        const trouves = Object.keys(libelles).filter((k) => r.champs[k] != null && r.champs[k] !== "");
        const manquants = Object.keys(libelles).filter((k) => !trouves.includes(k));
        const titre = [r.champs.nom, r.champs.millesime].filter(Boolean).join(" ");
        etape("e-ia", trouves.length
          ? `✓ Étiquette lue${titre ? " : " + titre : ""} : ${trouves.length} informations remplies${manquants.length ? ` (à compléter : ${manquants.map((k) => libelles[k]).join(", ")})` : ""}`
          : "✕ L'IA n'a rien pu lire : complétez à la main");
      })
      .catch((err) => etape("e-ia", "✕ Lecture impossible : " + err.message));
    await Promise.all([detourage, lecture]);

    // code-barres : celui lu sur la photo prime sur celui recopié par l'IA
    const code = codeVerso || ajout.champs.code_barre || null;
    if (code) {
      ajout.code_barre = code;
      if (!codeVerso) etape("e-verso", `✓ Verso reçu, code-barres ${code} (lu par l'IA)`);
      try {
        const r = await api("GET", "scan/" + encodeURIComponent(code));
        if (r.local) {
          const v = r.local;
          $("#e-existe", resultat).innerHTML = `<div class="carte nouveau-vin-case"><b>Ce vin est déjà dans votre cave : ${titreVin(v)}</b>
            <p class="muted petit-texte">${pluriel(v.stock, "bouteille")}. Ajoutez plutôt des bouteilles à ce vin.</p>
            <div class="actions"><button class="bouton primaire" id="e-entree">📥 Ajouter des bouteilles</button><a class="bouton" href="#/vins/${v.id}">Voir la fiche</a></div></div>`;
          $("#e-entree", resultat).onclick = () => dialogueEntree(v, () => apresAjout(v.id));
        }
      } catch { /* la vérification est un plus */ }
    }

    $("#e-actions", resultat).hidden = false;
    $("#e-suite", resultat).onclick = () => (location.hash = "#/vins/nouveau");
    const bf = $("#e-fond", resultat);
    if (bf) bf.onclick = () => dialogueFond(async (choix, cadrage) => {
      if (choix) await api("POST", `brouillons/${ident}/rendu`, { fond: choix, cadrage });
      ajout.fond = choix;
      ajout.cadrage = cadrage;
      $("#apercu", resultat).src = avecCle(`api/brouillons/${ident}/image?fond=${choix}&cadrage=${cadrage}`);
    }, avecCle(`api/brouillons/${ident}/image`), ajout.cadrage);
  };

  $("#t-photo", main).onchange = (e) => e.target.files[0] && traiterPhoto(e.target.files[0]);
}

/** Sortir une bouteille en scannant son code-barres. */
async function sortirParCodeBarres() {
  const code = await scanner();
  if (!code) return;
  let r;
  try { r = await api("GET", "scan/" + encodeURIComponent(code)); }
  catch (err) { return toast(err.message, true); }
  if (!r.local) return toast(`Aucun vin de votre cave ne porte le code-barres ${code}`, true, 6000);
  if (!r.local.stock) return toast(`${r.local.nom} : plus aucune bouteille en cave`, true, 6000);
  dialogueSortie(r.local, null, () => { location.hash = `#/vins/${r.local.id}`; route(); });
}

/** Après un ajout : retour au plan si la bouteille vient d'y être rangée, sinon à la fiche. */
function apresAjout(vinId) {
  const r = rangement;
  rangement = null;
  location.hash = r ? `#/caves/${r.cave_id}?vin=${vinId}` : `#/vins/${vinId}`;
}

async function pageCaves(main, id, params) {
  rangement = null;  // retour au plan : on abandonne un rangement commencé
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
    </div>
    <div class="carte nouveau-vin-case">
      <b>Vin absent de la liste ?</b>
      <p class="muted petit-texte" style="margin:4px 0 8px">Scannez son code-barres ou photographiez la bouteille : il sera ajouté à la cave et rangé dans cette case.</p>
      <button type="button" class="bouton primaire" id="case-nouveau">➕ Nouveau vin dans cette case</button>
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
  $("#case-nouveau").onclick = () => {
    rangement = { cave_id: cave.id, cave_nom: cave.nom, rangee, colonne };
    $("#dialogue").close();
    location.hash = "#/ajouter";
  };
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
  const [r, capteurs, entitesIA, gardes, diagIA] = await Promise.all([api("GET", "reglages"), api("GET", "ha/capteurs").catch(() => []),
    api("GET", "ia/entites").catch(() => []), api("GET", "ia/gardes").catch(() => null), api("GET", "ia/diagnostic").catch(() => null)]);
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
      <div class="carte"><h2>🤖 IA, photos & étiquettes</h2>
        <form class="form" id="photos">
          <label class="large">IA de Home Assistant (lecture d'étiquette, garde)
            <select name="ia_active">${options({ 1: "Activée", 0: "Désactivée" }, r.ia_active)}</select></label>
          <label class="large">Estimation de la garde par l'IA, chaque mois
            <select name="ia_garde_auto">${options({ 1: "Activée", 0: "Désactivée" }, r.ia_garde_auto)}</select></label>
          <div class="large petit-texte" id="etat-gardes"></div>
          <label class="large">IA à utiliser
            <select name="ia_entite"><option value="">Automatique${entitesIA.length ? ` (${esc(entitesIA[0].nom)})` : " — aucune IA trouvée"}</option>${entitesIA.map((e) => `<option value="${esc(e.entity_id)}"${e.entity_id === r.ia_entite ? " selected" : ""}>${esc(e.nom)}</option>`).join("")}</select></label>
          ${entitesIA.length || !diagIA ? "" : `<div class="large petit-texte diagnostic-ia">
            <b>IA trouvées dans Home Assistant</b><br>
            Tâches IA (photos, garde) : <b>aucune</b><br>
            Agents de conversation : ${diagIA.agents_conversation.length ? esc(diagIA.agents_conversation.join(", ")) : "aucun"}<br>
            <span style="color:var(--danger)">${esc(diagIA.conseil)}</span></div>`}
          <p class="large petit-texte" style="margin:0;color:${CAPACITES.ia.possible ? "var(--ok)" : "var(--texte-2)"}">${CAPACITES.ia.possible ? "✓ Lecture d'étiquette disponible" : "Indisponible : " + esc(CAPACITES.ia.raison)}</p>
          <label class="large">Qualité du détourage
            <select name="detourage_qualite">${options({ rapide: "Rapide (modèle de 5 Mo)", standard: "Standard (45 Mo, recommandé)", precis: "Précis (180 Mo, plus lent, 2 Go de mémoire conseillés)" }, r.detourage_qualite)}</select></label>
          <label class="large">Fond par défaut
            <select name="fond_defaut">${options(Object.fromEntries(CAPACITES.fonds.map((f) => [f.id, f.label])), r.fond_defaut)}</select></label>
          <label class="large">Cadrage par défaut
            <select name="cadrage_defaut">${options(Object.fromEntries((CAPACITES.cadrages || []).map((c) => [c.id, c.label])), r.cadrage_defaut)}</select></label>
          ${CAPACITES.detourage ? "" : `<p class="large petit-texte muted" style="margin:0">Le détourage n'est pas disponible sur cette installation (bibliothèques de traitement d'image absentes) : les photos sont gardées telles quelles.</p>`}
          <div class="actions large"><button class="bouton primaire" type="submit">Enregistrer</button></div>
        </form>
        <p class="muted petit-texte">Le modèle de détourage est téléchargé une seule fois, au premier usage, puis tout se fait sur votre installation. Pour la lecture d'étiquette, la photo est envoyée à l'IA configurée dans Home Assistant.</p>
      </div>
      <div class="carte"><h2>🔌 Intégration Home Assistant</h2>
        <p>L'intégration <b>Tessvine</b> (dossier <code>custom_components/cave_a_vin</code>) crée dans Home Assistant :</p>
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
        <p>Tessvine version ${esc(REF.version)}${r.addon ? " — module complémentaire Home Assistant" : ""}.</p>
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
  const etatGardes = $("#etat-gardes", main);
  const afficherGardes = (g) => {
    if (!g) return;
    const derniere = g.derniere ? `Dernier passage : ${dateFr(g.derniere.slice(0, 10))}.` : "Pas encore de passage.";
    etatGardes.innerHTML = g.en_cours
      ? `🤖 Estimation en cours : ${g.fait} / ${g.total} vins…`
      : `${derniere}${g.erreurs?.length ? ` ${g.erreurs.length} erreur(s) : ${esc(g.erreurs.slice(0, 3).join(" ; "))}` : ""}
         ${g.ia?.possible ? `<button class="bouton petit" type="button" id="lancer-gardes">🤖 Réestimer la garde de toute la cave maintenant</button>`
           : `<br><span style="color:var(--danger)">IA indisponible : ${esc(g.ia?.raison || "inconnue")}.</span>`}`;
    const bouton = $("#lancer-gardes", etatGardes);
    if (bouton) bouton.onclick = async () => {
      try { afficherGardes(await api("POST", "ia/gardes", {})); suivre(); } catch (err) { toast(err.message, true); }
    };
  };
  const suivre = async () => {
    const g = await api("GET", "ia/gardes").catch(() => null);
    if (!document.body.contains(etatGardes)) return;
    afficherGardes(g);
    if (g?.en_cours) setTimeout(suivre, 2000);
  };
  afficherGardes(gardes);
  if (gardes?.en_cours) setTimeout(suivre, 2000);
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
  [/^ajouter$/, pageAjouter, "ajouter"],
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
    $("#autres").classList.toggle("actif", ["envies", "historique", "reglages"].includes(menu));
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

$("#autres").addEventListener("click", feuillePlus);

let derniereRoute = "";
window.addEventListener("hashchange", () => {
  const chemin = location.hash.split("?")[0];
  if (chemin !== derniereRoute) window.scrollTo(0, 0);
  derniereRoute = chemin;
  route();
});
route();
