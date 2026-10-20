# Journal des modifications

## 1.15.0

- **Température et humidité dans le bandeau d'accueil** : les capteurs de la cave s'affichent en grand sous le nombre de
  bouteilles, avec la plage idéale, et passent en rouge s'ils en sortent (« trop humide », « trop chaude »…).
- **Filtre à charbon des caves électriques** (merci pour l'idée !) : durée de vie (3 à 24 mois), date du dernier
  remplacement, bouton **Filtre remplacé**, historique. Rappel dans le bandeau d'accueil et **notification Home
  Assistant** deux semaines avant l'échéance (une fois par échéance). Petit bouton « Filtre » sur chaque cave électrique
  du plan. Dans l'intégration : un capteur « Filtre à charbon » (date du prochain remplacement) par cave suivie et une
  action `cave_a_vin.filtre_remplace`.
- **Statistiques → Par prix** : classement des vins en cave du plus cher au moins cher (prix d'une bouteille), selon
  la **valeur estimée** ou le **prix d'achat**, avec le nombre de bouteilles, le total par vin et le total de la cave.

## 1.14.5

- **Place libre : uniquement des bouteilles en stock.** On ne peut plus « créer » une bouteille en touchant une place
  vide : on y range une bouteille en stock sans place, ou on y **déplace** une bouteille déjà rangée ailleurs (le
  bouton indique d'où elle vient). Le stock ne change pas. Pour un nouvel achat : « Nouveau vin dans cette case ».

## 1.14.4

- **Ranger dans une place libre** : au lieu de listes déroulantes, toutes vos fiches s'affichent avec la bouteille
  dessinée (ou la photo), le nom, le millésime, l'appellation et le stock, avec une recherche. Les bouteilles déjà en
  stock sans place sont proposées en premier ; touchez une fiche, puis « Ranger ici ».

## 1.14.3

- Présentation mise à jour (GitHub et HACS) : nouvelles captures (vue éclatée, réglage d'une rangée, bouteilles
  redessinées), nouveautés récentes, images visibles aussi dans HACS. Version anglaise de la présentation à jour.

## 1.14.2

- Correction : le module **ne plantait plus au démarrage** sur un processeur sans instructions SSE4.2 (x86-64-v2),
  fréquent dans une machine virtuelle Proxmox avec un type de processeur générique. La cave démarre normalement ;
  seul le détourage des photos est désactivé, avec la raison et la solution dans le journal et dans **Réglages → IA,
  photos & étiquettes** (machine virtuelle : type de processeur « host »). Merci pour le signalement détaillé !

## 1.14.1

- **Sens des bouteilles**, rang par rang, comme dans une vraie cave : *Avant* (goulot vers vous), *Arrière* (fond vers
  vous), *Alterné* (goulot et fond l'un après l'autre, en commençant par l'un ou l'autre), *Allongé* (couchées de
  côté, goulot à droite ou à gauche). Choix avec aperçu dans « Personnalisez votre rangée » ; nouvelles bouteilles
  dessinées vues par le fond et de côté.
- Correction : **supprimer une étagère** fonctionne de nouveau (la confirmation se fermait toute seule).
- Casier avec des rangs derrière : le **premier toucher** sur une bouteille ouvre la vue éclatée ; le suivant agit sur
  la bouteille, même au fond.
- **Places libres** en gris clair : un casier vide se distingue bien du fond sombre.
- Sur téléphone, plus d'infobulle qui reste affichée après un toucher.

## 1.14.0

- **Vue éclatée** : touchez le nom d'un casier (« Rangée 3 », « Réfrigérateur »…) : les autres casiers s'estompent et
  ses rangs de derrière glissent au-dessus de celui de devant, chacun sur sa tablette en bois, avec « devant » /
  « derrière ». Toucher un casier estompé le met en avant ; toucher le fond revient à la vue d'ensemble. Une bouteille
  localisée au fond ouvre directement cette vue. Elle remplace les boutons « Tout / Devant / Derrière ».
- **Bouteilles redessinées** : vues presque de face, comme dans une vraie cave (moins inclinées, goulot vers vous),
  et plus serrées : elles se touchent presque, et s'emboîtent dans les creux en quinconce.
- L'aperçu du réglage d'un casier et le choix d'un emplacement montrent aussi les rangs écartés.

## 1.13.1

- **« Personnalisez votre rangée »** : le bouton **+ Rangée** ajoute une étagère dessous ou dessus, ou une colonne à côté,
  avec sa disposition et ses rangs derrière ; le compteur **Rangées identiques** en ajoute plusieurs d'un coup.
- Le réglage d'un casier est plus visible : bouton **✎ Régler** sur chaque casier, et **Modifier** ouvre le réglage
  complet (nom, disposition, rangs derrière).
- L'aperçu de la disposition tient dans la largeur d'un téléphone.

## 1.13.0

- **Disposition réelle des casiers** : largeur, hauteur et **empilement** (aligné, décalé à gauche ou à droite quand
  les bouteilles se calent dans les creux de l'étage du dessous), et jusqu'à 4 **rangs en profondeur** (« rang
  derrière »). Aperçu en direct pendant le réglage, dès la création d'une cave.
- **Lecture des bouteilles** : le plan dessine les bouteilles en quinconce comme dans la vraie cave ; « Tout / Devant /
  Derrière » isole chaque rang, et la position indique le rang (« A3 · derrière »). Une bouteille localisée au fond
  ouvre directement la vue « Derrière ».
- **English version**: l'application est en anglais ou en français selon la langue du téléphone ou du navigateur,
  avec un choix dans **Réglages → Affichage**. **Devise** réglable (€, $, £, CHF). Notifications et textes de l'IA
  dans la langue choisie ; unités des capteurs de l'intégration dans la langue et la devise de Home Assistant.
  README et notice en anglais.
- Correction : modifier le nom d'une cave ne réinitialise plus sa disposition.

## 1.12.0

- **Nouvelle identité visuelle « Chai de nuit »** : anthracite, bordeaux, ivoire et or patiné ; titres, noms de vins
  et chiffres en Cormorant Garamond, interface en Instrument Sans. Thème clair (papier ivoire) et sombre (anthracite)
  selon le réglage de l'appareil. Icônes au trait à la place des émojis dans les boutons. Nouvelle icône.
- **Bouteilles dessinées** d'après chaque vin : bordelaise, bourguignonne, flûte d'Alsace, champagne ; verre teinté
  ou blanc (on voit alors la couleur du vin), capsule, reflets et ombre. L'étiquette porte les vraies informations
  (domaine, nom, appellation, millésime) et s'adapte à la taille d'affichage.
- **Plan de cave** : vitrine sombre où les bouteilles ressortent, formes et couleurs selon le vin, places libres
  discrètes. Zoom (boutons, pincement, Ctrl + molette), « Ajuster à l'écran », taille mémorisée. Recherche dans la
  cave (nom, millésime ou position comme « B4 »), mise en évidence par couleur ou par garde, infobulle au survol,
  vue « Liste » du contenu par casier, fenêtre de bouteille avec son dessin et sa position. Taux de remplissage de
  chaque casier ; caves électriques signalées.
- **Fiche d'un vin** : la bouteille en scène quand il n'y a pas de photo ; millésime mis en valeur.
- **Mes vins** : cartes avec bouteille, appellation, garde ; filtres par couleur en un geste.
- **Accueil** : vins réservés pour une occasion (note personnelle), les plus proches d'abord.
- **Annuler une sortie** : « Annuler » dans le message qui suit la sortie (30 minutes), la bouteille revient à sa place.
- **Note personnelle datée** : une date d'occasion facultative ; Home Assistant le rappelle 7 jours avant.
- **Prix payé** à côté de la valeur estimée sur l'accueil.

## 1.11.0

- **Place libre dans la cave électrique : choisir le vin à y mettre.** Bouton « Choisir un autre vin » dans l'alerte
  de l'accueil : liste des vins avec photo d'étiquette, appellation, garde, valeur et emplacement actuel, puis
  « Ranger » ouvre le plan prêt à le placer.
- **Priorité** : d'abord les vins qui ont le plus d'années de garde devant eux (ceux qui profitent d'une cave stable),
  puis les plus précieux. La température de service n'entre pas en compte ; les vins à garde dépassée et ceux du
  réfrigérateur ne sont pas proposés.

## 1.10.0

- **Page « Statistiques »** (menu) : par couleur, garde, région, millésime, cave et derniers mouvements. Chaque ligne
  ou barre ouvre « Mes vins » filtré (par exemple toutes les bouteilles de 2022, ou celles à l'apogée).
- **Couleurs distinctes par étape de garde** : à garder (bleu), prêt à boire (vert), à l'apogée (or), après l'apogée
  (orange), à boire vite (rouge), dépassée (gris).
- **Place libre** : s'il ne reste aucune bouteille à ranger, la cave propose de déplacer vers la cave électrique la
  plus prestigieuse d'une étagère non réfrigérée (jamais celles du réfrigérateur).
- Mets & Vins : le plat « Barbecue » est retiré (l'ancien nom reste accepté par les scripts).
- « Mes vins » : le badge de filtre dit précisément ce qui est filtré.

## 1.9.1

- **Bouteilles en 3D** sur le plan de cave : vues par le goulot comme dans un vrai casier (corps qui s'enfonce,
  épaule bombée et éclairée, capsule métallisée), plus grandes et qui se chevauchent. Champagnes avec collerette
  dorée, bouchon et muselet.
- Le nom d'un casier, son ❄ et son ✎ sont alignés sur une même ligne.

## 1.9.0

- **Bouteilles réalistes** sur le plan : bouteilles de vin couchées (verre teinté, reflets, capsule métallisée) et
  vraies bouteilles de champagne pour les effervescents (collerette dorée, bouchon et muselet).
- **Caves électriques** : à la création d'une cave ou d'une étagère, et dans leur ✎, la question « Est-ce une cave
  électrique ? ». Seules les caves électriques (❄ sur le plan) déclenchent l'alerte de place libre. Une cave nommée
  « … électrique » est reconnue automatiquement.
- **Casier principal** modifiable comme une étagère : nom, rangées, colonnes, cave électrique.
- **Mets & Vins** : 16 plats précis en tuiles animées (bœuf, agneau, canard, gibier, volaille, porc, poisson, fruits de
  mer, foie gras, fromages, pâtes et pizza, barbecue, épicé, végétarien, dessert, apéritif), chacun avec ses vins ;
  classement par qualité de l'accord puis par urgence ; photo de la bouteille à gauche.
- **Accueil** : « À boire vite » et « Prêts à boire » côte à côte, puis une séparation avant les statistiques.

## 1.8.0

- **Note personnelle** sur un vin (« À boire pour un anniversaire ») : elle clignote en rouge sous le titre de
  la fiche, et sortir ce vin demande « Êtes-vous sûr de vouloir consommer ce vin ? » en rappelant la note.
- **Notifications de fin de garde** (Réglages → Notifications) : Home Assistant prévient quand un vin entre dans sa
  dernière année de garde, au plus 2 fois par vin, à 15 jours d'intervalle. Bouton d'envoi d'un test.
- **Bouteilles non rangées** : nombre sur le plan de cave, liste avec photo d'étiquette, appellation et domaine,
  bouton « Ranger » ; chiffre « à ranger » dans le bandeau de l'accueil.
- **Place libre** : le bandeau de l'accueil signale les places libres et propose d'y mettre la bouteille non rangée
  la plus prestigieuse, puis de choisir l'emplacement sur le plan.
- **Casiers** : nom du casier principal modifiable ; disposition des étagères modifiable (position et casier de
  référence) ; nom d'étagère facultatif ; casiers alignés en haut et empilés en colonnes ; fin trait noir à la place
  de la tablette en bois.
- La bouteille localisée clignote en noir puis en rouge.
- Accueil : « Par couleur », « Par région » et « Par cave » juste sous « À boire vite ».
- « Mes vins » signale un filtre actif, avec un bouton « Tout afficher ».

## 1.7.0

- **Plan de cave redessiné** : un casier de bouteilles couchées vues par le goulot, colorées selon le vin, posées sur
  une tablette. Seule la bouteille dessinée réagit au toucher, plus de clic à côté.
- **Étagères** : bouton « + Étagère » pour ajouter un casier en haut, en bas, à gauche ou à droite d'un autre, avec
  ses propres rangées et colonnes. Chaque étagère se modifie ou se supprime (ses bouteilles restent dans la cave).
- **Localiser une bouteille** : bouton sur la fiche (Emplacements) et petit bouton 📍 sur chaque carte de « Mes vins ».
  Le plan s'ouvre et toutes les bouteilles du vin clignotent.
- **Ranger en touchant le plan** : en enregistrant un vin ou en ajoutant des bouteilles, le plan de la cave choisie
  s'affiche ; on touche les emplacements, les bouteilles y sont rangées.
- **Nom de la cave** modifiable dans Réglages → Ma cave.
- « Ce soir ? » devient **« Mets & Vins »**.

## 1.6.1

- L'appellation (Fitou, Chablis…) s'affiche en premier sous le nom du vin, dans les listes et sur l'accueil : on
  reconnaît un vin même quand son nom de cuvée ne la mentionne pas.

## 1.6.0

- **Ajout d'un vin en deux photos** : l'étiquette, puis le verso (contre-étiquette), qu'on peut ignorer. L'IA lit
  les deux en une seule demande et remplit mieux la fiche (cépages, degré, contenance…). Le verso n'est pas conservé.
- **Le code-barres est récupéré sur la photo du verso** (lu directement sur l'image, sinon recopié par l'IA). Si le
  vin est déjà dans la cave, la cave propose d'y ajouter des bouteilles.
- L'ajout par scan du code-barres disparaît de la page « Ajouter ».
- **Sortir une bouteille par son code-barres** : bouton sur l'accueil et dans « Mes vins ».

## 1.5.0

- **La cave s'appelle désormais Tessvine** (barre latérale de Home Assistant, application, écran d'accueil de
  l'iPhone). Les données, les capteurs et la liste d'envies existants ne changent pas.
- La page principale n'est plus jamais gardée en mémoire par le navigateur : chaque mise à jour s'affiche tout de suite.

## 1.4.2

- Après une mise à jour, l'iPhone (et l'appli Home Assistant) recharge forcément la nouvelle mise en page au lieu de
  garder l'ancienne en mémoire.

## 1.4.1

- **Fiche d'un vin sur iPhone corrigée** : elle gardait la mise en page sur deux colonnes de l'iPad et écrasait le
  texte. Titre, compteur, frise de garde puis boutons en grille de deux.
- **Nouvelle typographie** : titres en Fraunces (police intégrée, fonctionne sans internet), sous-titres en italique.
- Accueil sur iPhone : le statut de garde passe sous le nom du vin, les noms ne sont plus coupés.

## 1.4.0

- **Nouveau design « cave en pierre »** : tons pierre et vert bouteille, lie-de-vin et or pour l'apogée, mode sombre
  « nuit de cave ».
- **Accueil** : le « casier vivant » montre chaque bouteille de la cave par sa couleur, avec le total, la valeur et
  les bouteilles bues dans l'année.
- **iPhone** : barre d'onglets en bas avec un gros bouton « Ajouter » au centre, fenêtres qui montent du bas, filtres
  qui défilent. Icône d'écran d'accueil.
- **iPad et ordinateur** : menu latéral fixe (en icônes sur iPad en portrait).
- IA : le conseil explique quoi faire quand l'intégration d'IA installée ne sait pas faire de « tâche IA ».

## 1.3.6

- Réglages → IA : diagnostic de ce que Home Assistant propose (tâches IA, agents de conversation) et marche à suivre
  adaptée : ajouter une « tâche IA » à une intégration d'IA existante, ou installer une intégration d'IA.
- Le message d'erreur de lecture d'étiquette donne cette même marche à suivre.

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
