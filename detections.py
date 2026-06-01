import math
import networkx as nx
from collections import deque
from neo4j import GraphDatabase
from itertools import combinations

def connexion_neo4j():
    user = (input("Votre identifiant pour neo4j : "))
    password = (input("Votre mot de passe neo4j : "))

    URI = "neo4j://127.0.0.1:7687"
    AUTH = (user, password)

    return URI, AUTH

def generer_graphe_aleatoire(n, p):
    """Genere un graphe aleatoire basé sur le modèle G(n, p).
       La boucle va garantir l'obtention d'un graphe connexe"""
    
    while True:
        G = nx.gnp_random_graph(n, p, directed=False)
        G.remove_edges_from(nx.selfloop_edges(G))

        if nx.is_connected(G):
            return G


def est_une_clique(G, liste_sommets):
    #Verifie si chaque membre est connecté à tous les autres membres

    taille = len(liste_sommets)
    if taille < 3:
        return False
    
    for i in range(0, taille):
        for j in range(i+1, taille):
            sommet_u = liste_sommets[i]
            sommet_v = liste_sommets[j]

            if G.has_edge(sommet_u, sommet_v) == False:
                return False
    return True

def detecter_clique_viaBFS(G, taille_min = 3):
    cliques_globales = []
    noeuds_visites = set()

    for noeud_depart in G.nodes():
        if noeud_depart in noeuds_visites:
            continue

        file_bfs = deque() #file d'Attente pour les noeud à explorer
        file_bfs.append(noeud_depart)

        decouvert_local = set()
        decouvert_local.add(noeud_depart)

        while len(file_bfs) > 0:
            sommet_actuel = file_bfs.popleft()
            noeuds_visites.add(sommet_actuel)

            voisins_directs = list(G.neighbors(sommet_actuel))

            for v in voisins_directs:
                if v not in decouvert_local and v not in noeuds_visites:
                    decouvert_local.add(v)
                    file_bfs.append(v)
            
            voisinage_local = [sommet_actuel] + voisins_directs

            for taille_clique in range(len(voisinage_local), taille_min-1, -1):
                clique_trouvee = False

                for combinaison in combinations(voisinage_local, taille_clique):
                    liste_combinaison = list(combinaison)

                    if est_une_clique(G, liste_combinaison) == True:
                        deja_incluse = False
                        for existante in cliques_globales:
                            if set(liste_combinaison).issubset(set(existante)):
                                deja_incluse = True

                        if deja_incluse == False:
                            cliques_globales.append(liste_combinaison)
                            clique_trouvee = True
                
                if clique_trouvee == True:
                    break
    return cliques_globales


def classifier_individu(G, cliques):
    ensemble_sommet = list(G.nodes())  
    liaison_forte = set()
    liaison_moyenne = set()
    liaison_faible = []

    for chaque_clique in cliques:
        for noeud in chaque_clique:
            liaison_forte.add(noeud)

    for noeud_fort in liaison_forte:
        for voisin in G.neighbors(noeud_fort):
            if voisin not in liaison_forte:
                liaison_moyenne.add(voisin)

    for individu in ensemble_sommet:
        if individu not in liaison_forte and individu not in liaison_moyenne:
            liaison_faible.append(individu)
    
    print("\n BILAN DE LA CLASSIFICATION DE L'ENSEMBLE DES INDIVIDUS (S)\n")
    print(f"Nombre total d'individus dans l'univers S : {len(ensemble_sommet)}")

    print(f"\n 1 . FORTE COHÉSION [{len(liaison_forte)} individus]")
    print("  --> Font partie integrante d'une communauté parfaite (clique).")
    print(f"    Liste des noeuds : {sorted(list(liaison_forte))}")

    print(f"\n 2 . MOYENNE COHÉSION [{len(liaison_moyenne)} individus]")
    print("  --> Connectés en ligne directe au coeur de la communauté (peripherie).")
    print(f"    Liste des noeuds : {sorted(list(liaison_moyenne))}")

    print(f"\n 3 . FAIBLE COHÉSION [{len(liaison_faible)} individus]")
    print("  --> Liés au reste du réseau aleatoire, hors portée de la communauté")
    print(f"    Liste des noeuds : {sorted(list(liaison_faible))}")

    print("\nLISTE DES COMMUNAUTÉS (CLIQUES)\n")

    if len(cliques) > 0:
        compteur = 1
        for c in cliques:
            print(f" Communauté {compteur} (Taille {len(c)}) : {sorted(c)}")
            compteur += compteur

    else:
        print("  Aucune clique de taille >= 3 n'a été décelée.")

    return liaison_forte, liaison_moyenne

def exporter_vers_neo4j(G, noeuds_fortes, noeuds_moyennes, URI, AUTH):
    print("\n Initialisation de la liaison avec l'instance Neo4j...")

    try:
        connexion = GraphDatabase.driver(URI, auth=AUTH)

        with connexion.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

            for noeud in G.nodes():
                if noeud in noeuds_fortes:
                    session.run("CREATE (n:Individu:ForteCohesion {id: $noeud_id, cohesion: 'Forte (Clique)'})", noeud_id=int(noeud))
                elif noeud in noeuds_moyennes:
                    session.run("CREATE (n:Individu:MoyenneCohesion {id: $noeud_id, cohesion: 'Moyenne (Clique)'})", noeud_id=int(noeud))
                else:
                    session.run("CREATE (n:Individu:FaibleCohesion {id: $noeud_id, cohesion: 'Faible (Clique)'})", noeud_id=int(noeud))

            print("Generation des aretes du reseau..")
            for lien_u, lien_v in G.edges():
                session.run("MATCH (a:Individu {id: $u}), (b:Individu {id: $v}) CREATE (a)-[:LIEN_SOCIAL]->(b)", u=int(lien_u), v=int(lien_v))

        connexion.close()
        print("\nOperation terminée..")

    except Exception as erreur:
        print(f"\nEchec de la commmunication avec Neo4j : {str(erreur)}")


if __name__ == "__main__":
    print("\nANALYSE DES COMMUNAUTES \n")

    neo4j_uri, neo4j_auth = connexion_neo4j()

    nb_sommets = int(input("\n Entrez la taille du graphe (nombre de sommets) n = "))
    seuil = math.log(nb_sommets)/nb_sommets
    print(f"Seuil critique d'Erdos Renyi : {seuil:.4f}")

    #boucle de securtité pour p
    while True:
        p = float(input(f"Entrez la probabilité d'arete (p doit etre > {seuil:.4f}) ex: 0.05 : p = "))
        if p > seuil and p <= 1.0:
            break

        print("La probabilité doit être supérieur qu seuil. Recommencez.")

    #genertion et calcul
    graphe_analyse = generer_graphe_aleatoire(nb_sommets, p)
    cliques_globales = detecter_clique_viaBFS(graphe_analyse, taille_min=3)

    #classification de S
    noeuds_fortes, noeuds_moyenne = classifier_individu(graphe_analyse, cliques_globales)

    exporter_vers_neo4j(graphe_analyse, noeuds_fortes, noeuds_moyenne, neo4j_uri, neo4j_auth)

    print("Executons: MATCH (n) RETURN n dans Neo4j ")