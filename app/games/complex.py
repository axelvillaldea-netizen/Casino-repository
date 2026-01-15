import asyncio
import random
from aiogram import types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.utils.casino_logic import CasinoLogic
from app.utils.keyboards import get_bet_menu


class ComplexGames:
    """Jeux complexes (Mines, Tower, Horse, etc)"""
    
    def __init__(self, dp, db):
        self.dp = dp
        self.db = db
        self.games = {}
        self.register_handlers()
    
    def register_handlers(self):
        # --- MINES ---
        @self.dp.callback_query(F.data == "game_mines")
        async def g_mines(c):
            uid = c.from_user.id
            await c.message.edit_text("💣 **MINES**", reply_markup=get_bet_menu("mines", 20, uid))

        @self.dp.callback_query(F.data.startswith("start_mines:"))
        async def s_mines(c):
            bet = int(c.data.split(":")[1])
            uid = c.from_user.id
            if self.db.get_user_data(uid)['bal'] < bet:
                return
            self.db.modify_balance(uid, -bet, "wager")
            self.games[uid] = {"t": "mines", "grid": CasinoLogic.create_mines_grid(3), "bet": bet, "rev": [], "on": True}
            await self._render_mines(c, uid)

        @self.dp.callback_query(F.data.startswith("mi:"))
        async def mi_c(c):
            uid = c.from_user.id
            idx = int(c.data.split(":")[1])
            g = self.games.get(uid)
            if not g or not g['on']:
                return
            if g['grid'][idx]:
                await self._render_mines(c, uid, boom=True)
            else:
                g['rev'].append(idx)
                await self._render_mines(c, uid)

        @self.dp.callback_query(F.data == "mi_out")
        async def mi_o(c):
            uid = c.from_user.id
            g = self.games.get(uid)
            if g:
                w = g['bet'] * CasinoLogic.get_mines_multiplier(3, len(g['rev']))
                self.db.modify_balance(uid, w, "game")
                await self._render_mines(c, uid, cash=True)

        # --- TOWER ---
        @self.dp.callback_query(F.data == "game_tower")
        async def g_tower(c):
            uid = c.from_user.id
            await c.message.edit_text("🗼 **TOWER**\nMontez sans tomber !", reply_markup=get_bet_menu("tower", 20, uid))

        @self.dp.callback_query(F.data.startswith("start_tower:"))
        async def s_tower(c):
            bet = int(c.data.split(":")[1])
            uid = c.from_user.id
            if self.db.get_user_data(uid)['bal'] < bet:
                return
            self.db.modify_balance(uid, -bet, "wager")
            self.games[uid] = {"t": "tower", "lvl": 1, "row": CasinoLogic.generate_tower_row(), "bet": bet, "on": True}
            await self._render_tower(c, uid)

        @self.dp.callback_query(F.data.startswith("tc:"))
        async def tc(c):
            uid = c.from_user.id
            idx = int(c.data.split(":")[1])
            g = self.games.get(uid)
            if not g or not g['on']:
                return
            if g['row'][idx] == 1:
                await self._render_tower(c, uid, lost=True)
            else:
                g['lvl'] += 1
                g['row'] = CasinoLogic.generate_tower_row()
                if g['lvl'] > 8:
                    await self._render_tower(c, uid, cash=True)
                else:
                    await self._render_tower(c, uid)

        @self.dp.callback_query(F.data == "tout")
        async def tout(c):
            await self._render_tower(c, c.from_user.id, cash=True)

        # --- HORSE ---
        @self.dp.callback_query(F.data == "game_horse")
        async def g_horse(c):
            uid = c.from_user.id
            await c.message.edit_text("🐎 **COURSES**", reply_markup=get_bet_menu("horse", 50, uid))

        @self.dp.callback_query(F.data.startswith("play_horse:"))
        async def p_horse(c):
            p = c.data.split(":")
            h_pk = int(p[1])
            bet = int(p[2])
            uid = c.from_user.id
            if self.db.get_user_data(uid)['bal'] < bet:
                return
            self.db.modify_balance(uid, -bet, "wager")
            msg = await c.message.edit_text("🏁 DÉPART...")
            frames, win_h = CasinoLogic.simulate_horse_race()
            emo = ["🔴", "🔵", "🟢", "🟡", "🟣"]
            for i, f in enumerate(frames):
                if i % 2 == 0 or i == len(frames) - 1:
                    t = "\n".join([f"{j+1} {emo[j]} " + ("." * p) for j, p in enumerate(f)])
                    try:
                        await msg.edit_text(f"🐎 COURSE\n{t}")
                        await asyncio.sleep(0.5)
                    except:
                        pass
            w = bet * 4 if win_h == h_pk else 0
            if w:
                self.db.modify_balance(uid, w, "game")
            await msg.edit_text(f"🏆 {emo[win_h]} Gagne !\n{'✅ +$' + str(w) if w else '❌ PERDU'}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="REJOUER", callback_data="game_horse"), InlineKeyboardButton(text="MENU", callback_data="home")]]))

        # --- PLINKO ---
        @self.dp.callback_query(F.data == "game_plinko")
        async def g_pk(c):
            uid = c.from_user.id
            await c.message.edit_text("🎯 **PLINKO**", reply_markup=get_bet_menu("plinko", 50, uid))

        @self.dp.callback_query(F.data.startswith("play_plinko:"))
        async def p_pk(c):
            bet = int(c.data.split(":")[1])
            uid = c.from_user.id
            if self.db.get_user_data(uid)['bal'] < bet:
                return
            self.db.modify_balance(uid, -bet, "wager")
            _, m = CasinoLogic.drop_plinko_ball()
            msg = await c.message.edit_text("🔴...")
            await asyncio.sleep(0.5)
            win = int(bet * m)
            if win:
                self.db.modify_balance(uid, win, "game")
            kb = InlineKeyboardBuilder().add(InlineKeyboardButton(text="REJOUER", callback_data="game_plinko")).add(InlineKeyboardButton(text="MENU", callback_data="home"))
            await msg.edit_text(f"🎯 **x{m}**\nGain: ${win}", reply_markup=kb.as_markup())

    async def _render_mines(self, c, uid, boom=False, cash=False):
        g = self.games[uid]
        kb = InlineKeyboardBuilder()
        for i in range(25):
            t = "🟦"
            cb = f"mi:{i}"
            if i in g['rev'] or boom or cash:
                t = "💣" if g['grid'][i] else "💎"
                cb = "ign"
            kb.add(InlineKeyboardButton(text=t, callback_data=cb))
        kb.adjust(5)
        if not boom and not cash:
            val = g['bet'] * CasinoLogic.get_mines_multiplier(3, len(g['rev']))
            kb.row(InlineKeyboardButton(text=f"💰 CASH ${val:.2f}", callback_data="mi_out"))
            await c.message.edit_text(f"Gain: ${val:.2f}", reply_markup=kb.as_markup())
        else:
            kb.row(InlineKeyboardButton(text="REJOUER", callback_data="game_mines"), InlineKeyboardButton(text="MENU", callback_data="home"))
            await c.message.edit_text("✅ GAGNÉ" if cash else "💥 PERDU", reply_markup=kb.as_markup())
            del self.games[uid]

    async def _render_tower(self, c, uid, lost=False, cash=False):
        g = self.games[uid]
        if lost:
            await c.message.edit_text(f"💥 **CHUTE !** (Étage {g['lvl']})", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="REJOUER", callback_data="game_tower"), InlineKeyboardButton(text="MENU", callback_data="home")]]))
            del self.games[uid]
        elif cash:
            w = g['bet'] * CasinoLogic.get_tower_multiplier(g['lvl'] - 1)
            self.db.modify_balance(uid, w, "game")
            await c.message.edit_text(f"✅ **ENCAISSÉ !** +${w:.2f}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="REJOUER", callback_data="game_tower"), InlineKeyboardButton(text="MENU", callback_data="home")]]))
            del self.games[uid]
        else:
            m = CasinoLogic.get_tower_multiplier(g['lvl'])
            kb = InlineKeyboardBuilder()
            for i in range(3):
                kb.add(InlineKeyboardButton(text="❓", callback_data=f"tc:{i}"))
            if g['lvl'] > 1:
                kb.row(InlineKeyboardButton(text="💰 CASH OUT", callback_data="tout"))
            await c.message.edit_text(f"🗼 Étage {g['lvl']} (Prochain: x{m})", reply_markup=kb.as_markup())
