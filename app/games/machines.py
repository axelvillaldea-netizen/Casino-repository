import asyncio
import random
from aiogram import types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.utils.casino_logic import CasinoLogic
from app.utils.keyboards import get_bet_menu


class MachineGames:
    """Jeux d'arcade (Slots, Keno, Wheel, High-Low, Scratch)"""
    
    def __init__(self, dp, db):
        self.dp = dp
        self.db = db
        self.games = {}
        self.register_handlers()
    
    def register_handlers(self):
        # --- SLOTS ---
        @self.dp.callback_query(F.data == "menu_slots")
        async def g_slots(c):
            kb = InlineKeyboardBuilder()
            for t in ["fruit", "egypt", "cyber"]:
                kb.add(InlineKeyboardButton(text=t.upper(), callback_data=f"slot_t:{t}"))
            kb.row(InlineKeyboardButton(text="🔙", callback_data="home"))
            await c.message.edit_text("🎰 Thème ?", reply_markup=kb.as_markup())

        @self.dp.callback_query(F.data.startswith("slot_t:"))
        async def s_t(c):
            th = c.data.split(":")[1]
            uid = c.from_user.id
            await c.message.edit_text(f"🎰 **{th.upper()}**", reply_markup=get_bet_menu(f"slots_{th}", 20, uid))

        @self.dp.callback_query(F.data.startswith("play_slots:"))
        async def s_p(c):
            p = c.data.split(":")
            th = p[1]
            bet = int(p[2])
            uid = c.from_user.id
            if self.db.get_user_data(uid)['bal'] < bet:
                return
            self.db.modify_balance(uid, -bet, "wager")
            res, syms = CasinoLogic.spin_slots(th)
            await c.message.edit_text(f"🎰 {res[0]}|{res[1]}|{res[2]}")
            w = 0
            if res[0] == res[1] == res[2]:
                w = bet * (100 if res[0] == syms[4] else 20)
            elif res[0] == res[1]:
                w = int(bet / 2)
            if w:
                self.db.modify_balance(uid, w, "game")
            kb = get_bet_menu(f"slots_{th}", bet, uid)
            await c.message.answer(f"{'✅' if w else '❌'} +${w}", reply_markup=kb)

        # --- SCRATCH ---
        @self.dp.callback_query(F.data == "menu_scratch")
        async def m_sc(c):
            kb = InlineKeyboardBuilder()
            kb.row(InlineKeyboardButton(text="SILVER ($10)", callback_data="play_scratch_silver:10"))
            kb.row(InlineKeyboardButton(text="GOLD ($50)", callback_data="play_scratch_gold:50"))
            kb.row(InlineKeyboardButton(text="DIAMOND ($100)", callback_data="play_scratch_diamond:100"))
            kb.row(InlineKeyboardButton(text="🔙", callback_data="home"))
            await c.message.edit_text("🎫 **GRATTAGE**\nChoisissez votre ticket :", reply_markup=kb.as_markup())

        @self.dp.callback_query(F.data.startswith("play_scratch_"))
        async def p_sc(c):
            p = c.data.split(":")
            type = p[0].replace("play_scratch_", "")
            bet = int(p[1])
            uid = c.from_user.id
            if self.db.get_user_data(uid)['bal'] < bet:
                return
            self.db.modify_balance(uid, -bet, "wager")
            
            msg = await c.message.edit_text("🎫 Grattage en cours... ▒▒▒")
            await asyncio.sleep(1)
            
            if type == "silver":
                syms = ["🍒", "🍋", "🔔", "❌", "❌"]
                mult = 5
            elif type == "gold":
                syms = ["💰", "💎", "💵", "❌", "❌"]
                mult = 15
            else:
                syms = ["👑", "💍", "7️⃣", "❌", "❌", "❌"]
                mult = 50
                
            grid = random.choices(syms, k=9)
            
            win = 0
            match = None
            counts = {x: grid.count(x) for x in grid if x != "❌"}
            
            for s, count in counts.items():
                if count >= 3:
                    match = s
                    win = bet * mult
                    break
                    
            if win:
                self.db.modify_balance(uid, win, "game")
            
            gt = "\n".join([" ".join(grid[i:i+3]) for i in range(0, 9, 3)])
            res = f"✅ **GAGNÉ !** (3x {match}) +${win}" if win else "❌ **PERDU**"
            
            kb = InlineKeyboardBuilder().add(InlineKeyboardButton(text="REJOUER", callback_data="menu_scratch"), InlineKeyboardButton(text="MENU", callback_data="home"))
            await msg.edit_text(f"🎫 **TICKET {type.upper()}**\n\n{gt}\n\n{res}", reply_markup=kb.as_markup())

        # --- KENO ---
        @self.dp.callback_query(F.data == "game_keno")
        async def g_kn(c):
            uid = c.from_user.id
            await c.message.edit_text("🔢 **KENO**", reply_markup=get_bet_menu("keno", 20, uid))

        @self.dp.callback_query(F.data.startswith("play_keno:"))
        async def p_kn(c):
            bet = int(c.data.split(":")[1])
            uid = c.from_user.id
            if self.db.get_user_data(uid)['bal'] < bet:
                return
            self.db.modify_balance(uid, -bet, "wager")
            up = set(random.sample(range(1, 81), 10))
            hp = set(CasinoLogic.draw_keno_numbers())
            match = len(up.intersection(hp))
            win = bet * CasinoLogic.get_keno_payout(match)
            if win:
                self.db.modify_balance(uid, win, "game")
            kb = InlineKeyboardBuilder().add(InlineKeyboardButton(text="REJOUER", callback_data="game_keno")).add(InlineKeyboardButton(text="MENU", callback_data="home"))
            await c.message.edit_text(f"✅ Matchs: {match}/10\nGain: ${win}", reply_markup=kb.as_markup())

        # --- WHEEL ---
        @self.dp.callback_query(F.data == "game_wheel")
        async def g_wh(c):
            uid = c.from_user.id
            await c.message.edit_text("🎡 **ROUE**", reply_markup=get_bet_menu("wheel", 50, uid))

        @self.dp.callback_query(F.data.startswith("play_wheel:"))
        async def p_wh(c):
            bet = int(c.data.split(":")[1])
            uid = c.from_user.id
            if self.db.get_user_data(uid)['bal'] < bet:
                return
            self.db.modify_balance(uid, -bet, "wager")
            msg = await c.message.edit_text("🎡 Tourne...")
            await asyncio.sleep(1)
            mult = CasinoLogic.spin_wheel()
            win = bet * mult
            self.db.modify_balance(uid, win, "game")
            kb = InlineKeyboardBuilder().add(InlineKeyboardButton(text="REJOUER", callback_data="game_wheel")).add(InlineKeyboardButton(text="MENU", callback_data="home"))
            await msg.edit_text(f"💎 **x{mult}**\nGain: ${win}", reply_markup=kb.as_markup())

        # --- HIGH-LOW ---
        @self.dp.callback_query(F.data == "game_hilo")
        async def g_hl(c):
            uid = c.from_user.id
            await c.message.edit_text("📈 **HIGH-LOW**", reply_markup=get_bet_menu("hilo", 50, uid))

        @self.dp.callback_query(F.data.startswith("start_hilo:"))
        async def s_hl(c):
            bet = int(c.data.split(":")[1])
            uid = c.from_user.id
            if self.db.get_user_data(uid)['bal'] < bet:
                return
            self.db.modify_balance(uid, -bet, "wager")
            d = CasinoLogic.get_blackjack_deck()
            curr = d.pop()
            self.games[uid] = {"t": "hilo", "d": d, "c": curr, "b": bet, "s": 1}
            await self._render_hilo(c, uid)

        @self.dp.callback_query(F.data.startswith("hl_"))
        async def p_hl(c):
            act = c.data.split("_")[1]
            uid = c.from_user.id
            g = self.games.get(uid)
            if not g:
                return
            if act == "out":
                self.db.modify_balance(uid, g['b'] * (1.3 ** g['s']), "game")
                # Go back to home
                await c.message.edit_text("✅ Gains encaissés!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="MENU", callback_data="home")]]))
                del self.games[uid]
                return
            nx = g['d'].pop()
            ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
            old_v = ranks.index(g['c']['rank'])
            new_v = ranks.index(nx['rank'])
            g['c'] = nx
            if (act == "high" and new_v >= old_v) or (act == "low" and new_v <= old_v):
                g['s'] += 1
                await self._render_hilo(c, uid, True)
            else:
                await self._render_hilo(c, uid, False, True)

    async def _render_hilo(self, c, uid, win=False, lose=False):
        g = self.games[uid]
        txt = f"{g['c']['rank']}{g['c']['suit']}"
        if lose:
            await c.message.edit_text(f"📈 Carte: {txt}\n❌ PERDU", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="MENU", callback_data="home")]]))
            del self.games[uid]
        else:
            pot = g['b'] * (1.3 ** g['s'])
            kb = InlineKeyboardBuilder().row(InlineKeyboardButton(text="🔼 PLUS", callback_data="hl_high"), InlineKeyboardButton(text="🔽 MOINS", callback_data="hl_low"))
            if win:
                kb.row(InlineKeyboardButton(text=f"💰 CASH ${pot:.0f}", callback_data="hl_out"))
            await c.message.edit_text(f"📈 Carte: {txt}\nGain potentiel: ${pot:.2f}", reply_markup=kb.as_markup())
