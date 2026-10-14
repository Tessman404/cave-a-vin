# Cave à vin

Gérez votre cave à vin depuis Home Assistant : inventaire, plan de cave, fenêtres de garde, dégustations, suggestions d'accords et liste d'envies.

## Démarrage

1. Activez **Afficher dans la barre latérale**, puis **Démarrer**.
2. Ouvrez **Cave à vin** dans la barre latérale.
3. **Plan de cave → + Nouvelle cave** pour décrire vos casiers, puis **+ Ajouter** pour vos premiers vins.

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
