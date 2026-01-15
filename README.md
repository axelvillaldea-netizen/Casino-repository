# 🏛️ OLYMPUS CASINO - Final Cut

Bot Telegram complet de casino avec 18 jeux différents.

## 📦 Structure du projet

```
Casino-repository/
├── main.py                 # Point d'entrée principal
├── requirements.txt        # Dépendances Python
├── .env                    # Configuration sensible (tokens, etc)
├── .gitignore             # Fichiers à ignorer dans Git
│
└── app/
    ├── __init__.py
    ├── config.py          # Configuration centralisée
    │
    ├── utils/
    │   ├── __init__.py
    │   ├── database.py     # Gestion SQLite
    │   ├── casino_logic.py # Moteur mathématique des jeux
    │   └── keyboards.py    # Construction des menus
    │
    ├── handlers/
    │   ├── __init__.py
    │   └── system.py       # Accueil, admin, coffre, bonus
    │
    └── games/
        ├── __init__.py
        ├── crash.py        # Jeu du Crash
        ├── cards.py        # Blackjack, Baccarat, Video Poker
        ├── simple.py       # Coinflip, Roulette, Shifumi, Dés
        ├── complex.py      # Mines, Tower, Horse, Plinko
        └── machines.py     # Slots, Scratch, Keno, Wheel, High-Low
```

## 🎮 Jeux implémentés

### Stratégie & Progression
- 🚀 **CRASH** - Multiplieur croissant avec risque
- 💣 **MINES** - Découvrez les diamants sans heurter les mines
- 🗼 **TOWER** - Escaladez étage par étage

### Cartes
- 🃏 **BLACKJACK** - Le classique du casino
- 🎩 **BACCARAT** - Joueur vs Banque
- 🃏 **VIDEO POKER** - 5 cartes, évaluez votre main

### Machines
- 🎰 **SLOTS** - 3 thèmes (Fruit, Egypte, Cyber)
- 🎫 **GRATTAGE** - 3 niveaux (Silver, Gold, Diamond)
- 🔢 **KENO** - Loterie numérique
- 🎡 **ROUE** - Spin la roue de la fortune
- 📈 **HIGH-LOW** - Prédisez si la carte sera plus haute

### Rapide
- 🪙 **COINFLIP** - Pile ou Face simple
- 🔴 **ROULETTE** - Le classique rouge/noir/vert
- 🎲 **DÉS** - Lancez pour 4+ gagne
- ✊ **SHIFUMI** - Pierre-Papier-Ciseaux
- 🐎 **COURSES** - Courses de chevaux simulées
- 🎯 **PLINKO** - Bille tombe sur des clous

## 🔧 Installation

### Prérequis
- Python 3.9+
- pip

### Étapes

1. **Cloner le repo**
```bash
git clone https://github.com/axelvillaldea-netizen/Casino-repository.git
cd Casino-repository
```

2. **Créer un environnement virtuel**
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
```

3. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

4. **Configurer le .env**
```bash
# .env
BOT_TOKEN=votre_token_telegram
ADMIN_ID=votre_id_telegram
DB_NAME=casino_final_cut.db
LOG_LEVEL=INFO
```

5. **Lancer le bot**
```bash
python main.py
```

## 🎟️ Commandes Admin

```
/create_code CODE MONTANT USES
  Crée un code promo

/add_money USER_ID MONTANT
  Ajoute de l'argent à un joueur
```

## 💾 Données sensibles

**Le fichier `.env` N'EST PAS versionné** (voir `.gitignore`)

Données stockées en `.env`:
- `BOT_TOKEN` - Token Telegram du bot
- `ADMIN_ID` - ID administrateur
- `DB_NAME` - Nom de la BD SQLite
- `LOG_LEVEL` - Niveau de logging

## 📊 Base de données

SQLite local avec 3 tables:

| Table | Description |
|-------|-------------|
| `users` | Profils joueurs (balance, stats) |
| `coupons` | Codes promo disponibles |
| `redeemed` | Codes promo utilisés |

## 🏗️ Architecture

- **Modulaire** - Un fichier par type de jeu
- **Configurable** - Tout via `.env`
- **Extensible** - Ajoutez facilement de nouveaux jeux
- **Sécurisé** - Données sensibles isolées

## 📝 Logs

Logs visibles dans la console avec format:
```
2026-01-15 21:10:29 - app.config - INFO - Message
```

## 🛠️ Modification

Pour ajouter un nouveau jeu:

1. Créer `app/games/myjeu.py`
2. Créer une classe avec `register_handlers()`
3. Importer dans `main.py`
4. Appeler `MyGame(dp, db)` dans `register_all_handlers()`

## 📄 Licence

Non spécifiée

## 👤 Auteur

axelvillaldea-netizen
