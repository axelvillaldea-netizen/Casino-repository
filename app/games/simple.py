import asyncio
import random
from aiogram import types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.utils.casino_logic import CasinoLogic
from app.utils.keyboards import get_bet_menu


class SimplGames:
    """Jeux simples et rapides"""
    
    def __init__(self, dp, db):
        self.dp = dp
        self.db = db
        self.register_handlers()
    
    def register_handlers(self):
        # --- COINFLIP ---
        @self.dp.callback_query(F.data == "game_coin")
        async def g_coin(c):
            uid = c.from_user.id
            await c.message.edit_text("🪙 **PILE OU FACE**", reply_markup=get_bet_menu("coin", 50, uid))

        @self.dp.callback_query(F.data.startswith("play_coin:"))
        async def p_coin(c):
            p = c.data.split(":")
            pk = p[1]
            bet = int(p[2])
            uid = c.from_user.id
            if self.db.get_user_data(uid)['bal'] < bet:
                return
            self.db.modify_balance(uid, -bet, "wager")
            msg = await c.message.edit_text("🪙 ...")
            await asyncio.sleep(1)
            res = random.choice(["pile", "face"])
            w = bet * 2 if res == pk else 0
            if w:
                self.db.modify_balance(uid, w, "game")
            kb = InlineKeyboardBuilder().add(InlineKeyboardButton(text="REJOUER", callback_data="game_coin"), InlineKeyboardButton(text="MENU", callback_data="home"))
            await msg.edit_text(f"Résultat: {res.upper()}\n{'✅ +$' + str(w) if w else '❌'}", reply_markup=kb.as_markup())

        # --- ROULETTE ---
        @self.dp.callback_query(F.data == "game_roulette")
        async def g_rl(c):
            uid = c.from_user.id
            await c.message.edit_text("🔴 **ROULETTE**", reply_markup=get_bet_menu("roulette", 50, uid))

        @self.dp.callback_query(F.data.startswith("play_rl:"))
        async def p_rl(c):
            p = c.data.split(":")
            ch = p[1]
            bet = int(p[2])
            uid = c.from_user.id
            if self.db.get_user_data(uid)['bal'] < bet:
                return
            self.db.modify_balance(uid, -bet, "wager")
            await c.message.edit_text("🎲 ...")
            n = random.randint(0, 36)
            col = "green" if n == 0 else "red" if n in [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36] else "black"
            win = bet * 2 if ch == col else bet * 14 if ch == "green" and col == "green" else 0
            if win:
                self.db.modify_balance(uid, win, "game")
            kb = InlineKeyboardBuilder().add(InlineKeyboardButton(text="REJOUER", callback_data="game_roulette"), InlineKeyboardButton(text="MENU", callback_data="home"))
            await c.message.edit_text(f"Résultat: {col.upper()} **{n}**\n{'✅' if win else '❌'} +${win}", reply_markup=kb.as_markup())

        # --- SHIFUMI (PIERRE-PAPIER-CISEAUX) ---
        @self.dp.callback_query(F.data == "game_rps")
        async def g_rps(c):
            uid = c.from_user.id
            await c.message.edit_text("✊ **SHIFUMI**", reply_markup=get_bet_menu("rps", 50, uid))

        @self.dp.callback_query(F.data.startswith("play_rps:"))
        async def p_rps(c):
            _, p, b_s = c.data.split(":")
            bet = int(b_s)
            uid = c.from_user.id
            if self.db.get_user_data(uid)['bal'] < bet:
                return
            self.db.modify_balance(uid, -bet, "wager")
            o = random.choice(['r', 'p', 's'])
            w = 0
            if (p == 'r' and o == 's') or (p == 'p' and o == 'r') or (p == 's' and o == 'p'):
                w = bet * 2
            elif p == o:
                w = bet
            if w:
                self.db.modify_balance(uid, w, "game")
            kb = InlineKeyboardBuilder().add(InlineKeyboardButton(text="REJOUER", callback_data="game_rps"), InlineKeyboardButton(text="MENU", callback_data="home"))
            await c.message.edit_text(f"Bot: {o}\n{'✅ GAGNÉ' if w > bet else '🤝 EGAL' if w == bet else '❌ PERDU'}", reply_markup=kb.as_markup())

        # --- DÉS ---
        @self.dp.callback_query(F.data == "game_sports")
        async def g_dice(c):
            uid = c.from_user.id
            await c.message.edit_text("🎲 **DÉS** (4+ gagne)", reply_markup=get_bet_menu("dice", 50, uid))

        @self.dp.callback_query(F.data.startswith("play_dice:"))
        async def p_dice(c):
            bet = int(c.data.split(":")[1])
            uid = c.from_user.id
            if self.db.get_user_data(uid)['bal'] < bet:
                return
            self.db.modify_balance(uid, -bet, "wager")
            m = await c.message.answer_dice()
            await asyncio.sleep(4)
            w = bet * 2 if m.dice.value >= 4 else 0
            if w:
                self.db.modify_balance(uid, w, "game")
            await c.message.answer(f"{'✅' if w else '❌'} +${w}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="MENU", callback_data="home")]]))
