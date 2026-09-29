# Industrial Data Space for Predictive Maintenance

## Installation (Windows / PowerShell)

Installez Python 3.12, puis ouvrez PowerShell à la racine du projet :

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m venv .venv312
.\.venv312\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Les scripts ML et fédérés utilisent les CSV déjà présents dans `data/factory_1` à `data/factory_3`.

## Entraînement local

```powershell
python ml/local_training.py
```

Le script entraîne un modèle Random Forest indépendant pour chaque usine et affiche les scores de test.

Pour remplacer les CSV par un nouveau jeu de données synthétiques (12 000 lignes par usine) :

```powershell
python simulator/generate_data.py
```

## Entraînement fédéré

Ouvrez quatre terminaux PowerShell à la racine du projet et activez `.venv312` dans chacun.

Dans le premier terminal, démarrez le serveur :

```powershell
python federated/server.py
```

Dans chacun des trois autres, lancez un client :

```powershell
python federated/client.py factory_1
python federated/client.py factory_2
python federated/client.py factory_3
```

Le serveur attend les trois clients et effectue cinq rounds. Le modèle global est écrit dans `federated/global_model.keras`.
Chaque client emploie les mêmes constantes de mise à l'échelle définies dans `federated/preprocessing.py`; gardez cette configuration identique sur tous les participants.

## Vérification rapide

```powershell
python -m py_compile ml/local_training.py federated/server.py federated/client.py federated/preprocessing.py
```
