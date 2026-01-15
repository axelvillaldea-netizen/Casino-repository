import random
import logging

logger = logging.getLogger(__name__)


class CasinoLogic:
    """Moteur mathématique pour tous les jeux du casino"""
    
    # --- BLACKJACK ---
    @staticmethod
    def get_blackjack_deck():
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        suits = ['♠️', '♥️', '♣️', '♦️']
        deck = []
        for s in suits:
            for r in ranks:
                if r == 'A': val = 11
                elif r in ['J', 'Q', 'K']: val = 10
                else: val = int(r)
                deck.append({'rank': r, 'suit': s, 'val': val})
        random.shuffle(deck)
        return deck

    @staticmethod
    def calculate_blackjack_score(hand):
        score = sum(card['val'] for card in hand)
        aces = sum(1 for card in hand if card['rank'] == 'A')
        while score > 21 and aces > 0:
            score -= 10
            aces -= 1
        return score

    # --- TOWER ---
    @staticmethod
    def generate_tower_row():
        row = [0, 0, 1]  # 2 Safe, 1 Bomb
        random.shuffle(row)
        return row

    @staticmethod
    def get_tower_multiplier(level):
        return round(1.45 ** level, 2)

    # --- HORSE ---
    @staticmethod
    def simulate_horse_race():
        pos = [0]*5
        frames = []
        winner = -1
        while winner == -1:
            for i in range(5):
                pos[i] += random.choices([0, 1, 2, 3], [10, 40, 30, 20])[0]
                if pos[i] >= 20 and winner == -1:
                    winner = i
            frames.append(list(pos))
        return frames, winner

    # --- CRASH ---
    @staticmethod
    def get_crash_multiplier():
        if random.random() < 0.04:
            return 1.00
        return round(random.expovariate(0.3) + 1.0, 2)

    # --- MINES ---
    @staticmethod
    def create_mines_grid(count=3):
        grid = [0]*25
        idx = random.sample(range(25), count)
        for i in idx:
            grid[i] = 1
        return grid

    @staticmethod
    def get_mines_multiplier(count, revealed):
        return round(0.97 * (25/(25-count))**revealed, 2)

    # --- PLINKO ---
    @staticmethod
    def drop_plinko_ball():
        path = [random.choice([0, 1]) for _ in range(12)]
        slot = sum(path)
        mults = {0: 100, 1: 50, 2: 25, 3: 10, 4: 5, 5: 2, 6: 0.2, 7: 2, 8: 5, 9: 10, 10: 25, 11: 50, 12: 100}
        return path, mults.get(slot, 0.2)

    # --- SLOTS ---
    @staticmethod
    def spin_slots(theme):
        if theme == "fruit":
            syms = ["🍒", "🍋", "🍊", "💎", "7️⃣"]
        elif theme == "egypt":
            syms = ["🏺", "📜", "👁️", "🦂", "👑"]
        elif theme == "cyber":
            syms = ["💿", "📡", "🔫", "👽", "⚛️"]
        else:
            syms = ["🍒", "🍋", "🍊", "💎", "7️⃣"]
        
        res = random.choices(syms, weights=[40, 30, 20, 8, 2], k=3)
        return res, syms

    # --- POKER ---
    @staticmethod
    def create_poker_deck():
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        suits = ['♠️', '♥️', '♣️', '♦️']
        deck = [{'rank': r, 'suit': s} for s in suits for r in ranks]
        random.shuffle(deck)
        return deck

    @staticmethod
    def evaluate_poker_hand(hand):
        ranks_map = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        vals = sorted([ranks_map[c['rank']] for c in hand])
        suits = [c['suit'] for c in hand]
        cnt = {x: vals.count(x) for x in vals}
        cnt_vals = sorted(cnt.values(), reverse=True)
        is_flush = len(set(suits)) == 1
        is_str = (vals[-1]-vals[0] == 4 and len(set(vals)) == 5) or vals == [2, 3, 4, 5, 14]
        
        if is_flush and is_str and vals[-1] == 14: return "ROYAL FLUSH", 250
        if is_flush and is_str: return "STR FLUSH", 50
        if cnt_vals == [4, 1]: return "CARRÉ", 25
        if cnt_vals == [3, 2]: return "FULL HOUSE", 9
        if is_flush: return "COULEUR", 6
        if is_str: return "QUINTE", 4
        if cnt_vals == [3, 1, 1]: return "BRELAN", 3
        if cnt_vals == [2, 2, 1]: return "2 PAIRES", 2
        if cnt_vals == [2, 1, 1, 1] and any(k >= 11 for k, v in cnt.items() if v == 2): return "PAIRE J+", 1
        return "RIEN", 0

    # --- KENO ---
    @staticmethod
    def draw_keno_numbers():
        return sorted(random.sample(range(1, 81), 20))

    @staticmethod
    def get_keno_payout(matches):
        return {0: 0, 1: 0, 2: 0, 3: 0, 4: 2, 5: 5, 6: 15, 7: 50, 8: 200, 9: 500, 10: 1000}.get(matches, 0)

    # --- WHEEL ---
    @staticmethod
    def spin_wheel():
        values = [0.2, 0.5, 1.0, 2.0, 5.0, 10.0, 25.0]
        weights = [30, 25, 20, 15, 7, 2, 1]
        return random.choices(values, weights=weights)[0]

    # --- HIGH-LOW ---
    @staticmethod
    def get_blackjack_deck_hl():
        return CasinoLogic.get_blackjack_deck()
