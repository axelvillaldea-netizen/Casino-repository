import asyncio
import random
from aiogram import types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.utils.casino_logic import CasinoLogic
from app.utils.keyboards import get_bet_menu


class CrashGame:
    """Jeu du Crash"""
    
    def __init__(self, dp, db, system_handlers=None):
        self.dp = dp
        self.db = db
        self.system_handlers = system_handlers
        self.register_handlers()
    
    def register_handlers(self):
        @self.dp.callback_query(F.data == "game_crash")
        async def g_crash(c):
            uid = c.from_user.id
            if self.system_handlers:
                if uid not in self.system_handlers.user_crash_targets:
                    self.system_handlers.user_crash_targets[uid] = 2.0
                crash_target = self.system_handlers.user_crash_targets[uid]
                crash_history = self.system_handlers.crash_history
            else:
                crash_target = 2.0
                crash_history = [1.00, 2.50, 1.10]
            await c.message.edit_text("🚀 **CRASH**", reply_markup=get_bet_menu("crash", 50, uid, crash_target, crash_history))

        @self.dp.callback_query(F.data.startswith("play_crash:"))
        async def p_crash(c):
            p = c.data.split(":")
            tgt = float(p[1])
            bet = int(p[2])
            uid = c.from_user.id
            if self.db.get_user_data(uid)['bal'] < bet:
                return
            self.db.modify_balance(uid, -bet, "wager")
            msg = await c.message.edit_text("🚀 1.00x")
            crash = CasinoLogic.get_crash_multiplier()
            if self.system_handlers:
                self.system_handlers.crash_history.append(crash)
                if len(self.system_handlers.crash_history) > 10:
                    self.system_handlers.crash_history.pop(0)
            curr = 1.0
            while curr < crash and curr < tgt:
                await asyncio.sleep(0.5)
                curr += random.uniform(0.1, 0.4)
                if curr > crash:
                    curr = crash
                try:
                    await msg.edit_text(f"🚀 {curr:.2f}x")
                except:
                    pass
            w = int(bet * tgt) if crash >= tgt else 0
            if w:
                self.db.modify_balance(uid, w, "game")
            kb = InlineKeyboardBuilder().add(InlineKeyboardButton(text="REJOUER", callback_data="game_crash"), InlineKeyboardButton(text="MENU", callback_data="home"))
            await msg.edit_text(f"{'✅' if w else '💥'} Crash: {crash}x\nGain: ${w}", reply_markup=kb.as_markup())

        @self.dp.callback_query(F.data.startswith("t_"))
        async def tgt_act(c):
            p = c.data.split("_")
            act = p[1]
            val = float(p[2])
            uid = c.from_user.id
            if self.system_handlers:
                curr = self.system_handlers.user_crash_targets.get(uid, 2.0)
                curr = curr + val if act == "add" else max(1.01, curr - val)
                self.system_handlers.user_crash_targets[uid] = round(curr, 2)
                crash_target = self.system_handlers.user_crash_targets[uid]
                crash_history = self.system_handlers.crash_history
                bet = self.system_handlers.user_bets.get(uid, 50)
            else:
                crash_target = 2.0
                crash_history = [1.00, 2.50, 1.10]
                bet = 50
            await c.message.edit_reply_markup(reply_markup=get_bet_menu("crash", bet, uid, crash_target, crash_history))
