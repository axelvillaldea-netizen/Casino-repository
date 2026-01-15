import sqlite3
from datetime import datetime, timedelta
from app.config import DB_NAME


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
