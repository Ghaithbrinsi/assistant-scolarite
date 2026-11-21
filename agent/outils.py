import unicodedata

CALENDRIER = {
    "algorithmique": {"examen": "05/01/2027 à 9h, amphi A", "rattrapage": "13/01/2027 à 14h, salle B10"},
    "bases de donnees": {"examen": "08/01/2027 à 9h, amphi A", "rattrapage": "15/01/2027 à 9h, salle B12"},
    "reseaux": {"examen": "11/01/2027 à 9h, amphi B", "rattrapage": "18/01/2027 à 9h, salle B14"},
    "anglais": {"examen": "12/01/2027 à 14h, salle B11", "rattrapage": "19/01/2027 à 10h, salle B11"},
    "projet de fin de module": {"examen": "Remise le 20/01/2027", "rattrapage": "Pas de rattrapage"},
}


def normaliser(texte: str) -> str:
    """Minuscules, sans accents, sans espaces superflus : 'Bases de Données ' -> 'bases de donnees'."""
    texte = unicodedata.normalize("NFD", texte.strip().lower())
    return "".join(c for c in texte if unicodedata.category(c) != "Mn")


def get_calendrier(module: str) -> str:
    cle = normaliser(module)
    if cle in CALENDRIER:
        d = CALENDRIER[cle]
        return f"Module : {module}. Examen : {d['examen']}. Rattrapage : {d['rattrapage']}."
    modules = ", ".join(CALENDRIER.keys())
    return f"Module introuvable. Modules du calendrier : {modules}."


# Registre : nom de l'outil -> fonction Python
OUTILS = {"get_calendrier": get_calendrier}

# Description envoyée au modèle (c'est ce qu'il "voit")
TOOLS = [{
    "type": "function",
    "function": {
        "name": "get_calendrier",
        "description": "Donne la date d'examen et la date de rattrapage d'un module du calendrier de janvier 2027.",
        "parameters": {
            "type": "object",
            "properties": {
                "module": {"type": "string",
                           "description": "Nom du module : algorithmique, bases de données, réseaux, anglais, projet de fin de module"}
            },
            "required": ["module"],
        },
    },
}]