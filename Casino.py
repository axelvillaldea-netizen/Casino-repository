import asyncio
import logging
import sqlite3
import random
import time
import secrets
import string
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

# ==============================================================================
# 1. CONFIGURATION DU SERVEUR
# ==============================================================================
TOKEN = ":" 
DB_NAME = "casino_final_cut.db"
ADMIN_ID = 7464738226

# Configuration des logs détaillés
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialisation du bot
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- MÉMOIRE VIVE (RAM) ---
GAMES = {} 
USER_BETS = {} 
USER_CRASH_TARGETS = {}
USER_INPUT_CONTEXT = {}
CRASH_HISTORY = [1.00, 2.50, 1.10, 5.00, 1.20] 

# ==============================================================================
# 2. GESTIONNAIRE DE BASE DE DONNÉES
# ==============================================================================
class DatabaseManager:
    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME)
        self.initialize_tables()

    def initialize_tables(self):
        cursor = self.conn.cursor()
        
        # 1. Table Utilisateurs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                balance REAL DEFAULT 1000.0,
                vault REAL DEFAULT 0.0,
                wagered REAL DEFAULT 0.0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                xp INTEGER DEFAULT 0,
                last_bonus_date TEXT DEFAULT '2000-01-01',
                bonus_streak INTEGER DEFAULT 0
            )
        """)
        
        # 2. Table Codes Promo (Coupons)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS coupons (
                code TEXT PRIMARY KEY,
                amount REAL,
                uses_left INTEGER
            )
        """)
        
        # 3. Table Historique des Codes utilisés
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS redeemed (
                user_id INTEGER,
                code TEXT,
                PRIMARY KEY (user_id, code)
            )
        """)
        
        self.conn.commit()

    def get_user_data(self, user_id, username="Joueur"):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if result is None:
            cursor.execute(
                "INSERT INTO users (id, username) VALUES (?, ?)", 
                (user_id, username)
            )
            self.conn.commit()
            return self.get_user_data(user_id, username)
        
        return {
            "id": result[0], "name": result[1], "bal": result[2], "vault": result[3],
            "wager": result[4], "wins": result[5], "losses": result[6],
            "xp": result[7], "last_date": result[8], "streak": result[9]
        }

    def modify_balance(self, user_id, amount, transaction_type="game"):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, user_id))
        
        if transaction_type not in ["system", "vault", "bonus", "coupon"]:
            if amount < 0:
                abs_amount = abs(amount)
                cursor.execute(
                    "UPDATE users SET wagered = wagered + ?, xp = xp + ? WHERE id = ?", 
                    (abs_amount, abs_amount, user_id)
                )
            elif amount > 0:
                cursor.execute("UPDATE users SET wins = wins + 1 WHERE id = ?", (user_id,))
        
        self.conn.commit()
        return self.get_user_data(user_id)

    def process_vault_transaction(self, user_id, amount, action):
        user = self.get_user_data(user_id)
        cursor = self.conn.cursor()
        
        if action == "deposit":
            if user['bal'] < amount: return False
            cursor.execute(
                "UPDATE users SET balance = balance - ?, vault = vault + ? WHERE id = ?", 
                (amount, amount, user_id)
            )
        elif action == "withdraw":
            if user['vault'] < amount: return False
            cursor.execute(
                "UPDATE users SET balance = balance + ?, vault = vault - ? WHERE id = ?", 
                (amount, amount, user_id)
            )
            
        self.conn.commit()
        return True

    def claim_daily_bonus(self, user_id):
        user = self.get_user_data(user_id)
        today = datetime.now().date()
        last_date = datetime.strptime(user['last_date'], "%Y-%m-%d").date()
        
        if last_date == today: return False, 0, "Déjà réclamé."
        
        if last_date == today - timedelta(days=1):
            new_streak = min(user['streak'] + 1, 10)
        else:
            new_streak = 1
            
        amount = 500 + ((new_streak - 1) * 100)
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE users SET balance = balance + ?, last_bonus_date = ?, bonus_streak = ? WHERE id = ?",
            (amount, str(today), new_streak, user_id)
        )
        self.conn.commit()
        return True, amount, f"Série: {new_streak} jours"

    def create_coupon(self, code, amount, uses):
        try:
            self.conn.execute("INSERT INTO coupons (code, amount, uses_left) VALUES (?, ?, ?)", (code, amount, uses))
            self.conn.commit()
            return True
        except: return False

    def redeem_coupon(self, user_id, code):
        cursor = self.conn.cursor()
        row = cursor.execute("SELECT amount, uses_left FROM coupons WHERE code = ?", (code,)).fetchone()
        if not row: return False, "Invalide."
        if row[1] <= 0: return False, "Épuisé."
        if cursor.execute("SELECT * FROM redeemed WHERE user_id = ? AND code = ?", (user_id, code)).fetchone():
            return False, "Déjà utilisé."
            
        cursor.execute("UPDATE coupons SET uses_left = uses_left - 1 WHERE code = ?", (code,))
        cursor.execute("INSERT INTO redeemed (user_id, code) VALUES (?, ?)", (user_id, code))
        self.modify_balance(user_id, row[0], "coupon")
        self.conn.commit()
        return True, f"+${row[0]} ajoutés !"

    def get_leaderboard(self, limit=10):
        cursor = self.conn.cursor()
        cursor.execute("SELECT username, balance FROM users ORDER BY balance DESC LIMIT ?", (limit,))
        return cursor.fetchall()

db = DatabaseManager()

# ==============================================================================
# 3. MOTEUR MATHÉMATIQUE
# ==============================================================================
class CasinoLogic:
    
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
        row = [0, 0, 1] # 2 Safe, 1 Bomb
        random.shuffle(row)
        return row

    @staticmethod
    def get_tower_multiplier(level):
        return round(1.45 ** level, 2)

    # --- HORSE ---
    @staticmethod
    def simulate_horse_race():
        pos = [0]*5; frames = []; winner = -1
        while winner == -1:
            for i in range(5):
                pos[i] += random.choices([0,1,2,3], [10,40,30,20])[0]
                if pos[i]>=20 and winner==-1: winner=i
            frames.append(list(pos))
        return frames, winner

    # --- CRASH ---
    @staticmethod
    def get_crash_multiplier():
        if random.random() < 0.04: return 1.00
        return round(random.expovariate(0.3) + 1.0, 2)

    # --- MINES ---
    @staticmethod
    def create_mines_grid(count=3):
        grid = [0]*25
        idx = random.sample(range(25), count)
        for i in idx: grid[i] = 1
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
        if theme == "fruit": syms = ["🍒", "🍋", "🍊", "💎", "7️⃣"]
        elif theme == "egypt": syms = ["🏺", "📜", "👁️", "🦂", "👑"]
        elif theme == "cyber": syms = ["💿", "📡", "🔫", "👽", "⚛️"]
        else: syms = ["🍒", "🍋", "🍊", "💎", "7️⃣"]
        
        # Weighted random (Last is rarest)
        res = random.choices(syms, weights=[40, 30, 20, 8, 2], k=3)
        return res, syms

    # --- POKER ---
    @staticmethod
    def create_poker_deck():
        ranks = ['2','3','4','5','6','7','8','9','10','J','Q','K','A']
        suits = ['♠️','♥️','♣️','♦️']
        deck = [{'rank': r, 'suit': s} for s in suits for r in ranks]
        random.shuffle(deck)
        return deck

    @staticmethod
    def evaluate_poker_hand(hand):
        ranks_map = {'2':2, '3':3, '4':4, '5':5, '6':6, '7':7, '8':8, '9':9, '10':10, 'J':11, 'Q':12, 'K':13, 'A':14}
        vals = sorted([ranks_map[c['rank']] for c in hand])
        suits = [c['suit'] for c in hand]
        cnt = {x: vals.count(x) for x in vals}
        cnt_vals = sorted(cnt.values(), reverse=True)
        is_flush = len(set(suits)) == 1
        is_str = (vals[-1]-vals[0]==4 and len(set(vals))==5) or vals==[2,3,4,5,14]
        
        if is_flush and is_str and vals[-1]==14: return "ROYAL FLUSH", 250
        if is_flush and is_str: return "STR FLUSH", 50
        if cnt_vals==[4,1]: return "CARRÉ", 25
        if cnt_vals==[3,2]: return "FULL HOUSE", 9
        if is_flush: return "COULEUR", 6
        if is_str: return "QUINTE", 4
        if cnt_vals==[3,1,1]: return "BRELAN", 3
        if cnt_vals==[2,2,1]: return "2 PAIRES", 2
        if cnt_vals==[2,1,1,1] and any(k>=11 for k,v in cnt.items() if v==2): return "PAIRE J+", 1
        return "RIEN", 0

    # --- KENO ---
    @staticmethod
    def draw_keno_numbers():
        return sorted(random.sample(range(1, 81), 20))

    @staticmethod
    def get_keno_payout(matches):
        return {0:0, 1:0, 2:0, 3:0, 4:2, 5:5, 6:15, 7:50, 8:200, 9:500, 10:1000}.get(matches, 0)

# ==============================================================================
# 4. INTERFACE UTILISATEUR
# ==============================================================================
def get_rank_name(xp):
    if xp < 1000: return "Vagabond"
    if xp < 5000: return "Soldat"
    if xp < 20000: return "Capitaine"
    if xp < 100000: return "Général"
    return "EMPEREUR"

def get_main_menu(user):
    rank = get_rank_name(user['xp'])
    text = (
        f"🏛️ **OLYMPUS CASINO : FINAL CUT**\n\n"
        f"👤 **{user['name']}** | {rank}\n"
        f"💰 **Solde:** ${user['bal']:,.2f}\n"
        f"🏦 **Coffre:** ${user['vault']:,.2f}\n\n"
        f"👇 **CHOISISSEZ VOTRE JEU :**"
    )
    kb = InlineKeyboardBuilder()
    
    # Stars
    kb.row(InlineKeyboardButton(text="🚀 CRASH", callback_data="game_crash"),
           InlineKeyboardButton(text="💣 MINES", callback_data="game_mines"))
    
    # Cartes
    kb.row(InlineKeyboardButton(text="🃏 BLACKJACK", callback_data="game_bj"),
           InlineKeyboardButton(text="🎩 BACCARAT", callback_data="game_bacc"))
    kb.row(InlineKeyboardButton(text="🃏 POKER VIDÉO", callback_data="game_vpoker"))
    
    # Machines
    kb.row(InlineKeyboardButton(text="🎰 SLOTS (Multi)", callback_data="menu_slots"),
           InlineKeyboardButton(text="🎯 PLINKO", callback_data="game_plinko"))
    
    # Nouveautés
    kb.row(InlineKeyboardButton(text="🗼 TOWER", callback_data="game_tower"),
           InlineKeyboardButton(text="🐎 COURSES", callback_data="game_horse"))
    
    # Loterie & Grattage
    kb.row(InlineKeyboardButton(text="🔢 KENO", callback_data="game_keno"),
           InlineKeyboardButton(text="🎫 GRATTAGE", callback_data="menu_scratch"))
    
    # Classiques
    kb.row(InlineKeyboardButton(text="🔴 ROULETTE", callback_data="game_roulette"),
           InlineKeyboardButton(text="🪙 COINFLIP", callback_data="game_coin"))
    
    # Rapide
    kb.row(InlineKeyboardButton(text="📈 HIGH-LOW", callback_data="game_hilo"),
           InlineKeyboardButton(text="🎲 DÉS & SPORTS", callback_data="game_sports"))
    kb.row(InlineKeyboardButton(text="🎡 ROUE DREAM", callback_data="game_wheel"),
           InlineKeyboardButton(text="✊ SHIFUMI", callback_data="game_rps"))
           
    # Gestion
    kb.row(InlineKeyboardButton(text="🏦 COFFRE", callback_data="menu_vault"),
           InlineKeyboardButton(text="🎁 BONUS", callback_data="daily_bonus"))
    kb.row(InlineKeyboardButton(text="🏆 CLASSEMENT", callback_data="leaderboard"),
           InlineKeyboardButton(text="🎟️ CODE PROMO", callback_data="menu_coupon"))
    kb.row(InlineKeyboardButton(text="💳 DÉPÔT", callback_data="refill"))
           
    return text, kb.as_markup()

def get_bet_menu(game, bet, uid):
    kb = InlineKeyboardBuilder()
    
    # Ligne 1 : Contrôle Rapide
    kb.row(
        InlineKeyboardButton(text="MIN", callback_data=f"b_set_10_{game}"),
        InlineKeyboardButton(text="÷2", callback_data=f"b_div_2_{game}"),
        InlineKeyboardButton(text="x2", callback_data=f"b_mul_2_{game}"),
        InlineKeyboardButton(text="MAX", callback_data=f"b_max_{game}")
    )
    
    # Ligne 2 : Ajustement
    kb.row(
        InlineKeyboardButton(text="-100", callback_data=f"b_sub_100_{game}"),
        InlineKeyboardButton(text="-10", callback_data=f"b_sub_10_{game}"),
        InlineKeyboardButton(text=f"💰 ${bet}", callback_data="manual_trig"),
        InlineKeyboardButton(text="+10", callback_data=f"b_add_10_{game}"),
        InlineKeyboardButton(text="+100", callback_data=f"b_add_100_{game}")
    )
    
    # Bouton Saisie Manuelle
    kb.row(InlineKeyboardButton(text="✏️ SAISIR MONTANT", callback_data=f"manual_in_{game}"))
    
    # Commandes
    if game == "crash":
        t = USER_CRASH_TARGETS.get(uid, 2.0)
        h = " ".join([f"{x}x" for x in CRASH_HISTORY[-3:]])
        kb.row(InlineKeyboardButton(text=f"📊 Derniers: {h}", callback_data="ignore"))
        kb.row(InlineKeyboardButton(text="-0.1", callback_data="t_sub_0.1"), 
               InlineKeyboardButton(text=f"🎯 {t:.2f}x", callback_data="ign"), 
               InlineKeyboardButton(text="+0.1", callback_data="t_add_0.1"))
        kb.row(InlineKeyboardButton(text="🚀 DÉCOLLER", callback_data=f"play_crash:{t}:{bet}"))
    
    elif game == "tower": kb.row(InlineKeyboardButton(text="🧗 ESCALADER", callback_data=f"start_tower:{bet}"))
    elif game == "horse": 
        kb.row(InlineKeyboardButton(text="1️⃣", callback_data=f"play_horse:0:{bet}"), InlineKeyboardButton(text="2️⃣", callback_data=f"play_horse:1:{bet}"), InlineKeyboardButton(text="3️⃣", callback_data=f"play_horse:2:{bet}"))
        kb.row(InlineKeyboardButton(text="4️⃣", callback_data=f"play_horse:3:{bet}"), InlineKeyboardButton(text="5️⃣", callback_data=f"play_horse:4:{bet}"))
    elif game == "coin": kb.row(InlineKeyboardButton(text="🟡 PILE (x2)", callback_data=f"play_coin:pile:{bet}"), InlineKeyboardButton(text="⚪ FACE (x2)", callback_data=f"play_coin:face:{bet}"))
    elif game == "bj": kb.row(InlineKeyboardButton(text="🃏 DISTRIBUER", callback_data=f"start_bj:{bet}"))
    elif game == "mines": kb.row(InlineKeyboardButton(text="💣 DÉMARRER", callback_data=f"start_mines:{bet}"))
    elif game == "plinko": kb.row(InlineKeyboardButton(text="🔴 LÂCHER", callback_data=f"play_plinko:{bet}"))
    elif game == "vpoker": kb.row(InlineKeyboardButton(text="🃏 DEAL", callback_data=f"play_vpoker:{bet}"))
    elif game == "keno": kb.row(InlineKeyboardButton(text="🔢 TIRAGE", callback_data=f"play_keno:{bet}"))
    elif game == "wheel": kb.row(InlineKeyboardButton(text="🎡 TOURNER", callback_data=f"play_wheel:{bet}"))
    elif game == "hilo": kb.row(InlineKeyboardButton(text="📈 COMMENCER", callback_data=f"start_hilo:{bet}"))
    elif "scratch" in game: kb.row(InlineKeyboardButton(text="🎫 GRATTER", callback_data=f"play_{game}:{bet}"))
    elif "slots" in game: 
        th = game.split("_")[1]
        kb.row(InlineKeyboardButton(text="🎰 SPIN", callback_data=f"play_slots:{th}:{bet}"))
    elif game == "roulette":
        kb.row(InlineKeyboardButton(text="🔴", callback_data=f"play_rl:red:{bet}"), InlineKeyboardButton(text="⚫", callback_data=f"play_rl:black:{bet}"), InlineKeyboardButton(text="🟢", callback_data=f"play_rl:green:{bet}"))
    elif game == "bacc":
        kb.row(InlineKeyboardButton(text="JOUEUR", callback_data=f"play_bacc:P:{bet}"), InlineKeyboardButton(text="BANQUE", callback_data=f"play_bacc:B:{bet}"), InlineKeyboardButton(text="EGALITE", callback_data=f"play_bacc:T:{bet}"))
    elif game == "rps":
        kb.row(InlineKeyboardButton(text="✊", callback_data=f"play_rps:r:{bet}"), InlineKeyboardButton(text="✋", callback_data=f"play_rps:p:{bet}"), InlineKeyboardButton(text="✌️", callback_data=f"play_rps:s:{bet}"))
    elif game == "dice": kb.row(InlineKeyboardButton(text="🎲 LANCER", callback_data=f"play_dice:{bet}"))

    kb.row(InlineKeyboardButton(text="🔙 RETOUR MENU", callback_data="home"))
    return kb.as_markup()

# ==============================================================================
# 5. HANDLERS SYSTÈME (ADMIN, MISE MANUELLE, COFFRE)
# ==============================================================================
@dp.message(Command("start"))
async def start(m: types.Message):
    u = db.get_user_data(m.from_user.id, m.from_user.first_name)
    await m.answer(get_main_menu(u)[0], reply_markup=get_main_menu(u)[1], parse_mode="Markdown")

@dp.callback_query(F.data == "home")
async def home(c: types.CallbackQuery):
    if c.from_user.id in USER_INPUT_CONTEXT: del USER_INPUT_CONTEXT[c.from_user.id]
    u = db.get_user_data(c.from_user.id)
    try: await c.message.edit_text(get_main_menu(u)[0], reply_markup=get_main_menu(u)[1], parse_mode="Markdown")
    except TelegramBadRequest: await c.answer()

@dp.callback_query(F.data == "refill")
async def refill(c: types.CallbackQuery):
    u = db.get_user_data(c.from_user.id)
    if u['bal'] < 100:
        db.modify_balance(u['id'], 1000)
        await c.answer("✅ +1000$ crédités !", show_alert=True)
        await home(c)
    else: await c.answer("❌ Assez d'argent !", show_alert=True)

# --- ADMIN ---
@dp.message(Command("create_code"))
async def admin_code(m: types.Message, command: CommandObject):
    if m.from_user.id != ADMIN_ID: return
    try:
        args = command.args.split()
        if db.create_coupon(args[0], float(args[1]), int(args[2])):
            await m.answer(f"✅ Code {args[0]} créé.")
    except: await m.answer("Format: /create_code CODE MONTANT USES")

@dp.message(Command("add_money"))
async def admin_money(m: types.Message, command: CommandObject):
    if m.from_user.id != ADMIN_ID: return
    try:
        args = command.args.split()
        db.modify_balance(int(args[0]), float(args[1]), "admin")
        await m.answer("✅")
    except: await m.answer("Format: /add_money ID MONTANT")

# --- SAISIE TEXTE ---
@dp.callback_query(F.data == "menu_code")
async def menu_code(c):
    await c.message.edit_text("🎟️ **CODE PROMO**\nEntrez votre code :", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙", callback_data="home")]]))
    USER_INPUT_CONTEXT[c.from_user.id] = "coupon"

@dp.callback_query(F.data.startswith("manual_in_"))
async def manual_trig(c):
    game = c.data.replace("manual_in_", "")
    USER_INPUT_CONTEXT[c.from_user.id] = f"bet_{game}"
    await c.answer("⌨️ Tapez le montant !", show_alert=True)

@dp.message(F.text)
async def text_input(m: types.Message):
    uid = m.from_user.id
    ctx = USER_INPUT_CONTEXT.get(uid)
    if not ctx: return

    if ctx == "coupon":
        ok, msg = db.redeem_coupon(uid, m.text.strip())
        del USER_INPUT_CONTEXT[uid]
        await m.answer(f"{'✅' if ok else '❌'} {msg}")
        return

    if ctx.startswith("bet_") and m.text.isdigit():
        game = ctx.replace("bet_", "")
        amt = int(m.text)
        u = db.get_user_data(uid)
        if amt < 10: return await m.answer("❌ Min 10$")
        if amt > u['bal']: amt = int(u['bal'])
        
        USER_BETS[uid] = amt
        del USER_INPUT_CONTEXT[uid]
        try: await m.delete()
        except: pass
        msg = await m.answer(f"✅ Mise fixée à **${amt}**")
        await asyncio.sleep(1); 
        try: await msg.delete()
        except: pass
        await m.answer(f"🎮 **{game.upper()}**", reply_markup=get_bet_menu(game, amt, uid), parse_mode="Markdown")

# --- MISE BOUTONS ---
@dp.callback_query(F.data.startswith("b_"))
async def bet_btn(c):
    p=c.data.split("_"); act=p[1]; val=p[2]; game="_".join(p[3:]); uid=c.from_user.id
    curr = USER_BETS.get(uid, 50); u = db.get_user_data(uid)
    
    if act=="add": curr+=int(val)
    elif act=="sub": curr=max(10, curr-int(val))
    elif act=="mul": curr*=2
    elif act=="div": curr=max(10, curr//2)
    elif act=="set": curr=10
    elif act=="max": curr=int(u['bal'])
    
    if curr>u['bal']: curr=int(u['bal'])
    if curr<10: curr=10
    USER_BETS[uid] = curr
    await c.message.edit_reply_markup(reply_markup=get_bet_menu(game, curr, uid))

# --- COFFRE & BONUS & TARGET ---
@dp.callback_query(F.data == "daily_bonus")
async def daily(c):
    ok, amt, msg = db.claim_daily_bonus(c.from_user.id)
    await c.answer(f"🎁 +${amt} ({msg})" if ok else f"⏳ {msg}", show_alert=True)

@dp.callback_query(F.data == "menu_vault")
async def vault_m(c):
    u = db.get_user_data(c.from_user.id)
    txt = f"🏦 **COFFRE**\nDispo: ${u['bal']:.2f}\nCoffre: ${u['vault']:.2f}"
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📥 50%", callback_data="v_d_50"), InlineKeyboardButton(text="📥 TOUT", callback_data="v_d_all"))
    kb.row(InlineKeyboardButton(text="📤 50%", callback_data="v_w_50"), InlineKeyboardButton(text="📤 TOUT", callback_data="v_w_all"))
    kb.row(InlineKeyboardButton(text="🔙", callback_data="home"))
    await c.message.edit_text(txt, reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("v_"))
async def vault_act(c):
    p=c.data.split("_"); act="deposit" if p[1]=="d" else "withdraw"
    u=db.get_user_data(c.from_user.id)
    src = u['bal'] if act=="deposit" else u['vault']
    amt = int(src) if p[2]=="all" else int(src/2)
    if amt>0 and db.process_vault_transaction(u['id'], amt, act): await vault_m(c)
    else: await c.answer("Erreur")

@dp.callback_query(F.data.startswith("t_"))
async def tgt_act(c):
    p=c.data.split("_"); act=p[1]; val=float(p[2]); uid=c.from_user.id
    curr = USER_CRASH_TARGETS.get(uid, 2.0)
    curr = curr+val if act=="add" else max(1.01, curr-val)
    USER_CRASH_TARGETS[uid] = round(curr, 2)
    await c.message.edit_reply_markup(reply_markup=get_bet_menu("crash", USER_BETS.get(uid,50), uid))

@dp.callback_query(F.data == "leaderboard")
async def lead(c):
    top = db.get_leaderboard(); txt="🏆 **TOP RICHESSE**\n\n"
    for i,p in enumerate(top):
        med = "🥇" if i==0 else "🥈" if i==1 else "🥉" if i==2 else f"#{i+1}"
        txt += f"{med} **{p[0]}** — ${p[1]:,.2f}\n"
    kb = InlineKeyboardBuilder().add(InlineKeyboardButton(text="🔙", callback_data="home"))
    await c.message.edit_text(txt, reply_markup=kb.as_markup(), parse_mode="Markdown")

# ==============================================================================
# 6. LOGIQUE JEUX (LES 18 JEUX)
# ==============================================================================

# --- SCRATCH (CORRIGÉ & AMÉLIORÉ) ---
@dp.callback_query(F.data == "menu_scratch")
async def m_sc(c):
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="SILVER ($10)", callback_data="play_scratch_silver:10"))
    kb.row(InlineKeyboardButton(text="GOLD ($50)", callback_data="play_scratch_gold:50"))
    kb.row(InlineKeyboardButton(text="DIAMOND ($100)", callback_data="play_scratch_diamond:100"))
    kb.row(InlineKeyboardButton(text="🔙", callback_data="home"))
    await c.message.edit_text("🎫 **GRATTAGE**\nChoisissez votre ticket :", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("play_scratch_"))
async def p_sc(c):
    p=c.data.split(":"); type=p[0].replace("play_scratch_",""); bet=int(p[1]); uid=c.from_user.id
    if db.get_user_data(uid)['bal'] < bet: return await c.answer("Pauvre")
    db.modify_balance(uid, -bet, "wager")
    
    msg = await c.message.edit_text("🎫 Grattage en cours... ▒▒▒")
    await asyncio.sleep(1)
    
    # Configuration des symboles et gains
    if type == "silver":
        syms = ["🍒", "🍋", "🔔", "❌", "❌"] # Plus de perdants
        mult = 5
    elif type == "gold":
        syms = ["💰", "💎", "💵", "❌", "❌"]
        mult = 15
    else: # Diamond
        syms = ["👑", "💍", "7️⃣", "❌", "❌", "❌"] # Plus risqué
        mult = 50
        
    grid = random.choices(syms, k=9)
    
    # Check Win (3 symboles identiques hors ❌)
    win = 0
    match = None
    counts = {x: grid.count(x) for x in grid if x != "❌"}
    
    for s, count in counts.items():
        if count >= 3:
            match = s
            win = bet * mult
            break
            
    if win: db.modify_balance(uid, win, "game")
    
    # Affichage Grille
    gt = "\n".join([" ".join(grid[i:i+3]) for i in range(0,9,3)])
    res = f"✅ **GAGNÉ !** (3x {match}) +${win}" if win else "❌ **PERDU**"
    
    kb = InlineKeyboardBuilder().add(InlineKeyboardButton(text="REJOUER", callback_data="menu_scratch"), InlineKeyboardButton(text="MENU", callback_data="home"))
    await msg.edit_text(f"🎫 **TICKET {type.upper()}**\n\n{gt}\n\n{res}", reply_markup=kb.as_markup())

# --- TOWER ---
@dp.callback_query(F.data == "game_tower")
async def g_tower(c):
    uid=c.from_user.id; USER_BETS.setdefault(uid, 20)
    await c.message.edit_text("🗼 **TOWER**\nMontez sans tomber !", reply_markup=get_bet_menu("tower", USER_BETS[uid], uid))
@dp.callback_query(F.data.startswith("start_tower:"))
async def s_tower(c):
    bet=int(c.data.split(":")[1]); uid=c.from_user.id
    if db.get_user_data(uid)['bal']<bet: return
    db.modify_balance(uid, -bet, "wager")
    GAMES[uid] = {"t":"tower", "lvl":1, "row":CasinoLogic.generate_tower_row(), "bet":bet, "on":True}
    await r_tower(c, uid)
async def r_tower(c, uid, lost=False, cash=False):
    g=GAMES[uid]
    if lost:
        await c.message.edit_text(f"💥 **CHUTE !** (Étage {g['lvl']})", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="REJOUER", callback_data="game_tower"), InlineKeyboardButton(text="MENU", callback_data="home")]]))
        del GAMES[uid]
    elif cash:
        w=g['bet']*CasinoLogic.get_tower_multiplier(g['lvl']-1)
        db.modify_balance(uid, w, "game")
        await c.message.edit_text(f"✅ **ENCAISSÉ !** +${w:.2f}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="REJOUER", callback_data="game_tower"), InlineKeyboardButton(text="MENU", callback_data="home")]]))
        del GAMES[uid]
    else:
        m=CasinoLogic.get_tower_multiplier(g['lvl'])
        kb=InlineKeyboardBuilder()
        for i in range(3): kb.add(InlineKeyboardButton(text="❓", callback_data=f"tc:{i}"))
        if g['lvl']>1: kb.row(InlineKeyboardButton(text="💰 CASH OUT", callback_data="tout"))
        await c.message.edit_text(f"🗼 Étage {g['lvl']} (Prochain: x{m})", reply_markup=kb.as_markup())
@dp.callback_query(F.data.startswith("tc:"))
async def tc(c):
    uid=c.from_user.id; idx=int(c.data.split(":")[1]); g=GAMES.get(uid)
    if not g or not g['on']: return
    if g['row'][idx]==1: await r_tower(c, uid, lost=True)
    else:
        g['lvl']+=1; g['row']=CasinoLogic.generate_tower_row()
        if g['lvl']>8: await r_tower(c, uid, cash=True)
        else: await r_tower(c, uid)
@dp.callback_query(F.data == "tout")
async def tout(c): await r_tower(c, c.from_user.id, cash=True)

# --- HORSE ---
@dp.callback_query(F.data == "game_horse")
async def g_horse(c):
    uid=c.from_user.id; USER_BETS.setdefault(uid, 50)
    await c.message.edit_text("🐎 **COURSES**", reply_markup=get_bet_menu("horse", USER_BETS[uid], uid))
@dp.callback_query(F.data.startswith("play_horse:"))
async def p_horse(c):
    p=c.data.split(":"); h_pk=int(p[1]); bet=int(p[2]); uid=c.from_user.id
    if db.get_user_data(uid)['bal']<bet: return
    db.modify_balance(uid, -bet, "wager")
    msg = await c.message.edit_text("🏁 DÉPART...")
    frames, win_h = CasinoLogic.simulate_horse_race()
    emo = ["🔴","🔵","🟢","🟡","🟣"]
    for i, f in enumerate(frames):
        if i%2==0 or i==len(frames)-1:
            t = "\n".join([f"{j+1} {emo[j]} "+("."*p) for j,p in enumerate(f)])
            try: await msg.edit_text(f"🐎 COURSE\n{t}"); await asyncio.sleep(0.5)
            except: pass
    w = bet*4 if win_h==h_pk else 0
    if w: db.modify_balance(uid, w, "game")
    await msg.edit_text(f"🏆 {emo[win_h]} Gagne !\n{'✅ +$'+str(w) if w else '❌ PERDU'}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="REJOUER", callback_data="game_horse"), InlineKeyboardButton(text="MENU", callback_data="home")]]))

# --- COINFLIP ---
@dp.callback_query(F.data == "game_coin")
async def g_coin(c):
    uid=c.from_user.id; USER_BETS.setdefault(uid, 50)
    await c.message.edit_text("🪙 **PILE OU FACE**", reply_markup=get_bet_menu("coin", USER_BETS[uid], uid))
@dp.callback_query(F.data.startswith("play_coin:"))
async def p_coin(c):
    p=c.data.split(":"); pk=p[1]; bet=int(p[2]); uid=c.from_user.id
    if db.get_user_data(uid)['bal']<bet: return
    db.modify_balance(uid, -bet, "wager")
    msg = await c.message.edit_text("🪙 ...")
    await asyncio.sleep(1)
    res = random.choice(["pile", "face"])
    w = bet*2 if res==pk else 0
    if w: db.modify_balance(uid, w, "game")
    kb=InlineKeyboardBuilder().add(InlineKeyboardButton(text="REJOUER", callback_data="game_coin"), InlineKeyboardButton(text="MENU", callback_data="home"))
    await msg.edit_text(f"Résultat: {res.upper()}\n{'✅ +$'+str(w) if w else '❌'}", reply_markup=kb.as_markup())

# --- BLACKJACK ---
@dp.callback_query(F.data == "game_bj")
async def g_bj(c):
    uid=c.from_user.id; USER_BETS.setdefault(uid, 50)
    await c.message.edit_text("🃏 **BLACKJACK**", reply_markup=get_bet_menu("bj", USER_BETS[uid], uid))
@dp.callback_query(F.data.startswith("start_bj:"))
async def s_bj(c):
    bet=int(c.data.split(":")[1]); uid=c.from_user.id
    if db.get_user_data(uid)['bal']<bet: return
    db.modify_balance(uid, -bet, "wager")
    d=CasinoLogic.get_blackjack_deck()
    GAMES[uid] = {"t":"bj", "d":d, "ph":[d.pop(),d.pop()], "dh":[d.pop(),d.pop()], "b":bet}
    await r_bj(c, uid)
async def r_bj(c, uid, over=False, win=0):
    g=GAMES[uid]; ps=CasinoLogic.calculate_blackjack_score(g['ph'])
    pt=" ".join([f"{x['rank']}{x['suit']}" for x in g['ph']])
    if not over:
        dt=f"{g['dh'][0]['rank']}{g['dh'][0]['suit']} 🎴"
        kb=InlineKeyboardBuilder().row(InlineKeyboardButton(text="HIT",callback_data="bjh"), InlineKeyboardButton(text="STAND",callback_data="bjs"))
        if len(g['ph'])==2: kb.row(InlineKeyboardButton(text="DOUBLE",callback_data="bjd"))
        await c.message.edit_text(f"🃏 **BJ** (${g['b']})\n🤵 {dt}\n👤 {pt} ({ps})", reply_markup=kb.as_markup())
    else:
        ds=CasinoLogic.calculate_blackjack_score(g['dh']); dt=" ".join([f"{x['rank']}{x['suit']}" for x in g['dh']])
        st="✅" if win>g['b'] else "🤝" if win==g['b'] else "❌"
        kb=InlineKeyboardBuilder().add(InlineKeyboardButton(text="REJOUER", callback_data="game_bj"), InlineKeyboardButton(text="MENU", callback_data="home"))
        await c.message.edit_text(f"🏁 {st} (${win})\n🤵 {dt} ({ds})\n👤 {pt} ({ps})", reply_markup=kb.as_markup())
        del GAMES[uid]
@dp.callback_query(F.data=="bjh")
async def bjh(c):
    g=GAMES[c.from_user.id]; g['ph'].append(g['d'].pop())
    if CasinoLogic.calculate_blackjack_score(g['ph'])>21: await r_bj(c, c.from_user.id, True, 0)
    else: await r_bj(c, c.from_user.id)
@dp.callback_query(F.data=="bjs")
async def bjs(c): await bjd_turn(c, c.from_user.id)
@dp.callback_query(F.data=="bjd")
async def bjd(c):
    uid=c.from_user.id; g=GAMES[uid]
    db.modify_balance(uid, -g['b'], "wager"); g['b']*=2
    g['ph'].append(g['d'].pop())
    if CasinoLogic.calculate_blackjack_score(g['ph'])>21: await r_bj(c, uid, True, 0)
    else: await bjd_turn(c, uid)
async def bjd_turn(c, uid):
    g=GAMES[uid]
    while CasinoLogic.calculate_blackjack_score(g['dh'])<17: g['dh'].append(g['d'].pop())
    ps, ds = CasinoLogic.calculate_blackjack_score(g['ph']), CasinoLogic.calculate_blackjack_score(g['dh'])
    w=0
    if ds>21 or ps>ds: w=g['b']*2
    elif ps==ds: w=g['b']
    if w: db.modify_balance(uid, w, "game")
    await r_bj(c, uid, True, w)

# --- CRASH ---
@dp.callback_query(F.data == "game_crash")
async def g_crash(c):
    uid=c.from_user.id; USER_BETS.setdefault(uid, 50); USER_CRASH_TARGETS.setdefault(uid, 2.0)
    await c.message.edit_text("🚀 **CRASH**", reply_markup=get_bet_menu("crash", USER_BETS[uid], uid))
@dp.callback_query(F.data.startswith("play_crash:"))
async def p_crash(c):
    p=c.data.split(":"); tgt=float(p[1]); bet=int(p[2]); uid=c.from_user.id
    if db.get_user_data(uid)['bal']<bet: return
    db.modify_balance(uid, -bet, "wager")
    msg=await c.message.edit_text("🚀 1.00x")
    crash=CasinoLogic.get_crash_multiplier(); CRASH_HISTORY.append(crash)
    if len(CRASH_HISTORY)>10: CRASH_HISTORY.pop(0)
    curr=1.0
    while curr<crash and curr<tgt:
        await asyncio.sleep(0.5); curr+=random.uniform(0.1,0.4)
        if curr>crash: curr=crash
        try: await msg.edit_text(f"🚀 {curr:.2f}x")
        except: pass
    w=int(bet*tgt) if crash>=tgt else 0
    if w: db.modify_balance(uid, w, "game")
    kb=InlineKeyboardBuilder().add(InlineKeyboardButton(text="REJOUER", callback_data="game_crash"), InlineKeyboardButton(text="MENU", callback_data="home"))
    await msg.edit_text(f"{'✅' if w else '💥'} Crash: {crash}x\nGain: ${w}", reply_markup=kb.as_markup())

# --- MINES ---
@dp.callback_query(F.data == "game_mines")
async def g_mines(c):
    uid=c.from_user.id; USER_BETS.setdefault(uid, 20)
    await c.message.edit_text("💣 **MINES**", reply_markup=get_bet_menu("mines", USER_BETS[uid], uid))
@dp.callback_query(F.data.startswith("start_mines:"))
async def s_mines(c):
    bet=int(c.data.split(":")[1]); uid=c.from_user.id
    if db.get_user_data(uid)['bal']<bet: return
    db.modify_balance(uid, -bet, "wager")
    GAMES[uid] = {"t":"mines", "grid":CasinoLogic.create_mines_grid(3), "bet":bet, "rev":[], "on":True}
    await r_mines(c, uid)
async def r_mines(c, uid, boom=False, cash=False):
    g=GAMES[uid]; kb=InlineKeyboardBuilder()
    for i in range(25):
        t="🟦"; cb=f"mi:{i}"
        if i in g['rev'] or boom or cash:
            t="💣" if g['grid'][i] else "💎"; cb="ign"
        kb.add(InlineKeyboardButton(text=t, callback_data=cb))
    kb.adjust(5)
    if not boom and not cash:
        val = g['bet']*CasinoLogic.get_mines_multiplier(3, len(g['rev']))
        kb.row(InlineKeyboardButton(text=f"💰 CASH ${val:.2f}", callback_data="mi_out"))
        await c.message.edit_text(f"Gain: ${val:.2f}", reply_markup=kb.as_markup())
    else:
        kb.row(InlineKeyboardButton(text="REJOUER", callback_data="game_mines"), InlineKeyboardButton(text="MENU", callback_data="home"))
        await c.message.edit_text("✅ GAGNÉ" if cash else "💥 PERDU", reply_markup=kb.as_markup())
        del GAMES[uid]
@dp.callback_query(F.data.startswith("mi:"))
async def mi_c(c):
    uid=c.from_user.id; idx=int(c.data.split(":")[1]); g=GAMES.get(uid)
    if not g or not g['on']: return
    if g['grid'][idx]: await r_mines(c, uid, boom=True)
    else: g['rev'].append(idx); await r_mines(c, uid)
@dp.callback_query(F.data == "mi_out")
async def mi_o(c):
    uid=c.from_user.id; g=GAMES.get(uid)
    if g:
        w=g['bet']*CasinoLogic.get_mines_multiplier(3, len(g['rev']))
        db.modify_balance(uid, w, "game")
        await r_mines(c, uid, cash=True)

# --- SLOTS ---
@dp.callback_query(F.data == "menu_slots")
async def g_slots(c):
    kb=InlineKeyboardBuilder()
    for t in ["fruit","egypt","cyber"]: kb.add(InlineKeyboardButton(text=t.upper(), callback_data=f"slot_t:{t}"))
    kb.row(InlineKeyboardButton(text="🔙", callback_data="home"))
    await c.message.edit_text("🎰 Thème ?", reply_markup=kb.as_markup())
@dp.callback_query(F.data.startswith("slot_t:"))
async def s_t(c):
    th=c.data.split(":")[1]; uid=c.from_user.id; USER_BETS.setdefault(uid, 20)
    await c.message.edit_text(f"🎰 **{th.upper()}**", reply_markup=get_bet_menu(f"slots_{th}", USER_BETS[uid], uid))
@dp.callback_query(F.data.startswith("play_slots:"))
async def s_p(c):
    p=c.data.split(":"); th=p[1]; bet=int(p[2]); uid=c.from_user.id
    if db.get_user_data(uid)['bal']<bet: return
    db.modify_balance(uid, -bet, "wager")
    res, syms = CasinoLogic.spin_slots(th)
    await c.message.edit_text(f"🎰 {res[0]}|{res[1]}|{res[2]}")
    w=0
    if res[0]==res[1]==res[2]: w=bet*(100 if res[0]==syms[4] else 20)
    elif res[0]==res[1]: w=int(bet/2)
    if w: db.modify_balance(uid, w, "game")
    kb = get_bet_menu(f"slots_{th}", bet, uid)
    await c.message.answer(f"{'✅' if w else '❌'} +${w}", reply_markup=kb)

# --- VIDEO POKER ---
@dp.callback_query(F.data == "game_vpoker")
async def g_vp(c):
    uid=c.from_user.id; USER_BETS.setdefault(uid, 50)
    await c.message.edit_text("🃏 **POKER**", reply_markup=get_bet_menu("vpoker", USER_BETS[uid], uid))
@dp.callback_query(F.data.startswith("play_vpoker:"))
async def p_vp(c):
    bet=int(c.data.split(":")[1]); uid=c.from_user.id
    if db.get_user_data(uid)['bal']<bet: return
    db.modify_balance(uid, -bet, "wager")
    d=CasinoLogic.create_poker_deck(); hand=[d.pop() for _ in range(5)]
    name, mult = CasinoLogic.evaluate_poker_hand(hand)
    win = bet*mult
    if win: db.modify_balance(uid, win, "game")
    ht = " ".join([f"{x['rank']}{x['suit']}" for x in hand])
    kb=InlineKeyboardBuilder().add(InlineKeyboardButton(text="REJOUER", callback_data="game_vpoker"), InlineKeyboardButton(text="MENU", callback_data="home"))
    await c.message.edit_text(f"🃏 **{name}**\n{ht}\nGain: ${win}", reply_markup=kb.as_markup())

# --- ROULETTE ---
@dp.callback_query(F.data == "game_roulette")
async def g_rl(c):
    uid=c.from_user.id; USER_BETS.setdefault(uid, 50)
    await c.message.edit_text("🔴 **ROULETTE**", reply_markup=get_bet_menu("roulette", USER_BETS[uid], uid))
@dp.callback_query(F.data.startswith("play_rl:"))
async def p_rl(c):
    p=c.data.split(":"); ch=p[1]; bet=int(p[2]); uid=c.from_user.id
    if db.get_user_data(uid)['bal']<bet: return
    db.modify_balance(uid, -bet, "wager")
    await c.message.edit_text("🎲 ...")
    n=random.randint(0,36); col="green" if n==0 else "red" if n in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36] else "black"
    win = bet*2 if ch==col else bet*14 if ch=="green" and col=="green" else 0
    if win: db.modify_balance(uid, win, "game")
    kb=InlineKeyboardBuilder().add(InlineKeyboardButton(text="REJOUER", callback_data="game_roulette"), InlineKeyboardButton(text="MENU", callback_data="home"))
    await c.message.edit_text(f"Résultat: {col.upper()} **{n}**\n{'✅' if win else '❌'} +${win}", reply_markup=kb.as_markup())

# --- PLINKO ---
@dp.callback_query(F.data == "game_plinko")
async def g_pk(c): 
    uid=c.from_user.id; USER_BETS.setdefault(uid, 50)
    await c.message.edit_text("🎯 **PLINKO**", reply_markup=get_bet_menu("plinko", USER_BETS[uid], uid))
@dp.callback_query(F.data.startswith("play_plinko:"))
async def p_pk(c):
    bet=int(c.data.split(":")[1]); uid=c.from_user.id
    if db.get_user_data(uid)['bal']<bet: return
    db.modify_balance(uid, -bet, "wager")
    _, m = CasinoLogic.drop_plinko_ball()
    msg = await c.message.edit_text("🔴...")
    await asyncio.sleep(0.5)
    win = int(bet*m)
    if win: db.modify_balance(uid, win, "game")
    kb = InlineKeyboardBuilder().add(InlineKeyboardButton(text="REJOUER", callback_data="game_plinko")).add(InlineKeyboardButton(text="MENU", callback_data="home"))
    await msg.edit_text(f"🎯 **x{m}**\nGain: ${win}", reply_markup=kb.as_markup())

# --- KENO ---
@dp.callback_query(F.data == "game_keno")
async def g_kn(c): 
    uid=c.from_user.id; USER_BETS.setdefault(uid, 20)
    await c.message.edit_text("🔢 **KENO**", reply_markup=get_bet_menu("keno", USER_BETS[uid], uid))
@dp.callback_query(F.data.startswith("play_keno:"))
async def p_kn(c):
    bet = int(c.data.split(":")[1]); uid = c.from_user.id
    if db.get_user_data(uid)['bal'] < bet: return
    db.modify_balance(uid, -bet, "wager")
    up = set(random.sample(range(1, 81), 10)); hp = set(CasinoLogic.draw_keno_numbers())
    match = len(up.intersection(hp))
    win = bet * CasinoLogic.get_keno_payout(match)
    if win: db.modify_balance(uid, win, "game")
    kb = InlineKeyboardBuilder().add(InlineKeyboardButton(text="REJOUER", callback_data="game_keno")).add(InlineKeyboardButton(text="MENU", callback_data="home"))
    await c.message.edit_text(f"✅ Matchs: {match}/10\nGain: ${win}", reply_markup=kb.as_markup())

# --- RESTANTS (WHEEL, HILO, RPS, SPORTS, BACCARAT) ---
@dp.callback_query(F.data == "game_wheel")
async def g_wh(c): 
    uid=c.from_user.id; USER_BETS.setdefault(uid, 50)
    await c.message.edit_text("🎡 **ROUE**", reply_markup=get_bet_menu("wheel", USER_BETS[uid], uid))
@dp.callback_query(F.data.startswith("play_wheel:"))
async def p_wh(c):
    bet = int(c.data.split(":")[1]); uid = c.from_user.id
    if db.get_user_data(uid)['bal'] < bet: return
    db.modify_balance(uid, -bet, "wager")
    msg = await c.message.edit_text("🎡 Tourne...")
    await asyncio.sleep(1)
    mult = CasinoLogic.spin_wheel()
    win = bet * mult
    db.modify_balance(uid, win, "game")
    kb = InlineKeyboardBuilder().add(InlineKeyboardButton(text="REJOUER", callback_data="game_wheel")).add(InlineKeyboardButton(text="MENU", callback_data="home"))
    await msg.edit_text(f"💎 **x{mult}**\nGain: ${win}", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "game_hilo")
async def g_hl(c):
    uid=c.from_user.id; USER_BETS.setdefault(uid, 50)
    await c.message.edit_text("📈 **HIGH-LOW**", reply_markup=get_bet_menu("hilo", USER_BETS[uid], uid))
@dp.callback_query(F.data.startswith("start_hilo:"))
async def s_hl(c):
    bet = int(c.data.split(":")[1]); uid = c.from_user.id
    if db.get_user_data(uid)['bal'] < bet: return
    db.modify_balance(uid, -bet, "wager")
    d = CasinoLogic.get_blackjack_deck(); curr = d.pop()
    GAMES[uid] = {"t": "hilo", "d": d, "c": curr, "b": bet, "s": 1}
    await render_hilo(c, uid)
async def render_hilo(c, uid, win=False, lose=False):
    g=GAMES[uid]; txt=f"{g['c']['rank']}{g['c']['suit']}"
    if lose: 
        await c.message.edit_text(f"📈 Carte: {txt}\n❌ PERDU", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="MENU", callback_data="home")]]))
        del GAMES[uid]
    else:
        pot = g['b'] * (1.3 ** g['s'])
        kb = InlineKeyboardBuilder().row(InlineKeyboardButton(text="🔼 PLUS", callback_data="hl_high"), InlineKeyboardButton(text="🔽 MOINS", callback_data="hl_low"))
        if win: kb.row(InlineKeyboardButton(text=f"💰 CASH ${pot:.0f}", callback_data="hl_out"))
        await c.message.edit_text(f"📈 Carte: {txt}\nGain potentiel: ${pot:.2f}", reply_markup=kb.as_markup())
@dp.callback_query(F.data.startswith("hl_"))
async def p_hl(c):
    act = c.data.split("_")[1]; uid = c.from_user.id; g = GAMES.get(uid)
    if act == "out": 
        db.modify_balance(uid, g['b']*(1.3**g['s']), "game"); await home(c); return
    nx = g['d'].pop()
    ranks = ['2','3','4','5','6','7','8','9','10','J','Q','K','A']
    old_v = ranks.index(g['c']['rank']); new_v = ranks.index(nx['rank'])
    g['c'] = nx
    if (act=="high" and new_v>=old_v) or (act=="low" and new_v<=old_v): g['s']+=1; await render_hilo(c, uid, True)
    else: await render_hilo(c, uid, False, True)

@dp.callback_query(F.data == "game_rps")
async def g_rps(c): 
    uid=c.from_user.id; USER_BETS.setdefault(uid, 50)
    await c.message.edit_text("✊ **SHIFUMI**", reply_markup=get_bet_menu("rps", USER_BETS[uid], uid))
@dp.callback_query(F.data.startswith("play_rps:"))
async def p_rps(c):
    _, p, b_s = c.data.split(":"); bet = int(b_s); uid = c.from_user.id
    if db.get_user_data(uid)['bal'] < bet: return
    db.modify_balance(uid, -bet, "wager")
    o = random.choice(['r','p','s']); w = 0
    if (p=='r' and o=='s') or (p=='p' and o=='r') or (p=='s' and o=='p'): w = bet * 2
    elif p==o: w = bet
    if w: db.modify_balance(uid, w, "game")
    kb = InlineKeyboardBuilder().add(InlineKeyboardButton(text="REJOUER", callback_data="game_rps"), InlineKeyboardButton(text="MENU", callback_data="home"))
    await c.message.edit_text(f"Bot: {o}\n{'✅ GAGNÉ' if w>bet else '🤝 EGAL' if w==bet else '❌ PERDU'}", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "game_bacc")
async def g_bc(c): 
    uid=c.from_user.id; USER_BETS.setdefault(uid, 50)
    await c.message.edit_text("🎩 **BACCARAT**", reply_markup=get_bet_menu("bacc", USER_BETS[uid], uid))
@dp.callback_query(F.data.startswith("play_bacc:"))
async def p_bc(c):
    p=c.data.split(":"); ch=p[1]; bet=int(p[2]); uid=c.from_user.id
    if db.get_user_data(uid)['bal'] < bet: return
    db.modify_balance(uid, -bet, "wager")
    d = CasinoLogic.get_blackjack_deck()
    ph = [d.pop(), d.pop()]; bh = [d.pop(), d.pop()]
    ps = CasinoLogic.calculate_bacc_score(ph); bs = CasinoLogic.calculate_bacc_score(bh)
    winner = "T" if ps == bs else "P" if ps > bs else "B"
    win = bet * 9 if ch == winner and ch == "T" else bet * 2 if ch == winner else 0
    if win: db.modify_balance(uid, win, "game")
    kb = InlineKeyboardBuilder().add(InlineKeyboardButton(text="REJOUER", callback_data="game_bacc"), InlineKeyboardButton(text="MENU", callback_data="home"))
    await c.message.edit_text(f"🎩 P:{ps} | B:{bs}\n{'✅' if win else '❌'} +${win}", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "game_sports")
async def g_dice(c):
    uid=c.from_user.id; USER_BETS.setdefault(uid, 50)
    await c.message.edit_text("🎲 **DÉS** (4+ gagne)", reply_markup=get_bet_menu("dice", USER_BETS[uid], uid))
@dp.callback_query(F.data.startswith("play_dice:"))
async def p_dice(c):
    bet = int(c.data.split(":")[1]); uid = c.from_user.id
    if db.get_user_data(uid)['bal'] < bet: return
    db.modify_balance(uid, -bet, "wager")
    m = await c.message.answer_dice()
    await asyncio.sleep(4); w = bet * 2 if m.dice.value >= 4 else 0
    if w: db.modify_balance(uid, w, "game")
    await c.message.answer(f"{'✅' if w else '❌'} +${w}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="MENU", callback_data="home")]]))

# ==============================================================================
# MAIN
# ==============================================================================
async def main():
    print("--- OLYMPUS FINAL CUT ONLINE ---")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
