# Rapport de projet ? Industrial Data Space for Predictive Maintenance

## 1. Donnees

Le simulateur `simulator/generate_data.py` cree trois fichiers, un par usine, dans `data/factory_1/`, `data/factory_2/` et `data/factory_3/`. Chaque CSV contient 12 000 lignes avec `timestamp`, `factory_id`, `temperature`, `vibration`, `pressure`, `humidity`, `energy_consumption` et `state` (`normal` ou `failure`). Les mesures sont synthetiques, avec profils propres aux usines, derive, alea de mesure et environ 6 % de pannes visees.

Les fichiers CSV existants n'ont pas ete modifies pour cette livraison. Leur comptage actuel est de 36 000 lignes, dont 2 168 pannes (6,02 %).

## 2. Apprentissage federe

Chaque client Flower (`federated/client.py`) ne lit que le CSV de l'usine indiquee. Il cree un jeu d'entrainement et un jeu de test locaux, normalise les cinq variables avec les constantes partagees de `federated/preprocessing.py`, puis entraine un reseau dense 5 -> 32 -> 16 -> 1 avec sortie sigmoide. Des poids de classe compensent la rarete des pannes. Les donnees brutes ne quittent pas le client.

Le serveur (`federated/server.py`) utilise FedAvg : a chaque round, les parametres des clients sont moyennes avec une ponderation par le nombre d'exemples locaux. Il requiert trois clients par defaut et effectue cinq rounds. Le modele global est sauvegarde dans `federated/global_model.keras` apres chaque round.

## 3. Metriques

Chaque client calcule loss, accuracy, precision, recall et F1 sur son jeu de test, puis transmet ces metriques et son nombre d'exemples d'evaluation. Le serveur calcule une moyenne ponderee par nombre d'exemples, affiche les resultats par round et les ajoute a `federated/results/metrics.json`. Ce fichier est une liste d'objets contenant `round`, `loss`, `accuracy`, `precision`, `recall` et `f1`.

## 4. Etat d'execution

Les CSV sont presents et le code Python peut etre verifie avec `python -m py_compile federated/server.py federated/client.py federated/preprocessing.py`. L'execution complete du serveur et des trois clients doit etre effectuee dans un environnement avec les dependances de `requirements.txt`. Aucun score de modele n'est avance sans execution effective.
