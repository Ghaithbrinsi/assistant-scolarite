import json
import sys
from pathlib import Path

import streamlit as st

RACINE = Path(__file__).resolve().parent
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "agent"))

from graphe import lancer, reprendre  # noqa: E402

st.set_page_config(page_title="Assistant de scolarité", page_icon="🎓")
st.title("🎓 Assistant de scolarité")
st.caption("ISET Charguia – réponses fondées uniquement sur le règlement des études "
           "et le calendrier des examens (documents fictifs).")

ss = st.session_state
ss.setdefault("historique", [])
ss.setdefault("attente", None)


def afficher_trace(trace: list):
    with st.expander("🔍 Étapes suivies par l'agent"):
        for i, t in enumerate(trace, 1):
            etape = t["etape"]
            if etape == "classification":
                st.markdown(f"**{i}. Classification** : intention `{t.get('intention')}`, "
                            f"module `{t.get('module')}`")
            elif etape == "appel_outil":
                valide = " ✅ validé par l'étudiant" if t.get("valide_par_humain") else ""
                st.markdown(f"**{i}. Outil MCP** `{t['outil']}`{valide}")
                st.code(t["args"], language="json")
                st.text(t["resultat"][:600])
            elif etape == "refus_hors_sujet":
                st.markdown(f"**{i}. Question hors sujet** : refus sans appeler le modèle")
            elif etape == "refus_humain":
                st.markdown(f"**{i}. Action `{t['outil']}` refusée par l'étudiant**")
            elif etape == "reponse_finale":
                st.markdown(f"**{i}. Réponse finale**")


def traiter(bilan: dict):
    if bilan["statut"] == "validation":
        ss.attente = bilan
    else:
        ss.attente = None
        ss.historique.append({"role": "assistant", "content": bilan["reponse"], "trace": bilan["trace"]})


for m in ss.historique:
    with st.chat_message(m["role"]):
        st.markdown(m["content"].replace("\n", "  \n"))
        if m.get("trace"):
            afficher_trace(m["trace"])

# --- Validation humaine d'une action sensible ---
if ss.attente:
    action = ss.attente["action"]
    try:
        args = json.loads(action["args"])
    except json.JSONDecodeError:
        args = {"arguments": action["args"]}
    with st.chat_message("assistant"):
        st.warning("Action sensible : l'agent veut préparer une demande administrative avec les "
                   "informations ci-dessous. Vérifiez-les avant de valider.")
        st.json(args)
        col1, col2 = st.columns(2)
        decision = None
        if col1.button("✅ Valider", use_container_width=True):
            decision = True
        if col2.button("❌ Annuler", use_container_width=True):
            decision = False
        if decision is not None:
            try:
                with st.spinner("Traitement…"):
                    traiter(reprendre(ss.attente["thread_id"], decision))
            except Exception as e:
                ss.attente = None
                st.error(f"Erreur : {e}")
            st.rerun()

question = st.chat_input("Posez votre question…", disabled=bool(ss.attente))
if question:
    ss.historique.append({"role": "user", "content": question})
    try:
        with st.spinner("L'agent travaille… (le premier appel est plus long)"):
            traiter(lancer(question))
    except Exception as e:
        st.error(f"Erreur : {e}")
    st.rerun()