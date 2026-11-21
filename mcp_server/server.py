"""Serveur MCP de l'assistant de scolarité (transport stdio).
Ne jamais utiliser print() ici : stdout est le canal du protocole MCP."""
import sys
from pathlib import Path
from typing import Annotated

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

from mcp.server.fastmcp import FastMCP  # noqa: E402
from pydantic import Field  # noqa: E402

from agent import outils  # noqa: E402

mcp = FastMCP("scolarite")

Module = Annotated[str, Field(
    description="Nom du module : algorithmique, bases de données, réseaux, anglais ou projet de fin de module")]


@mcp.tool()
def rechercher_reglement(
    question: Annotated[str, Field(
        description="Mots-clés de recherche, pas la phrase entière. Exemples : "
                    "'délai certificat médical absence examen', 'durée stage', 'conditions rattrapage'")]
) -> str:
    """Cherche dans le règlement des études les articles pertinents (absences, certificat médical,
    rattrapage, stage, réclamation). Renvoie le texte des articles avec leur numéro."""
    return outils.rechercher_reglement(question)


@mcp.tool()
def get_calendrier(module: Module) -> str:
    """Donne la date, l'heure et la salle de l'examen et du rattrapage d'un module (session de janvier 2027)."""
    return outils.get_calendrier(module)


@mcp.tool()
def calculer_delai(
    module: Module,
    hospitalisation: Annotated[bool, Field(
        description="true si l'étudiant a été hospitalisé (délai de 7 jours ouvrables)")] = False,
) -> str:
    """Calcule la date limite de remise du certificat médical à la scolarité après un examen manqué."""
    return outils.calculer_delai(module, hospitalisation)


@mcp.tool()
def generer_demande(
    nom: Annotated[str, Field(description="Nom complet de l'étudiant, tel qu'il l'a écrit lui-même")],
    numero_etudiant: Annotated[str, Field(description="Numéro d'étudiant donné par l'étudiant")],
    module: Module,
    justificatif: Annotated[str, Field(description="Type de justificatif")] = "certificat médical",
) -> str:
    """Rédige le brouillon d'une demande de rattrapage (non envoyé). À appeler seulement quand
    l'étudiant a fourni lui-même son nom et son numéro d'étudiant."""
    return outils.generer_demande(nom, numero_etudiant, module, justificatif)


if __name__ == "__main__":
    mcp.run()   # transport stdio