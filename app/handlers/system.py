import asyncio
import random
from aiogram import types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

from app.utils.database import DatabaseManager
from app.utils.keyboards import get_main_menu, get_bet_menu
from app.config import ADMIN_ID


class SystemHandlers:
    """Gestionnaires système (accueil, admin, coffre, bonus)"""
    
    def __init__(self, dp, db):
        self.dp = dp
        self.db = db
        self.user_input_context = {}
        self.user_bets = {}
        self.user_crash_targets = {}
        self.crash_history = [1.00, 2.50, 1.10, 5.00, 1.20]
        self.games_state = {}  # État des jeux complexes
        self.register_handlers()
    
    def get_correct_bet_menu(self, game, bet, uid):
        """Construit le menu de mise avec les bons paramètres selon le jeu"""
        crash_target = None
        crash_history = None
        
        if game == "crash":
            crash_target = self.user_crash_targets.get(uid, 2.0)
            crash_history = self.crash_history
        
        return get_bet_menu(game, bet, uid, crash_target, crash_history)
    
    def register_handlers(self):
        @self.dp.message(lambda m: m.text == "/start" or m.text == "/start@olympuscasinobot")
        async def start(m: types.Message):
            u = self.db.get_user_data(m.from_user.id, m.from_user.first_name)
            await m.answer(get_main_menu(u)[0], reply_markup=get_main_menu(u)[1], parse_mode="Markdown")

        @self.dp.callback_query(F.data == "home")
        async def home(c: types.CallbackQuery):
            if c.from_user.id in self.user_input_context:
                del self.user_input_context[c.from_user.id]
            u = self.db.get_user_data(c.from_user.id)
            try:
                await c.message.edit_text(get_main_menu(u)[0], reply_markup=get_main_menu(u)[1], parse_mode="Markdown")
            except TelegramBadRequest:
                await c.answer()

        @self.dp.callback_query(F.data == "refill")
        async def refill(c: types.CallbackQuery):
            u = self.db.get_user_data(c.from_user.id)
            if u['bal'] < 100:
                self.db.modify_balance(u['id'], 1000)
                await c.answer("✅ +1000$ crédités !", show_alert=True)
                await home(c)
            else:
                await c.answer("❌ Assez d'argent !", show_alert=True)

        # --- ADMIN ---
        @self.dp.message(lambda m: m.text and m.text.startswith("/create_code"))
        async def admin_code(m: types.Message):
            if m.from_user.id != ADMIN_ID:
                return
            try:
                args = m.text.split()[1:]
                if len(args) >= 3 and self.db.create_coupon(args[0], float(args[1]), int(args[2])):
                    await m.answer(f"✅ Code {args[0]} créé.")
            except:
                await m.answer("Format: /create_code CODE MONTANT USES")

        @self.dp.message(lambda m: m.text and m.text.startswith("/add_money"))
        async def admin_money(m: types.Message):
            if m.from_user.id != ADMIN_ID:
                return
            try:
                args = m.text.split()[1:]
                if len(args) >= 2:
                    self.db.modify_balance(int(args[0]), float(args[1]), "admin")
                    await m.answer("✅")
            except:
                await m.answer("Format: /add_money ID MONTANT")

        # --- COFFRE & BONUS & LEADERBOARD ---
        @self.dp.callback_query(F.data == "daily_bonus")
        async def daily(c):
            ok, amt, msg = self.db.claim_daily_bonus(c.from_user.id)
            await c.answer(f"🎁 +${amt} ({msg})" if ok else f"⏳ {msg}", show_alert=True)

        @self.dp.callback_query(F.data == "menu_vault")
        async def vault_m(c):
            u = self.db.get_user_data(c.from_user.id)
            txt = f"🏦 **COFFRE**\nDispo: ${u['bal']:.2f}\nCoffre: ${u['vault']:.2f}"
            kb = InlineKeyboardBuilder()
            kb.row(InlineKeyboardButton(text="📥 50%", callback_data="v_d_50"), InlineKeyboardButton(text="📥 TOUT", callback_data="v_d_all"))
            kb.row(InlineKeyboardButton(text="📤 50%", callback_data="v_w_50"), InlineKeyboardButton(text="📤 TOUT", callback_data="v_w_all"))
            kb.row(InlineKeyboardButton(text="🔙", callback_data="home"))
            await c.message.edit_text(txt, reply_markup=kb.as_markup(), parse_mode="Markdown")

        @self.dp.callback_query(F.data.startswith("v_"))
        async def vault_act(c):
            p = c.data.split("_")
            act = "deposit" if p[1] == "d" else "withdraw"
            u = self.db.get_user_data(c.from_user.id)
            src = u['bal'] if act == "deposit" else u['vault']
            amt = int(src) if p[2] == "all" else int(src/2)
            if amt > 0 and self.db.process_vault_transaction(u['id'], amt, act):
                await vault_m(c)
            else:
                await c.answer("Erreur")

        @self.dp.callback_query(F.data == "leaderboard")
        async def lead(c):
            top = self.db.get_leaderboard()
            txt = "🏆 **TOP RICHESSE**\n\n"
            for i, p in enumerate(top):
                med = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"#{i+1}"
                txt += f"{med} **{p[0]}** — ${p[1]:,.2f}\n"
            kb = InlineKeyboardBuilder().add(InlineKeyboardButton(text="🔙", callback_data="home"))
            await c.message.edit_text(txt, reply_markup=kb.as_markup(), parse_mode="Markdown")

        @self.dp.callback_query(F.data == "menu_coupon")
        async def menu_code(c):
            await c.message.edit_text("🎟️ **CODE PROMO**\nEntrez votre code :", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙", callback_data="home")]]))
            self.user_input_context[c.from_user.id] = "coupon"

        # --- SAISIE TEXTE ---
        @self.dp.callback_query(F.data.startswith("manual_in_"))
        async def manual_trig(c):
            game = c.data.replace("manual_in_", "")
            self.user_input_context[c.from_user.id] = f"bet_{game}"
            await c.answer("⌨️ Tapez le montant !", show_alert=True)

        @self.dp.message(F.text)
        async def text_input(m: types.Message):
            uid = m.from_user.id
            ctx = self.user_input_context.get(uid)
            if not ctx:
                return

            if ctx == "coupon":
                ok, msg = self.db.redeem_coupon(uid, m.text.strip())
                del self.user_input_context[uid]
                await m.answer(f"{'✅' if ok else '❌'} {msg}")
                return

            if ctx.startswith("bet_"):
                game = ctx.replace("bet_", "")
                text_input = m.text.strip()
                u = self.db.get_user_data(uid)
                
                # Validation 1: Vérifie que c'est bien un nombre
                if not text_input.isdigit():
                    await m.answer("❌ Vous devez entrer un nombre valide")
                    return
                
                amt = int(text_input)
                balance = int(u['bal'])
                
                # Validation 2: Vérifie le minimum
                if amt < 10:
                    await m.answer("❌ Montant minimum: 10$")
                    return
                
                # Validation 3: Vérifie le maximum (solde du joueur)
                if amt > balance:
                    await m.answer(f"❌ Vous n'avez que ${balance}$")
                    return
                
                # Validation 4: Limite de chiffres basée sur le solde
                max_chiffres = len(str(balance))
                if len(text_input) > max_chiffres:
                    await m.answer(f"❌ Montant trop élevé (max {balance}$)")
                    return
                
                self.user_bets[uid] = amt
                del self.user_input_context[uid]
                try:
                    await m.delete()
                except:
                    pass
                msg = await m.answer(f"✅ Mise fixée à **${amt}**")
                await asyncio.sleep(1)
                try:
                    await msg.delete()
                except:
                    pass
                await m.answer(f"🎮 **{game.upper()}**", reply_markup=self.get_correct_bet_menu(game, amt, uid), parse_mode="Markdown")

        # --- MISE BOUTONS ---
        @self.dp.callback_query(F.data.startswith("b_"))
        async def bet_btn(c):
            p = c.data.split("_")
            act = p[1]
            val = p[2]
            game = "_".join(p[3:])
            uid = c.from_user.id
            curr = self.user_bets.get(uid, 50)
            u = self.db.get_user_data(uid)
            
            if act == "add":
                curr += int(val)
            elif act == "sub":
                curr = max(10, curr - int(val))
            elif act == "mul":
                curr *= 2
            elif act == "div":
                curr = max(10, curr // 2)
            elif act == "set":
                curr = 10
            elif act == "max":
                curr = int(u['bal'])
            
            if curr > u['bal']:
                curr = int(u['bal'])
            if curr < 10:
                curr = 10
            self.user_bets[uid] = curr
            
            # Utilise la méthode helper pour construire le bon menu
            await c.message.edit_reply_markup(reply_markup=self.get_correct_bet_menu(game, curr, uid))
