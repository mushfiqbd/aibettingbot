#!/usr/bin/env python3
"""
Bot Runner with Error Handling
"""
import sys
import logging
import asyncio
import os

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('D:/AIBetingBot/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def check_dependencies():
    """Check if all required packages are installed"""
    required_packages = [
        'telegram',
        'requests',
        'dotenv',
        'openai',
        'gtts',
        'pyttsx3',
        'schedule',
        'pytz',
        'elevenlabs'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        logger.error(f"❌ Missing packages: {', '.join(missing)}")
        logger.error("Run: pip install -r requirements.txt")
        return False
    
    logger.info("✅ All dependencies installed")
    return True

def check_env_file():
    """Check if .env file exists and is configured"""
    if not os.path.exists('.env'):
        logger.error("❌ .env file not found!")
        logger.error("Run: copy env_example.txt .env")
        return False
    
    logger.info("✅ .env file found")
    return True

async def run_bot():
    """Run the bot with error handling"""
    try:
        from main import BettingBot
        
        logger.info("🤖 Initializing Betting Bot...")
        bot = BettingBot()
        
        logger.info("🚀 Starting bot...")
        await bot.run()
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.error("Make sure all files are in D:\\AIBetingBot")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")
        logger.error("Check the log file for details")
        sys.exit(1)

def main():
    """Main entry point"""
    print("""
    ╔═══════════════════════════════════════╗
    ║  🎰 AI Betting Telegram Bot  🎰      ║
    ║  Version: 1.0.0                      ║
    ╚═══════════════════════════════════════╝
    """)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Check env file
    if not check_env_file():
        sys.exit(1)
    
    logger.info("=" * 50)
    logger.info("🎯 All checks passed. Starting bot...")
    logger.info("=" * 50)
    
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("\n✋ Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
