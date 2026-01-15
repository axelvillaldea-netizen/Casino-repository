import asyncio
import logging
from aiogram import Bot, Dispatcher

from app.config import BOT_TOKEN, LOG_LEVEL
from app.utils.database import DatabaseManager
from app.handlers.system import SystemHandlers
from app.games.crash import CrashGame
from app.games.cards import CardGames
from app.games.simple import SimplGames
from app.games.complex import ComplexGames
from app.games.machines import MachineGames


# Configuration des logs
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialisation
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db = DatabaseManager()


def register_all_handlers():
    """Enregistre tous les handlers du bot"""
    logger.info("Enregistrement des handlers...")
    
    # Handlers système (doit être en premier)
    system_handlers = SystemHandlers(dp, db)
    
    # Jeux
    CrashGame(dp, db, system_handlers)
    CardGames(dp, db)
    SimplGames(dp, db)
    ComplexGames(dp, db)
    MachineGames(dp, db)
    
    logger.info("✅ Tous les handlers sont enregistrés")


async def main():
    """Fonction principale"""
    print("=" * 50)
    print("🏛️  OLYMPUS CASINO : FINAL CUT")
    print("=" * 50)
    print("✅ Base de données initialisée")
    print("✅ Bot configuré depuis .env")
    
    register_all_handlers()
    
    print("🚀 Démarrage du bot...")
    print("--- Polling en cours ---\n")
    
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ Bot arrêté")
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        raise
