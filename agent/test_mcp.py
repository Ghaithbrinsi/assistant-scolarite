import time

from mcp_client import get_mcp

t0 = time.time()
mcp = get_mcp()
print(f"Serveur MCP démarré en {time.time() - t0:.1f}s\n")

for t in mcp.lister_outils():
    print("-", t["function"]["name"], ":", t["function"]["description"][:70])

print("\n", mcp.appeler("get_calendrier", {"module": "réseaux"}))
print("\n", mcp.appeler("calculer_delai", {"module": "bases de données", "hospitalisation": True}))
print("\n", mcp.appeler("generer_demande", {"nom": "", "numero_etudiant": "", "module": "anglais"}))
print("\n", mcp.appeler("outil_inexistant", {}))