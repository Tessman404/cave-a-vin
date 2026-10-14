"""Constantes de l'intégration Cave à vin."""

from datetime import timedelta

DOMAIN = "cave_a_vin"
CONF_API_KEY = "api_key"
INTERVALLE = timedelta(minutes=5)

COULEURS = ["rouge", "blanc", "rose", "effervescent", "liquoreux", "autre"]
RAISONS_SORTIE = ["bue", "offerte", "cassee", "vendue", "autre"]
RAISONS_ENTREE = ["achat", "cadeau", "inventaire", "autre"]
PLATS = [
    "viande_rouge", "viande_blanche", "poisson", "fruits_de_mer", "fromage",
    "dessert", "aperitif", "epice", "barbecue", "vegetarien",
]
