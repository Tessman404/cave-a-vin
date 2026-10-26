# Tessvine 🍷

*[English version](https://github.com/Tessman404/cave-a-vin/blob/main/README.en.md)*

**➡️ Nouveau ? Lisez la [notice rapide](https://github.com/Tessman404/cave-a-vin/blob/main/NOTICE.md) : installé et utilisé en 5 minutes.**

[![Soutenir Tessvine sur Ko-fi](https://img.shields.io/badge/Soutenir%20le%20projet-Ko--fi-7a1b33?logo=ko-fi&logoColor=white)](https://ko-fi.com/tessman)

Un logiciel de gestion de cave à vin, dans l'esprit d'Oeni, **qui s'intègre à Home Assistant** : il s'ouvre dans la barre latérale de Home Assistant, lit la température et l'humidité de votre cave, et crée des capteurs, une liste d'envies et des actions utilisables dans vos automatisations ou avec Assist.

| Tableau de bord | Sur téléphone |
|---|---|
| ![Tableau de bord](https://raw.githubusercontent.com/Tessman404/cave-a-vin/main/docs/tableau-de-bord.png) | ![Mes vins sur mobile](https://raw.githubusercontent.com/Tessman404/cave-a-vin/main/docs/mobile.png) |

| Plan de cave | Fiche d'un vin |
|---|---|
| ![Plan de cave](https://raw.githubusercontent.com/Tessman404/cave-a-vin/main/docs/plan-de-cave.png) | ![Fiche d'un vin](https://raw.githubusercontent.com/Tessman404/cave-a-vin/main/docs/fiche-vin.png) |

| Vue éclatée : les rangs de derrière s'écartent | Personnalisez votre rangée | Plan sur téléphone (thème sombre) |
|---|---|---|
| ![Vue éclatée d'un casier à deux rangs](https://raw.githubusercontent.com/Tessman404/cave-a-vin/main/docs/vue-eclatee.png) | ![Réglage d'une rangée : largeur, hauteur, rang derrière, sens des bouteilles](https://raw.githubusercontent.com/Tessman404/cave-a-vin/main/docs/reglage-rangee.png) | ![Plan de cave sur téléphone](https://raw.githubusercontent.com/Tessman404/cave-a-vin/main/docs/plan-mobile-sombre.png) |

| Une bouteille du plan | Mets & Vins |
|---|---|
| ![Fenêtre d'une bouteille](https://raw.githubusercontent.com/Tessman404/cave-a-vin/main/docs/bouteille-mobile-sombre.png) | ![Mets & Vins sur téléphone](https://raw.githubusercontent.com/Tessman404/cave-a-vin/main/docs/ce-soir-mobile.png) |

*Captures réalisées avec une cave de démonstration (version 1.14).*

**Nouveautés récentes** : vue éclatée des casiers à plusieurs rangs, **sens des bouteilles** rang par rang (goulot ou fond vers vous, alterné, allongé), bouteilles vues de face et plus serrées, « Personnalisez votre rangée » avec rangées identiques, version **anglaise** et devise réglable. Détail : [journal des modifications](https://github.com/Tessman404/cave-a-vin/blob/main/cave_a_vin/CHANGELOG.md).

Ce qu'il fait :

- **ajout en un geste** : **photographiez la bouteille**, puis son verso : l'**IA de Home Assistant lit l'étiquette** et remplit la fiche, le **code-barres** est lu sur le verso, et la bouteille est **détourée et posée sur un fond de cave** (cave voûtée, casier en bois, studio, pierre claire) ;
- **inventaire complet** : cuvée, domaine, appellation, région, couleur, millésime, cépages, format, prix d'achat, valeur estimée, fournisseur, accords, notes, note personnelle datée, code-barres, photo ;
- **bouteilles dessinées** d'après chaque vin : bordelaise, bourguignonne, flûte d'Alsace ou champagne, verre et capsule selon le vin, étiquette avec le domaine, le nom, l'appellation et le millésime ;
- **plan de cave fidèle** : chaque casier est décrit tel qu'il est (**largeur, hauteur, empilement** aligné ou décalé quand les bouteilles se calent dans les creux, et **rangs derrière** pour les étagères profondes), et le **sens des bouteilles** rang par rang : goulot vers vous, fond vers vous, alterné, ou allongées de côté ; touchez le nom d'un casier : les autres s'estompent et ses rangs s'écartent (vue éclatée), chacun sur sa tablette, pour lire chaque bouteille sans hésiter. Une cave principale et ses étagères, placées en haut, en bas, à gauche ou à droite ; bouteilles couchées vues par le goulot. Zoom, recherche (nom, millésime ou position comme « B4 »), mise en évidence par couleur ou par garde, vue en liste, **localisation** d'un vin (ses bouteilles clignotent). Toucher une bouteille pour la sortir ou la déplacer, une place vide pour y ranger une bouteille. Les **places libres d'une cave électrique** sont signalées, avec le vin à y mettre en priorité ;
- **sortie par code-barres** : scannez la bouteille pour la sortir ; une sortie par erreur s'annule d'un geste ;
- **garde** : « à boire à partir de », « apogée », « à boire avant », **estimée par l'IA de Home Assistant** (producteur, appellation, qualité du millésime, prix) et réévaluée chaque mois, ou par une règle générale sans IA. Une garde corrigée à la main est toujours respectée. Les vins à boire vite sont signalés partout ;
- **dégustations** : chaque bouteille sortie peut recevoir une note sur 5 et un commentaire, conservés dans l'historique ;
- **notifications Home Assistant** : un vin qui arrive en fin de garde (au plus deux rappels, à quinze jours d'écart), une occasion notée sur un vin, sept jours avant, et le **filtre à charbon** d'une cave électrique à changer ;
- **climat de la cave** : température et humidité de vos capteurs Home Assistant affichées en grand sur l'accueil, en rouge hors de la plage idéale ;
- **« Mets & Vins »** : choisissez le plat (bœuf, agneau, canard, poisson, fromages…), la cave classe les bouteilles de la mieux accordée à la moins accordée, puis celles à boire en priorité ;
- **statistiques** : bouteilles, valeur estimée et prix payé, répartition par couleur, région, millésime, garde et cave, **classement des vins par prix** ; chaque ligne ouvre les vins correspondants ;
- **liste d'envies** (vins à acheter), visible aussi dans Home Assistant ;
- **sauvegarde** : export CSV (Excel), sauvegarde complète JSON, import CSV ;
- **en français, en anglais ou en italien** selon l'appareil, devise réglable (€, $, £, CHF) ;
- fonctionne sur ordinateur, tablette et téléphone, en thème clair (ivoire) ou sombre (anthracite) selon l'appareil ;
- **léger** : Python, tourne sur un Raspberry Pi 4 ou 5 ; le détourage des photos se fait sur votre installation, sans service extérieur.

---

## Sommaire

1. [Installation dans Home Assistant (recommandé)](#1-installation-dans-home-assistant-recommandé)
2. [Ajouter l'intégration (capteurs, actions, envies)](#2-ajouter-lintégration-capteurs-actions-envies)
3. [Afficher la température de la cave](#3-afficher-la-température-de-la-cave)
4. [Premiers pas](#4-premiers-pas)
   - [Ajouter un vin : scan, photo et IA](#4-bis-ajouter-un-vin--scan-photo-et-ia)
5. [Exemples d'automatisations et de tableau de bord](#5-exemples-dautomatisations-et-de-tableau-de-bord)
6. [Installation sans Home Assistant OS (Docker)](#6-installation-sans-home-assistant-os-docker)
7. [Import, export et sauvegardes](#7-import-export-et-sauvegardes)
8. [Pour les curieux : API et développement](#8-pour-les-curieux--api-et-développement)

---

## 1. Installation dans Home Assistant (recommandé)

Cette méthode demande **Home Assistant OS** ou **Supervised** (ceux qui ont le menu *Paramètres → Modules complémentaires*). Sinon, voir la [section 6](#6-installation-sans-home-assistant-os-docker).

### Méthode A : depuis la boutique (recommandé)

[![Ajouter le dépôt à Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FTessman404%2Fcave-a-vin)

Cliquez sur le bouton ci-dessus, ou à la main :

1. *Paramètres → Modules complémentaires → Boutique des modules complémentaires*.
2. Menu **⋮** en haut à droite → **Dépôts** → collez `https://github.com/Tessman404/cave-a-vin` → **Ajouter**.
3. Cherchez **Tessvine** dans la boutique → **Installer** (la construction prend une à deux minutes sur un Raspberry Pi).

Les nouvelles versions apparaîtront ensuite comme des mises à jour classiques.

### Méthode B : en module local (sans accès à GitHub)

1. Installez le module **Samba share** ou **Advanced SSH & Web Terminal** pour accéder aux fichiers de Home Assistant.
2. Copiez le dossier **`cave_a_vin`** (celui qui contient `config.yaml`) dans le dossier **`addons`** de Home Assistant. Vous devez obtenir `addons/cave_a_vin/config.yaml`.
3. *Paramètres → Modules complémentaires → Boutique* → menu **⋮** → **Rechercher des mises à jour**.
4. **Tessvine** apparaît dans la section **Modules complémentaires locaux** → **Installer** (la construction prend une à deux minutes sur un Raspberry Pi).

### Ensuite

1. Dans l'onglet **Info** du module, activez **Afficher dans la barre latérale** et **Démarrer au démarrage**, puis **Démarrer**.
2. L'entrée **Tessvine** 🍷 apparaît dans la barre latérale : c'est votre cave, accessible aussi depuis l'application mobile Home Assistant, y compris hors de chez vous.

Vos données (base de données et photos) sont stockées dans le module et **incluses dans les sauvegardes Home Assistant**.

Onglet **Configuration** du module (facultatif) :

| Option | Rôle |
|---|---|
| **Clé d'API** | Protège l'accès direct à la cave (port 8099 et intégration). Le panneau dans Home Assistant n'est pas concerné. |
| **Réseau → 8099/tcp** | Renseignez `8099` pour ouvrir la cave directement sur `http://<ip-de-home-assistant>:8099` (inutile si vous passez par Home Assistant). |

---

## 2. Ajouter l'intégration (capteurs, actions, envies)

Le module complémentaire donne l'interface ; l'**intégration** donne les capteurs et les actions pour vos automatisations.

### Installation

- **Avec HACS** (recommandé, pour recevoir les mises à jour) :

  [![Ouvrir dans HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Tessman404&repository=cave-a-vin&category=integration)

  ou à la main : *HACS → ⋮ → Dépôts personnalisés* → `https://github.com/Tessman404/cave-a-vin`, catégorie **Intégration** → installez **Tessvine**.
- **À la main** : copiez le dossier **`custom_components/cave_a_vin`** dans le dossier `config/custom_components/` de Home Assistant (créez `custom_components` s'il n'existe pas).

Puis **redémarrez Home Assistant**.

### Configuration

- **Avec le module complémentaire**, la cave est **détectée automatiquement** : une notification « Nouvel appareil détecté : Tessvine » apparaît dans *Paramètres → Appareils et services*. Cliquez sur **Configurer**, c'est tout.
- Sinon : *Paramètres → Appareils et services → Ajouter une intégration → Tessvine*, puis saisissez l'adresse :
  - module complémentaire : `http://<nom d'hôte>:8099`, le nom d'hôte étant indiqué dans l'onglet **Info** du module (par exemple `local-cave-a-vin`) ;
  - installation Docker : `http://<ip-de-la-machine>:8099`.
  - Si vous avez défini une clé d'API, saisissez-la aussi.

### Ce que vous obtenez

| Entité | Contenu |
|---|---|
| `sensor.tessvine_bouteilles` | Nombre de bouteilles (attributs : par couleur, par cave, par garde) |
| `sensor.tessvine_references` | Nombre de vins différents |
| `sensor.tessvine_valeur_de_la_cave` | Valeur estimée en € |
| `sensor.tessvine_pretes_a_boire` | Bouteilles dans leur fenêtre de garde (attribut `vins` : la liste) |
| `sensor.tessvine_a_boire_vite` | Bouteilles en dernière année de garde ou dépassées (attribut `vins`) |
| `sensor.tessvine_bues_cette_annee` | Bouteilles bues depuis le 1er janvier |
| `sensor.tessvine_dernier_mouvement` | Dernière entrée/sortie (attributs : note, commentaire, date…) |
| un capteur par cave | Bouteilles dans chaque cave (attributs : capacité, places libres, taux de remplissage) |
| un capteur « Filtre à charbon » par cave électrique suivie | Date du prochain remplacement (attributs : jours restants, dernier remplacement) |
| `todo.tessvine_envies` | Votre liste d'envies, modifiable depuis Home Assistant et **avec Assist** : « Ajoute Meursault à Tessvine Envies » |

Les noms exacts des entités dépendent de la langue de Home Assistant : vérifiez-les dans *Paramètres → Appareils et services → Tessvine*. Sur une installation antérieure au changement de nom, elles commencent par `cave_a_vin_` au lieu de `tessvine_`.

| Action | Rôle |
|---|---|
| `cave_a_vin.sortir_bouteille` | Sort une ou plusieurs bouteilles d'un vin, avec note et commentaire |
| `cave_a_vin.ajouter_bouteilles` | Ajoute des bouteilles d'un vin déjà connu |
| `cave_a_vin.suggerer_vin` | Renvoie les meilleures bouteilles pour un plat (réponse utilisable dans un script) |
| `cave_a_vin.rechercher_vin` | Cherche un vin et renvoie son identifiant, son stock, sa garde |
| `cave_a_vin.filtre_remplace` | Enregistre le remplacement du filtre à charbon d'une cave électrique |

---

## 3. Afficher la température de la cave

Si votre cave a un capteur de température et/ou d'humidité dans Home Assistant (Zigbee, Bluetooth, Wi-Fi…), la cave l'affiche sur son tableau de bord, avec une alerte s'il sort de la plage idéale.

1. Dans la cave : **Réglages → Home Assistant — capteurs de la cave**.
2. Choisissez vos capteurs dans les listes (avec le module complémentaire, la connexion est automatique).
3. Ajustez les plages idéales (par défaut 10–16 °C et 60–80 % d'humidité) → **Enregistrer**.

Sans le module complémentaire, renseignez aussi l'adresse de Home Assistant et un **jeton d'accès longue durée** (*Profil → Sécurité → Jetons d'accès longue durée → Créer un jeton*).

---

## 4. Premiers pas

1. **Plan de cave → + Nouvelle cave** : donnez un nom et décrivez la disposition : largeur, hauteur, empilement (aligné ou décalé), et **rang derrière** si vos étagères sont profondes (ou choisissez un rangement libre, sans plan). Le crayon au-dessus d'un casier permet de la modifier ensuite. Créez-en autant que vous avez d'emplacements (cave, armoire à vin, cellier…).
2. Ajoutez des **étagères** (bouton **+ Rangée**, avec le nombre de rangées identiques à ajouter d'un coup) en haut, en bas, à gauche ou à droite d'un casier pour reproduire votre cave ; indiquez si c'est une **cave électrique** pour être prévenu de ses places libres.
3. **+ Ajouter** : photographiez la bouteille ou saisissez la fiche à la main (voir ci-dessous). Le bouton **Estimer** propose une fenêtre de garde ; corrigez-la si votre caviste vous a donné d'autres conseils. Indiquez le nombre de bouteilles et la cave : le plan s'affiche, touchez les places où vous les rangez.
4. Sur la fiche, **Photo de l'étiquette** pour prendre ou changer la photo, **Fond** pour changer de décor. Sans photo, la fiche montre la bouteille dessinée d'après le vin.
5. Pour boire une bouteille : bouton **−** ou **Déguster / sortir** sur la fiche, toucher sa place dans le plan, ou **Sortir par code-barres**. Ajoutez une note et vos impressions : elles restent dans l'historique, même si le vin n'est plus en cave. Une sortie par erreur s'annule avec **Annuler** dans le message qui suit.
6. Dans le plan, touchez une **place vide** pour y ranger une bouteille non rangée, ou une bouteille puis **Déplacer** pour changer sa place. Sur la fiche d'un vin, **Localiser dans la cave** ouvre le plan où ses bouteilles clignotent.

Astuce : sur téléphone, utilisez *Ajouter à l'écran d'accueil* depuis le navigateur pour avoir la cave comme une application.

---

## 4 bis. Ajouter un vin : scan, photo et IA

![Ajouter un vin](https://raw.githubusercontent.com/Tessman404/cave-a-vin/main/docs/ajout-assiste.png)

Bouton **+ Ajouter**, puis **Photographier la bouteille** :

1. **L'étiquette** (de face, étiquette lisible, la bouteille entière dans l'image) :
   - la bouteille est **détourée** et posée sur le **fond de cave** choisi dans les réglages, en **gros plan sur l'étiquette** (ou bouteille entière) ; **Changer de fond** pour essayer les autres fonds et cadrages. La photo d'origine est conservée : vous pourrez changer de fond plus tard depuis la fiche.
2. **Le verso** (facultatif, bouton **Ignorer**) : la contre-étiquette complète la fiche (cépages, degré…) et donne le **code-barres**, qui servira à sortir la bouteille d'un simple scan.
3. L'**IA lit les étiquettes** : nom, domaine, appellation, millésime, couleur, cépages, degré, valeur. Si le vin est **déjà dans votre cave**, un bouton propose plutôt d'ajouter des bouteilles à ce vin.
4. Vérifiez la fiche pré-remplie, indiquez le nombre de bouteilles, choisissez la cave et touchez leurs places sur le plan, puis **Ajouter à ma cave**.

**Garde estimée par l'IA** : la même IA estime la fenêtre de dégustation de chaque vin en cave, au démarrage du module puis chaque mois, et chaque nouveau vin dès son ajout. La fiche indique l'origine de la garde (« estimée par l'IA », avec sa justification et sa confiance, ou « saisie à la main »). Si vous corrigez une garde, l'IA ne la touche plus et affiche seulement sa suggestion ; le bouton **Garde par l'IA** la remplace à votre demande. Statuts : *À garder* → *Prêt à boire* → *À l'apogée* (plateau) → *Après l'apogée* → *À boire vite* (dernière année) → *Garde dépassée*.

**Pas à pas pour activer l'IA (Google Gemini gratuit)** : voir la [notice rapide](https://github.com/Tessman404/cave-a-vin/blob/main/NOTICE.md#activer-lia-facultatif-gratuit-5-minutes).

**Ce qu'il faut pour la lecture d'étiquette** : Home Assistant 2025.8 ou plus récent, avec une intégration d'IA qui fournit une entité **« AI Task »** et qui comprend les images : OpenAI, Google Gemini, Anthropic (Claude), ou Ollama avec un modèle de vision (par exemple `qwen2.5vl`). Dans la cave, **Réglages → IA, photos & étiquettes** indique si tout est prêt et permet de choisir l'IA. La photo est alors envoyée à cette IA (et donc à son fournisseur si elle est en ligne).

**Le détourage** se fait sur votre installation, sans rien envoyer. Le modèle (45 Mo) est téléchargé au premier usage : la toute première photo prend environ une minute, les suivantes quelques secondes. Trois qualités au choix dans les réglages : *rapide* (5 Mo), *standard* et *précis* (180 Mo, pour un Raspberry Pi 5 ou un mini-PC).

**Sortir par code-barres** : le scan en direct demande une connexion sécurisée (adresse en `https://`, par exemple l'accès distant Home Assistant Cloud). Sur une adresse `http://` locale, les navigateurs interdisent la caméra en direct : l'application ouvre alors l'appareil photo pour **photographier le code-barres**, qu'elle lit ensuite. Vous pouvez aussi taper les chiffres.

---

## 5. Exemples d'automatisations et de tableau de bord

### Rappel hebdomadaire des bouteilles à boire vite

```yaml
automation:
  - alias: "Cave : bouteilles à boire vite"
    triggers:
      - trigger: time
        at: "18:00:00"
    conditions:
      - condition: time
        weekday: [fri]
      - condition: numeric_state
        entity_id: sensor.tessvine_a_boire_vite
        above: 0
    actions:
      - action: notify.mobile_app_mon_telephone
        data:
          title: "🍷 À boire ce week-end"
          message: "{{ state_attr('sensor.tessvine_a_boire_vite', 'vins') | join(', ') }}"
```

### Alerte de température de la cave

Elle se fait directement sur votre capteur (exemple : `sensor.cave_temperature`) :

```yaml
automation:
  - alias: "Cave : température anormale"
    triggers:
      - trigger: numeric_state
        entity_id: sensor.cave_temperature
        above: 18
        for: "01:00:00"
    actions:
      - action: notify.mobile_app_mon_telephone
        data:
          message: "La cave est à {{ states('sensor.cave_temperature') }} °C !"
```

### Script « Que boire ce soir ? » (utilisable avec Assist)

```yaml
script:
  vin_du_soir:
    alias: "Que boire ce soir ?"
    fields:
      plat:
        description: "boeuf, agneau, canard, gibier, volaille, porc, poisson, fruits_de_mer, foie_gras, fromage, pates_pizza, epice, vegetarien, dessert ou aperitif"
    sequence:
      - action: cave_a_vin.suggerer_vin
        data:
          plat: "{{ plat | default('boeuf') }}"
          nombre: 3
        response_variable: cave
      - variables:
          resultat:
            texte: >-
              {% for s in cave.suggestions %}{{ s.nom }}{{ ' ' ~ s.millesime if s.millesime }}{{ ', ' if not loop.last }}{% endfor %}
      - stop: ""
        response_variable: resultat
```

Exposez ce script à Assist (*Paramètres → Assistants vocaux → Exposer*) : avec un assistant conversationnel (LLM), « Quel vin pour l'agneau ce soir ? » suffit.

### Carte de tableau de bord

```yaml
type: vertical-stack
cards:
  - type: glance
    title: Tessvine
    entities:
      - entity: sensor.tessvine_bouteilles
        name: Bouteilles
      - entity: sensor.tessvine_pretes_a_boire
        name: Prêtes
      - entity: sensor.tessvine_a_boire_vite
        name: Vite !
      - entity: sensor.cave_temperature
        name: Temp.
  - type: markdown
    content: >-
      **À boire vite :** {{ state_attr('sensor.tessvine_a_boire_vite', 'vins') | join(' · ') or 'rien d’urgent' }}
  - type: todo-list
    entity: todo.tessvine_envies
```

---

## 6. Installation sans Home Assistant OS (Docker)

Pour Home Assistant « Container », un NAS ou un serveur :

```bash
git clone https://github.com/Tessman404/cave-a-vin.git
cd cave-a-vin
docker compose up -d
```

La cave est alors sur `http://<ip-de-la-machine>:8099` et ses données dans le dossier `donnees/`. Les variables commentées dans `docker-compose.yml` permettent d'ajouter une clé d'API et la connexion à Home Assistant (aussi réglable depuis la page **Réglages**). Ajoutez ensuite l'intégration comme expliqué en [section 2](#2-ajouter-lintégration-capteurs-actions-envies).

Sans Docker, avec Python 3.11 ou plus récent :

```bash
cd cave-a-vin/cave_a_vin
pip install -r requirements.txt   # facultatif : détourage des photos
python3 -m app                    # données dans ./data, interface sur http://localhost:8099
```

Sans le module Home Assistant, la lecture d'étiquette par l'IA demande que la cave puisse écrire dans le dossier `media` de Home Assistant : indiquez son chemin dans la variable `HA_MEDIA_DIR`.

Variables d'environnement : `CAVE_DATA_DIR` (dossier des données), `CAVE_PORT` (port, 8099 par défaut), `CAVE_API_KEY` (clé d'API), `HA_URL` et `HA_TOKEN` (connexion à Home Assistant), `HA_MEDIA_DIR` (dossier media de Home Assistant, pour l'IA).

> Si la cave est accessible depuis Internet sans passer par Home Assistant, **définissez une clé d'API**.

---

## 7. Import, export et sauvegardes

Dans **Réglages → Sauvegarde & import** :

- **Exporter en CSV** : un fichier qui s'ouvre dans Excel ou LibreOffice (séparateur `;`), une ligne par vin avec sa quantité ;
- **Sauvegarde complète (JSON)** : tout (caves, vins, emplacements, historique, envies), sauf les photos (elles sont dans les sauvegardes Home Assistant) ;
- **Importer un CSV** : pour reprendre une cave tenue dans un tableur ou exportée d'une autre application. La première ligne doit contenir les noms de colonnes ; seule `nom` est obligatoire. Colonnes reconnues : `nom`, `domaine`, `appellation`, `region`, `pays`, `couleur` (`rouge`, `blanc`, `rose`, `effervescent`, `liquoreux`, `autre`), `millesime`, `cepages`, `format`, `degre`, `prix_achat`, `valeur`, `fournisseur`, `garde_debut`, `garde_apogee`, `garde_fin`, `accords`, `notes`, `favori`, `code_barre`, `quantite`. Le plus simple : exportez d'abord un CSV pour voir le format, puis renommez les colonnes de votre fichier ;
- **Restaurer une sauvegarde JSON** : remplace toute la cave.

---

## 8. Pour les curieux : API et développement

Organisation :

```
cave-a-vin/
├── cave_a_vin/                 module complémentaire Home Assistant
│   ├── config.yaml, build.yaml, Dockerfile
│   ├── app/                    application (Python)
│   │   ├── server.py           serveur HTTP et routes de l'API
│   │   ├── cave.py             logique : vins, bouteilles, garde, accords, stats
│   │   ├── db.py               base SQLite
│   │   ├── ha.py               lecture des capteurs Home Assistant
│   │   ├── scan.py             recherche par code-barres (Open Food Facts)
│   │   ├── photo.py            détourage (onnxruntime) et mise en scène sur fond
│   │   ├── ia.py               lecture d'étiquette et garde par l'IA de Home Assistant (ai_task)
│   │   ├── garde_ia.py         estimation de la garde : à l'ajout, à la demande et chaque mois
│   │   └── static/             interface web (HTML/CSS/JS, sans étape de compilation ; vendor/ : lecteur ZXing)
│   └── tests/                  tests de l'API
├── custom_components/cave_a_vin/   intégration Home Assistant
├── tests_ha/                   tests de l'intégration dans un vrai Home Assistant
├── outils/fonds/               sources des fonds de cave (SVG) et script de rendu
├── repository.yaml, hacs.json  pour publier en dépôt de modules / HACS
└── docker-compose.yml
```

Principales routes (toutes en JSON, préfixe `api/`) :

| Route | Rôle |
|---|---|
| `GET vins?q=&couleur=&statut=&cave_id=&stock=1\|0\|all&tri=` | Liste et recherche |
| `POST vins` · `GET/PUT/DELETE vins/{id}` | Fiches des vins |
| `POST vins/{id}/entree` · `POST vins/{id}/sortie` | Ajouter / sortir des bouteilles |
| `PUT vins/{id}/photo` · `POST vins/{id}/photo/fond` | Photo (data-URL, `fond` facultatif) · changer de fond |
| `GET scan/{code}` | Vin de la cave ou d'Open Food Facts correspondant au code-barres |
| `POST brouillons` · `POST brouillons/{id}/rendu` · `POST brouillons/{id}/lire` | Photo en cours d'ajout : détourage sur fond, lecture par l'IA |
| `GET capacites` | Détourage, fonds et IA disponibles |
| `POST vins/{id}/garde-ia` · `GET/POST ia/gardes` | Garde d'un vin par l'IA · état / lancement du passage sur toute la cave |
| `GET/POST caves` · `GET/PUT/DELETE caves/{id}` | Caves et plan |
| `PUT bouteilles/{id}` | Déplacer une bouteille |
| `GET suggestion?plat=&couleur=` | Accords |
| `GET stats` · `GET ha/resume` | Statistiques (le second est utilisé par l'intégration) |
| `GET export.csv` · `GET export.json` · `POST import.csv` · `POST import.json` | Sauvegardes |

Avec une clé d'API, ajoutez l'en-tête `X-API-Key: <clé>` (ou `Authorization: Bearer <clé>`).

Lancer les tests :

```bash
# API (Pillow et numpy conseillés pour les tests de photos, sinon ils sont ignorés)
cd cave_a_vin && python3 -m unittest discover -s tests

# Intégration Home Assistant
pip install pytest-homeassistant-custom-component
python3 -m pytest -c tests_ha/pytest.ini --rootdir . tests_ha
```

---

## Soutenir le projet

Tessvine est gratuit et développé sur mon temps libre. S'il vous rend service, vous pouvez [m'offrir un café sur Ko-fi](https://ko-fi.com/tessman) 🍷 Merci !
