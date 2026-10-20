# Tessvine: quick start 🍷

*[Version française](https://github.com/Tessman404/cave-a-vin/blob/main/NOTICE.md)*

Manage your wine cellar in Home Assistant, in 5 minutes. The app is in English or French, following your phone or browser (you can change it in **Settings → Display**, along with the currency).

![Tessvine](https://raw.githubusercontent.com/Tessman404/cave-a-vin/main/docs/en/dashboard.png)

## 1. Install (2 minutes)

You need **Home Assistant OS** (most installations: Raspberry Pi, Home Assistant Green, mini-PC…).

1. Click this button from the computer or phone where Home Assistant is open:

   [![Add the repository to Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FTessman404%2Fcave-a-vin)

   *(or by hand: Settings → Add-ons → Add-on store → ⋮ → Repositories → paste `https://github.com/Tessman404/cave-a-vin`)*
2. Search for **Tessvine** in the store → **Install** (one to two minutes).
3. Turn on **Show in sidebar**, then **Start**.

**Tessvine** appears in Home Assistant's sidebar, on a computer as well as in the mobile app.

## 2. Describe your cellar (1 minute)

**Cellar map → + New cellar**: a name, then the layout of your rack or wine fridge:

- **Width** and **Height**: how many bottles side by side, and how many layers;
- **Stacking**: *Aligned* (each bottle in its own slot) or *Offset left / right* (bottles nested in the gaps of the layer below, like in a wine fridge);
- **Bottle direction**: *Neck out*, *Base out*, *Alternate*, or *Side* (lying on their side, neck right or left);
- **Row behind**: add a second row of bottles behind the first one, if your shelves are deep enough. On the map, tap the rack's name: its rows move apart, each on its own shelf, and you can see every bottle, even at the back.

Several racks? **+ Shelf** adds a shelf below or above, or a column next to it; the “Identical shelves” counter adds several at once.
Tell Tessvine if it's a **wine fridge**: it will let you know when a spot frees up.

![Cellar map](https://raw.githubusercontent.com/Tessman404/cave-a-vin/main/docs/en/cellar-map.png)

## 3. Add a wine (1 minute)

**+** button → **Photograph the bottle**, then its back label (or **Skip**).
Home Assistant's AI fills in the details: name, producer, appellation, vintage, drinking window… *(you need an AI set up in Home Assistant, see [Turn on the AI](#turn-on-the-ai-optional-free-5-minutes); otherwise, fill in the form by hand)*.
Choose the cellar and **tap the spot** where you put the bottle on the map. That's it.

## 4. Every day

- **What should I drink?** Home shows wines to **drink soon** and those **ready to drink**.
- **With what?** **Food & Wine**: choose the dish, Tessvine suggests the best bottles.
- **Where is it?** On a wine's page, **Locate**: its bottles blink on the map.
- **I'm drinking it**: tap the bottle on the map → **Take out**, or scan its barcode. A mistake? **Undo**.
- **A special occasion?** Add a note (“For Paul's birthday”, with the date): Home Assistant reminds you 7 days before.

| On a phone | A bottle on the map |
|---|---|
| ![My wines](https://raw.githubusercontent.com/Tessman404/cave-a-vin/main/docs/en/mobile.png) | ![Bottle](https://raw.githubusercontent.com/Tessman404/cave-a-vin/main/docs/en/bottle-mobile-dark.png) |

## Turn on the AI (optional, free, 5 minutes)

Without AI, Tessvine works just fine: you fill in the form by hand and the drinking window is estimated by a general rule.
With AI, **a photo of the label is enough** to fill in the form, and each wine's drinking window is estimated precisely.
Example with **Google Gemini**, which has a free tier:

1. **Get a key**: on [aistudio.google.com](https://aistudio.google.com/apikey), sign in with a Google account → **Create API key** → copy the key.
2. **Add it to Home Assistant**: *Settings → Devices & services → Add integration* → search for **Google Generative AI** (Gemini) → paste the key.
3. **Create the “AI Task”**: in that integration, tap **Add AI Task** (button or ⋮ menu) and confirm. This is what Tessvine uses.
4. **Check**: in Tessvine, **Settings → AI, photos & labels** should show “Label reading available”. If not, that page explains what's missing.

Good to know:
- you need **Home Assistant 2025.8 or later**;
- it also works with OpenAI, Anthropic or a local AI (Ollama with a model that understands images); you always need an integration that offers “Add AI Task”;
- an AI that Home Assistant is only *connected to* (Claude or ChatGPT subscriptions, MCP server…) can't be used by Tessvine;
- label photos are sent to the AI service you chose; with Google's free tier, they may be used to improve its products.
- with English selected, the AI writes its notes in English.

## 5. Optional

- **Notifications** (Settings): choose your phone to be told about wines reaching the end of their window.
- **Carbon filter**: on the map, tap “Filter” on your wine fridge, enter its lifetime and the date it was last changed: Tessvine reminds you two weeks before.
- **Cellar temperature** (Settings): choose your sensors, temperature and humidity show on the home page, in red if they leave the right range.
- **Sensors and actions in Home Assistant** (dashboards, Assist): install the integration with HACS, see the [full guide](https://github.com/Tessman404/cave-a-vin/blob/main/README.en.md#2-add-the-integration-sensors-actions-wishlist).

Your data stays **at home**, in Home Assistant, and is included in its backups.

---

A question, an idea? [Open an issue on GitHub](https://github.com/Tessman404/cave-a-vin/issues).
Enjoying Tessvine? [Buy me a coffee on Ko-fi](https://ko-fi.com/tessman) 🍷
