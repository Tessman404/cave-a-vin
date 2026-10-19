# Tessvine

*English: the app follows your device language (English or French). Full guide: [README in English](https://github.com/Tessman404/cave-a-vin/blob/main/README.en.md), [quick start](https://github.com/Tessman404/cave-a-vin/blob/main/NOTICE.en.md).*

Gérez votre cave à vin depuis Home Assistant : inventaire, plan de cave, fenêtres de garde, dégustations, suggestions d'accords et liste d'envies.

## Démarrage

1. Activez **Afficher dans la barre latérale**, puis **Démarrer**.
2. Ouvrez **Tessvine** dans la barre latérale.
3. **Plan de cave → + Nouvelle cave** pour décrire vos casiers (largeur, hauteur, empilement, rangs derrière) (puis **+ Étagère** pour les casiers voisins), et **+ Ajouter** pour vos premiers vins.

## Ajouter un vin

Bouton **+ Ajouter** : photographiez l'étiquette, puis le verso (facultatif) : l'IA remplit la fiche et le code-barres est lu sur le verso. Choisissez ensuite les places sur le plan de cave.

- **Lecture d'étiquette** : utilise l'IA de Home Assistant (action « AI Task », Home Assistant 2025.8 ou plus récent,
  avec une IA qui comprend les images : OpenAI, Google Gemini, Anthropic, Ollama avec un modèle de vision…).
  La photo est déposée un instant dans le dossier `media/cave_a_vin` de Home Assistant, puis supprimée.
  Choix de l'IA : **Réglages → IA, photos & étiquettes** dans la cave.
- **Garde** : la même IA estime la fenêtre de dégustation de chaque vin, au démarrage puis chaque mois
  (désactivable dans les réglages). Une garde corrigée à la main n'est jamais modifiée.
- **Détourage** : fait par le module lui-même. Le modèle (45 Mo) est téléchargé au premier usage, puis conservé.
- **Sortir par code-barres** : le scan en direct demande une adresse `https://`. Sinon, l'application photographie le code-barres pour le lire.

## Notifications

Dans **Réglages → Notifications de fin de garde**, choisissez votre téléphone : Home Assistant vous prévient quand un vin arrive en fin de garde (au plus deux rappels, à quinze jours d'écart), et sept jours avant une occasion notée sur un vin.

## Température et humidité de la cave

Dans la cave : **Réglages → Home Assistant — capteurs de la cave**, choisissez vos capteurs. La connexion à Home Assistant est automatique.

## Intégration (capteurs, actions, liste d'envies)

Copiez le dossier `custom_components/cave_a_vin` dans `config/custom_components/` (ou installez-le avec HACS), puis redémarrez Home Assistant : la cave est détectée automatiquement dans *Paramètres → Appareils et services*.

Pour un ajout manuel, l'adresse est `http://<nom d'hôte>:8099`, avec le nom d'hôte indiqué dans l'onglet **Info** de ce module.

## Options

- **Clé d'API** : protège l'accès direct (port 8099 et intégration). Le panneau Home Assistant n'est pas concerné. Si vous la définissez, saisissez-la aussi dans l'intégration.
- **Niveau de journalisation** : `info` par défaut.

## Données et sauvegardes

La base de données et les photos sont dans le dossier du module : elles font partie des **sauvegardes Home Assistant**. Vous pouvez aussi exporter la cave (CSV ou JSON) depuis **Réglages**.
