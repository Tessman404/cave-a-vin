# Journal des modifications

## 1.3.5

- **IA choisie automatiquement** : si aucune IA n'est choisie dans les réglages de la cave et que Home Assistant n'a
  pas d'IA « préférée », la cave utilise la première « tâche IA » (AI Task) disponible. Corrige l'erreur
  « No entity_id provided and no preferred entity set ».
- Message clair s'il n'existe aucune IA « tâche IA » dans Home Assistant, avec la marche à suivre.
- Réglages : l'option « Automatique » indique l'IA qui sera utilisée.

## 1.3.4

- **Scan du code-barres beaucoup plus fiable** :
  - codes **verticaux** reconnus (c'est le cas de la plupart des contre-étiquettes sur une bouteille debout) ;
  - photo du code lue à plusieurs tailles, et en recadrant le centre quand le code est petit ;
  - caméra en direct en haute définition avec mise au point continue ;
  - si la caméra en direct est bloquée (fréquent dans le panneau Home Assistant), la fenêtre de scan propose
    directement de **photographier le code-barres** ou de **taper ses chiffres**, avec la raison du blocage.
- **Plan de cave** : dans une case vide, « ➕ Nouveau vin dans cette case » ouvre l'ajout (scan, photo, IA ou saisie)
  et range la bouteille dans cette case. Pour un vin déjà connu trouvé par le scan, « Ajouter des bouteilles » la range
  aussi dans la case. Plusieurs bouteilles : la première dans la case choisie, les suivantes dans les cases libres.

## 1.3.3

- **Photo détourée : gros plan sur l'étiquette** par défaut. Le corps de la bouteille remplit l'image (le col sort du
  cadre), l'étiquette est environ deux fois plus grande et se lit sur la fiche. Le cadrage « Bouteille entière »
  reste disponible dans la fenêtre « 🎨 Fond » et comme réglage par défaut.
- Images mises en scène plus détaillées (1200 × 1600).
- Sur la fiche, toucher la photo l'ouvre en grand, avec un bouton pour voir la photo d'origine.

## 1.3.2

- **Lecture d'étiquette bien plus complète** : l'IA recopie ce qui est écrit (y compris le producteur indiqué dans
  « mis en bouteille par… ») puis complète avec ses connaissances : région et pays d'après l'appellation, couleur,
  cépages habituels, **prix de marché indicatif**, **accords mets-vins** et une courte **description** (dans les notes).
  Avant, la consigne lui demandait de laisser vide tout ce qui n'était pas écrit mot pour mot.
- Couleurs comprises même en texte libre (« Vin rouge », « Champagne brut », « Moelleux »…).
- L'étape de lecture indique les informations trouvées et celles qui restent à compléter.

## 1.3.1

- Le bouton « 🤖 Demander la garde à l'IA » est toujours visible sur la fiche d'un vin ; si l'IA n'est pas
  joignable, il indique pourquoi au lieu d'être caché. Même chose dans les réglages.

## 1.3.0

- **Garde estimée par l'IA de Home Assistant** : pour chaque vin en cave, l'IA estime la fenêtre de dégustation
  (début, apogée, fin) en tenant compte du producteur, de l'appellation, de la qualité du millésime, du prix et du
  format, avec une courte justification et un niveau de confiance. Premier passage au démarrage du module, puis
  **chaque mois** ; les nouveaux vins sont estimés dès leur ajout. Bouton « 🤖 Demander la garde à l'IA » sur la fiche,
  et « Réestimer toute la cave » dans les réglages.
- Une garde **corrigée à la main n'est jamais modifiée** par l'IA : sa suggestion reste affichée sur la fiche.
- **Statuts plus justes** : l'apogée est un plateau limité (environ 40 % du temps entre l'apogée et la fin de garde),
  suivi d'un nouveau statut « Après l'apogée ». Avant, un vin restait « À l'apogée » jusqu'à la fin de sa garde.
- « Apogée dépassée » devient « Garde dépassée ».

## 1.2.1

- Garde des vins **sans millésime** : elle n'est plus « à boire dès maintenant » d'office. Elle est comptée à
  partir de l'année d'achat (première entrée en cave), avec le même potentiel qu'un vin millésimé du même
  niveau : un champagne de grande maison reste à garder plusieurs années, un rosé courant est à boire vite.

## 1.2.0

- **Ajout assisté** (bouton « + Ajouter ») :
  - **scan du code-barres** avec l'appareil photo du téléphone : si le vin est déjà dans la cave, on ajoute
    des bouteilles en un clic ; sinon la fiche est pré-remplie depuis **Open Food Facts** (base libre) ;
  - **photo de la bouteille** si le vin est inconnu : l'**IA de Home Assistant** (action « AI Task ») lit
    l'étiquette et remplit la fiche (nom, domaine, appellation, millésime, couleur…) ;
  - la bouteille est **détourée automatiquement** et posée sur un **fond de cave** au choix (cave voûtée,
    casier en bois, studio bordeaux, pierre claire). Le détourage se fait sur votre installation.
- Bouton « 🎨 Fond » sur la fiche d'un vin pour changer de décor (la photo d'origine est conservée).
- Code-barres enregistré sur la fiche : un nouveau scan retrouve directement le vin.
- Nouveaux réglages : IA à utiliser, qualité du détourage, fond par défaut.
- Le module n'est plus proposé pour les systèmes 32 bits (armv7), abandonnés par Home Assistant.

## 1.1.0

- Estimation de garde plus juste : elle tient compte du prix (prix d'achat ou valeur) et de l'appellation.
  Un Médoc à 5 € n'est plus estimé comme un grand cru : il est classé « vin de tous les jours » (à boire sous 5 ans),
  un Saint-Julien à 60 € « vin de garde », un Côte-Rôtie à 250 € « grand vin de garde ».

## 1.0.0

Première version :

- inventaire des vins (fiche complète, photo d'étiquette, favoris, recherche et filtres) ;
- plan de cave visuel : plusieurs caves, casiers en rangées × colonnes ou rangement libre ;
- fenêtre de garde (à boire à partir de / apogée / avant) avec estimation automatique ;
- sorties avec note sur 5 et commentaire de dégustation, historique complet ;
- « Que boire ce soir ? » : suggestions selon le plat ;
- liste d'envies, exports CSV / JSON, import CSV, restauration de sauvegarde ;
- affichage de la température et de l'humidité de la cave depuis Home Assistant ;
- panneau dans la barre latérale de Home Assistant et découverte automatique de l'intégration.
