import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_ID = int(os.getenv("ADMIN_ID", "YOUR_ADMIN_ID_HERE"))

# The Odds API Configuration
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "YOUR_ODDS_API_KEY_HERE")
ODDS_API_BASE_URL = "https://api.the-odds-api.com/v4"

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_KEY_HERE")

# Database Configuration
DATABASE_TYPE = os.getenv("DATABASE_TYPE", "sqlite")  # sqlite or postgresql

# Get the current working directory for database path
current_dir = os.path.dirname(os.path.abspath(__file__))
default_db_path = os.path.join(current_dir, "betting_bot.db")

SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", default_db_path)
POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://user:password@localhost/betting_bot")

# Voice Configuration
VOICE_ENABLED = os.getenv("VOICE_ENABLED", "True").lower() == "true"
VOICE_ENGINE = os.getenv("VOICE_ENGINE", "elevenlabs")  # elevenlabs, gtts, or pyttsx3

# ElevenLabs Configuration (Premium Voice Quality)
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "YOUR_ELEVENLABS_KEY_HERE")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
ELEVENLABS_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "eleven_monolingual_v1")

# 🇺🇸 USA REGION CONFIGURATION
REGION = "USA"
COUNTRY_CODE = "US"
LANGUAGE = "en-US"

# 💵 USA CURRENCY (USD - United States Dollar)
CURRENCY = "USD"
CURRENCY_SYMBOL = "$"
MIN_BET_AMOUNT = 1
MAX_BET_AMOUNT = 10000
INITIAL_BALANCE = 0  # $0 starting balance for new users

# 🏆 USA SPORTS LEAGUES
SPORTS_LIST = [
    # American Football
    "americanfootball_nfl",                 # NFL - National Football League
    "americanfootball_ncaaf",               # College Football (NCAA)
    
    # Basketball
    "basketball_nba",                       # NBA - National Basketball Association
    "basketball_ncaab",                     # College Basketball (NCAA)
    
    # Baseball
    "baseball_mlb",                         # MLB - Major League Baseball
    
    # Hockey
    "ice_hockey_nhl",                       # NHL - National Hockey League
    
    # Soccer (Growing in USA)
    "soccer_mls",                           # MLS - Major League Soccer
    "soccer_epl",                           # Premier League (Popular in USA)
    
    # Other Popular US Sports
    "golf_pga",                             # PGA Tour
    "tennis_atp",                           # ATP Tennis
]

DEFAULT_SPORT = os.getenv("DEFAULT_SPORT", "americanfootball_nfl")

# Auto-refresh Configuration
LIVE_MATCHES_REFRESH_INTERVAL = 300  # 5 minutes in seconds
RESULT_CHECK_INTERVAL = 3600  # 1 hour in seconds

# Status Messages
STATUS_MESSAGES = {
    "welcome": "🇺🇸 Welcome to USA Betting Bot!",
    "live_matches": "🏆 Live USA Sports Matches",
    "balance": "💰 Your Account Balance",
}

# ⚖️ RESPONSIBLE GAMBLING SETTINGS
RESPONSIBLE_GAMBLING = {
    "enabled": True,
    "daily_loss_limit": 500,  # $500 daily loss limit
    "daily_bet_limit": 1000,  # $1000 daily betting limit
    "session_timeout_minutes": 120,  # 2 hour session limit
    "warning_message": "Please gamble responsibly. Set limits for yourself.",
}

# 📊 BETTING ODDS TYPES
ODDS_TYPES = {
    "decimal": "Decimal (European)",
    "american": "American (-110, +110, etc)",
    "fractional": "Fractional (1/2, 2/1, etc)"
}
DEFAULT_ODDS_TYPE = "american"  # USA default

# 🎯 POPULAR US SPORTSBOOKS (for reference)
POPULAR_SPORTSBOOKS = [
    "DraftKings",
    "FanDuel",
    "BetMGM",
    "Caesars",
    "PointsBet",
    "Wynn",
]

# 🌐 USA STATE REGULATIONS
# Sports betting is legal in these states (as of 2024)
LEGAL_STATES = [
    "AZ", "CO", "CT", "DE", "DC", "IL", "IN", "IA", "KS", "KY",
    "LA", "MD", "MI", "MS", "MO", "MT", "NV", "NH", "NJ", "NY",
    "OH", "PA", "RI", "TN", "VA", "VT", "WV", "WY"
]

# 💬 USA/ENGLISH LOCALIZATION
MESSAGES = {
    "currency_symbol": "$",
    "team_label": "Team",
    "odds_label": "Odds",
    "bet_label": "Bet Amount",
    "win_label": "Potential Win",
}
