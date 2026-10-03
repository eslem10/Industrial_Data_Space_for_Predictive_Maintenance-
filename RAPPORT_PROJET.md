# Rapport de projet - Industrial Data Space for Predictive Maintenance

## 1. Donnees

`simulator/stream_simulator.py` est la source unique de mesures pour le mode temps reel et le mode rattrapage. Les profils de temperature, vibration, pression, humidite et consommation electrique different selon l'usine. La generation ajoute une derive sinusoidale, des variations aleatoires, des defauts ponctuels de capteur et un score de risque qui determine l'etat normal ou panne. Le seuil est calibre pour viser environ 6 % de pannes.

Le mode rattrapage a produit 12 000 observations par usine, avec un depart fixe au 2026-01-01 et une minute entre mesures. La graine est fixe et distincte par usine. Les CSV sauvegardes avant remplacement sont conserves dans `data_backup/`, ignore par Git.

| Usine | Lignes | Pannes | Taux panne | Temp. moy. | Vibr. moy. | Press. moy. | Humid. moy. | Energie moy. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| factory_1 | 12 000 | 822 | 6,85 % | 55,097 | 0,629 | 3,470 | 55,052 | 6,561 |
| factory_2 | 12 000 | 764 | 6,37 % | 75,060 | 0,674 | 3,740 | 65,009 | 7,537 |
| factory_3 | 12 000 | 666 | 5,55 % | 67,893 | 0,785 | 3,779 | 48,099 | 8,468 |
| **Total** | **36 000** | **2 252** | **6,26 %** | | | | | |

Les CSV ont les colonnes `timestamp`, `factory_id`, `temperature`, `vibration`, `pressure`, `humidity`, `energy_consumption`, `state`. Le controle a trouve 12 000 lignes par usine, aucune valeur manquante, des dates strictement croissantes et des profils moyens distincts.

## 2. Apprentissage federe

Chaque client Flower (`federated/client.py`) lit uniquement le CSV de son usine, separe localement apprentissage et test, normalise les cinq capteurs avec `federated/preprocessing.py` et entraine le reseau dense 5 -> 32 -> 16 -> 1. Les poids de classe compensent la rarete des pannes. Les lignes brutes ne quittent pas le client.

Le serveur (`federated/server.py`) execute FedAvg sur cinq rounds et trois clients, ponderes par leurs nombres d'exemples. Le modele agrege est enregistre apres chaque round dans `federated/global_model.keras`.

## 3. Metriques

Chaque client calcule loss, accuracy, precision, recall et F1 sur son jeu de test. Le serveur affiche les moyennes ponderees par le nombre d'exemples et les enregistre dans `federated/results/metrics.json`, avec un objet par round. Le fichier contient `round`, `loss`, `accuracy`, `precision`, `recall` et `f1`.

## 4. Simulation IoT temps reel

`python simulator/stream_simulator.py factory_X` lance un processus par usine. Toutes les 2 secondes par defaut, il ajoute une mesure au CSV et publie atomiquement un instantane dans `data/factory_X/latest.json`. `--backfill 12000 --step-seconds 60` utilise le meme generateur pour reconstruire l'historique sans attente. `simulator/generate_data.py` est le wrapper de regeneration des trois historiques.

`simulator/live_predictor.py` charge le modele global, lit `latest.json`, reutilise la normalisation commune et expose `predict(sensor_values)`. Au-dessus de `ALERT_THRESHOLD`, il affiche une alerte et conserve jusqu'a 50 objets dans `data/alerts.json`. Le simulateur peut aussi publier vers MQTT lorsque `MQTT_HOST` est defini.

## 5. Etat d'execution et resultats

Le 3 octobre 2026, le serveur Flower et les trois clients ont termine cinq rounds avec les nouveaux CSV. Le modele et `federated/results/metrics.json` ont ete regeneres. Le mode temps reel a ete lance dans un repertoire temporaire : le CSV s'est rempli, `latest.json` correspondait a sa derniere ligne, et le predicteur a lu la mesure et ecrit une alerte avec un seuil de test de 0,0. Le test MQTT n'a pas ete execute : PyPI etait inaccessible pour installer `paho-mqtt` dans cet environnement.

| Round | Loss | Accuracy | Precision | Recall | F1 |
|---:|---:|---:|---:|---:|---:|
| 1 | 0,3853 | 0,8211 | 0,3339 | 0,7546 | 0,3629 |
| 2 | 0,3996 | 0,8233 | 0,3291 | 0,7546 | 0,3636 |
| 3 | 0,3847 | 0,8293 | 0,3371 | 0,7358 | 0,3588 |
| 4 | 0,4203 | 0,8219 | 0,3109 | 0,7785 | 0,3774 |
| 5 | 0,3777 | 0,8331 | 0,3369 | 0,7379 | 0,3638 |

Les resultats detailles sont dans `federated/results/metrics.json`. Les scores peuvent varier selon l'initialisation aleatoire du reseau.
