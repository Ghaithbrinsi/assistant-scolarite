import uuid
from typing import TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import Command, interrupt

from boucle import (MAX_TOURS, REFUS_HUMAIN, SENSIBLES, confirmer_cli, executer_outil,
                    finaliser, get_tools, nettoyer)
from classifier import classifier
from llm import MODEL, client
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
                              "intention": c.get("intention"), "module": c.get("module")}]
    return {"intention": c.get("intention", "erreur"), "trace": trace}


def noeud_refus(etat: Etat):
    return {"reponse": REFUS_HORS_SUJET,
            "trace": etat["trace"] + [{"etape": "refus_hors_sujet"}]}


def noeud_llm(etat: Etat):
    # LE MODÈLE DÉCIDE ICI
    msg = client.chat.completions.create(
        model=MODEL, messages=etat["messages"], tools=get_tools(), temperature=0
    ).choices[0].message

    assistant = {"role": "assistant", "content": msg.content or ""}
    if msg.tool_calls:
        assistant["tool_calls"] = [
            {"id": c.id, "type": "function",
             "function": {"name": c.function.name, "arguments": c.function.arguments}}
            for c in msg.tool_calls]
    maj = {"messages": etat["messages"] + [assistant], "tours": etat["tours"] + 1}
    if not msg.tool_calls:
        maj["reponse"] = nettoyer(msg.content)
        maj["trace"] = etat["trace"] + [{"etape": "reponse_finale"}]
    return maj


def noeud_outils(etat: Etat):
    appels = etat["messages"][-1]["tool_calls"]
    messages, trace = list(etat["messages"]), list(etat["trace"])

    # 1) VALIDATION HUMAINE avant toute exécution : le graphe se met en pause ici
    decisions = {}
    for call in appels:
        if call["function"]["name"] in SENSIBLES:
            decisions[call["id"]] = interrupt({"outil": call["function"]["name"],
                                               "args": call["function"]["arguments"]})

    # 2) LE PROGRAMME AGIT ICI
    for call in appels:
        nom, args = call["function"]["name"], call["function"]["arguments"]
        if call["id"] in decisions and decisions[call["id"]] is not True:
            resultat = REFUS_HUMAIN
            trace.append({"etape": "refus_humain", "outil": nom})
        else:
            resultat = executer_outil(nom, args)
            trace.append({"etape": "appel_outil", "outil": nom, "args": args, "resultat": resultat,
                          "valide_par_humain": call["id"] in decisions})
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
app = g.compile(checkpointer=MemorySaver())


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _bilan(thread_id: str) -> dict:
    snap = app.get_state(_config(thread_id))
    v = snap.values
    if snap.next:   # le graphe attend la décision de l'étudiant
        return {"statut": "validation", "action": snap.tasks[0].interrupts[0].value,
                "trace": v["trace"], "thread_id": thread_id}
    reponse = finaliser(v["reponse"] or "Je n'ai pas pu terminer la tâche.", v["trace"])
    return {"statut": "termine", "reponse": reponse, "trace": v["trace"], "thread_id": thread_id}


def lancer(question: str, thread_id: str | None = None) -> dict:
    """Démarre une question. Retourne un bilan : statut 'termine' ou 'validation'."""
    thread_id = thread_id or str(uuid.uuid4())
    app.invoke({"question": question, "intention": "", "tours": 0, "reponse": "", "trace": [],
                "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                             {"role": "user", "content": question}]},
               _config(thread_id))
    return _bilan(thread_id)


def reprendre(thread_id: str, decision: bool) -> dict:
    """Reprend après la décision de l'étudiant (True = valider, False = annuler)."""
    app.invoke(Command(resume=bool(decision)), _config(thread_id))
    return _bilan(thread_id)


def agent_graphe(question: str, confirmer=confirmer_cli):
    """Interface simple : retourne (réponse, trace). `confirmer` décide des actions sensibles."""
    bilan = lancer(question)
    while bilan["statut"] == "validation":
        bilan = reprendre(bilan["thread_id"], confirmer(bilan["action"]))
    return bilan["reponse"], bilan["trace"]


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "J'étais malade le jour de l'examen de bases de données, que dois-je faire ?"
    reponse, trace = agent_graphe(q)
    for t in trace:
        print("   trace:", t)
    print("R:", reponse)