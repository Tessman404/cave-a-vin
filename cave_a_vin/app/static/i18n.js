/* Tessvine — traduction de l'interface (français → anglais).
 *
 * L'application est écrite en français. En anglais, chaque texte affiché (nœuds de texte, placeholder, aria-label,
 * title, alt) est traduit au moment où il apparaît : d'abord par correspondance exacte, puis par motifs (phrases avec
 * des nombres ou des noms), puis par remplacements partiels. Les données de l'utilisateur (noms de vins, notes) ne
 * correspondent à aucune entrée et restent intactes. Les dessins SVG et les champs de saisie ne sont jamais touchés.
 *
 * Langue : réglage de l'appareil (Réglages → Affichage), sinon langue du navigateur ou de l'appli Home Assistant.
 */
const I18N = (() => {
  const lire = (cle) => { try { return localStorage.getItem(cle) || ""; } catch { return ""; } };
  const ecrire = (cle, v) => { try { v ? localStorage.setItem(cle, v) : localStorage.removeItem(cle); } catch { /* navigation privée */ } };
  const choix = lire("tessvine-langue");  // "", "fr" ou "en"
  const auto = /^fr\b/i.test(navigator.language || "fr") ? "fr" : "en";
  const langue = choix === "fr" || choix === "en" ? choix : auto;
  const DEVISES = { EUR: "€", USD: "$", GBP: "£", CHF: "CHF" };
  const devise = DEVISES[lire("tessvine-devise")] ? lire("tessvine-devise") : (langue === "en" && /US/.test(navigator.language || "") ? "USD" : "EUR");
  const locale = langue === "fr" ? "fr-FR" : (navigator.language && /^en/i.test(navigator.language) ? navigator.language : "en-US");

  /* ---------------------------------------------------------------- correspondances exactes */
  const EXACT = {
    // navigation
    "Accueil": "Home", "Mes vins": "My wines", "Plan de cave": "Cellar map", "Ajouter": "Add", "Mets & Vins": "Food & Wine",
    "Statistiques": "Statistics", "Envies": "Wishlist", "Historique": "History", "Réglages": "Settings", "Plus": "More",
    "Plus de pages": "More pages", "Navigation principale": "Main navigation", "Ajouter un vin": "Add a wine", "Cave": "Cellar",
    "Ajouter un vin ": "Add a wine",
    // en-têtes
    "Collection": "Collection", "Votre cave": "Your cellar", "Accords": "Pairings", "Nouvelle référence": "New wine",
    "À acheter, à goûter": "To buy, to taste", "Entrées et sorties": "Ins and outs", "Tessvine": "Tessvine",
    "Chargement…": "Loading…", "Oups": "Oops", "Retour à l'accueil": "Back to home",
    // accueil
    "bouteilles dans votre cave": "bottles in your cellar", "bouteille dans votre cave": "bottle in your cellar",
    "références": "wines", "référence": "wine", "valeur estimée": "estimated value", "payé": "paid", "payé (prix connus)": "paid (known prices)",
    "à ranger ›": "to place ›", "Bouteilles sans emplacement sur le plan": "Bottles without a spot on the map",
    "Valeur de marché indicative, souvent estimée par l'IA": "Indicative market value, often estimated by AI",
    "Prix d'achat de toutes les bouteilles": "Purchase price of all bottles",
    "Ranger celle-ci": "Place this one", "Choisir un autre vin": "Choose another wine",
    "Sortir une bouteille par son code-barres": "Take out a bottle by its barcode",
    "À boire vite": "Drink soon", "Prêts à boire": "Ready to drink", "Réservés pour une occasion": "Saved for an occasion",
    "Rien d'urgent : toutes vos bouteilles sont dans leur fenêtre de garde.": "Nothing urgent: all your bottles are within their drinking window.",
    "Aucun vin dans sa fenêtre de dégustation.": "No wine in its drinking window.",
    "Climat de la cave": "Cellar climate", "Température": "Temperature", "Humidité": "Humidity",
    "Voir les statistiques de la cave": "See cellar statistics", "Home Assistant": "Home Assistant",
    "Bienvenue dans votre cave": "Welcome to your cellar",
    "Commencez par décrire votre cave (casiers, armoire à vin…) puis ajoutez vos premières bouteilles.": "Start by describing your cellar (racks, wine fridge…) then add your first bottles.",
    "Créer une cave": "Create a cellar", "aujourd'hui": "today", "demain": "tomorrow", "passée": "past",
    // statuts, couleurs, raisons, plats (référentiel du serveur)
    "À garder": "Keep", "Prêt à boire": "Ready to drink", "À l'apogée": "At its peak", "Après l'apogée": "Past its peak",
    "Garde dépassée": "Past its window", "Garde non renseignée": "No drinking window", "Garde inconnue": "Unknown window",
    "Rouge": "Red", "Blanc": "White", "Rosé": "Rosé", "Effervescent": "Sparkling", "Liquoreux / moelleux": "Sweet / dessert", "Autre": "Other",
    "Achat": "Purchase", "Cadeau": "Gift", "Inventaire": "Inventory", "Transfert": "Transfer", "Bue": "Drunk", "Offerte": "Given away",
    "Vendue": "Sold", "Cassée / bouchonnée": "Broken / corked", "Erreur de saisie": "Data entry error",
    "Bœuf": "Beef", "Agneau": "Lamb", "Canard": "Duck", "Gibier": "Game", "Volaille": "Poultry", "Porc & charcuterie": "Pork & charcuterie",
    "Poisson": "Fish", "Fruits de mer": "Seafood", "Foie gras": "Foie gras", "Fromages": "Cheese", "Pâtes & pizza": "Pasta & pizza",
    "Épicé & exotique": "Spicy & exotic", "Végétarien": "Vegetarian", "Dessert": "Dessert", "Apéritif": "Aperitif",
    "Accord parfait": "Perfect match", "Très bon accord": "Very good match", "Bon accord": "Good match", "Accord possible": "Possible match",
    // mes vins
    "Toutes": "All", "Toutes couleurs": "All colours", "Toutes gardes": "All windows", "Toutes caves": "All cellars",
    "En cave": "In cellar", "Épuisés": "Finished", "Tous": "All", "Tri : nom": "Sort: name", "Tri : millésime": "Sort: vintage",
    "Tri : région": "Sort: region", "Tri : à boire en premier": "Sort: drink first", "Tri : quantité": "Sort: quantity",
    "Tri : valeur": "Sort: value", "Tri : derniers ajouts": "Sort: recently added", "Sortir par code-barres": "Take out by barcode",
    "Nom, domaine, appellation, cépage, millésime…": "Name, producer, appellation, grape, vintage…", "Rechercher": "Search",
    "Couleur": "Colour", "Garde": "Drinking window", "Stock": "Stock", "Tri": "Sort", "Tout afficher": "Show all",
    "⚠ À boire vite ou dépassés": "⚠ Drink soon or past", "✓ Prêts à boire": "✓ Ready to drink", "filtre actif": "filter on",
    "Aucun résultat": "No results", "Aucun vin ne correspond à ces critères.": "No wine matches these filters.",
    "bouteille": "bottle", "bouteilles": "bottles", "Localiser dans la cave": "Locate in the cellar", "Fenêtre de dégustation": "Drinking window",
    "Favori": "Favourite", "♥ Favori": "♥ Favourite",
    // fiche
    "Mes vins ": "My wines", "Photo de l'étiquette": "Label photo", "Changer la photo": "Change photo", "Fond": "Background", "Retirer": "Remove",
    "Agrandir": "Enlarge", "Bouteilles en cave": "Bottles in cellar", "bouteilles en cave": "bottles in cellar", "Sortir une bouteille": "Take out a bottle", "Ajouter une bouteille": "Add a bottle",
    "Déguster / sortir": "Drink / take out", "Ajouter des bouteilles": "Add bottles", "Modifier": "Edit", "Garde par l'IA": "AI drinking window",
    "Ajouter aux favoris": "Add to favourites", "Supprimer": "Delete", "Caractéristiques": "Details", "Appellation": "Appellation",
    "Région": "Region", "Pays": "Country", "Cépages": "Grapes", "Format": "Size", "Degré": "ABV", "Prix d'achat": "Purchase price",
    "Valeur estimée": "Estimated value", "Fournisseur": "Supplier", "À boire": "Drink", "Apogée": "Peak", "Notes": "Notes",
    "Emplacements": "Locations", "Historique & dégustations": "History & tastings", "Date": "Date", "Mouvement": "Movement",
    "Note": "Rating", "Commentaire": "Comment", "Aucun mouvement.": "No movements.", "Plus aucune bouteille en cave.": "No bottles left in the cellar.",
    "Non rangée": "Not placed", "Garde saisie à la main : l'IA ne la modifie pas.": "Window entered by hand: the AI won't change it.",
    "L'IA réfléchit…": "The AI is thinking…", "Photo d'origine": "Original photo", "Photo mise en scène": "Styled photo", "Fermer": "Close",
    // formulaire
    "Fiche du vin": "Wine page", "Modifier le vin": "Edit wine", "Identité": "Identity", "Nom de la cuvée *": "Wine name *",
    "Château Margaux, Clos des Mouches…": "Château Margaux, Clos des Mouches…", "Domaine / producteur": "Producer", "Millésime": "Vintage",
    "Non millésimé": "Non-vintage", "Merlot, Cabernet franc": "Merlot, Cabernet Franc", "Degré (%)": "ABV (%)", "Code-barres": "Barcode",
    "Rempli par le scan": "Filled in by the scan", "Achat & valeur": "Purchase & value", "Prix d'achat (€ / bouteille)": "Purchase price (per bottle)",
    "Valeur actuelle estimée (€)": "Current estimated value", "Fournisseur / caviste": "Supplier / wine shop", "À boire à partir de": "Drink from",
    "À boire avant (fin)": "Drink by (end)", "Estimer": "Estimate", "Bouteilles": "Bottles", "Nombre de bouteilles": "Number of bottles",
    "Ranger dans": "Put in", "Non rangées": "Not placed", "Raison": "Reason", "Accords mets & vins": "Food pairings",
    "Agneau, fromages affinés…": "Lamb, aged cheeses…", "Note personnelle": "Personal note", "À boire pour un anniversaire…": "To drink for a birthday…",
    "Date de l'occasion (facultatif)": "Occasion date (optional)", "Avec une date, Home Assistant vous le rappelle 7 jours avant.": "With a date, Home Assistant reminds you 7 days before.",
    "Enregistrer": "Save", "Ajouter à ma cave": "Add to my cellar", "Annuler": "Cancel", "Mes vins": "My wines",
    "« Estimer » applique une règle générale (couleur, appellation, prix, millésime). Une garde corrigée à la main n'est jamais modifiée par l'IA.": "“Estimate” applies a general rule (colour, appellation, price, vintage). A window corrected by hand is never changed by the AI.",
    "« Estimer » applique une règle générale (couleur, appellation, prix, millésime). L'IA de Home Assistant l'affinera ensuite, puis chaque mois. Une garde corrigée à la main n'est jamais modifiée par l'IA.": "“Estimate” applies a general rule (colour, appellation, price, vintage). Home Assistant's AI then refines it, and again every month. A window corrected by hand is never changed by the AI.",
    "Touchez l'emplacement où vous rangez la bouteille.": "Tap the spot where you put the bottle.",
    "Cave sans plan : les bouteilles y seront rangées en vrac.": "Cellar without a map: bottles will be stored loose.",
    "Fiche pré-remplie depuis Open Food Facts": "Pre-filled from Open Food Facts", "Fiche pré-remplie par l'IA à partir de l'étiquette": "Pre-filled by AI from the label",
    "Complétez la fiche de la bouteille photographiée": "Complete the details of the photographed bottle", "Changer de fond": "Change background",
    // ajouter
    "Photographier la bouteille": "Photograph the bottle", "Saisir à la main": "Enter by hand", "Formulaire complet": "Full form",
    "D'abord l'étiquette, puis le verso. La bouteille est détourée et posée sur un fond de cave": "First the label, then the back. The bottle is cut out and placed on a cellar background",
    "D'abord l'étiquette, puis le verso": "First the label, then the back", "Photographiez maintenant le verso": "Now photograph the back label",
    "La contre-étiquette donne plus d'informations (cépages, degré…) et le code-barres, qui servira à sortir la bouteille d'un simple scan.": "The back label gives more details (grapes, ABV…) and the barcode, used to take the bottle out with a simple scan.",
    "Photographier le verso": "Photograph the back", "Ignorer": "Skip", "Continuer": "Continue", "Ne pas la ranger": "Don't place it",
    "Photo de la bouteille": "Bottle photo", "Voir la fiche": "See the wine",
    // scan
    "Scanner la bouteille": "Scan the bottle", "Code-barres ": "Barcode", "Photographier le code-barres": "Photograph the barcode",
    "… ou tapez les chiffres": "… or type the digits", "Chiffres du code-barres": "Barcode digits", "OK": "OK", "Ouverture de la caméra…": "Opening the camera…",
    "Lecture de la photo…": "Reading the photo…", "Visez le code-barres, de près, sans reflet (horizontal ou vertical).": "Aim at the barcode, close up, without glare (horizontal or vertical).",
    "La caméra en direct n'est pas disponible sur cette connexion : photographiez le code-barres ou tapez ses chiffres.": "The live camera isn't available on this connection: photograph the barcode or type its digits.",
    "Aucun code-barres lisible sur cette photo. Rapprochez-vous (le code doit remplir une bonne partie de l'image), évitez les reflets, puis réessayez.": "No readable barcode on this photo. Move closer (the code should fill much of the image), avoid glare, and try again.",
    "Lecteur de code-barres indisponible": "Barcode reader unavailable", "Image illisible": "Unreadable image",
    // sortie
    "Valider la sortie": "Confirm", "Commentaire de dégustation": "Tasting note", "Robe, nez, bouche, accord du jour…": "Colour, nose, palate, today's pairing…",
    "Oui, et effacer la note": "Yes, and clear the note", "Oui, garder la note": "Yes, keep the note", "santé !": "cheers!",
    "Bouteille sortie, santé !": "Bottle taken out, cheers!", "Bouteilles sorties, santé !": "Bottles taken out, cheers!",
    "Sortie annulée : la bouteille est revenue à sa place": "Undone: the bottle is back in its spot",
    // plan
    "Nouvelle cave": "New cellar", "Étagère": "Rack", "Supprimer la cave": "Delete cellar",
    "Trouver une bouteille : nom, millésime, B4…": "Find a bottle: name, vintage, B4…", "Rechercher dans la cave": "Search the cellar",
    "Zoom du plan": "Map zoom", "Réduire": "Zoom out", "Ajuster à l'écran": "Fit to screen", "Affichage": "Display", "Plan": "Map", "Liste": "List",
    "Mettre en évidence": "Highlight", "À boire vite ou dépassé": "Drink soon or past", "à boire vite ou dépassé": "drink soon or past",
    "◌ emplacement libre : touchez-le pour y ranger une bouteille": "◌ free spot: tap it to put a bottle there", "cave électrique": "wine fridge",
    "Cave électrique : places libres signalées": "Wine fridge: free spots are reported", "Cave réfrigérée": "Cooled cellar", "Emplacements occupés": "Occupied spots",
    "Casier principal": "Main rack", "Rang affiché": "Row shown", "Tout": "All", "Devant": "Front", "Derrière": "Back",
    "Choisissez l'emplacement de destination…": "Choose the destination spot…", "Touchez l'emplacement libre où ranger": "Tap the free spot to put",
    "Bouteilles non rangées": "Unplaced bottles", "À ranger": "To place", "Ranger": "Place", "Arrêter": "Stop", "Fiche": "Wine",
    "Sortir cette bouteille": "Take out this bottle", "Déplacer": "Move", "Bouteille rangée": "Bottle placed",
    "Sans emplacement précis": "No specific spot", "Aucune bouteille.": "No bottles.", "Aucune bouteille dans cette cave": "No bottles in this cellar",
    "Aucune bouteille. Ajoutez-en depuis la fiche d'un vin.": "No bottles. Add some from a wine's page.",
    "Décrivez votre cave : une armoire à vin, un casier, une pièce…": "Describe your cellar: a wine fridge, a rack, a room…",
    "Indiquez le nombre de rangées et de colonnes pour obtenir un plan cliquable, ou 0 pour un rangement « en vrac ».": "Enter the number of rows and columns for a clickable map, or 0 for loose storage.",
    "Ranger une bouteille déjà en stock (non rangée ou en vrac)": "Place a bottle already in stock (unplaced or loose)", "… ou bien :": "… or:",
    "Ajouter une nouvelle bouteille de": "Add a new bottle of", "Vin absent de la liste ?": "Wine not in the list?",
    "Scannez son code-barres ou photographiez la bouteille : il sera ajouté à la cave et rangé dans cette case.": "Scan its barcode or photograph the bottle: it will be added to the cellar and placed in this spot.",
    "Nouveau vin dans cette case": "New wine in this spot", "Ranger ici": "Place here", "Choisissez une bouteille ou un vin": "Choose a bottle or a wine",
    "Plan de cave ": "Cellar map", "Nom (facultatif)": "Name (optional)", "Cave électrique, armoire du garage…": "Wine fridge, garage cabinet…",
    "Affiché au-dessus du casier et dans les alertes de place libre.": "Shown above the rack and in free-spot alerts.",
    "Est-ce une cave électrique (réfrigérée) ?": "Is it a wine fridge (cooled)?", "Choisir…": "Choose…",
    "Oui : je serai prévenu des places libres": "Yes: notify me of free spots", "Non : étagère ou casier non refroidi": "No: shelf or rack without cooling",
    "Disposition des bouteilles": "Bottle layout", "Sans nom : rien n'est affiché au-dessus de l'étagère": "No name: nothing is shown above the rack",
    "Position": "Position", "Par rapport à": "Relative to", "À droite": "On the right", "En dessous": "Below", "Au-dessus": "Above", "À gauche": "On the left",
    "Nouvelle étagère": "New rack", "Étagère modifiée": "Rack updated", "Étagère ajoutée": "Rack added", "Étagère supprimée": "Rack deleted",
    "Casier modifié": "Rack updated", "Cave enregistrée": "Cellar saved", "Modifier la cave": "Edit cellar", "Nom": "Name", "Rangées": "Rows", "Colonnes": "Columns",
    "Cave du sous-sol, armoire à vin…": "Basement cellar, wine fridge…", "Description": "Description", "Température, emplacement…": "Temperature, location…",
    "Mettez 0 rangée ou 0 colonne pour un rangement libre, sans plan.": "Set 0 rows or 0 columns for loose storage, without a map.",
    "Largeur": "Width", "Hauteur": "Height", "Empilement": "Stacking", "bouteilles côte à côte": "bottles side by side",
    "bouteilles empilées les unes sur les autres": "bottles stacked on top of each other", "comment chaque étage repose sur celui du dessous": "how each layer rests on the one below",
    "à choisir dès 2 bouteilles de hauteur": "available from 2 bottles high", "Décalé à gauche": "Offset left", "Aligné": "Aligned", "Décalé à droite": "Offset right",
    "Rang derrière": "Row behind", "Profondeurs": "Depths", "Moins": "Less", 
    "Étagère du bas": "Bottom rack", "Étagère du haut": "Top rack", "Étagère de gauche": "Left rack", "Étagère de droite": "Right rack",
    "Place libre": "Free spot", "Quel vin ranger dans la cave ?": "Which wine should go in the fridge?",
    "Par ordre de priorité : d'abord les vins qui ont le plus d'années de garde devant eux, puis les plus précieux.": "By priority: first the wines with the most ageing years ahead, then the most valuable.",
    "Aucune bouteille à proposer : tout est déjà en cave électrique ou au réfrigérateur.": "No bottle to suggest: everything is already in a wine fridge or the fridge.",
    "Non rangé": "Not placed", "Hors cave": "Not in a cellar",
    // mets & vins
    "Que mangez-vous ? La cave classe ses bouteilles de la mieux accordée à la moins accordée, et à accord égal, celles à boire en priorité.": "What are you eating? The cellar ranks its bottles from best to least matching, and for equal matches, those to drink first.",
    "Plat": "Dish", "Déguster": "Drink", "Aucun accord": "No match",
    "Aucune bouteille prête à boire ne s'accorde avec ce plat. Essayez une autre couleur ou un autre plat.": "No ready-to-drink bottle matches this dish. Try another colour or dish.",
    // statistiques
    "Touchez une ligne ou une barre pour voir les bouteilles correspondantes.": "Tap a row or bar to see the matching bottles.",
    "Par couleur": "By colour", "Par garde": "By drinking window", "Par région": "By region", "Par millésime": "By vintage", "Par cave": "By cellar",
    "Derniers mouvements": "Latest movements", "Tout l'historique ›": "Full history ›", "Bouteilles par millésime": "Bottles by vintage",
    "Aucune donnée.": "No data.", "Aucun millésime renseigné.": "No vintage entered.", "Ajoutez des vins pour voir les statistiques de votre cave.": "Add wines to see your cellar's statistics.",
    // envies, historique
    "Vin à acheter ou à goûter…": "Wine to buy or taste…", "Détails (millésime, caviste, prix…)": "Details (vintage, shop, price…)", "Détails": "Details",
    "Fait": "Done", "Envies ": "Wishlist", "Entrées": "Ins", "Sorties": "Outs", "Entrée": "In", "Sortie": "Out", "Vin": "Wine", "Type": "Type",
    "Aucun mouvement pour l'instant.": "No movements yet.",
    "Votre liste est vide. Elle est aussi disponible dans Home Assistant (liste de tâches « Cave à vin – Envies »).": "Your list is empty. It's also available in Home Assistant (to-do list “Tessvine Wishlist”).",
    // réglages
    "Ma cave": "My cellar", "Nom de la cave": "Cellar name",
    "Affiché en haut de l'application et dans l'onglet. Le nom dans la barre latérale de Home Assistant se change dans Home Assistant.": "Shown at the top of the app and in the tab. The name in Home Assistant's sidebar is changed in Home Assistant.",
    "Notifications de fin de garde": "End-of-window notifications", "Envoyer sur": "Send to", "Désactivées": "Off", "Envoyer un test": "Send a test",
    "Quand un vin entre dans sa dernière année de garde (« à boire vite »), Home Assistant vous prévient : au plus 2 rappels par vin, à 15 jours d'intervalle. Un vin dont la garde est dépassée n'est plus rappelé.": "When a wine enters the last year of its window (“drink soon”), Home Assistant notifies you: at most 2 reminders per wine, 15 days apart. A wine past its window is no longer reminded.",
    "Home Assistant — capteurs de la cave": "Home Assistant — cellar sensors",
    "L'application tourne comme module complémentaire : la connexion à Home Assistant est automatique.": "The app runs as an add-on: the connection to Home Assistant is automatic.",
    "Pour afficher la température et l'humidité de la cave, indiquez l'adresse de Home Assistant et un jeton d'accès longue durée (Profil → Sécurité → Jetons d'accès longue durée).": "To show the cellar's temperature and humidity, enter Home Assistant's address and a long-lived access token (Profile → Security → Long-lived access tokens).",
    "Home Assistant ne répond pas, ou aucun capteur de température / humidité n'a été trouvé.": "Home Assistant isn't responding, or no temperature / humidity sensor was found.",
    "Adresse de Home Assistant": "Home Assistant address", "Jeton d'accès": "Access token", "Capteur de température": "Temperature sensor",
    "Température min (°C)": "Min temperature (°C)", "Température max (°C)": "Max temperature (°C)", "Capteur d'humidité": "Humidity sensor",
    "Humidité min (%)": "Min humidity (%)", "Humidité max (%)": "Max humidity (%)", "— Aucun —": "— None —",
    "IA, photos & étiquettes": "AI, photos & labels", "IA de Home Assistant (lecture d'étiquette, garde)": "Home Assistant AI (label reading, drinking window)",
    "Activée": "On", "Désactivée": "Off", "Estimation de la garde par l'IA, chaque mois": "AI drinking-window estimate, every month",
    "IA à utiliser": "AI to use", "Automatique — aucune IA trouvée": "Automatic — no AI found", "IA trouvées dans Home Assistant": "AI found in Home Assistant",
    "Tâches IA (photos, garde) :": "AI tasks (photos, window):", "aucune": "none", "Agents de conversation : aucun": "Conversation agents: none",
    "Lecture d'étiquette disponible": "Label reading available", "✓ Lecture d'étiquette disponible": "✓ Label reading available",
    "Qualité du détourage": "Cut-out quality", "Rapide (modèle de 5 Mo)": "Fast (5 MB model)", "Standard (45 Mo, recommandé)": "Standard (45 MB, recommended)",
    "Précis (180 Mo, plus lent, 2 Go de mémoire conseillés)": "Precise (180 MB, slower, 2 GB of memory advised)", "Fond par défaut": "Default background",
    "Cadrage par défaut": "Default framing", "Gros plan sur l'étiquette": "Close-up on the label", "Bouteille entière": "Whole bottle", "Cadrage": "Framing",
    "Cave voûtée": "Vaulted cellar", "Casier en bois": "Wooden rack", "Studio bordeaux": "Burgundy studio", "Pierre claire": "Light stone", "Choisir le fond": "Choose the background",
    "Choisissez maintenant un fond.": "Now choose a background.", "Détourage et mise en scène…": "Cutting out and staging…", "Photo": "Photo",
    "Le modèle de détourage est téléchargé une seule fois, au premier usage, puis tout se fait sur votre installation. Pour la lecture d'étiquette, la photo est envoyée à l'IA configurée dans Home Assistant.": "The cut-out model is downloaded once, on first use, then everything runs on your installation. For label reading, the photo is sent to the AI configured in Home Assistant.",
    "Le détourage n'est pas disponible sur cette installation : les photos sont gardées telles quelles.": "Cut-out isn't available on this installation: photos are kept as they are.",
    "Intégration Home Assistant": "Home Assistant integration", "L'intégration": "The", ") crée dans Home Assistant :": ") integration creates in Home Assistant:",
    "(dossier": "(folder", "des capteurs : bouteilles, valeur, vins à boire, à boire vite…": "sensors: bottles, value, wines to drink, drink soon…",
    "la liste de tâches": "the to-do list", "(utilisable avec Assist : « ajoute Chablis à Cave à vin Envies »)": "(usable with Assist: “add Chablis to Tessvine Wishlist”)",
    "les actions": "the actions", "et": "and", "Adresse à saisir lors de l'ajout de l'intégration :": "Address to enter when adding the integration:",
    "Sauvegarde & import": "Backup & import", "Exporter en CSV (Excel)": "Export to CSV (Excel)", "Sauvegarde complète (JSON)": "Full backup (JSON)",
    "Importer des vins depuis un fichier CSV (colonnes : nom, domaine, appellation, region, couleur, millesime, quantite…)": "Import wines from a CSV file (columns: nom, domaine, appellation, region, couleur, millesime, quantite…)",
    "Restaurer une sauvegarde JSON (remplace toute la cave !)": "Restore a JSON backup (replaces the whole cellar!)", "À propos": "About",
    "Une clé d'API est mémorisée sur cet appareil.": "An API key is stored on this device.", "Oublier la clé": "Forget the key",
    "Pas encore de passage.": "Not run yet.", "Réestimer la garde de toute la cave maintenant": "Re-estimate the whole cellar now",
    "IA indisponible : Home Assistant n'est pas connecté.": "AI unavailable: Home Assistant isn't connected.",
    "Indisponible : Home Assistant n'est pas connecté": "Unavailable: Home Assistant isn't connected",
    "Langue": "Language", "Automatique": "Automatic", "Devise": "Currency", "Affichage ": "Display",
    "Langue et devise de cet appareil. La devise ne change que l'affichage des prix, pas leurs montants.": "Language and currency on this device. The currency only changes how prices are shown, not their amounts.",
    // messages
    "Réglages enregistrés": "Settings saved", "Nom enregistré": "Name saved", "Notifications enregistrées": "Notifications saved",
    "Notification de test envoyée": "Test notification sent", "Modifications enregistrées": "Changes saved", "Vin ajouté à la cave": "Wine added to the cellar",
    "Vin ajouté et rangé dans le plan": "Wine added and placed on the map", "Vin supprimé": "Wine deleted", "Bouteilles ajoutées": "Bottles added",
    "Bouteilles rangées dans le plan": "Bottles placed on the map", "Photo enregistrée": "Photo saved", "Photo mise à jour": "Photo updated",
    "Pas d'estimation pour cette couleur": "No estimate for this colour", "Plus aucune bouteille de ce vin en cave": "No bottle of this wine left",
    "Ce vin n'est rangé dans aucune cave : rangez-le depuis le plan de cave": "This wine isn't in any cellar: place it from the cellar map",
    "Remplacer la garde saisie à la main par l'estimation de l'IA ?": "Replace the hand-entered window with the AI's estimate?", "Remplacer": "Replace",
    "Restaurer cette sauvegarde ? Toutes les données actuelles de la cave seront remplacées.": "Restore this backup? All current cellar data will be replaced.",
    "Restaurer": "Restore", "Confirmer": "Confirm", "Envoi de la photo…": "Uploading the photo…", "Détourage de la bouteille…": "Cutting out the bottle…",
    "Cette cave est protégée par une clé d'API. Saisissez-la :": "This cellar is protected by an API key. Enter it:",
    // erreurs du serveur fréquentes
    "Erreur interne": "Internal error", "Cet emplacement est déjà occupé": "This spot is already taken", "Emplacement hors du plan de la cave": "Spot outside the cellar map",
    "Vin introuvable": "Wine not found", "Cave introuvable": "Cellar not found", "Bouteille introuvable": "Bottle not found",
    "Le nom de la cave est obligatoire": "The cellar name is required", "Le nom du vin est obligatoire": "The wine name is required",
    "Une étagère a au moins une rangée et une colonne": "A rack has at least one row and one column", "Le même emplacement est choisi deux fois": "The same spot is chosen twice",
    "Largeur et hauteur : de 1 à 50 bouteilles": "Width and height: 1 to 50 bottles", "Un casier a de 1 à 4 profondeurs": "A rack has 1 to 4 depths",
    "IA désactivée dans les réglages": "AI turned off in settings", "Home Assistant n'est pas connecté": "Home Assistant isn't connected",
    "Dossier « media » de Home Assistant inaccessible": "Home Assistant's “media” folder is not accessible",
    "Home Assistant n'a aucune IA de type « tâche IA » : ajoutez une intégration d'IA (OpenAI, Google Gemini, Anthropic, Ollama…) et, dans ses options, une « tâche IA » (AI Task). La cave l'utilisera automatiquement.": "Home Assistant has no “AI Task” AI: add an AI integration (OpenAI, Google Gemini, Anthropic, Ollama…) and, in its options, an “AI Task”. Tessvine will use it automatically.",
    "Home Assistant n'a aucune intégration d'IA. Ajoutez-en une : Paramètres → Appareils et services → Ajouter une intégration → Google Gemini (« Google Generative AI », offre gratuite), OpenAI, Anthropic ou Ollama (IA locale) ; puis, dans cette intégration, « Ajouter une tâche IA ». Un modèle qui comprend les images est nécessaire pour lire les étiquettes. Remarque : Claude ou une autre IA connectée À Home Assistant (serveur MCP, appli) ne peut pas être utilisée PAR Home Assistant.": "Home Assistant has no AI integration. Add one: Settings → Devices & services → Add integration → Google Gemini (“Google Generative AI”, free tier), OpenAI, Anthropic or Ollama (local AI); then, in that integration, “Add AI Task”. A model that understands images is needed to read labels. Note: Claude or another AI connected TO Home Assistant (MCP server, app) can't be used BY Home Assistant.",
    "L'IA n'a pas renvoyé de données exploitables": "The AI returned no usable data", "Réponse de l'IA inattendue": "Unexpected AI response",
    "L'IA n'a pas donné d'années exploitables": "The AI gave no usable years", "Image invalide (JPEG, PNG ou WebP attendu)": "Invalid image (JPEG, PNG or WebP expected)",
    "Pas de photo": "No photo", "Ce vin n'a pas de photo : prenez-en une d'abord": "This wine has no photo: take one first",
    "Clé d'API manquante ou invalide": "Missing or invalid API key", "Requête trop volumineuse": "Request too large", "Introuvable": "Not found",
    "Capteur introuvable": "Sensor not found",
    "Pour changer la disposition des bouteilles, touchez le crayon au-dessus du casier.": "To change the bottle layout, tap the pencil above the rack.",
    "Cave sans plan : les bouteilles y sont rangées en vrac.": "Cellar without a map: bottles are stored loose.",
    "Casier avec un plan : chaque bouteille a sa place": "Rack with a map: every bottle has its spot",
    "Rangement libre, sans plan (carton, étagère en vrac…)": "Loose storage, no map (case, open shelf…)",
    "Indiquez la disposition de vos bouteilles pour obtenir un plan où chaque bouteille a sa place, ou choisissez un rangement libre.": "Describe how your bottles are laid out to get a map where every bottle has its spot, or choose loose storage.",
    "Empilement : aligné, décalé à gauche ou décalé à droite": "Stacking: aligned, offset left or offset right", "Disposition invalide": "Invalid layout",
    "Le plan est limité à 100 rangées × 100 colonnes": "The map is limited to 100 rows × 100 columns",
    "✎ Régler": "✎ Adjust", "Nom de la cave": "Cellar name", "Nom du casier (facultatif)": "Rack name (optional)",
    "Rangée": "Shelf", "Personnalisez votre rangée": "Customize your shelf", "Enregistrer la rangée": "Save shelf", "Rangée ajoutée": "Shelf added",
    "En dessous (nouvelle rangée)": "Below (new shelf)", "Au-dessus (nouvelle rangée)": "Above (new shelf)",
    "À droite (nouvelle colonne)": "On the right (new column)", "À gauche (nouvelle colonne)": "On the left (new column)",
    "Rangées identiques": "Identical shelves", "ajoutées les unes sous les autres": "added one below the other",
    "devant": "front", "derrière": "back", "Casier": "Rack",
    "Sens des bouteilles": "Bottle direction", "comment elles sont posées dans ce rang": "how they lie in this row",
    "Arrière": "Base out", "Avant": "Neck out", "Alterné (arrière)": "Alternate (base)", "Alterné (avant)": "Alternate (neck)",
    "Allongé (droite)": "Side (right)", "Allongé (gauche)": "Side (left)", "fond vers vous": "base toward you", "goulot vers vous": "neck toward you",
    "fond, goulot, fond…": "base, neck, base…", "goulot, fond, goulot…": "neck, base, neck…", "de côté, goulot à droite": "on its side, neck right",
    "de côté, goulot à gauche": "on its side, neck left", "les bouteilles allongées s'empilent droites": "bottles on their side stack straight",
    "Sens des bouteilles inconnu": "Unknown bottle direction",
    "Rechercher : nom, millésime, domaine…": "Search: name, vintage, producer…", "Rechercher un vin": "Search for a wine",
    "bouteilles déjà en stock, sans place": "bottles already in stock, without a spot", "Toutes vos fiches": "All your wines",
    "ajoute une nouvelle bouteille de ce vin": "adds a new bottle of this wine", "en cave": "in cellar", "épuisé": "finished",
    "non rangée": "not placed", "Aucun vin ne correspond.": "No wine matches.",
    "Déplacer une bouteille déjà rangée": "Move a bottle already placed", "elle quitte sa place actuelle": "it leaves its current spot",
    "Aucune bouteille en stock. Ajoutez d'abord un vin à votre cave.": "No bottles in stock. Add a wine to your cellar first.", "Choisissez une bouteille": "Choose a bottle",
    "Home Assistant n'est pas configuré": "Home Assistant isn't configured", "Plat inconnu": "Unknown dish", "Choisissez d'abord où envoyer les notifications": "First choose where to send notifications",
    "Choisissez une bouteille ou un vin ": "Choose a bottle or a wine", "Emplacement incomplet": "Incomplete spot",
    "Garde importée : l'IA l'affinera lors de son prochain passage.": "Imported window: the AI will refine it on its next run.",
  };

  /* ---------------------------------------------------------------- motifs (phrases avec nombres ou noms) */
  const s = (n) => (+n > 1 ? "s" : "");
  const T = (x) => traduire(x);  // traduction d'un morceau capturé
  const MOTIFS = [
    [/^(\d[\d\s ]*) bouteilles?$/, (m) => `${m[1]} bottle${s(m[1])}`],
    [/^(\d[\d\s ]*) références? · (\d[\d\s ]*) bouteilles?$/, (m) => `${m[1]} wine${s(m[1])} · ${m[2]} bottle${s(m[2])}`],
    [/^(.+) : (\d[\d\s ]*) bouteilles?$/, (m) => `${T(m[1])}: ${m[2]} bottle${s(m[2])}`],
    [/^(\d+) bouteilles? en évidence$/, (m) => `${m[1]} bottle${s(m[1])} highlighted`],
    [/^Aucune bouteille ne correspond$/, () => "No bottle matches"],
    [/^(\d+) places libres dans (.+)$/, (m) => `${m[1]} free spots in ${T(m[2])}`],
    [/^Une place libre dans (.+)$/, (m) => `One free spot in ${T(m[1])}`],
    [/^(\d+) bouteilles? non rangées?$/, (m) => `${m[1]} unplaced bottle${s(m[1])}`],
    [/^(\d+) bouteilles? sans emplacement sur un plan\.(.*)$/, (m) => `${m[1]} bottle${s(m[1])} without a spot on a map.${m[2].includes("Ranger") ? " Tap “Place”, then the spot you want." : ""}`],
    [/^(\d+) \/ (\d+) emplacements occupés · (\d+) casiers?$/, (m) => `${m[1]} / ${m[2]} spots taken · ${m[3]} rack${s(m[3])}`],
    [/^(\d+) \/ (\d+) emplacements occupés · (\d+) rangées × (\d+) colonnes$/, (m) => `${m[1]} / ${m[2]} spots taken · ${m[3]} rows × ${m[4]} columns`],
    [/^(\d+) bouteilles? \(rangement libre\)$/, (m) => `${m[1]} bottle${s(m[1])} (loose storage)`],
    [/^([+−-])(\d+) · (.+) · (.+)$/, (m) => `${m[1]}${m[2]} · ${T(m[3])} · ${m[4]}`],
    [/^(\d) sur 5$/, (m) => `${m[1]} out of 5`],
    [/^Ce mois-ci : (.+)$/, (m) => `This month: ${m[1]}`],
    [/^(.+) \((\d+) place\(s\) libre\(s\)\)$/, (m) => `${T(m[1])} (${m[2]} free spot${s(m[2])})`],
    [/^(.+) — en vrac$/, (m) => `${T(m[1])} — loose`],
    [/^Localiser (.+) dans la cave$/, (m) => `Locate ${m[1]} in the cellar`],
    [/^Régler la disposition de (.+)$/, (m) => `Adjust the layout of ${T(m[1])}`],
    [/^Modifier (.+)$/, (m) => `Edit ${T(m[1])}`],
    [/^Voir les (\d+)$/, (m) => `See all ${m[1]}`],
    [/^dans (\d+) jours$/, (m) => `in ${m[1]} days`],
    [/^se garde jusqu'en (\d{4})(.*)$/, (m) => `keeps until ${m[1]}${m[2]}`],
    [/^à boire d'ici (\d{4})(.*)$/, (m) => `drink by ${m[1]}${m[2]}`],
    [/^Fenêtre de dégustation de (\d{4}) à (\d{4})$/, (m) => `Drinking window ${m[1]}–${m[2]}`],
    [/^À boire de (\d{4}) à (\d{4})(?: · ★ apogée (\d{4}))?$/, (m) => `Drink ${m[1]}–${m[2]}${m[3] ? ` · ★ peak ${m[3]}` : ""}`],
    [/^Apogée : (\d{4})(?: à (\d{4}))?$/, (m) => `Peak: ${m[1]}${m[2] ? `–${m[2]}` : ""}`],
    [/^Apogée (\d{4})$/, (m) => `Peak ${m[1]}`],
    [/^à boire (\S+) – (\S+)$/, (m) => `drink ${m[1]} – ${m[2]}`],
    [/^Sur (.+?)( · ×\d+)?$/, (m) => `In ${T(m[1])}${m[2] || ""}`],
    [/^En vrac dans (.+?)( · ×\d+)?$/, (m) => `Loose in ${T(m[1])}${m[2] || ""}`],
    [/^Hors cave( · ×\d+)?$/, (m) => `Not in a cellar${m[1] || ""}`],
    [/^Non rangé( · ×\d+)?$/, (m) => `Not placed${m[1] || ""}`],
    [/^Tessvine version (.+?)( — module complémentaire Home Assistant)?\.$/, (m) => `Tessvine version ${m[1]}${m[2] ? " — Home Assistant add-on" : ""}.`],
    [/^À y mettre : (.+?)(?:, actuellement sur (.+))?$/, (m) => `To put there: ${m[1]}${m[2] ? `, currently in ${T(m[2])}` : ""}`],
    [/^Suggestion : (.+)$/, (m) => `Suggestion: ${m[1]}`],
    [/^bues? en (\d{4})$/, (m) => `drunk in ${m[1]}`],
    [/^Bouteille rangée en (.+)$/, (m) => `Bottle placed in ${pos(m[1])}`],
    [/^Emplacement (.+)$/, (m) => `Spot ${pos(m[1])}`],
    [/^([A-Z]\d*\d+) · derrière$/, (m) => `${m[1]} · back`],
    [/^([A-Z]\d*\d+) · rang (\d)$/, (m) => `${m[1]} · row ${m[2]}`],
    [/^Profondeur (\d) · (.+)$/, (m) => `Depth ${m[1]} · ${prof(m[2])}`],
    [/^Supprimer la profondeur (\d)$/, (m) => `Delete depth ${m[1]}`],
    [/^(\d+) places? dans ce casier$/, () => null],
    [/^places? dans ce casier$/, () => "spots in this rack"],
    [/^(.+), ([A-Z]\d+)(?: \((.+)\))? : libre$/, (m) => `${T(m[1])}, ${m[2]}${m[3] ? ` (${prof(m[3])})` : ""}: free`],
    [/^(.+), ([A-Z]\d+)(?: \((.+)\))? : (.+), ([^,]+)$/, (m) => `${T(m[1])}, ${m[2]}${m[3] ? ` (${prof(m[3])})` : ""}: ${m[4]}, ${T(m[5])}`],
    [/^Votre cave : (\d+) bouteilles?, dont (.+)$/, (m) => `Your cellar: ${m[1]} bottles, including ${m[2]}`],
    [/^Touchez les (\d+) emplacements où vous rangez les bouteilles \(ou un seul : les suivantes iront dans les places libres\)\.$/, (m) => `Tap the ${m[1]} spots where you put the bottles (or just one: the rest will go to free spots).`],
    [/^(\d+) emplacements? choisis? sur (\d+)(.*)$/, (m) => `${m[1]} spot${s(m[1])} chosen out of ${m[2]}${m[3].startsWith(" :") ? ": tap more, or the rest will go to free spots." : "."}`],
    [/^\(actuellement en (.+)\)\.$/, (m) => `(currently in ${pos(m[1])}).`],
    [/^Garde estimée par l'IA le (.+?)(?: : (.+))?$/, (m) => `Window estimated by AI on ${m[1]}${m[2] ? `: ${m[2]}` : ""}`],
    [/^Garde estimée automatiquement \(règle générale\)(.*)$/, (m) => `Window estimated automatically (general rule)${m[1].includes("affinera") ? ": the AI will refine it." : "."}`],
    [/^Garde estimée par l'IA : (\d+) → (\d+)$/, (m) => `Window estimated by AI: ${m[1]} → ${m[2]}`],
    [/^Estimé comme (.+?)(?:\. Sans millésime, la garde est comptée à partir de l'achat \((\d+)\))?$/, (m) => `Estimated as ${m[1]}${m[2] ? `. Without a vintage, the window counts from purchase (${m[2]})` : ""}`],
    [/^Supprimer définitivement « (.+) » et ses (\d+) bouteille\(s\) \? L'historique des dégustations est conservé\.$/, (m) => `Permanently delete “${m[1]}” and its ${m[2]} bottle(s)? The tasting history is kept.`],
    [/^Supprimer « (.+) »(?: et ses (\d+) étagères?)? \? Ses (\d+) bouteille\(s\) resteront dans votre inventaire, sans emplacement\.$/, (m) => `Delete “${m[1]}”${m[2] ? ` and its ${m[2]} rack(s)` : ""}? Its ${m[3]} bottle(s) will stay in your inventory, without a spot.`],
    [/^Supprimer « (.+) » \? Ses (\d+) bouteille\(s\) resteront dans la cave, sans emplacement précis\.$/, (m) => `Delete “${T(m[1])}”? Its ${m[2]} bottle(s) will stay in the cellar, without a specific spot.`],
    [/^Êtes-vous sûr de vouloir consommer ce vin \?([\s\S]*)$/, (m) => `Are you sure you want to drink this wine?${m[1]}`],
    [/^Aucun vin de votre cave ne porte le code-barres (.+)$/, (m) => `No wine in your cellar has the barcode ${m[1]}`],
    [/^(.+) : plus aucune bouteille en cave$/, (m) => `${m[1]}: no bottles left in the cellar`],
    [/^Plus assez de place dans « (.+) » \((\d+) emplacement\(s\) libre\(s\)\)$/, (m) => `Not enough room in “${m[1]}” (${m[2]} free spot(s))`],
    [/^(\d+) bouteille\(s\) se trouvent en dehors du nouveau plan : déplacez-les d'abord$/, (m) => `${m[1]} bottle(s) would be outside the new layout: move them first`],
    [/^Déjà (\d+) emplacements? choisis? : augmentez le nombre de bouteilles ou retirez-en un$/, (m) => `Already ${m[1]} spot(s) chosen: increase the number of bottles or remove one`],
    [/^Caméra en direct indisponible \((.+)\) : photographiez le code-barres ou tapez ses chiffres\.$/, (m) => `Live camera unavailable (${m[1]}): photograph the barcode or type its digits.`],
    [/^Estimation en cours : (\d+) \/ (\d+) vins…$/, (m) => `Estimating: ${m[1]} / ${m[2]} wines…`],
    [/^Dernier passage : (.+?)\.(.*)$/, (m) => `Last run: ${m[1]}.${m[2]}`],
    [/^✓ Connecté à Home Assistant \((\d+) capteur\(s\) de température \/ humidité trouvé\(s\)\)\.$/, (m) => `✓ Connected to Home Assistant (${m[1]} temperature / humidity sensor(s) found).`],
    [/^idéal (.+)$/, (m) => `ideal ${m[1]}`],
    [/^⚠ trop (élevée|basse) \(idéal (.+)\)$/, (m) => `⚠ too ${m[1] === "élevée" ? "high" : "low"} (ideal ${m[2]})`],
    [/^IA indisponible : (.+)$/, (m) => `AI unavailable: ${T(m[1])}`],
    [/^Indisponible : (.+)$/, (m) => `Unavailable: ${T(m[1])}`],
    [/^(\d+) vin\(s\) importé\(s\)(.*)$/, (m) => `${m[1]} wine(s) imported${m[2].replace(" erreur(s)", " error(s)")}`],
    [/^Sauvegarde restaurée : (\d+) vin\(s\), (\d+) bouteille\(s\)$/, (m) => `Backup restored: ${m[1]} wine(s), ${m[2]} bottle(s)`],
    [/^Vous avez une IA de conversation \((.+?)\) mais pas de « tâche IA »\./, (m) => `You have a conversation AI (${m[1]}) but no “AI Task”. In Home Assistant: Settings → Devices & services → open that AI integration → “Add AI Task” (button or ⋮ menu). Tessvine will use it automatically. If there's no such button, that integration can't do AI tasks (this is the case for integrations that use a Claude or ChatGPT subscription): add the official Google Gemini integration (“Google Generative AI”, free tier), Anthropic or OpenAI with an API key, then “Add AI Task”.`],
    [/^L'IA « (.+?) » de Home Assistant est introuvable ou indisponible : (.*)$/, (m) => `Home Assistant AI “${m[1]}” was not found or is unavailable: ${m[2]}`],
    [/^L'IA de Home Assistant a refusé la demande \((\d+)\) : (.*)$/, (m) => `Home Assistant's AI refused the request (${m[1]}): ${m[2]}`],
    [/^Home Assistant injoignable \((.*)\)$/, (m) => `Home Assistant unreachable (${m[1]})`],
    [/^Estimation de l'IA incohérente \((.*)\)$/, (m) => `Inconsistent AI estimate (${m[1]})`],
    [/^Photo enregistrée sans détourage : (.*)$/, (m) => `Photo saved without cut-out: ${m[1]}`],
    [/^Erreur HTTP (\d+)$/, (m) => `HTTP error ${m[1]}`],
    [/^(\d+) rangées ajoutées$/, (m) => `${m[1]} shelves added`],
    [/^Rangée (\d+)$/, (m) => `Shelf ${m[1]}`],
    [/^(\d) rangs$/, (m) => `${m[1]} rows deep`],
    [/^rang (\d)$/, (m) => `row ${m[1]}`],
    [/^Voir ce casier de près(.*)$/, (m) => `Look at this rack up close${m[1] ? ": its rows move apart to show the bottles at the back" : ""}`],
    [/^Raison : le processeur ne gère pas les instructions SSE4\.2 \(x86-64-v2\)\..*$/, () => "Reason: the processor doesn't support SSE4.2 instructions (x86-64-v2). Virtual machine: choose the “host” CPU type (Proxmox: Hardware → Processors → Type)."],
    [/^Raison : (.*)$/, (m) => `Reason: ${m[1]}`],
    [/^Déplacer ici : (.+) \(depuis (.+?)\)$/, (m) => `Move here: ${m[1]} (from ${pos(m[2])})`],
    [/^Ranger ici : (.+)$/, (m) => `Place here: ${m[1]}`],
    [/^en vrac · (.+)$/, (m) => `loose · ${T(m[1])}`],
    [/^Envoi impossible : (.+)$/, (m) => `Couldn't send: ${m[1]}`],
    [/^Accord : (.+)$/, (m) => `Pairing: ${m[1]}`],
  ];
  const prof = (x) => ({ devant: "front", "derrière": "back" }[x] || x.replace(/^rang (\d)$/, "row $1"));
  const pos = (x) => x.replace(" · derrière", " · back").replace(/ · rang (\d)/, " · row $1");
  // remplacements partiels, pour les textes qui mêlent données et interface
  const PARTIELS = [
    [" · jusqu'en ", " · until "], ["accord : ", "match: "], ["conseillé avec : ", "recommended with: "],
    ["Prêt à boire", "Ready to drink"], ["À l'apogée", "At its peak"], ["Après l'apogée", "Past its peak"], ["À boire vite", "Drink soon"],
    ["Garde dépassée", "Past its window"], ["À garder", "Keep"], ["Garde non renseignée", "No drinking window"],
    [" rouge, ", " red, "], [" blanc, ", " white, "], [" effervescent", " sparkling"], [" liquoreux / moelleux", " sweet"],
  ];

  const cache = new Map();
  function traduire(texte) {
    if (langue === "fr" || !texte) return texte;
    const t = texte.trim();
    if (!t || !/[A-Za-zÀ-ÿ]/.test(t)) return texte;
    if (cache.has(t)) return remettre(texte, t, cache.get(t));
    let r = EXACT[t];
    if (r === undefined) {
      for (const [motif, f] of MOTIFS) {
        const m = t.match(motif);
        if (m) { const v = f(m); if (v != null) { r = v; break; } }
      }
    }
    if (r === undefined) {
      let v = t;
      for (const [a, b] of PARTIELS) if (v.includes(a)) v = v.split(a).join(b);
      r = v;
    }
    if (cache.size > 5000) cache.clear();
    cache.set(t, r);
    return remettre(texte, t, r);
  }
  const remettre = (original, coeur, trad) => coeur === original ? trad : original.replace(coeur, trad);

  const ATTRIBUTS = ["placeholder", "aria-label", "title", "alt"];
  const ignorer = (el) => !el || el.closest("svg, script, style, textarea, [translate=no], .bouteille-debout");
  function traduireArbre(racine) {
    if (langue === "fr" || !racine) return;
    if (racine.nodeType === 3) { if (!ignorer(racine.parentElement)) { const v = traduire(racine.nodeValue); if (v !== racine.nodeValue) racine.nodeValue = v; } return; }
    if (racine.nodeType !== 1 || ignorer(racine)) return;
    const w = document.createTreeWalker(racine, NodeFilter.SHOW_TEXT);
    let n;
    while ((n = w.nextNode())) {
      if (ignorer(n.parentElement)) continue;
      const v = traduire(n.nodeValue);
      if (v !== n.nodeValue) n.nodeValue = v;
    }
    const els = [racine, ...racine.querySelectorAll("[placeholder],[aria-label],[title],[alt]")];
    for (const el of els) {
      if (el.nodeType !== 1 || ignorer(el)) continue;
      for (const a of ATTRIBUTS) {
        const v = el.getAttribute(a);
        if (v) { const t = traduire(v); if (t !== v) el.setAttribute(a, t); }
      }
    }
  }
  function demarrer() {
    document.documentElement.lang = langue;
    if (langue === "fr") return;
    traduireArbre(document.body);
    new MutationObserver((mutations) => {
      for (const m of mutations) {
        if (m.type === "characterData") traduireArbre(m.target);
        else if (m.type === "attributes") {
          if (ignorer(m.target)) continue;
          const v = m.target.getAttribute(m.attributeName);
          const t = v && traduire(v);
          if (t && t !== v) m.target.setAttribute(m.attributeName, t);
        }
        else m.addedNodes.forEach(traduireArbre);
      }
    }).observe(document.body, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ATTRIBUTS });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", demarrer); else demarrer();

  return {
    langue, locale, devise, choix, DEVISES,
    t: traduire,
    regler(l, d) { ecrire("tessvine-langue", l); ecrire("tessvine-devise", d); },
  };
})();
