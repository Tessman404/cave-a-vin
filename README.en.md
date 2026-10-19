# Tessvine 🍷

*[Version française](https://github.com/Tessman404/cave-a-vin/blob/main/README.md)*

**➡️ New here? Read the [quick start](https://github.com/Tessman404/cave-a-vin/blob/main/NOTICE.en.md): installed and running in 5 minutes.**

[![Support Tessvine on Ko-fi](https://img.shields.io/badge/Support%20the%20project-Ko--fi-7a1b33?logo=ko-fi&logoColor=white)](https://ko-fi.com/tessman)

A wine cellar manager **built into Home Assistant**: it opens in Home Assistant's sidebar, reads your cellar's temperature and humidity, and creates sensors, a wishlist and actions you can use in automations or with Assist.

The app speaks **English and French** and follows the language of your phone or browser; you can switch language and currency (€, $, £, CHF) in **Settings → Display**.

| Dashboard | On a phone |
|---|---|
| ![Dashboard](https://raw.githubusercontent.com/Tessman404/cave-a-vin/main/docs/en/dashboard.png) | ![My wines on a phone](https://raw.githubusercontent.com/Tessman404/cave-a-vin/main/docs/en/mobile.png) |

| Cellar map | Wine page |
|---|---|
| ![Cellar map](https://raw.githubusercontent.com/Tessman404/cave-a-vin/main/docs/en/cellar-map.png) | ![Wine page](https://raw.githubusercontent.com/Tessman404/cave-a-vin/main/docs/en/wine-page.png) |

| Exploded view: back rows move apart | Customize your shelf | Map on a phone (dark theme) |
|---|---|---|
| ![Exploded view of a two-row rack](https://raw.githubusercontent.com/Tessman404/cave-a-vin/main/docs/en/exploded-view.png) | ![Shelf settings: width, height, row behind, bottle direction](https://raw.githubusercontent.com/Tessman404/cave-a-vin/main/docs/en/shelf-settings.png) | ![Cellar map on a phone](https://raw.githubusercontent.com/Tessman404/cave-a-vin/main/docs/en/map-mobile-dark.png) |

| A bottle on the map | Food & Wine |
|---|---|
| ![Bottle window](https://raw.githubusercontent.com/Tessman404/cave-a-vin/main/docs/en/bottle-mobile-dark.png) | ![Food & Wine on a phone](https://raw.githubusercontent.com/Tessman404/cave-a-vin/main/docs/en/food-wine-mobile.png) |

*Screenshots taken with a demo cellar (version 1.14).*

**What's new**: exploded view for racks with several rows, **bottle direction** per row (neck or base toward you, alternate, on the side), bottles seen from the front and closer together, “Customize your shelf” with identical shelves, **English version** and currency choice.

What it does:

- **add a wine in one go**: **photograph the bottle**, then its back label: **Home Assistant's AI reads the label** and fills in the form, the **barcode** is read from the back, and the bottle is **cut out and placed on a cellar background** (vaulted cellar, wooden rack, studio, light stone);
- **full inventory**: wine name, producer, appellation, region, colour, vintage, grapes, size, purchase price, estimated value, supplier, pairings, notes, dated personal note, barcode, photo;
- **bottles drawn from each wine**: Bordeaux, Burgundy, Alsace flute or Champagne shape, glass and capsule matching the wine, label with producer, name, appellation and vintage;
- **an accurate cellar map**: describe each rack exactly as it is — **width, height, stacking** (aligned, or offset left / right when bottles nest in the gaps of the layer below) and **rows behind** for deep shelves, plus the **bottle direction** for each row: neck out, base out, alternate, or lying on their side. The map shows bottles lying down, seen from the neck; tap a rack's name: the others fade and its rows move apart (exploded view), each on its own shelf, so every bottle is easy to read. Zoom, search (name, vintage or position such as “B4”), highlight by colour or drinking window, list view, **locate** a wine (its bottles blink). Tap a bottle to take it out or move it, an empty spot to put a bottle there. **Free spots in a wine fridge** are reported, with the wine to put there first;
- **take out by barcode**: scan the bottle to take it out; a mistake can be undone with one tap;
- **drinking window**: “drink from”, “peak”, “drink by”, **estimated by Home Assistant's AI** (producer, appellation, vintage quality, price) and reviewed every month, or by a general rule without AI. A window you corrected by hand is always kept. Wines to drink soon are flagged everywhere;
- **tastings**: every bottle taken out can get a rating out of 5 and a comment, kept in the history;
- **Home Assistant notifications**: a wine reaching the end of its window (at most two reminders, fifteen days apart), and an occasion noted on a wine, seven days before;
- **“Food & Wine”**: choose the dish (beef, lamb, duck, fish, cheese…), the cellar ranks bottles from best to least matching, then those to drink first;
- **statistics**: bottles, estimated value and price paid, by colour, region, vintage, drinking window and cellar; each row opens the matching wines;
- **wishlist** (wines to buy), also visible in Home Assistant;
- **backups**: CSV export (Excel), full JSON backup, CSV import;
- works on computer, tablet and phone, in a light (ivory) or dark (charcoal) theme following the device;
- **lightweight**: Python, runs on a Raspberry Pi 4 or 5; photo cut-out runs on your own installation, with no outside service.

---

## Contents

1. [Install in Home Assistant (recommended)](#1-install-in-home-assistant-recommended)
2. [Add the integration (sensors, actions, wishlist)](#2-add-the-integration-sensors-actions-wishlist)
3. [Show the cellar temperature](#3-show-the-cellar-temperature)
4. [Getting started](#4-getting-started)
5. [Adding a wine: scan, photo and AI](#5-adding-a-wine-scan-photo-and-ai)
6. [Automation and dashboard examples](#6-automation-and-dashboard-examples)
7. [Install without Home Assistant OS (Docker)](#7-install-without-home-assistant-os-docker)
8. [Import, export and backups](#8-import-export-and-backups)
9. [Developers](#9-developers)

---

## 1. Install in Home Assistant (recommended)

This method needs **Home Assistant OS** or **Supervised** (the ones with the *Settings → Add-ons* menu). Otherwise, see [section 7](#7-install-without-home-assistant-os-docker).

[![Add the repository to Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FTessman404%2Fcave-a-vin)

Click the button above, or by hand:

1. *Settings → Add-ons → Add-on store*.
2. **⋮** menu (top right) → **Repositories** → paste `https://github.com/Tessman404/cave-a-vin` → **Add**.
3. Search for **Tessvine** in the store → **Install** (building takes one to two minutes on a Raspberry Pi).

New versions then show up as regular updates.

Then:

1. In the add-on's **Info** tab, turn on **Show in sidebar** and **Start on boot**, then **Start**.
2. **Tessvine** 🍷 appears in the sidebar: that's your cellar, also available from the Home Assistant mobile app, including away from home.

Your data (database and photos) is stored in the add-on and **included in Home Assistant backups**.

Add-on **Configuration** tab (optional):

| Option | Purpose |
|---|---|
| **API key** | Protects direct access to the cellar (port 8099 and the integration). The panel inside Home Assistant is not affected. |
| **Network → 8099/tcp** | Enter `8099` to open the cellar directly at `http://<home-assistant-ip>:8099` (not needed through Home Assistant). |

---

## 2. Add the integration (sensors, actions, wishlist)

The add-on gives you the app; the **integration** gives you sensors and actions for your automations.

### Install

- **With HACS** (recommended, to get updates):

  [![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Tessman404&repository=cave-a-vin&category=integration)

  or by hand: *HACS → ⋮ → Custom repositories* → `https://github.com/Tessman404/cave-a-vin`, category **Integration** → install **Tessvine**.
- **By hand**: copy the **`custom_components/cave_a_vin`** folder into Home Assistant's `config/custom_components/` folder (create `custom_components` if needed).

Then **restart Home Assistant**.

### Setup

- **With the add-on**, the cellar is **discovered automatically**: a “New device discovered: Tessvine” notification appears in *Settings → Devices & services*. Click **Configure**, that's all.
- Otherwise: *Settings → Devices & services → Add integration → Tessvine*, then enter the address:
  - add-on: `http://<hostname>:8099`, the hostname being shown in the add-on's **Info** tab (for example `local-cave-a-vin`);
  - Docker install: `http://<machine-ip>:8099`.
  - If you set an API key, enter it too.

### What you get

Entity names follow Home Assistant's language; with English they are:

| Entity | Content |
|---|---|
| `sensor.tessvine_bottles` | Number of bottles (attributes: by colour, by cellar, by drinking window) |
| `sensor.tessvine_wines` | Number of different wines |
| `sensor.tessvine_cellar_value` | Estimated value, in Home Assistant's currency |
| `sensor.tessvine_ready_to_drink` | Bottles within their drinking window (attribute `vins`: the list) |
| `sensor.tessvine_drink_soon` | Bottles in the last year of their window or past it (attribute `vins`) |
| `sensor.tessvine_drunk_this_year` | Bottles drunk since January 1st |
| `sensor.tessvine_last_movement` | Last in/out (attributes: rating, comment, date…) |
| one sensor per cellar | Bottles in each cellar (attributes: capacity, free spots, fill rate) |
| `todo.tessvine_wishlist` | Your wishlist, editable from Home Assistant and **with Assist**: “Add Meursault to Tessvine Wishlist” |

Check the exact names in *Settings → Devices & services → Tessvine*.

| Action | Purpose |
|---|---|
| `cave_a_vin.sortir_bouteille` | Take out one or more bottles of a wine, with rating and comment |
| `cave_a_vin.ajouter_bouteilles` | Add bottles of a wine already in the cellar |
| `cave_a_vin.suggerer_vin` | Returns the best bottles for a dish (response usable in a script) |
| `cave_a_vin.rechercher_vin` | Finds a wine and returns its id, stock and drinking window |

---

## 3. Show the cellar temperature

If your cellar has a temperature and/or humidity sensor in Home Assistant (Zigbee, Bluetooth, Wi-Fi…), Tessvine shows it on its dashboard, with a warning when it leaves the ideal range.

1. In Tessvine: **Settings → Home Assistant — cellar sensors**.
2. Pick your sensors from the lists (with the add-on, the connection is automatic).
3. Adjust the ideal ranges (default 10–16 °C and 60–80 % humidity) → **Save**.

Without the add-on, also enter Home Assistant's address and a **long-lived access token** (*Profile → Security → Long-lived access tokens → Create token*).

---

## 4. Getting started

1. **Cellar map → + New cellar**: give it a name and describe the layout — width, height, stacking, and rows behind if your shelves are deep (or a loose storage area without a map). Create as many as you have places (cellar, wine fridge, pantry…).
2. Add **racks** (**+ Shelf** button, with the number of identical shelves to add at once) above, below, left or right of a rack to recreate your cellar; say whether it's a **wine fridge** to be told about free spots.
3. **+ Add**: photograph the bottle or fill in the form by hand (see below). The **Estimate** button suggests a drinking window; correct it if your wine shop gave you other advice. Enter the number of bottles and the cellar: the map appears, tap the spots where you put them.
4. On the wine page, **Label photo** takes or changes the photo, **Background** changes the setting. Without a photo, the page shows the bottle drawn from the wine.
5. To drink a bottle: **−** button or **Drink / take out** on the wine page, tap its spot on the map, or **Take out by barcode**. Add a rating and your impressions: they stay in the history, even when the wine is gone. A mistake can be undone with **Undo** in the message that follows.
6. On the map, tap an **empty spot** to put an unplaced bottle there, or a bottle then **Move** to change its spot. On a wine page, **Locate in the cellar** opens the map with its bottles blinking.

Tip: on a phone, use *Add to Home Screen* in the browser to get the cellar as an app.

---

## 5. Adding a wine: scan, photo and AI

**+ Add**, then **Photograph the bottle**:

1. **The label** (from the front, readable, the whole bottle in the picture): the bottle is **cut out** and placed on the **cellar background** chosen in settings, as a **close-up on the label** (or whole bottle); **Change background** tries the other backgrounds and framings. The original photo is kept, so you can change the background later from the wine page.
2. **The back label** (optional, **Skip** button): it completes the form (grapes, ABV…) and gives the **barcode**, used to take the bottle out with a simple scan.
3. The **AI reads the labels**: name, producer, appellation, vintage, colour, grapes, ABV, value. If the wine is **already in your cellar**, a button offers to add bottles to it instead.
4. Check the pre-filled form, enter the number of bottles, choose the cellar and tap their spots on the map, then **Add to my cellar**.

**Drinking window by AI**: the same AI estimates the drinking window of every wine in the cellar, when the add-on starts and then every month, and each new wine as soon as it's added. The wine page shows where the window comes from (“estimated by AI”, with its reasoning and confidence, or “entered by hand”). If you correct a window, the AI leaves it alone and only shows its suggestion; the **AI drinking window** button replaces it on request. Statuses: *Keep* → *Ready to drink* → *At its peak* → *Past its peak* → *Drink soon* (last year) → *Past its window*.

**Step by step to turn on the AI (free Google Gemini)**: see the [quick start](https://github.com/Tessman404/cave-a-vin/blob/main/NOTICE.en.md#turn-on-the-ai-optional-free-5-minutes).

**What label reading needs**: Home Assistant 2025.8 or later, with an AI integration that provides an **“AI Task”** entity and understands images: OpenAI, Google Gemini, Anthropic (Claude), or Ollama with a vision model (for example `qwen2.5vl`). In Tessvine, **Settings → AI, photos & labels** tells you whether everything is ready and lets you choose the AI. The photo is then sent to that AI (and so to its provider if it's online).

**Cut-out** runs on your installation and sends nothing. The model (45 MB) is downloaded on first use: the very first photo takes about a minute, then a few seconds. Three quality levels in settings: *fast* (5 MB), *standard* and *precise* (180 MB, for a Raspberry Pi 5 or a mini-PC).

**Take out by barcode**: live scanning needs a secure connection (an `https://` address, for example Home Assistant Cloud remote access). On a local `http://` address, browsers block the live camera: the app then opens the camera to **photograph the barcode** and reads it. You can also type the digits.

---

## 6. Automation and dashboard examples

### Weekly reminder of bottles to drink soon

```yaml
automation:
  - alias: "Cellar: bottles to drink soon"
    triggers:
      - trigger: time
        at: "18:00:00"
    conditions:
      - condition: time
        weekday: [fri]
      - condition: numeric_state
        entity_id: sensor.tessvine_drink_soon
        above: 0
    actions:
      - action: notify.mobile_app_my_phone
        data:
          title: "🍷 To drink this weekend"
          message: "{{ state_attr('sensor.tessvine_drink_soon', 'vins') | join(', ') }}"
```

### “What should I drink tonight?” script (works with Assist)

```yaml
script:
  wine_tonight:
    alias: "What should I drink tonight?"
    fields:
      plat:
        description: "boeuf (beef), agneau (lamb), canard (duck), gibier (game), volaille (poultry), porc, poisson (fish), fruits_de_mer (seafood), foie_gras, fromage (cheese), pates_pizza, epice (spicy), vegetarien, dessert or aperitif"
    sequence:
      - action: cave_a_vin.suggerer_vin
        data:
          plat: "{{ plat | default('boeuf') }}"
          nombre: 3
        response_variable: cellar
      - variables:
          result:
            text: >-
              {% for s in cellar.suggestions %}{{ s.nom }}{{ ' ' ~ s.millesime if s.millesime }}{{ ', ' if not loop.last }}{% endfor %}
      - stop: ""
        response_variable: result
```

Expose this script to Assist (*Settings → Voice assistants → Expose*): with a conversational assistant (LLM), “Which wine with lamb tonight?” is enough.

### Dashboard card

```yaml
type: vertical-stack
cards:
  - type: glance
    title: Tessvine
    entities:
      - entity: sensor.tessvine_bottles
        name: Bottles
      - entity: sensor.tessvine_ready_to_drink
        name: Ready
      - entity: sensor.tessvine_drink_soon
        name: Soon!
  - type: markdown
    content: >-
      **Drink soon:** {{ state_attr('sensor.tessvine_drink_soon', 'vins') | join(' · ') or 'nothing urgent' }}
  - type: todo-list
    entity: todo.tessvine_wishlist
```

---

## 7. Install without Home Assistant OS (Docker)

For Home Assistant “Container”, a NAS or a server:

```bash
git clone https://github.com/Tessman404/cave-a-vin.git
cd cave-a-vin
docker compose up -d
```

The cellar is then at `http://<machine-ip>:8099` and its data in the `donnees/` folder. The commented variables in `docker-compose.yml` add an API key and the connection to Home Assistant (also available in **Settings**). Then add the integration as explained in [section 2](#2-add-the-integration-sensors-actions-wishlist).

Environment variables: `CAVE_DATA_DIR` (data folder), `CAVE_PORT` (port, 8099 by default), `CAVE_API_KEY` (API key), `HA_URL` and `HA_TOKEN` (Home Assistant connection), `HA_MEDIA_DIR` (Home Assistant's media folder, for the AI).

> If the cellar is reachable from the Internet without going through Home Assistant, **set an API key**.

---

## 8. Import, export and backups

In **Settings → Backup & import**:

- **Export to CSV**: a file that opens in Excel or LibreOffice (`;` separator), one row per wine with its quantity;
- **Full backup (JSON)**: everything (cellars, wines, spots, history, wishlist), except photos (they are in Home Assistant backups);
- **Import a CSV**: to bring in a cellar kept in a spreadsheet or exported from another app. The first row must hold the column names (in French); only `nom` (name) is required. Recognised columns: `nom`, `domaine` (producer), `appellation`, `region`, `pays` (country), `couleur` (`rouge`, `blanc`, `rose`, `effervescent`, `liquoreux`, `autre`), `millesime` (vintage), `cepages` (grapes), `format`, `degre` (ABV), `prix_achat`, `valeur`, `fournisseur`, `garde_debut`, `garde_apogee`, `garde_fin`, `accords`, `notes`, `favori`, `code_barre`, `quantite`. The easiest way: export a CSV first to see the format, then rename your file's columns;
- **Restore a JSON backup**: replaces the whole cellar.

---

## 9. Developers

The code (in French) and the API are described in the [French README](https://github.com/Tessman404/cave-a-vin/blob/main/README.md#8-pour-les-curieux--api-et-développement). Tests:

```bash
cd cave_a_vin && python3 -m unittest discover -s tests
```

---

## Support the project

Tessvine is free and built in my spare time. If it's useful to you, you can [buy me a coffee on Ko-fi](https://ko-fi.com/tessman) 🍷 Thank you!
