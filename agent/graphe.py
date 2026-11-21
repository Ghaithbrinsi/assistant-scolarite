from typing import TypedDict

from langgraph.graph import END, StateGraph

from boucle import MAX_TOURS, executer_outil, nettoyer
from classifier import classifier
from llm import MODEL, client
from outils import TOOLS
from prompts import REFUS_HORS_SUJET, SYSTEM_PROMPT


class Etat(TypedDict):
    question: str
    intention: str
    messages: list
    trace: list
    tours: int
    reponse: str


def noeud_classifier(etat: Etat):
    c = classifier(etat["question"])
    trace = etat["trace"] + [{"etape": "classification",
                              "intention": c.get("intention"),
                              "module": c.get("module")}]
    return {"intention": c.get("intention", "erreur"), "trace": trace}


def noeud_refus(etat: Etat):
    return {"reponse": REFUS_HORS_SUJET,
            "trace": etat["trace"] + [{"etape": "refus_hors_sujet"}]}


def noeud_llm(etat: Etat):
    # LE MODÈLE DÉCIDE ICI
    msg = client.chat.completions.create(
        model=MODEL, messages=etat["messages"], tools=TOOLS, temperature=0
    ).choices[0].message

    assistant = {"role": "assistant", "content": msg.content or ""}
    if msg.tool_calls:
        assistant["tool_calls"] = [
            {"id": c.id, "type": "function",
             "function": {"name": c.function.name, "arguments": c.function.arguments}}
            for c in msg.tool_calls
        ]
    maj = {"messages": etat["messages"] + [assistant], "tours": etat["tours"] + 1}
    if not msg.tool_calls:
        maj["reponse"] = nettoyer(msg.content)
        maj["trace"] = etat["trace"] + [{"etape": "reponse_finale"}]
    return maj


def noeud_outils(etat: Etat):
    # LE PROGRAMME AGIT ICI
    messages, trace = list(etat["messages"]), list(etat["trace"])
    for call in messages[-1]["tool_calls"]:
        resultat = executer_outil(call["function"]["name"], call["function"]["arguments"])
        trace.append({"etape": "appel_outil", "outil": call["function"]["name"],
                      "args": call["function"]["arguments"], "resultat": resultat})
        messages.append({"role": "tool", "tool_call_id": call["id"], "content": resultat})
    return {"messages": messages, "trace": trace}


def apres_classifier(etat: Etat):
    return "refus" if etat["intention"] == "hors_sujet" else "llm"


def apres_llm(etat: Etat):
    demande_outil = bool(etat["messages"][-1].get("tool_calls"))
    return "outils" if demande_outil and etat["tours"] < MAX_TOURS else "fin"


g = StateGraph(Etat)
g.add_node("classifier", noeud_classifier)
g.add_node("refus", noeud_refus)
g.add_node("llm", noeud_llm)
g.add_node("outils", noeud_outils)
g.set_entry_point("classifier")
g.add_conditional_edges("classifier", apres_classifier, {"refus": "refus", "llm": "llm"})
g.add_edge("refus", END)
g.add_conditional_edges("llm", apres_llm, {"outils": "outils", "fin": END})
g.add_edge("outils", "llm")
app = g.compile()


def agent_graphe(question: str):
    """Même interface que boucle.agent : retourne (réponse, trace)."""
    etat = app.invoke({
        "question": question, "intention": "", "tours": 0, "reponse": "", "trace": [],
        "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                     {"role": "user", "content": question}],
    })
    return etat["reponse"] or "Je n'ai pas pu terminer la tâche.", etat["trace"]


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "J'étais malade le jour de l'examen de bases de données, que dois-je faire ?"
    reponse, trace = agent_graphe(q)
    for t in trace:
        print("   trace:", t)
    print("R:", reponse)