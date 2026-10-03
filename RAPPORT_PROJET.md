# Rapport de projet - Industrial Data Space for Predictive Maintenance

## 1. Donnees

Le generateur `simulator/generate_data.py` cree un CSV par usine dans `data/factory_1/`, `data/factory_2/` et `data/factory_3/`. Chaque fichier comporte 12 000 observations avec `timestamp`, `factory_id`, `temperature`, `vibration`, `pressure`, `humidity`, `energy_consumption` et `state` (`normal` ou `failure`). Les profils varient selon l'usine; le generateur ajoute derive et aleas de mesure et vise environ 6 % de pannes.

Les CSV existants n'ont pas ete modifies. Leur comptage verifie est de 36 000 lignes, dont 2 168 pannes (6,02 %).

## 2. Apprentissage federe

Chaque client Flower (`federated/client.py`) lit uniquement le CSV de l'usine choisie. Il separe localement les donnees en apprentissage et test en conservant les proportions de classes, puis normalise les cinq capteurs avec les constantes communes de `federated/preprocessing.py`. Le reseau dense est de forme 5 -> 32 -> 16 -> 1, avec sortie sigmoide. Des poids de classe compensent la rarete des pannes. Les lignes brutes ne quittent pas le client.

Le serveur (`federated/server.py`) agrege les poids avec FedAvg, pondere par le nombre d'exemples d'entrainement. Il requiert au moins trois clients et effectue cinq rounds par defaut. Il sauvegarde le modele global dans `federated/global_model.keras` apres chaque round.

## 3. Metriques

Chaque client evalue le modele sur son jeu de test et transmet loss, accuracy, precision, recall, F1 et le nombre d'exemples evalues. Le serveur calcule les metriques moyennes ponderees par le nombre de lignes de test, les affiche a chaque round et les ecrit dans `federated/results/metrics.json`. Le fichier est une liste d'objets avec `round`, `loss`, `accuracy`, `precision`, `recall` et `f1`.

## 4. Etat d'execution et resultats

Le 3 octobre 2026, l'execution a utilise Python 3.12.10, le serveur Flower et les trois clients sur les CSV existants. Les cinq rounds se sont termines sans echec de client. Le modele `federated/global_model.keras` et les resultats `federated/results/metrics.json` ont ete generes. Aucun CSV n'a ete reecrit.

| Round | Loss | Accuracy | Precision | Recall | F1 |
|---:|---:|---:|---:|---:|---:|
| 1 | 0.4077 | 0.8054 | 0.2754 | 0.8429 | 0.3775 |
| 2 | 0.4202 | 0.8161 | 0.2974 | 0.8218 | 0.3846 |
| 3 | 0.4136 | 0.8225 | 0.3073 | 0.8055 | 0.3858 |
| 4 | 0.3954 | 0.8275 | 0.3287 | 0.7961 | 0.3922 |
| 5 | 0.4361 | 0.8157 | 0.2900 | 0.8125 | 0.3788 |

Ce tableau rapporte une execution mesuree sur les CSV actuels; les scores peuvent varier lors d'un nouvel entrainement.
