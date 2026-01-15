# Documentation du projet

## Fichiers clés

### `config.py`
Gère TOUTE la configuration du bot, chargée depuis `.env`

### `database.py`
Classe `DatabaseManager` - gère SQLite
- CRUD utilisateurs
- Gestion balance/vault
- Coupons promo

### `casino_logic.py`
Logique mathématique de TOUS les jeux
- Calculs de score (Blackjack, Baccarat)
- Générateurs aléatoires (Crash, Wheel)
- Évaluateurs de mains (Poker)

### `keyboards.py`
Menus et boutons réutilisables
- Menu principal
- Menu de mise (adapté par jeu)

## Module `handlers/`

### `system.py`
Tout ce qui n'est pas un jeu:
- `/start` - Accueil
- Gestion coffre (deposit/withdraw)
- Bonus quotidien
- Leaderboard
- Coupon codes
- Saisie texte (montants, codes)

## Module `games/`

### `crash.py`
- Jeu du Crash seul
- Gestion multiplicateur montant

### `cards.py`
- Blackjack (Hit/Stand/Double)
- Baccarat (Joueur/Banque/Egalité)
- Video Poker (5 cartes)

### `simple.py`
- Coinflip
- Roulette (Rouge/Noir/Vert)
- Shifumi
- Dés

### `complex.py`
- Mines (grille 5x5)
- Tower (étages)
- Horse (courses)
- Plinko

### `machines.py`
- Slots (3 thèmes)
- Scratch (3 niveaux)
- Keno (tirage)
- Wheel (roue fortune)
- High-Low (cartes)

---

Chaque jeu est ISOLÉ dans sa classe, facilitant maintenance et tests.
