import re
import sys
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))   # pour importer rag/
from rag.recherche import rechercher_reglement  # noqa: E402

CALENDRIER = {
    "algorithmique": {"examen": "05/01/2027 à 9h, amphi A", "rattrapage": "13/01/2027 à 14h, salle B10"},
    "bases de donnees": {"examen": "08/01/2027 à 9h, amphi A", "rattrapage": "15/01/2027 à 9h, salle B12"},
    "reseaux": {"examen": "11/01/2027 à 9h, amphi B", "rattrapage": "18/01/2027 à 9h, salle B14"},
    "anglais": {"examen": "12/01/2027 à 14h, salle B11", "rattrapage": "19/01/2027 à 10h, salle B11"},
    "projet de fin de module": {"examen": "Remise le 20/01/2027", "rattrapage": "Pas de rattrapage"},
}


def normaliser(texte: str) -> str:
    texte = unicodedata.normalize("NFD", texte.strip().lower())
    return "".join(c for c in texte if unicodedata.category(c) != "Mn")


def _module_introuvable() -> str:
    return "Module introuvable. Modules du calendrier : " + ", ".join(CALENDRIER) + "."


def get_calendrier(module: str) -> str:
    cle = normaliser(module)
    if cle not in CALENDRIER:
        return _module_introuvable()
    d = CALENDRIER[cle]
    return f"Module : {module}. Examen : {d['examen']}. Rattrapage : {d['rattrapage']}."


def calculer_delai(module: str, hospitalisation=False) -> str:
    cle = normaliser(module)
    if cle not in CALENDRIER:
        return _module_introuvable()
    d = CALENDRIER[cle]
    if "Pas de rattrapage" in d["rattrapage"]:
        return "Ce module n'a pas de session de rattrapage (article 10) : aucun délai de certificat à calculer."
    if isinstance(hospitalisation, str):
        hospitalisation = hospitalisation.strip().lower() in ("true", "vrai", "oui", "1")

    date_exam = datetime.strptime(re.search(r"\d{2}/\d{2}/\d{4}", d["examen"]).group(), "%d/%m/%Y")
    jours = 7 if hospitalisation else 3
    courant, restant = date_exam, jours
    while restant > 0:
        courant += timedelta(days=1)
        if courant.weekday() < 5:          # lundi à vendredi
            restant -= 1
    articles = "articles 4 et 6" if hospitalisation else "article 4"
    return (f"Examen du {date_exam:%d/%m/%Y}. Date limite de remise du justificatif à la scolarité : "
            f"{courant:%d/%m/%Y} ({jours} jours ouvrables du lundi au vendredi, le jour de l'examen "
            f"n'étant pas compté, {articles}). Rattrapage : {d['rattrapage']}.")


def generer_demande(nom: str, numero_etudiant: str, module: str,
                    justificatif: str = "certificat médical") -> str:
    manquants = [n for n, v in (("nom", nom), ("numéro d'étudiant", numero_etudiant)) if not str(v).strip()]
    if manquants:
        return ("Informations manquantes : " + ", ".join(manquants) +
                ". Demande-les à l'étudiant, ne les invente pas.")
    cle = normaliser(module)
    if cle not in CALENDRIER:
        return _module_introuvable()
    d = CALENDRIER[cle]
    if "Pas de rattrapage" in d["rattrapage"]:
        return "Impossible : ce module n'a pas de session de rattrapage (article 10)."
    date_exam = re.search(r"\d{2}/\d{2}/\d{4}", d["examen"]).group()

    return f"""[BROUILLON – NON ENVOYÉ]

À l'attention du Responsable de scolarité – ISET Charguia

Objet : Demande de session de rattrapage – module « {module} »

Madame, Monsieur,

Je soussigné(e) {nom}, numéro d'étudiant {numero_etudiant}, n'ai pas pu me présenter à l'examen du module « {module} » prévu le {date_exam}. Conformément aux articles 7 et 8 du règlement des études, je sollicite le passage de cet examen à la session de rattrapage ({d['rattrapage']}).

Vous trouverez ci-joint mon justificatif : {justificatif}.

Je vous prie d'agréer, Madame, Monsieur, l'expression de mes salutations distinguées.

{nom}"""


# ---------- Registre (liste blanche) et description pour le modèle ----------
OUTILS = {
    "rechercher_reglement": rechercher_reglement,
    "get_calendrier": get_calendrier,
    "calculer_delai": calculer_delai,
    "generer_demande": generer_demande,
}


def _outil(nom, description, proprietes, requis):
    return {"type": "function", "function": {
        "name": nom, "description": description,
        "parameters": {"type": "object", "properties": proprietes, "required": requis}}}


MODULE_DESC = "Nom du module : algorithmique, bases de données, réseaux, anglais ou projet de fin de module"

TOOLS = [
    _outil("rechercher_reglement",
           "Cherche dans le règlement des études les articles pertinents (absences, certificat médical, "
           "rattrapage, stage, réclamation). Renvoie le texte des articles avec leur numéro.",
           {"question": {"type": "string", "description": "La question de l'étudiant, reformulée si besoin"}},
           ["question"]),
    _outil("get_calendrier",
           "Donne la date, l'heure et la salle de l'examen et du rattrapage d'un module (session de janvier 2027).",
           {"module": {"type": "string", "description": MODULE_DESC}}, ["module"]),
    _outil("calculer_delai",
           "Calcule la date limite pour remettre le certificat médical à la scolarité après un examen manqué.",
           {"module": {"type": "string", "description": MODULE_DESC},
            "hospitalisation": {"type": "boolean", "description": "true si l'étudiant a été hospitalisé (délai de 7 jours)"}},
           ["module"]),
    _outil("generer_demande",
           "Rédige le brouillon d'une demande de rattrapage. À appeler seulement quand l'étudiant a fourni "
           "lui-même son nom et son numéro d'étudiant.",
           {"nom": {"type": "string", "description": "Nom complet de l'étudiant"},
            "numero_etudiant": {"type": "string", "description": "Numéro d'étudiant"},
            "module": {"type": "string", "description": MODULE_DESC},
            "justificatif": {"type": "string", "description": "Type de justificatif (par défaut : certificat médical)"}},
           ["nom", "numero_etudiant", "module"]),
]