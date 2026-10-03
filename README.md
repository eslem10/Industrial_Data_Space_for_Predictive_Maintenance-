# Industrial Data Space for Predictive Maintenance

## Role des fichiers

- `simulator/generate_data.py` genere les CSV synthetiques des trois usines.
- `simulator/mqtt_simulator.py` publie des mesures de capteurs sur MQTT.
- `simulator/mqtt_subscriber.py` recoit les messages MQTT et les enregistre en CSV.
- `federated/preprocessing.py` definit les cinq variables et leur normalisation commune.
- `federated/client.py` lit le CSV d'une seule usine, fait le split local, entraine le reseau et calcule les metriques.
- `federated/server.py` coordonne FedAvg, sauvegarde le modele global et agrege les metriques.
- `data/factory_X/sensor_data.csv` contient les donnees locales d'une usine.

## Installation

Avec Python 3.12, depuis la racine du projet :

```powershell
py -3.12 -m venv .venv312
.\.venv312\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Lancement

Demarrer le serveur en premier :

```powershell
python federated/server.py
```

Dans trois autres terminaux, demarrer un client par usine :

```powershell
python federated/client.py factory_1
python federated/client.py factory_2
python federated/client.py factory_3
```

Les lignes brutes restent sur les clients. Seuls poids du modele, nombre d'exemples et metriques sont transmis.

## Sorties

- `federated/global_model.keras` est le modele global sauvegarde apres chaque round.
- `federated/results/metrics.json` est une liste d'objets contenant `round`, `loss`, `accuracy`, `precision`, `recall` et `f1`. Les metriques sont moyennees en fonction du nombre d'exemples de test de chaque client.

## Variables d'environnement

- `DATA_DIR` : dossier racine des CSV, par defaut `data/` a la racine du projet. Utilise par les clients.
- `SERVER_ADDRESS` : adresse d'ecoute du serveur (defaut `0.0.0.0:8080`) ou cible de connexion du client (defaut `127.0.0.1:8080`). La valeur peut differer entre processus.
- `NUM_ROUNDS` : nombre de rounds du serveur, defaut `5`.
- `NUM_CLIENTS` : clients requis par le serveur, defaut `3` et minimum `3`.
