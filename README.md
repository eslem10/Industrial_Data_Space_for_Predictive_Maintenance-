# Industrial Data Space for Predictive Maintenance

## Role des fichiers

- `simulator/stream_simulator.py` emet les mesures d'une usine, les ajoute au CSV et publie la derniere mesure en JSON. Le mode MQTT est facultatif.
- `simulator/generate_data.py` regenere les trois historiques en appelant le meme simulateur en mode rattrapage.
- `simulator/live_predictor.py` lit les dernieres mesures, calcule le risque de panne et conserve les alertes.
- `simulator/mqtt_simulator.py` et `simulator/mqtt_subscriber.py` sont les outils de publication et de collecte MQTT.
- `federated/client.py` entraine et evalue le modele local d'une usine.
- `federated/server.py` agrege les poids FedAvg et sauvegarde modele et metriques.
- `federated/preprocessing.py` partage les variables et constantes de normalisation.
- `data/factory_X/` contient le CSV et le JSON de la derniere mesure de chaque usine.

## Installation

Avec Python 3.12, depuis la racine du projet :

```powershell
py -3.12 -m venv .venv312
.\.venv312\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Regenerer l'historique

Avant de remplacer les CSV, une copie ignoree par Git est conservee dans `data_backup/`. Le wrapper affiche un avertissement pour chaque CSV reinitialise :

```powershell
python simulator/generate_data.py
```

Pour reconstruire une seule usine :

```powershell
python simulator/stream_simulator.py factory_1 --backfill 12000 --step-seconds 60 --reset
```

## Simulation IoT temps reel

Demarrer une commande par usine dans trois terminaux distincts :

```powershell
python simulator/stream_simulator.py factory_1
python simulator/stream_simulator.py factory_2
python simulator/stream_simulator.py factory_3
```

Chaque processus ajoute une mesure au CSV toutes les 2 secondes par defaut et remplace atomiquement `latest.json`. L'option `--reset` vide le CSV apres avoir affiche un avertissement.

Lancer le predicteur apres le serveur et les clients Flower :

```powershell
python federated/server.py
python federated/client.py factory_1
python federated/client.py factory_2
python federated/client.py factory_3
python simulator/live_predictor.py
```

Les trois clients doivent tourner dans des terminaux separes du serveur. Le predicteur charge le modele global, applique `federated/preprocessing.py` et enregistre les alertes au-dessus du seuil.

### Formats produits

- `sensor_data.csv` : `timestamp,factory_id,temperature,vibration,pressure,humidity,energy_consumption,state`.
- `latest.json` : un objet avec les memes champs qu'une ligne CSV.
- `data/alerts.json` : liste des 50 alertes les plus recentes; chaque objet contient `timestamp`, `factory_id`, `probability` et les cinq valeurs capteurs.
- `federated/results/metrics.json` : liste par round avec `round`, `loss`, `accuracy`, `precision`, `recall` et `f1`.
- `federated/global_model.keras` : modele global sauvegarde apres chaque round.

### Variables d'environnement

- `INTERVAL` : pause entre mesures temps reel et entre lectures du predicteur; defaut `2` secondes.
- `DATA_DIR` : racine des donnees; defaut `data` dans le projet.
- `ALERT_THRESHOLD` : seuil d'alerte; defaut `0.5`.
- `MODEL_PATH` : modele charge par le predicteur; defaut `federated/global_model.keras`.
- `MQTT_HOST` : facultatif; s'il est defini, le simulateur publie aussi les mesures.
- `MQTT_PORT` : port MQTT; defaut `1883`.

## Apprentissage federe

Demarrer `python federated/server.py`, puis les trois clients `python federated/client.py factory_1`, `factory_2` et `factory_3` dans des terminaux separes. Chaque client garde ses lignes brutes localement.
