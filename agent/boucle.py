import json
import re

from llm import MODEL, client
from mcp_client import get_mcp
from prompts import SYSTEM_PROMPT

MAX_TOURS = 5
SENSIBLES = {"generer_demande"}   # actions qui exigent la validation de l'étudiant
REFUS_HUMAIN = "Action refusée par l'étudiant : rien n'a été généré ni envoyé."

_TOOLS = None


def get_tools() -> list[dict]:
    """Outils décrits par le serveur MCP (chargés une seule fois)."""
    global _TOOLS
    if _TOOLS is None:
        _TOOLS = get_mcp().lister_outils()
    return _TOOLS


def nettoyer(texte: str) -> str:
    """Supprime les balises <think>...</think> éventuelles."""
    return re.sub(r"<think>.*?</think>", "", texte or "", flags=re.DOTALL).strip()


def executer_outil(nom: str, arguments_json: str) -> str:
    """LE PROGRAMME AGIT ICI : l'outil demandé par le modèle est appelé via le serveur MCP."""
    if nom not in {t["function"]["name"] for t in get_tools()}:
        return f"Erreur : outil inconnu '{nom}'."
    try:
        args = json.loads(arguments_json or "{}")
    except json.JSONDecodeError:
        return "Erreur : arguments JSON invalides."
    if not isinstance(args, dict):
        return "Erreur : arguments JSON invalides."
    return get_mcp().appeler(nom, args)


def finaliser(reponse: str, trace: list) -> str:
    """Si un brouillon de demande a été généré, on renvoie le texte EXACT de l'outil."""
    for t in reversed(trace):
        if t.get("outil") == "generer_demande" and t.get("resultat", "").startswith("[BROUILLON"):
            return t["resultat"]
    return reponse


def confirmer_cli(action: dict) -> bool:
    """Validation humaine en ligne de commande."""
    print(f"\n[ACTION SENSIBLE] L'agent veut appeler : {action['outil']}")
    print(f"   Arguments : {action['args']}")
    return input("   Valider ? (o/n) ").strip().lower() in ("o", "oui", "y")


def agent(question: str, confirmer=confirmer_cli):
    """Boucle manuelle (sans LangGraph). Retourne (réponse finale, trace)."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question}]
    trace = []

    for _ in range(MAX_TOURS):
        # LE MODÈLE DÉCIDE ICI
        msg = client.chat.completions.create(
            model=MODEL, messages=messages, tools=get_tools(), temperature=0
        ).choices[0].message

        if not msg.tool_calls:
            trace.append({"etape": "reponse_finale"})
            return finaliser(nettoyer(msg.content), trace), trace

        messages.append({
            "role": "assistant", "content": msg.content or "",
            "tool_calls": [{"id": c.id, "type": "function",
                            "function": {"name": c.function.name, "arguments": c.function.arguments}}
                           for c in msg.tool_calls],
        })
        for call in msg.tool_calls:
            nom, args = call.function.name, call.function.arguments
            if nom in SENSIBLES and not confirmer({"outil": nom, "args": args}):
                resultat = REFUS_HUMAIN
                trace.append({"etape": "refus_humain", "outil": nom})
            else:
                resultat = executer_outil(nom, args)
                trace.append({"etape": "appel_outil", "outil": nom, "args": args, "resultat": resultat})
            messages.append({"role": "tool", "tool_call_id": call.id, "content": resultat})

    return "Je n'ai pas pu terminer la tâche.", trace


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "Quelle est la durée minimale du stage ?"
    reponse, trace = agent(q)
    for t in trace:
        print("   trace:", t)
    print("R:", reponse)