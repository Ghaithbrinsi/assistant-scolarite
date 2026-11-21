import json
import os
import re

from llm import client, MODEL
from outils import OUTILS, TOOLS
from prompts import SYSTEM_PROMPT

MAX_TOURS = 5


def nettoyer(texte: str) -> str:
    """Supprime les balises <think>...</think> de Qwen3."""
    return re.sub(r"<think>.*?</think>", "", texte or "", flags=re.DOTALL).strip()


def executer_outil(nom: str, arguments_json: str) -> str:
    """LE PROGRAMME AGIT ICI : exécution contrôlée de l'outil demandé par le modèle."""
    if nom not in OUTILS:
        return f"Erreur : outil inconnu '{nom}'."
    try:
        args = json.loads(arguments_json or "{}")
    except json.JSONDecodeError:
        return "Erreur : arguments JSON invalides."
    try:
        return str(OUTILS[nom](**args))
    except TypeError as e:
        return f"Erreur : arguments incorrects ({e})."


def agent(question: str):
    """Retourne (réponse finale, trace des étapes)."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    trace = []

    for tour in range(MAX_TOURS):
        # LE MODÈLE DÉCIDE ICI : réponse finale ou demande d'outil
        msg = client.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOLS, temperature=0
        ).choices[0].message

        if not msg.tool_calls:
            trace.append({"etape": "reponse_finale", "tour": tour + 1})
            return nettoyer(msg.content), trace

        # On rejoue la demande du modèle dans l'historique (format dict simple)
        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {"id": c.id, "type": "function",
                 "function": {"name": c.function.name, "arguments": c.function.arguments}}
                for c in msg.tool_calls
            ],
        })

        for call in msg.tool_calls:
            resultat = executer_outil(call.function.name, call.function.arguments)
            trace.append({
                "etape": "appel_outil",
                "tour": tour + 1,
                "outil": call.function.name,
                "args": call.function.arguments,
                "resultat": resultat,
            })
            messages.append({"role": "tool", "tool_call_id": call.id, "content": resultat})

    return "Je n'ai pas pu terminer la tâche.", trace


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        questions = [" ".join(sys.argv[1:])]          # une seule question en argument
    else:
        questions = [
            "J'étais malade le jour de l'examen de bases de données, que dois-je faire ?",
            "Quelle est la durée minimale du stage ?",
            "Rédige-moi une demande de rattrapage pour réseaux",
            "Je m'appelle Test Etudiant, numéro 0000, rédige ma demande de rattrapage pour réseaux",
            "Y a-t-il un rattrapage pour le projet de fin de module ?",
            "Quel est le montant de la bourse ?",
        ]
    for q in questions:
        reponse, trace = agent(q)
        print("Q:", q)
        for t in trace:
            print("   trace:", t)
        print("R:", reponse, "\n")