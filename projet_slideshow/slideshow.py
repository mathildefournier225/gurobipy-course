import gurobipy as gp
from gurobipy import GRB
from itertools import combinations

def lire_fichier_entree(chemin_fichier):
    """
    Lit un fichier d'entrée au format spécifié et retourne une liste de dictionnaires représentant les photos.

    Args:
        chemin_fichier (str): Le chemin vers le fichier d'entrée.

    Returns:
        list: Une liste de dictionnaires où chaque dictionnaire représente une photo avec ses attributs.
    """
    photos = []
    
    with open(chemin_fichier, 'r') as fichier:
        lignes = fichier.readlines()
        
        # Le premier entier est le nombre de photos (nous l'ignorons ici)
        nombre_photos = int(lignes[0].strip())
        
        # Lire les lignes suivantes pour obtenir les informations des photos
        for idx, ligne in enumerate(lignes[1:]):
            elements = ligne.strip().split()
            
            # Extraire les informations
            orientation = elements[0]  # H ou V
            nombre_tags = int(elements[1])  # Nombre de tags
            tags = elements[nombre_tags:]  # Liste de tags
            
            
            # Ajouter la photo à la liste
            photos.append({
                'index': idx,  # Index de la photo dans le fichier
                'orientation': orientation,
                'tags': tags
            })
    
    return photos



def solve_slideshow(photos):
    """
    Organise un diaporama pour maximiser le score d'enchaînement.

    Args:
        photos (list): Liste de dictionnaires contenant les informations des photos.

    Returns:
        list: Ordre des slides.
    """
    n_photos = len(photos)

    # Indices pour les photos horizontales et verticales
    horizontal_photos = [i for i, p in enumerate(photos) if p['orientation'] == 'H']
    vertical_photos = [i for i, p in enumerate(photos) if p['orientation'] == 'V']
    indices_photos=[i for i, p in enumerate(photos)]

    # Modèle
    model = gp.Model("Slideshow")

    # Variables de décision
    x = model.addVars(n_photos, n_photos, vtype=GRB.BINARY, name="x")
    y = model.addVars(n_photos, n_photos, vtype=GRB.BINARY, name="y")

    
    # Contrainte : chaque photo est assignée à exactement un slide
    model.addConstrs((gp.quicksum(x[p, s] for s in range(n_photos)) == 1 for p in range(n_photos)), name="photo_once")

    # Contrainte : chaque slide contient une seule photo horizontale ou deux verticales
    for s in range(3):
        model.addConstr(
            2*gp.quicksum(x[p, s] for p in horizontal_photos)+gp.quicksum(x[p, s] for p in vertical_photos) == 2,
            name=f"two_photos_{s}"
        )

    # Calcul des scores
    def compute_score(photo1, photo2):
        tags1 = set(photo1['tags'])
        tags2 = set(photo2['tags'])
        common_tags = len(tags1 & tags2)
        unique_tags1 = len(tags1 - tags2)
        unique_tags2 = len(tags2 - tags1)
        return min(common_tags, unique_tags1, unique_tags2)

    scores = {
        (s1, s2): compute_score(photos[s1], photos[s2])
        for s1, s2 in combinations(range(n_photos), 2)
    }

    # Objectif : maximiser la somme des scores d'enchaînement
    model.setObjective(gp.quicksum(y[s1, s2] * scores.get((s1, s2), 0)
                                   for s1 in range(n_photos) for s2 in range(n_photos) if s1 != s2), GRB.MAXIMIZE)

    # Optimisation
    model.optimize()
    # Extraction des résultats
    if model.status == GRB.OPTIMAL:
        slides = []
        for s in range(n_photos):
            slide_photos = [p for p in range(n_photos) if x[p, s].X > 0.5]
            print (slide_photos)
            slides.append(slide_photos)
        return slides
    else:
        return None




photos=lire_fichier_entree("projet_slideshow/a_example.txt")
slides = solve_slideshow(photos)
print("Ordre des slides :", slides)