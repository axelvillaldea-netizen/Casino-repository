from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_rank_name(xp):
    """Retourne le rang de l'utilisateur basé sur son XP"""
    if xp < 1000: return "Vagabond"
    if xp < 5000: return "Soldat"
    if xp < 20000: return "Capitaine"
    if xp < 100000: return "Général"
    return "EMPEREUR"


def get_main_menu(user):
    """Menu principal du casino"""
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


def get_bet_menu(game, bet, uid, crash_target=None, crash_history=None):
    """Menu de mise pour tous les jeux"""
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
    
    # Commandes spécifiques au jeu
    if game == "crash":
        t = crash_target or 2.0
        default_history = [1.00, 2.50, 1.10]
        history_to_use = crash_history if crash_history else default_history
        h = " ".join([f"{x}x" for x in history_to_use[-3:]])
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
