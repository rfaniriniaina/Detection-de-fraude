import math
import networkx as nx
from collections import deque
import matplotlib.pyplot as plt
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

def detecter_et_classifier_viaBFS(G, taille_min = 3):
    cliques_globales = []
    noeuds_visites = set()

    couleurs_nodes = {noeud: 'green' for noeud in G.nodes()}

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

                            for n_clique in liste_combinaison:
                                couleurs_nodes[n_clique] = 'red'

                            #gestion de la peripherie
                            for n_clique in liste_combinaison:
                                for voisin in G.neighbors(n_clique):
                                    if couleurs_nodes[voisin] != 'red':
                                        couleurs_nodes[voisin] = 'orange'
                
                if clique_trouvee == True:
                    break
    return couleurs_nodes


def exporter_vers_neo4j(G, couleurs_nodes, URI, AUTH):
    print("\n Initialisation de la liaison avec l'instance Neo4j...")

    try:
        connexion = GraphDatabase.driver(URI, auth=AUTH)

        with connexion.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

            for noeud in G.nodes():
                statut = couleurs_nodes[noeud]
                if statut == 'red':
                    session.run("CREATE (n:Individu:ForteCohesion {id: $noeud_id, cohesion: 'Forte (Clique)'})", noeud_id=int(noeud))
                elif statut == 'orange':
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
   
    dictionnaire_couleurs = detecter_et_classifier_viaBFS(graphe_analyse, taille_min=3)
    exporter_vers_neo4j(graphe_analyse, dictionnaire_couleurs, neo4j_uri, neo4j_auth)

    print("Exportation reussie. Executons: MATCH (n) RETURN n dans Neo4j ")
