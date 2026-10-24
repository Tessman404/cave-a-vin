# Tessvine : notice rapide 🍷

*[English version](https://github.com/Tessman404/cave-a-vin/blob/main/NOTICE.en.md)*

Gérer sa cave à vin dans Home Assistant, en 5 minutes.

![Tessvine](https://raw.githubusercontent.com/Tessman404/cave-a-vin/main/docs/tableau-de-bord.png)

## 1. Installer (2 minutes)

Il faut **Home Assistant OS** (le cas de la plupart des installations : Raspberry Pi, Home Assistant Green, mini-PC…).

1. Cliquez sur ce bouton depuis l'ordinateur ou le téléphone où Home Assistant est ouvert :

   [![Ajouter le dépôt à Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FTessman404%2Fcave-a-vin)

   *(ou à la main : Paramètres → Modules complémentaires → Boutique → ⋮ → Dépôts → collez `https://github.com/Tessman404/cave-a-vin`)*
2. Cherchez **Tessvine** dans la boutique → **Installer** (une à deux minutes).
3. Activez **Afficher dans la barre latérale**, puis **Démarrer**.

**Tessvine** apparaît dans la barre latérale de Home Assistant, sur ordinateur comme dans l'application mobile.

## 2. Décrire sa cave (1 minute)

**Plan de cave → + Nouvelle cave** : un nom, puis la disposition de votre casier ou armoire à vin :

- **Largeur** et **Hauteur** : combien de bouteilles côte à côte, et combien d'étages ;
- **Empilement** : *Aligné* (chaque bouteille dans sa case) ou *Décalé à gauche / à droite* (les bouteilles se calent dans les creux de l'étage du dessous, comme dans une cave électrique) ;
- **Sens des bouteilles** : *Avant* (goulot vers vous), *Arrière* (fond vers vous), *Alterné*, ou *Allongé* (de côté, goulot à droite ou à gauche) ;
- **Retirer des emplacements** : pour un casier en diagonale ou avec un montant, touchez « Retirer des emplacements » puis les places qui n'existent pas ;
- **Rang derrière** : un deuxième rang de bouteilles derrière le premier, si vos étagères sont profondes. Sur le plan, touchez le nom du casier : ses rangs s'écartent, chacun sur sa tablette, et vous voyez toutes les bouteilles, même celles du fond.

Vous avez plusieurs casiers ? **+ Rangée** pour ajouter une étagère dessous ou dessus, ou une colonne à côté ; le compteur « Rangées identiques » en ajoute plusieurs d'un coup.
Dites si c'est une **cave électrique** : Tessvine vous préviendra quand une place s'y libère.

![Plan de cave](https://raw.githubusercontent.com/Tessman404/cave-a-vin/main/docs/plan-de-cave.png)

## 3. Ajouter un vin (1 minute)

Bouton **+** → **Photographier la bouteille**, puis son verso (ou **Ignorer**).
L'IA de Home Assistant remplit la fiche : nom, domaine, appellation, millésime, garde… *(il faut une IA configurée dans Home Assistant, voir [Activer l'IA](#activer-lia-facultatif-gratuit-5-minutes) ; sinon, saisissez la fiche à la main)*.
Choisissez la cave et **touchez la place** où vous rangez la bouteille sur le plan. C'est tout.

## 4. Au quotidien

- **Que boire ?** L'accueil montre les vins **à boire vite** et ceux **prêts à boire**.
- **Avec quoi ?** **Mets & Vins** : choisissez le plat, Tessvine propose les meilleures bouteilles.
- **Où est-elle ?** Sur la fiche d'un vin, **Localiser** : ses bouteilles clignotent sur le plan.
- **Je la bois** : touchez la bouteille sur le plan → **Sortir**, ou scannez son code-barres. Une erreur ? **Annuler**.
- **Une occasion ?** Ajoutez une note (« Pour l'anniversaire de Paul », avec la date) : Home Assistant vous le rappelle 7 jours avant.

| Sur téléphone | Une bouteille du plan |
|---|---|
| ![Mes vins](https://raw.githubusercontent.com/Tessman404/cave-a-vin/main/docs/mobile.png) | ![Bouteille](https://raw.githubusercontent.com/Tessman404/cave-a-vin/main/docs/bouteille-mobile-sombre.png) |

## Activer l'IA (facultatif, gratuit, 5 minutes)

Sans IA, Tessvine marche très bien : vous saisissez la fiche à la main et la garde est estimée par une règle générale.
Avec l'IA, une **photo de l'étiquette suffit** pour remplir la fiche, et la garde de chaque vin est estimée finement.
Exemple avec **Google Gemini**, qui a une offre gratuite :

1. **Obtenir une clé** : sur [aistudio.google.com](https://aistudio.google.com/apikey), connectez-vous avec un compte Google → **Create API key** → copiez la clé.
2. **L'ajouter à Home Assistant** : *Paramètres → Appareils et services → Ajouter une intégration* → cherchez **Google Generative AI** (Gemini) → collez la clé.
3. **Créer la « tâche IA »** : dans cette intégration, touchez **Ajouter une tâche IA** (bouton ou menu ⋮) et validez. C'est elle qu'utilise Tessvine.
4. **Vérifier** : dans Tessvine, **Réglages → IA, photos & étiquettes** doit afficher « Lecture d'étiquette disponible ». Sinon, cette page explique ce qui manque.

Bon à savoir :
- il faut **Home Assistant 2025.8 ou plus récent** ;
- ça marche aussi avec OpenAI, Anthropic ou une IA locale (Ollama avec un modèle qui comprend les images) ; il faut toujours une intégration qui propose « Ajouter une tâche IA » ;
- une IA à laquelle Home Assistant est seulement *connecté* (Claude ou ChatGPT par abonnement, serveur MCP…) ne peut pas être utilisée par Tessvine ;
- les photos d'étiquettes sont envoyées au service d'IA choisi ; avec l'offre gratuite de Google, elles peuvent servir à améliorer ses produits.

## 5. En option

- **Bouton de retour vers Home Assistant** (Réglages) : en haut du menu (ou dans « Plus » sur téléphone), il ramène à la page « Aperçu » ; vous pouvez changer son texte et la page de destination, ou le masquer.
- **Notifications** (Réglages) : choisissez votre téléphone pour être prévenu des vins en fin de garde.
- **Filtre à charbon** : sur le plan, touchez « Filtre » sur votre cave électrique, indiquez sa durée de vie et la date du dernier changement : Tessvine vous prévient deux semaines avant.
- **Température de la cave** (Réglages) : choisissez vos capteurs, la température et l'humidité s'affichent sur l'accueil, en rouge si elles sortent de la bonne plage.
- **Capteurs et actions dans Home Assistant** (tableaux de bord, Assist) : installez l'intégration avec HACS, voir le [guide complet](https://github.com/Tessman404/cave-a-vin/blob/main/README.md#2-ajouter-lintégration-capteurs-actions-envies).

Vos données restent **chez vous**, dans Home Assistant, et sont incluses dans ses sauvegardes.

---

Une question, une idée ? [Ouvrez un ticket sur GitHub](https://github.com/Tessman404/cave-a-vin/issues).
Tessvine vous plaît ? [Offrez-moi un café sur Ko-fi](https://ko-fi.com/tessman) 🍷
