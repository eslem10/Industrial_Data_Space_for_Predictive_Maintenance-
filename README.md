# Industrial Data Space for Predictive Maintenance

## Fichiers

- `simulator/generate_data.py` cree les CSV synthetiques des trois usines.
- `federated/client.py` lit les donnees d'une usine, entraine le reseau localement et calcule ses metriques.
- `federated/server.py` coordonne Flower/FedAvg, sauvegarde le modele global et les metriques par round.
- `federated/preprocessing.py` definit les variables et les constantes communes de normalisation.
- `data/factory_X/sensor_data.csv` contient les donnees locales de chaque usine.

## Installation

Avec Python 3.12, depuis la racine du projet :

```powershell
py -3.12 -m venv .venv312
.\.venv312\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Lancement

Demarrer d'abord le serveur dans un terminal :

```powershell
python federated/server.py
```

Dans trois autres terminaux, lancer un client par usine :

```powershell
python federated/client.py factory_1
python federated/client.py factory_2
python federated/client.py factory_3
```

Chaque client garde les lignes brutes sur son usine. Seuls les parametres du modele, le nombre d'exemples et les metriques sont transmis.

## Sorties et configuration

- `federated/global_model.keras` contient le modele global sauvegarde apres chaque round.
- `federated/results/metrics.json` est une liste d'objets JSON avec `round`, `loss`, `accuracy`, `precision`, `recall` et `f1`. Les valeurs sont des moyennes ponderees par le nombre d'exemples d'evaluation.
- `DATA_DIR` configure le repertoire des CSV (defaut : `data/` a la racine du projet).
- `SERVER_ADDRESS` configure l'adresse d'ecoute du serveur (defaut `0.0.0.0:8080`) ou l'adresse de connexion des clients (defaut `127.0.0.1:8080`).
- `NUM_ROUNDS` configure le nombre de rounds (defaut : `5`).
- `NUM_CLIENTS` configure le nombre de clients requis (defaut : `3`).
