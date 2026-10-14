# Journal des modifications

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
- Les vins non millésimés sont estimés « à boire dès maintenant ».

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
