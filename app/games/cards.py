import asyncio
from aiogram import types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.utils.casino_logic import CasinoLogic
from app.utils.keyboards import get_bet_menu


class CardGames:
    """Jeux de cartes (Blackjack, Baccarat, Video Poker)"""
    
    def __init__(self, dp, db):
        self.dp = dp
        self.db = db
        self.games = {}
        self.register_handlers()
    
    def register_handlers(self):
        # --- BLACKJACK ---
        @self.dp.callback_query(F.data == "game_bj")
        async def g_bj(c):
            uid = c.from_user.id
            await c.message.edit_text("🃏 **BLACKJACK**", reply_markup=get_bet_menu("bj", 50, uid))

        @self.dp.callback_query(F.data.startswith("start_bj:"))
        async def s_bj(c):
            bet = int(c.data.split(":")[1])
            uid = c.from_user.id
            if self.db.get_user_data(uid)['bal'] < bet:
                return
            self.db.modify_balance(uid, -bet, "wager")
            d = CasinoLogic.get_blackjack_deck()
            self.games[uid] = {"t": "bj", "d": d, "ph": [d.pop(), d.pop()], "dh": [d.pop(), d.pop()], "b": bet}
            await self._render_bj(c, uid)

        @self.dp.callback_query(F.data == "bjh")
        async def bjh(c):
            g = self.games[c.from_user.id]
            g['ph'].append(g['d'].pop())
            if CasinoLogic.calculate_blackjack_score(g['ph']) > 21:
                await self._render_bj(c, c.from_user.id, True, 0)
            else:
                await self._render_bj(c, c.from_user.id)

        @self.dp.callback_query(F.data == "bjs")
        async def bjs(c):
            await self._bj_dealer_turn(c, c.from_user.id)

        @self.dp.callback_query(F.data == "bjd")
        async def bjd(c):
            uid = c.from_user.id
            g = self.games[uid]
            self.db.modify_balance(uid, -g['b'], "wager")
            g['b'] *= 2
            g['ph'].append(g['d'].pop())
            if CasinoLogic.calculate_blackjack_score(g['ph']) > 21:
                await self._render_bj(c, uid, True, 0)
            else:
                await self._bj_dealer_turn(c, uid)

        # --- VIDEO POKER ---
        @self.dp.callback_query(F.data == "game_vpoker")
        async def g_vp(c):
            uid = c.from_user.id
            await c.message.edit_text("🃏 **POKER**", reply_markup=get_bet_menu("vpoker", 50, uid))

        @self.dp.callback_query(F.data.startswith("play_vpoker:"))
        async def p_vp(c):
            bet = int(c.data.split(":")[1])
            uid = c.from_user.id
            if self.db.get_user_data(uid)['bal'] < bet:
                return
            self.db.modify_balance(uid, -bet, "wager")
            d = CasinoLogic.create_poker_deck()
            hand = [d.pop() for _ in range(5)]
            name, mult = CasinoLogic.evaluate_poker_hand(hand)
            win = bet * mult
            if win:
                self.db.modify_balance(uid, win, "game")
            ht = " ".join([f"{x['rank']}{x['suit']}" for x in hand])
            kb = InlineKeyboardBuilder().add(InlineKeyboardButton(text="REJOUER", callback_data="game_vpoker"), InlineKeyboardButton(text="MENU", callback_data="home"))
            await c.message.edit_text(f"🃏 **{name}**\n{ht}\nGain: ${win}", reply_markup=kb.as_markup())

        # --- BACCARAT ---
        @self.dp.callback_query(F.data == "game_bacc")
        async def g_bc(c):
            uid = c.from_user.id
            await c.message.edit_text("🎩 **BACCARAT**", reply_markup=get_bet_menu("bacc", 50, uid))

        @self.dp.callback_query(F.data.startswith("play_bacc:"))
        async def p_bc(c):
            p = c.data.split(":")
            ch = p[1]
            bet = int(p[2])
            uid = c.from_user.id
            if self.db.get_user_data(uid)['bal'] < bet:
                return
            self.db.modify_balance(uid, -bet, "wager")
            d = CasinoLogic.get_blackjack_deck()
            ph = [d.pop(), d.pop()]
            bh = [d.pop(), d.pop()]
            ps = CasinoLogic.calculate_blackjack_score(ph)
            bs = CasinoLogic.calculate_blackjack_score(bh)
            winner = "T" if ps == bs else "P" if ps > bs else "B"
            win = bet * 9 if ch == winner and ch == "T" else bet * 2 if ch == winner else 0
            if win:
                self.db.modify_balance(uid, win, "game")
            kb = InlineKeyboardBuilder().add(InlineKeyboardButton(text="REJOUER", callback_data="game_bacc"), InlineKeyboardButton(text="MENU", callback_data="home"))
            await c.message.edit_text(f"🎩 P:{ps} | B:{bs}\n{'✅' if win else '❌'} +${win}", reply_markup=kb.as_markup())

    async def _render_bj(self, c, uid, over=False, win=0):
        g = self.games[uid]
        ps = CasinoLogic.calculate_blackjack_score(g['ph'])
        pt = " ".join([f"{x['rank']}{x['suit']}" for x in g['ph']])
        if not over:
            dt = f"{g['dh'][0]['rank']}{g['dh'][0]['suit']} 🎴"
            kb = InlineKeyboardBuilder().row(InlineKeyboardButton(text="HIT", callback_data="bjh"), InlineKeyboardButton(text="STAND", callback_data="bjs"))
            if len(g['ph']) == 2:
                kb.row(InlineKeyboardButton(text="DOUBLE", callback_data="bjd"))
            await c.message.edit_text(f"🃏 **BJ** (${g['b']})\n🤵 {dt}\n👤 {pt} ({ps})", reply_markup=kb.as_markup())
        else:
            ds = CasinoLogic.calculate_blackjack_score(g['dh'])
            dt = " ".join([f"{x['rank']}{x['suit']}" for x in g['dh']])
            st = "✅" if win > g['b'] else "🤝" if win == g['b'] else "❌"
            kb = InlineKeyboardBuilder().add(InlineKeyboardButton(text="REJOUER", callback_data="game_bj"), InlineKeyboardButton(text="MENU", callback_data="home"))
            await c.message.edit_text(f"🏁 {st} (${win})\n🤵 {dt} ({ds})\n👤 {pt} ({ps})", reply_markup=kb.as_markup())
            del self.games[uid]

    async def _bj_dealer_turn(self, c, uid):
        g = self.games[uid]
        while CasinoLogic.calculate_blackjack_score(g['dh']) < 17:
            g['dh'].append(g['d'].pop())
        ps, ds = CasinoLogic.calculate_blackjack_score(g['ph']), CasinoLogic.calculate_blackjack_score(g['dh'])
        w = 0
        if ds > 21 or ps > ds:
            w = g['b'] * 2
        elif ps == ds:
            w = g['b']
        if w:
            self.db.modify_balance(uid, w, "game")
        await self._render_bj(c, uid, True, w)
