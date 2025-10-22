import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
from config import TELEGRAM_BOT_TOKEN, ADMIN_ID, MIN_BET_AMOUNT, MAX_BET_AMOUNT, CURRENCY_SYMBOL, CURRENCY, INITIAL_BALANCE
from database import db
from api_handler import odds_api
from voice_handler import voice_handler
from ai_integration import ai_assistant

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('D:/AIBetingBot/bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Set console encoding for Windows
import sys
if sys.platform == 'win32':
    import os
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Conversation states
ASKING_AMOUNT, ASKING_TEAM, ASKING_DEPOSIT_AMOUNT, ASKING_WITHDRAW_AMOUNT, ASKING_MESSAGE, ASKING_WALLET_ADDRESS = range(6)


class FakeUpdate:
    """Helper class to wrap CallbackQuery as Update for command handlers"""
    def __init__(self, query):
        self.callback_query = query
        self.message = None
        self._effective_user = query.from_user
    
    @property
    def effective_user(self):
        return self._effective_user


class BettingBot:
    def __init__(self):
        self.app = None
        self.matches_cache = {}
        self.selected_match = {}

    async def send_or_edit_message(self, update: Update, text: str, reply_markup=None, parse_mode="HTML"):
        """Helper method to send message or edit existing message based on update type"""
        try:
            if update.message:
                await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
            elif update.callback_query:
                await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception as e:
            logger.error(f"Error sending/editing message: {e}")
            if update.callback_query:
                await update.callback_query.answer(f"❌ Error: {str(e)}", show_alert=True)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command - Welcome message and user registration"""
        user = update.effective_user
        user_id = user.id
        
        # Register user if new
        if not db.user_exists(user_id):
            db.add_user(user_id, user.username or "unknown", user.first_name, user.last_name or "")
            welcome_text = f"""
<b>🇺🇸 Welcome to USA Sports Betting Bot! 🇺🇸</b>

Hey {user.first_name}! 👋

I'm your AI-powered sports betting assistant. Get smart picks for:
• 🏈 NFL - National Football League
• 🏀 NBA - National Basketball Association
• ⚾ MLB - Major League Baseball
• 🏒 NHL - National Hockey League
• ⚽ MLS - Major League Soccer
• 🏫 College Sports

<b>What You Can Do:</b>
• 📊 View live games & odds
• 🤖 Get AI-powered betting tips
• 💰 Smart betting with real-time updates
• 📈 Track your bets & winnings
• 🔊 English voice responses

        <b>Your Starting Balance:</b> <b>${INITIAL_BALANCE:,}</b>
        
        <b>💡 To get started:</b>
        • Click "💰 Balance" to check your balance
        • Click "💵 Deposit" to add funds
        • Click "🏆 Live Games" to start betting

<i>Disclaimer: This is for educational purposes only. Gamble responsibly!</i>
"""
        else:
            balance = db.get_user_balance(user_id)
            welcome_text = f"""
<b>🇺🇸 Welcome Back, {user.first_name}! 👋</b>

Your current balance: <b>${balance:,.2f}</b>

Ready to find winning bets? Let's go! 🏈🏀⚾
"""
        
        # Build keyboard - common buttons
        keyboard = [
            [InlineKeyboardButton("🏆 Live Games", callback_data="live"),
             InlineKeyboardButton("📅 Upcoming", callback_data="upcoming")],
            [InlineKeyboardButton("💰 Balance", callback_data="balance"),
             InlineKeyboardButton("📋 My Bets", callback_data="mybets")],
            [InlineKeyboardButton("🤖 AI Assistant", callback_data="ai_chat"),
             InlineKeyboardButton("❓ Help", callback_data="help")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="settings")]
        ]
        
        # Add admin button if user is admin
        if user_id == ADMIN_ID:
            keyboard.append([InlineKeyboardButton("🔐 Admin Panel", callback_data="admin_panel")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Handle both regular messages and callback queries
        if update.message:
            await update.message.reply_text(
                welcome_text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        elif update.callback_query:
            await update.callback_query.edit_message_text(
                welcome_text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )

    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show admin panel with all features"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        # Check if admin
        if user_id != ADMIN_ID:
            await query.answer("❌ Unauthorized access", show_alert=True)
            return
        
        message = """
🔐 <b>Admin Control Panel</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 User Management
💰 Transaction Management
📊 Statistics & Reports
🛡️ Security & Compliance
⚙️ System Settings
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Select an option below:
"""
        
        keyboard = [
            [InlineKeyboardButton("👥 Users", callback_data="admin_users"),
             InlineKeyboardButton("💳 Transactions", callback_data="admin_transactions")],
            [InlineKeyboardButton("📈 Statistics", callback_data="admin_stats"),
             InlineKeyboardButton("🔍 Verify KYC", callback_data="admin_kyc")],
            [InlineKeyboardButton("💸 Pending Deposits", callback_data="admin_deposits"),
             InlineKeyboardButton("💸 Pending Withdrawals", callback_data="admin_withdrawals")],
            [InlineKeyboardButton("⚠️ Compliance Alerts", callback_data="admin_compliance"),
             InlineKeyboardButton("🛡️ Security", callback_data="admin_security")],
            [InlineKeyboardButton("📋 Reports", callback_data="admin_reports"),
             InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings")],
            [InlineKeyboardButton("🏠 Home", callback_data="home")]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    async def admin_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user management"""
        query = update.callback_query
        await query.answer()
        
        users = db.get_all_users()
        total_users = len(users)
        
        message = f"""
👥 <b>User Management</b>

Total Users: <b>{total_users}</b>

📊 User Statistics:
"""
        
        for user in users[:10]:  # Show first 10 users
            message += f"\n• @{user['username']} - Balance: ${user['balance']:.2f}"
        
        if total_users > 10:
            message += f"\n... and {total_users - 10} more users"
        
        keyboard = [
            [InlineKeyboardButton("🔎 Search User", callback_data="admin_search_user"),
             InlineKeyboardButton("🚫 Ban User", callback_data="admin_ban_user")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_panel"),
             InlineKeyboardButton("🏠 Home", callback_data="home")]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    async def admin_transactions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show pending transactions"""
        query = update.callback_query
        await query.answer()
        
        deposits = db.get_pending_deposits()
        withdrawals = db.get_pending_withdrawals()
        
        message = f"""
💳 <b>Transaction Management</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━
⏳ Pending Deposits: <b>{len(deposits)}</b>
⏳ Pending Withdrawals: <b>{len(withdrawals)}</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>Recent Pending:</b>
"""
        
        for tx in deposits[:3]:
            message += f"\n💵 Deposit #{tx['id']}: ${tx['amount']} - {tx['user_id']}"
        
        for tx in withdrawals[:3]:
            message += f"\n💸 Withdrawal #{tx['id']}: ${tx['amount']} - {tx['user_id']}"
        
        keyboard = [
            [InlineKeyboardButton("✅ Approve Deposits", callback_data="admin_approve_deposits"),
             InlineKeyboardButton("✅ Approve Withdrawals", callback_data="admin_approve_withdrawals")],
            [InlineKeyboardButton("❌ Reject Deposits", callback_data="admin_reject_deposits"),
             InlineKeyboardButton("❌ Reject Withdrawals", callback_data="admin_reject_withdrawals")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_panel"),
             InlineKeyboardButton("🏠 Home", callback_data="home")]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    async def admin_compliance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show compliance alerts"""
        query = update.callback_query
        await query.answer()
        
        message = """
⚠️ <b>Compliance Alerts</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━
🔴 High-Risk Users
🔴 Large Bets
🔴 Suspicious Activity
🔴 Responsible Gambling Violations
━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>Today's Alerts:</b>
• 3 users exceeded daily limits
• 2 suspicious bet patterns detected
• 1 user flagged for KYC review
"""
        
        keyboard = [
            [InlineKeyboardButton("👤 High-Risk Users", callback_data="admin_high_risk"),
             InlineKeyboardButton("📊 Betting Patterns", callback_data="admin_patterns")],
            [InlineKeyboardButton("🚨 Suspicious", callback_data="admin_suspicious"),
             InlineKeyboardButton("📢 Send Alert", callback_data="admin_send_alert")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_panel"),
             InlineKeyboardButton("🏠 Home", callback_data="home")]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    async def admin_security(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show security settings"""
        query = update.callback_query
        await query.answer()
        
        message = """
🛡️ <b>Security & System Status</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Telegram Bot: Online
✅ Database: Connected
✅ APIs: All Working
✅ Voice Engine: Active
━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>Recent Activities:</b>
• 15 users active today
• 42 bets placed
• 8 transactions pending
• 0 security incidents

<b>System Health:</b>
• CPU: Normal
• Memory: Normal
• Database: Normal
"""
        
        keyboard = [
            [InlineKeyboardButton("🔐 Change Password", callback_data="admin_change_password"),
             InlineKeyboardButton("🔑 API Keys", callback_data="admin_api_keys")],
            [InlineKeyboardButton("📋 Logs", callback_data="admin_logs"),
             InlineKeyboardButton("🔄 Restart Bot", callback_data="admin_restart")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_panel"),
             InlineKeyboardButton("🏠 Home", callback_data="home")]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    async def admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show platform statistics"""
        query = update.callback_query
        await query.answer()
        
        stats = db.get_stats()
        
        message = f"""
📈 <b>Platform Statistics</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━
👥 Total Users: <b>{stats.get('total_users', 0)}</b>
🎲 Total Bets: <b>{stats.get('total_bets', 0)}</b>
🏆 Total Wins: <b>{stats.get('total_wins', 0)}</b>
💸 Total Losses: <b>{stats.get('total_losses', 0)}</b>
💰 Total Balance: <b>${stats.get('total_balance', 0):,.2f}</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>Win Rate:</b> {((stats.get('total_wins', 0) / max(stats.get('total_bets', 1), 1)) * 100):.1f}%
<b>Average Bet:</b> ${(stats.get('total_balance', 0) / max(stats.get('total_bets', 1), 1)):.2f}
"""
        
        keyboard = [
            [InlineKeyboardButton("📊 Daily Stats", callback_data="admin_daily_stats"),
             InlineKeyboardButton("📈 Weekly Stats", callback_data="admin_weekly_stats")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_panel"),
             InlineKeyboardButton("🏠 Home", callback_data="home")]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    async def admin_kyc(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show KYC verification"""
        query = update.callback_query
        await query.answer()
        
        message = """
🔍 <b>KYC Verification</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━
⏳ Pending Verifications: <b>0</b>
✅ Verified Users: <b>0</b>
❌ Rejected Users: <b>0</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>Recent KYC Requests:</b>
• No pending requests

<i>KYC system will be implemented in future updates</i>
"""
        
        keyboard = [
            [InlineKeyboardButton("📄 Review Documents", callback_data="admin_review_docs"),
             InlineKeyboardButton("✅ Approve KYC", callback_data="admin_approve_kyc")],
            [InlineKeyboardButton("❌ Reject KYC", callback_data="admin_reject_kyc"),
             InlineKeyboardButton("📋 KYC History", callback_data="admin_kyc_history")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_panel"),
             InlineKeyboardButton("🏠 Home", callback_data="home")]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    async def admin_deposits(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show pending deposits"""
        query = update.callback_query
        await query.answer()
        
        deposits = db.get_pending_deposits()
        
        message = f"""
💸 <b>Pending Deposits</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━
⏳ Total Pending: <b>{len(deposits)}</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>Recent Deposits:</b>
"""
        
        if deposits:
            for tx in deposits[:5]:
                message += f"\n💵 #{tx['tx_id']}: ${tx['amount']} - User {tx['user_id']}"
        else:
            message += "\n• No pending deposits"
        
        keyboard = [
            [InlineKeyboardButton("✅ Approve All", callback_data="admin_approve_all_deposits"),
             InlineKeyboardButton("❌ Reject All", callback_data="admin_reject_all_deposits")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_panel"),
             InlineKeyboardButton("🏠 Home", callback_data="home")]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    async def admin_withdrawals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show pending withdrawals"""
        query = update.callback_query
        await query.answer()
        
        withdrawals = db.get_pending_withdrawals()
        
        message = f"""
💸 <b>Pending Withdrawals</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━
⏳ Total Pending: <b>{len(withdrawals)}</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>Recent Withdrawals:</b>
"""
        
        if withdrawals:
            for tx in withdrawals[:5]:
                message += f"\n💸 #{tx['tx_id']}: ${tx['amount']} - User {tx['user_id']}"
        else:
            message += "\n• No pending withdrawals"
        
        keyboard = [
            [InlineKeyboardButton("✅ Approve All", callback_data="admin_approve_all_withdrawals"),
             InlineKeyboardButton("❌ Reject All", callback_data="admin_reject_all_withdrawals")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_panel"),
             InlineKeyboardButton("🏠 Home", callback_data="home")]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    async def admin_reports(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show reports"""
        query = update.callback_query
        await query.answer()
        
        message = """
📋 <b>Reports & Analytics</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Available Reports:
━━━━━━━━━━━━━━━━━━━━━━━━━━

• 📅 Daily Activity Report
• 📈 Weekly Performance Report
• 💰 Monthly Revenue Report
• 👥 User Analytics Report
• 🎲 Betting Patterns Report
• ⚠️ Compliance Report

<i>Report generation will be implemented in future updates</i>
"""
        
        keyboard = [
            [InlineKeyboardButton("📅 Daily Report", callback_data="admin_daily_report"),
             InlineKeyboardButton("📈 Weekly Report", callback_data="admin_weekly_report")],
            [InlineKeyboardButton("💰 Revenue Report", callback_data="admin_revenue_report"),
             InlineKeyboardButton("👥 User Report", callback_data="admin_user_report")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_panel"),
             InlineKeyboardButton("🏠 Home", callback_data="home")]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    async def admin_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show admin settings"""
        query = update.callback_query
        await query.answer()
        
        # Get current wallet addresses
        wallets = db.get_all_wallet_addresses()
        wallet_info = ""
        for wallet in wallets:
            wallet_info += f"• {wallet['crypto_type']}: {wallet['wallet_address'][:10]}...\n"
        
        if not wallet_info:
            wallet_info = "• No wallet addresses set"
        
        message = f"""
⚙️ <b>Admin Settings</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━
🔧 System Configuration:
━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>Current Wallet Addresses:</b>
{wallet_info}

<b>Available Settings:</b>
• 💰 Wallet Addresses
• 🤖 Bot Settings
• 🔐 Security Settings
• 💵 Betting Limits
• 📢 Notifications
"""
        
        keyboard = [
            [InlineKeyboardButton("💰 Wallet Addresses", callback_data="admin_wallet_addresses"),
             InlineKeyboardButton("🤖 Bot Config", callback_data="admin_bot_config")],
            [InlineKeyboardButton("🔐 Security Config", callback_data="admin_security_config"),
             InlineKeyboardButton("💵 Betting Limits", callback_data="admin_betting_limits")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_panel"),
             InlineKeyboardButton("🏠 Home", callback_data="home")]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    async def admin_wallet_addresses(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manage wallet addresses"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        # Check if admin
        if user_id != ADMIN_ID:
            await query.answer("❌ Unauthorized access", show_alert=True)
            return
        
        # Get current wallet addresses
        wallets = db.get_all_wallet_addresses()
        
        message = """
💰 <b>Wallet Address Management</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━
📬 Current Wallet Addresses:
━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        if wallets:
            for wallet in wallets:
                message += f"\n<b>{wallet['crypto_type']}:</b>\n<code>{wallet['wallet_address']}</code>\n"
        else:
            message += "\n• No wallet addresses configured"
        
        message += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        message += "Click below to set wallet addresses:"
        
        keyboard = [
            [InlineKeyboardButton("₿ Set BTC Address", callback_data="admin_set_btc"),
             InlineKeyboardButton("Ξ Set ETH Address", callback_data="admin_set_eth")],
            [InlineKeyboardButton("◎ Set USDT Address", callback_data="admin_set_usdt")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_settings"),
             InlineKeyboardButton("🏠 Home", callback_data="home")]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    async def admin_set_wallet_crypto(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle crypto selection for wallet address setting"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        # Check if admin
        if user_id != ADMIN_ID:
            await query.answer("❌ Unauthorized access", show_alert=True)
            return
        
        crypto_type = query.data.split("_")[2].upper()  # btc, eth, usdt
        context.user_data['setting_crypto'] = crypto_type
        
        # Get current address if exists
        current_address = db.get_wallet_address(crypto_type)
        
        message = f"""
💰 <b>Set {crypto_type} Wallet Address</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━
Current Address:
━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        if current_address:
            message += f"<code>{current_address}</code>"
        else:
            message += "• No address set"
        
        message += f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>Instructions:</b>
1. Send the new {crypto_type} wallet address
2. Address will be updated immediately
3. Users will see this address for deposits

<b>Format Examples:</b>
• BTC: 1A1z7agoat2BYLC7NqfBi7cQ6ogU4xE5Bp
• ETH: 0x742d35Cc6634C0532925a3b844Bc9e7595f42bE
• USDT: 0x742d35Cc6634C0532925a3b844Bc9e7595f42bE
"""
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_wallet_addresses")]]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        
        return ASKING_WALLET_ADDRESS

    async def admin_handle_wallet_address(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle wallet address input"""
        user_id = update.effective_user.id
        
        # Check if admin
        if user_id != ADMIN_ID:
            await update.message.reply_text("❌ Unauthorized access")
            return ConversationHandler.END
        
        crypto_type = context.user_data.get('setting_crypto')
        wallet_address = update.message.text.strip()
        
        if not crypto_type or not wallet_address:
            await update.message.reply_text("❌ Invalid input. Please try again.")
            return ConversationHandler.END
        
        # Validate address format (basic validation)
        if crypto_type == 'BTC' and not wallet_address.startswith(('1', '3', 'bc1')):
            await update.message.reply_text("❌ Invalid BTC address format. Please check and try again.")
            return ASKING_WALLET_ADDRESS
        
        if crypto_type in ['ETH', 'USDT'] and not wallet_address.startswith('0x'):
            await update.message.reply_text(f"❌ Invalid {crypto_type} address format. Must start with '0x'. Please try again.")
            return ASKING_WALLET_ADDRESS
        
        # Save wallet address
        if db.set_wallet_address(crypto_type, wallet_address, user_id):
            message = f"""
✅ <b>{crypto_type} Wallet Address Updated!</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>New Address:</b>
<code>{wallet_address}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Address saved successfully
✅ Users will now see this address for {crypto_type} deposits
✅ Admin action logged
"""
            
            keyboard = [
                [InlineKeyboardButton("💰 Manage Addresses", callback_data="admin_wallet_addresses"),
                 InlineKeyboardButton("🔙 Settings", callback_data="admin_settings")],
                [InlineKeyboardButton("🏠 Home", callback_data="home")]
            ]
            
            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
            
            # Log admin action
            db.log_action(user_id, f"set_{crypto_type.lower()}_wallet", f"Updated {crypto_type} wallet address")
            
        else:
            await update.message.reply_text("❌ Failed to save wallet address. Please try again.")
            return ASKING_WALLET_ADDRESS
        
        return ConversationHandler.END

    async def live_matches(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show live matches"""
        try:
            matches = odds_api.get_live_matches()
            
            if not matches:
                await self.send_or_edit_message(
                    update,
                    "❌ No live games right now.\n\n"
                    "Try /upcoming to see upcoming games or check back soon!"
                )
                return
            
            message_text = "<b>🏆 Live USA Sports Games</b>\n\n"
            
            keyboard = []
            for idx, match in enumerate(matches[:8], 1):
                home = match['home_team']
                away = match['away_team']
                message_text += f"<b>{idx}.</b> {home} <b>vs</b> {away}\n"
                
                keyboard.append([InlineKeyboardButton(
                    f"⚽ {home[:15]} vs {away[:15]}",
                    callback_data=f"match_{match['match_id']}"
                )])
            
            keyboard.append([InlineKeyboardButton("🏠 Home", callback_data="home")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.send_or_edit_message(
                update,
                message_text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Error in live_matches: {e}")
            await self.send_or_edit_message(update, f"❌ Error: {str(e)}")

    async def upcoming_matches(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show upcoming matches"""
        try:
            matches = odds_api.get_upcoming_matches()
            
            if not matches:
                await self.send_or_edit_message(update, "❌ No upcoming matches.")
                return
            
            message_text = "📅 <b>Upcoming Matches:</b>\n\n"
            
            for idx, match in enumerate(matches[:5], 1):
                message_text += f"{idx}. {match['home_team']} vs {match['away_team']}\n"
                message_text += f"   ⏰ {match['commence_time']}\n\n"
            
            keyboard = []
            for match in matches[:5]:
                keyboard.append([InlineKeyboardButton(
                    f"{match['home_team']} vs {match['away_team']}",
                    callback_data=f"match_{match['match_id']}"
                )])
            
            keyboard.append([InlineKeyboardButton("🏠 Home", callback_data="home")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.send_or_edit_message(
                update,
                message_text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Error in upcoming_matches: {e}")
            await self.send_or_edit_message(update, f"❌ Error: {str(e)}")

    async def match_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle match selection"""
        query = update.callback_query
        await query.answer()
        
        match_id = query.data.split("_", 1)[1]
        context.user_data['selected_match_id'] = match_id
        
        # Get match odds
        odds_data = odds_api.get_match_odds(match_id)
        
        if odds_data:
            home = odds_data['home_team']
            away = odds_data['away_team']
            
            message = f"""
🏆 <b>Match Details</b>

<b>{home} vs {away}</b>

📊 <b>Odds:</b>
"""
            
            for odd in odds_data['odds']:
                team = odd['team']
                odds_value = odd['odds']
                message += f"\n  • {team}: <b>{odds_value:+.0f}</b>"
            
            if odds_data.get('spreads'):
                message += "\n\n📈 <b>Spreads:</b>"
                for spread in odds_data['spreads']:
                    message += f"\n  • {spread['team']} {spread['spread']:+.1f}: <b>{spread['odds']:+.0f}</b>"
            
            if odds_data.get('totals'):
                message += "\n\n🎯 <b>Totals:</b>"
                for total in odds_data['totals']:
                    message += f"\n  • {total['type']} {total['point']}: <b>{total['odds']:+.0f}</b>"
            
            # Only show "Place Bet" and "AI Tips" buttons
            # Team selection happens AFTER user enters bet amount
            keyboard = [
                [InlineKeyboardButton("🎯 Place Bet", callback_data="start_bet"),
                 InlineKeyboardButton("🤖 AI Tips", callback_data="get_ai_tip")],
                [InlineKeyboardButton("🏠 Home", callback_data="home")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            await query.answer("❌ Could not retrieve match data", show_alert=True)

    async def start_bet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start betting process"""
        query = update.callback_query
        user_id = query.from_user.id
        
        balance = db.get_user_balance(user_id)
        
        if balance <= 0:
            await query.answer(f"❌ Your balance is insufficient. Current balance: {CURRENCY_SYMBOL} {balance}", show_alert=True)
            return
        
        message = f"""
💰 <b>Place Bet</b>

Your current balance: {CURRENCY_SYMBOL} {balance}
Minimum bet: {CURRENCY_SYMBOL} {MIN_BET_AMOUNT}
Maximum bet: {CURRENCY_SYMBOL} {MAX_BET_AMOUNT}

Enter the amount:
"""
        
        await query.edit_message_text(message, parse_mode="HTML")
        
        return ASKING_AMOUNT

    async def get_bet_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get bet amount from user"""
        user_id = update.effective_user.id
        
        try:
            amount = float(update.message.text)
            
            if amount < MIN_BET_AMOUNT or amount > MAX_BET_AMOUNT:
                await update.message.reply_text(
                    f"❌ Bet amount must be between {CURRENCY_SYMBOL} {MIN_BET_AMOUNT} and {CURRENCY_SYMBOL} {MAX_BET_AMOUNT}."
                )
                return ASKING_AMOUNT
            
            context.user_data['bet_amount'] = amount
            
            match_id = context.user_data.get('selected_match_id')
            odds_data = odds_api.get_match_odds(match_id)
            
            if odds_data:
                teams = [odd['team'] for odd in odds_data['odds']]
                keyboard = [[InlineKeyboardButton(team, callback_data=f"team_{team}")] for team in teams]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                message = f"""
🏆 <b>Choose Team</b>

Bet amount: {CURRENCY_SYMBOL} {amount}

Which team would you like to bet on?
"""
                
                await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="HTML")
                return ASKING_TEAM
            else:
                await update.message.reply_text("❌ Could not retrieve match data")
                return ConversationHandler.END
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid number.")
            return ASKING_AMOUNT

    async def team_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle team selection for betting"""
        query = update.callback_query
        await query.answer()
        
        team = query.data.split("_", 1)[1]
        user_id = query.from_user.id
        amount = context.user_data.get('bet_amount')
        match_id = context.user_data.get('selected_match_id')
        
        # Get odds data
        odds_data = odds_api.get_match_odds(match_id)
        
        # Validate odds_data
        if not odds_data or not odds_data.get('odds'):
            await query.answer("❌ Odds data not available. Please try again.", show_alert=True)
            return ConversationHandler.END
        
        # Find odds for selected team
        selected_odds = None
        for odd in odds_data['odds']:
            if odd['team'] == team:
                selected_odds = odd['odds']
                break
        
        if selected_odds is not None:
            # Calculate potential win for American odds
            if selected_odds > 0:
                potential_win = (amount * selected_odds) / 100
            else:
                potential_win = (amount * 100) / abs(selected_odds)
            
            bet_id = db.place_bet(user_id, match_id, team, selected_odds, amount)
            
            message = f"""
✅ <b>Bet successfully placed!</b>

📊 Bet details:
• Team: {team}
• Odds: {selected_odds:+.0f}
• Bet amount: {CURRENCY_SYMBOL} {amount}
• Potential win: {CURRENCY_SYMBOL} {potential_win:.2f}

Your new balance: {CURRENCY_SYMBOL} {db.get_user_balance(user_id):.2f}
"""
            
            await query.edit_message_text(message, parse_mode="HTML")
            
            # Generate voice confirmation
            voice_file = voice_handler.create_bet_confirmation_voice(team, selected_odds, int(amount))
            if voice_file:
                try:
                    await query.message.reply_voice(voice=voice_file)
                    voice_file.close()
                    voice_handler.cleanup_old_files()
                except Exception as e:
                    logger.warning(f"Could not send voice message: {e}")
            
            # Log the bet
            logger.info(f"Bet placed: User {user_id}, Match {match_id}, Team {team}, Amount {amount}, Odds {selected_odds}")
        else:
            await query.answer(f"❌ Odds for {team} not found", show_alert=True)
        
        return ConversationHandler.END

    async def my_bets(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user's bets"""
        user_id = update.effective_user.id
        bets = db.get_user_bets(user_id)
        
        if not bets:
            keyboard = [[InlineKeyboardButton("🏠 Home", callback_data="home"),
                        InlineKeyboardButton("🏆 Live Games", callback_data="live")]]
            await self.send_or_edit_message(
                update,
                "📋 You have no bets yet.\n\nUse /live to see games and place your first bet!",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        message = "<b>📋 Your Bets</b>\n\n━━━━━━━━━━━━━━━━━━\n"
        
        active_bets = [b for b in bets if b['status'] != 'resolved']
        resolved_bets = [b for b in bets if b['status'] == 'resolved']
        
        if active_bets:
            message += "<b>🔴 Active Bets:</b>\n"
            for idx, bet in enumerate(active_bets[:5], 1):
                message += f"""
<b>{idx}.</b> {bet['team_name']}
  💰 Amount: {CURRENCY_SYMBOL} {bet['amount']}
  📊 Odds: {bet['odds']}
  🎯 Potential Win: {CURRENCY_SYMBOL} {bet['potential_win']:.0f}
"""
        
        if resolved_bets:
            message += "\n<b>✅ Completed Bets:</b>\n"
            for idx, bet in enumerate(resolved_bets[:5], 1):
                emoji = "✅" if bet['result'] == 'won' else "❌"
                message += f"{emoji} {idx}. {bet['team_name']} - {bet['result'].upper()}\n"
        
        message += "\n━━━━━━━━━━━━━━━━━━"
        
        keyboard = [[InlineKeyboardButton("🏠 Home", callback_data="home"),
                    InlineKeyboardButton("🏆 New Bet", callback_data="live")]]
        
        await self.send_or_edit_message(
            update,
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    async def balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check balance"""
        user_id = update.effective_user.id
        user_info = db.get_user_info(user_id)
        
        if user_info:
            win_rate = (user_info['total_win'] / max(user_info['total_bet'], 1) * 100) if user_info['total_bet'] > 0 else 0
            
            message = f"""
<b>💰 Your Account Information</b>

━━━━━━━━━━━━━━━━━━
<b>💵 Current Balance:</b> <b>${user_info['balance']:,.2f}</b>
━━━━━━━━━━━━━━━━━━

📊 <b>Statistics:</b>
🎯 Total Bets: {user_info['total_bet']}
✅ Total Wins: {user_info['total_win']}
❌ Total Losses: {user_info['total_loss']}
🏆 Win Rate: {win_rate:.1f}%

━━━━━━━━━━━━━━━━━━
"""
            
            keyboard = [
                [InlineKeyboardButton("💵 Deposit", callback_data="deposit"),
                 InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")],
                [InlineKeyboardButton("📊 Detailed Stats", callback_data="stats"),
                 InlineKeyboardButton("🏠 Home", callback_data="home")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.send_or_edit_message(update, message, reply_markup=reply_markup, parse_mode="HTML")

    async def deposit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start deposit - show payment methods"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        context.user_data['deposit_user_id'] = user_id
        
        message = f"""
💵 <b>Deposit - Choose Payment Method</b>

Select cryptocurrency to deposit:
"""
        
        keyboard = [
            [InlineKeyboardButton("₿ Bitcoin (BTC)", callback_data="deposit_btc"),
             InlineKeyboardButton("Ξ Ethereum (ETH)", callback_data="deposit_eth")],
            [InlineKeyboardButton("◎ USDT (Tether)", callback_data="deposit_usdt")],
            [InlineKeyboardButton("🏠 Home", callback_data="home")]
        ]
        
        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return ASKING_DEPOSIT_AMOUNT

    async def deposit_payment_method(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle payment method selection"""
        query = update.callback_query
        await query.answer()
        
        method = query.data.split("_")[1].upper()  # btc, eth, usdt
        context.user_data['payment_method'] = method
        
        message = f"""
💰 <b>Deposit {method}</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━
💵 <b>Step 1: Enter Amount</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━

Please enter the amount you want to deposit in USD:

<b>Examples:</b>
• 50 (for $50)
• 100.50 (for $100.50)
• 250 (for $250)

<b>Minimum:</b> $1
<b>Maximum:</b> $10,000
"""
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back", callback_data="deposit"),
             InlineKeyboardButton("🏠 Home", callback_data="home")]
        ]
        
        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return ASKING_DEPOSIT_AMOUNT

    async def deposit_proof(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ask user to upload proof (transaction ID and screenshot)"""
        query = update.callback_query
        await query.answer()
        
        message = """
📸 <b>Upload Deposit Proof</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 <b>Step 3: Upload Proof</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━

Please send:
1️⃣ Transaction ID (in text)
2️⃣ Screenshot (photo upload)

Send in this format:
• First message: Transaction ID (e.g., 0x123abc...)
• Second message: Screenshot image

<b>Example:</b>
First: <code>0x1234567890abcdef1234567890abcdef12345678</code>
Second: 📸 Screenshot image
"""
        
        await query.edit_message_text(message, parse_mode="HTML")
        context.user_data['waiting_for_tx_id'] = True
        return ASKING_MESSAGE

    async def handle_deposit_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle deposit amount input"""
        user_id = update.effective_user.id
        amount_str = update.message.text
        
        try:
            amount = float(amount_str)
            if amount <= 0:
                await update.message.reply_text("❌ Deposit amount must be positive. Please enter a valid amount.")
                return ASKING_DEPOSIT_AMOUNT
            
            if amount < 1:
                await update.message.reply_text("❌ Minimum deposit amount is $1. Please enter a valid amount.")
                return ASKING_DEPOSIT_AMOUNT
            
            if amount > 10000:
                await update.message.reply_text("❌ Maximum deposit amount is $10,000. Please enter a valid amount.")
                return ASKING_DEPOSIT_AMOUNT
            
            context.user_data['deposit_amount'] = amount
            
            # Get payment method and wallet address
            method = context.user_data.get('payment_method', 'BTC')
            wallet = db.get_wallet_address(method)
            
            if not wallet:
                await update.message.reply_text(
                    f"❌ <b>{method} wallet address not configured</b>\n\n"
                    f"Please contact admin to set up {method} wallet address.",
                    parse_mode="HTML"
                )
                return ConversationHandler.END
            
            message = f"""
✅ <b>Amount Confirmed: ${amount:,.2f}</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━
📬 <b>Step 2: Send {method} to this address:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━

<code>{wallet}</code>

📋 <b>Important Instructions:</b>
• Copy the address exactly
• Send exactly <b>${amount:,.2f}</b> worth of {method}
• Wait for confirmation
• Have your transaction ID ready

After sending, click "✅ I've Sent Payment" to upload proof.
"""
            
            keyboard = [
                [InlineKeyboardButton("✅ I've Sent Payment", callback_data="deposit_proof")],
                [InlineKeyboardButton("🔙 Back", callback_data="deposit"),
                 InlineKeyboardButton("🏠 Home", callback_data="home")]
            ]
            
            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
            
            return ASKING_MESSAGE
            
        except ValueError:
            await update.message.reply_text("❌ Invalid amount. Please enter a number (e.g., 50 or 100.50).")
            return ASKING_DEPOSIT_AMOUNT

    async def handle_deposit_proof(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle deposit proof upload (transaction ID and screenshot)"""
        user_id = update.effective_user.id
        
        # Check if waiting for transaction ID
        if context.user_data.get('waiting_for_tx_id'):
            tx_id = update.message.text.strip()
            context.user_data['transaction_id'] = tx_id
            context.user_data['waiting_for_tx_id'] = False
            context.user_data['waiting_for_screenshot'] = True
            
            await update.message.reply_text(
                "✅ Transaction ID received!\n\n"
                "Now please upload the screenshot of your payment."
            )
            return ASKING_MESSAGE
        
        # Check if waiting for screenshot
        if context.user_data.get('waiting_for_screenshot') and update.message.photo:
            # Get the photo
            photo_file = await update.message.photo[-1].get_file()
            
            # Save deposit request to database
            amount = context.user_data.get('deposit_amount', 100)
            method = context.user_data.get('payment_method', 'BTC')
            tx_id = context.user_data.get('transaction_id', 'UNKNOWN')
            
            deposit_id = db.request_deposit(user_id, amount)
            
            # Save photo
            photo_path = f"D:/AIBetingBot/proofs/deposit_{deposit_id}.jpg"
            await photo_file.download_to_drive(photo_path)
            
            # Confirmation message to user
            message = f"""
✅ <b>Deposit Request Submitted</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Request ID: <code>{deposit_id}</code>
💰 Amount: {CURRENCY_SYMBOL} {amount:,.2f}
💱 Method: {method}
🔄 Status: ⏳ Pending Admin Approval
━━━━━━━━━━━━━━━━━━━━━━━━━━

Your deposit will be processed soon!
"""
            
            keyboard = [[InlineKeyboardButton("🏠 Home", callback_data="home")]]
            
            await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
            
            # Send notification to admin with image
            admin_message = f"""
📩 <b>New Deposit Request</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 User: <code>{user_id}</code>
💰 Amount: <b>{CURRENCY_SYMBOL} {amount:,.2f}</b>
💱 Method: <b>{method}</b>
🔑 TX ID: <code>{tx_id}</code>
📋 Request ID: <code>{deposit_id}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            
            keyboard_admin = [
                [InlineKeyboardButton("✅ Approve", callback_data=f"approve_deposit_{deposit_id}"),
                 InlineKeyboardButton("❌ Reject", callback_data=f"reject_deposit_{deposit_id}")]
            ]
            
            # Send photo with message to admin
            with open(photo_path, 'rb') as photo:
                await context.bot.send_photo(
                    chat_id=ADMIN_ID,
                    photo=photo,
                    caption=admin_message,
                    reply_markup=InlineKeyboardMarkup(keyboard_admin),
                    parse_mode="HTML"
                )
            
            logger.info(f"Deposit request {deposit_id} submitted by user {user_id}")
            
            context.user_data.clear()
            return ConversationHandler.END
        
        return ASKING_MESSAGE

    async def withdraw(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start withdrawal process"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        balance = db.get_user_balance(user_id)
        
        if balance <= 0:
            await query.answer("❌ Insufficient balance for withdrawal", show_alert=True)
            return ConversationHandler.END
        
        message = f"""
💸 <b>Withdraw Funds</b>

Your current balance: <b>{CURRENCY_SYMBOL} {balance:,.2f}</b>

Select cryptocurrency to withdraw:
"""
        
        keyboard = [
            [InlineKeyboardButton("₿ Bitcoin (BTC)", callback_data="withdraw_btc"),
             InlineKeyboardButton("Ξ Ethereum (ETH)", callback_data="withdraw_eth")],
            [InlineKeyboardButton("◎ USDT (Tether)", callback_data="withdraw_usdt")],
            [InlineKeyboardButton("🏠 Home", callback_data="home")]
        ]
        
        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        context.user_data['withdraw_user_id'] = user_id
        context.user_data['withdraw_balance'] = balance
        return ASKING_WITHDRAW_AMOUNT

    async def withdraw_payment_method(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle withdrawal payment method"""
        query = update.callback_query
        await query.answer()
        
        method = query.data.split("_")[1].upper()
        context.user_data['withdraw_method'] = method
        
        message = f"""
💸 <b>Withdraw {method}</b>

Enter your {method} wallet address:
"""
        
        await query.edit_message_text(message, parse_mode="HTML")
        context.user_data['waiting_for_wallet'] = True
        return ASKING_WITHDRAW_AMOUNT

    async def handle_withdraw_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle withdrawal details"""
        user_id = update.effective_user.id
        
        # Get wallet address
        if context.user_data.get('waiting_for_wallet'):
            wallet = update.message.text.strip()
            context.user_data['withdraw_wallet'] = wallet
            context.user_data['waiting_for_wallet'] = False
            context.user_data['waiting_for_withdraw_amount'] = True
            
            await update.message.reply_text("✅ Wallet address saved!\n\nNow enter withdrawal amount:")
            return ASKING_WITHDRAW_AMOUNT
        
        # Get withdrawal amount
        if context.user_data.get('waiting_for_withdraw_amount'):
            try:
                amount = float(update.message.text)
                balance = context.user_data.get('withdraw_balance', 0)
                
                if amount > balance:
                    await update.message.reply_text(f"❌ Insufficient balance. Your balance: {CURRENCY_SYMBOL} {balance}")
                    return ASKING_WITHDRAW_AMOUNT
                
                if amount < 100:
                    await update.message.reply_text("❌ Minimum withdrawal: $100")
                    return ASKING_WITHDRAW_AMOUNT
                
                # Create withdrawal request
                method = context.user_data.get('withdraw_method', 'BTC')
                wallet = context.user_data.get('withdraw_wallet', '')
                
                withdraw_id = db.request_withdrawal(user_id, amount, method, wallet)
                
                # Confirmation to user
                message = f"""
✅ <b>Withdrawal Request Submitted</b>

📋 Request ID: <code>{withdraw_id}</code>
💸 Amount: {CURRENCY_SYMBOL} {amount:,.2f}
💱 Method: {method}
📬 Wallet: <code>{wallet[:20]}...</code>
🔄 Status: ⏳ Pending Admin Approval
"""
                
                keyboard = [[InlineKeyboardButton("🏠 Home", callback_data="home")]]
                
                await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
                
                # Notify admin
                admin_message = f"""
💸 <b>New Withdrawal Request</b>

👤 User: <code>{user_id}</code>
💰 Amount: <b>{CURRENCY_SYMBOL} {amount:,.2f}</b>
💱 Method: <b>{method}</b>
📬 Wallet: <code>{wallet}</code>
📋 Request ID: <code>{withdraw_id}</code>
"""
                
                keyboard_admin = [
                    [InlineKeyboardButton("✅ Approve", callback_data=f"approve_withdraw_{withdraw_id}"),
                     InlineKeyboardButton("❌ Reject", callback_data=f"reject_withdraw_{withdraw_id}")]
                ]
                
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=admin_message,
                    reply_markup=InlineKeyboardMarkup(keyboard_admin),
                    parse_mode="HTML"
                )
                
                logger.info(f"Withdrawal request {withdraw_id} submitted by user {user_id}")
                
                context.user_data.clear()
                return ConversationHandler.END
                
            except ValueError:
                await update.message.reply_text("❌ Please enter a valid amount")
                return ASKING_WITHDRAW_AMOUNT
        
        return ASKING_WITHDRAW_AMOUNT

    async def get_ai_tip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get AI-powered betting tips"""
        query = update.callback_query
        await query.answer()
        
        match_id = context.user_data.get('selected_match_id')
        
        if not match_id:
            await query.answer("❌ Please select a game first", show_alert=True)
            return
        
        # Get match data
        odds_data = odds_api.get_match_odds(match_id)
        
        if odds_data:
            tip = ai_assistant.get_bet_suggestion(odds_data)
            
            message = f"""
🤖 <b>AI Betting Tips:</b>

{tip}
"""
            
            await query.edit_message_text(message, parse_mode="HTML")
        else:
            await query.answer("❌ Could not retrieve match data", show_alert=True)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help menu"""
        help_text = """
<b>❓ Help & Getting Started</b>

━━━━━━━━━━━━━━━━━━

<b>🎮 How to Get Started:</b>

1️⃣ <b>Check Your Balance</b>
   /balance - View your account

2️⃣ <b>Find Live Games</b>
   /live - See live sports games

3️⃣ <b>Place a Bet</b>
   Select game → Enter amount → Choose team

4️⃣ <b>Check Results</b>
   /mybets - View your bet history

━━━━━━━━━━━━━━━━━━

<b>📱 All Commands:</b>

🏆 /live - Live games
📅 /upcoming - Upcoming games
💰 /balance - Your balance
📋 /mybets - Your bets
💵 /deposit - Add funds
💸 /withdraw - Withdraw funds
📞 /support - Contact support

━━━━━━━━━━━━━━━━━━

<b>⭐ Pro Tips:</b>

✓ Use AI betting tips for better picks
✓ Start with small bets
✓ Track your win rate
✓ Set daily limits & bet responsibly
✓ Check odds before betting

━━━━━━━━━━━━━━━━━━

<b>📊 Supported Sports:</b>

🏈 NFL - National Football
🏀 NBA - Basketball
⚾ MLB - Baseball
🏒 NHL - Hockey
⚽ MLS & International Soccer
🏫 College Sports

━━━━━━━━━━━━━━━━━━

<b>⚠️ Responsible Gambling:</b>

• Only bet what you can afford to lose
• Set daily betting limits
• Never chase losses
• Take breaks regularly
• Gambling should be fun, not stressful

For support: /support
"""
        
        keyboard = [
            [InlineKeyboardButton("🏠 Home", callback_data="home"),
             InlineKeyboardButton("🏆 Live Games", callback_data="live")],
            [InlineKeyboardButton("📊 My Stats", callback_data="balance"),
             InlineKeyboardButton("⚙️ Settings", callback_data="settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Handle both regular messages and callback queries
        if update.message:
            await update.message.reply_text(help_text, reply_markup=reply_markup, parse_mode="HTML")
        elif update.callback_query:
            await update.callback_query.edit_message_text(help_text, reply_markup=reply_markup, parse_mode="HTML")

    async def ai_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start AI chat session"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        message = f"""
🤖 <b>AI Assistant Chat</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>Welcome to your AI betting assistant!</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━

I can help you with:
• 🎯 Betting strategies and tips
• 📊 Match analysis and predictions
• 💰 Bankroll management advice
• 🏆 Sports knowledge and insights
• ❓ General questions about betting

<b>Just type your question below and I'll help you!</b>

<i>Example: "What's the best strategy for NFL betting?"</i>
"""
        
        keyboard = [
            [InlineKeyboardButton("💡 Get Betting Tips", callback_data="ai_tips"),
             InlineKeyboardButton("📊 Match Analysis", callback_data="ai_analysis")],
            [InlineKeyboardButton("💰 Bankroll Advice", callback_data="ai_bankroll"),
             InlineKeyboardButton("🏆 Sports Knowledge", callback_data="ai_sports")],
            [InlineKeyboardButton("🏠 Home", callback_data="home")]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        
        # Set AI chat mode
        context.user_data['ai_chat_mode'] = True

    async def ai_tips(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get AI betting tips"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        # Get user's betting history for personalized tips
        user_info = db.get_user_info(user_id)
        
        prompt = f"""
        User ID: {user_id}
        Total Bets: {user_info.get('total_bet', 0)}
        Win Rate: {(user_info.get('total_win', 0) / max(user_info.get('total_bet', 1), 1) * 100):.1f}%
        Balance: ${user_info.get('balance', 0):.2f}
        
        Provide personalized betting tips and strategies for this user. Keep it practical and under 200 words.
        """
        
        ai_response = ai_assistant.get_response(user_id, prompt)
        
        message = f"""
🎯 <b>Personalized Betting Tips</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━
{ai_response}
━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>💡 Quick Actions:</b>
• Ask me specific questions
• Get match analysis
• Learn bankroll management
"""
        
        keyboard = [
            [InlineKeyboardButton("❓ Ask Question", callback_data="ai_chat"),
             InlineKeyboardButton("📊 Match Analysis", callback_data="ai_analysis")],
            [InlineKeyboardButton("🏠 Home", callback_data="home")]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    async def ai_analysis(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get AI match analysis"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        # Get recent matches for analysis
        live_matches = odds_api.get_live_matches()
        
        if live_matches:
            # Pick the first match for analysis
            match = live_matches[0]
            home_team = match.get('home_team', 'Team A')
            away_team = match.get('away_team', 'Team B')
            
            prompt = f"""
            Analyze this upcoming match: {home_team} vs {away_team}
            
            Provide:
            1. Key factors to consider
            2. Betting recommendations
            3. Risk assessment
            4. Best bet types for this match
            
            Keep it concise and actionable.
            """
            
            ai_response = ai_assistant.get_response(user_id, prompt)
            
            message = f"""
📊 <b>Match Analysis: {home_team} vs {away_team}</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━
{ai_response}
━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>🎯 Next Steps:</b>
• View live games to place bets
• Get more specific analysis
• Ask me questions
"""
        else:
            message = """
📊 <b>Match Analysis</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━
No live matches available for analysis right now.

<b>💡 What I can help with:</b>
• General betting strategies
• Bankroll management
• Sports knowledge
• Specific match questions

Try asking me about a specific team or sport!
"""
        
        keyboard = [
            [InlineKeyboardButton("🏆 Live Games", callback_data="live"),
             InlineKeyboardButton("❓ Ask Question", callback_data="ai_chat")],
            [InlineKeyboardButton("🏠 Home", callback_data="home")]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    async def ai_bankroll(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get AI bankroll management advice"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        user_info = db.get_user_info(user_id)
        balance = user_info.get('balance', 0)
        
        prompt = f"""
        User has ${balance:.2f} balance.
        Total bets: {user_info.get('total_bet', 0)}
        Win rate: {(user_info.get('total_win', 0) / max(user_info.get('total_bet', 1), 1) * 100):.1f}%
        
        Provide personalized bankroll management advice including:
        1. Recommended bet sizes
        2. Daily/weekly limits
        3. Risk management strategies
        4. When to increase/decrease betting
        
        Keep it practical and specific to their situation.
        """
        
        ai_response = ai_assistant.get_response(user_id, prompt)
        
        message = f"""
💰 <b>Bankroll Management Advice</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>Your Current Status:</b>
• Balance: ${balance:.2f}
• Total Bets: {user_info.get('total_bet', 0)}
• Win Rate: {(user_info.get('total_win', 0) / max(user_info.get('total_bet', 1), 1) * 100):.1f}%

━━━━━━━━━━━━━━━━━━━━━━━━━━
{ai_response}
━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        keyboard = [
            [InlineKeyboardButton("💵 Deposit Funds", callback_data="deposit"),
             InlineKeyboardButton("📊 My Stats", callback_data="balance")],
            [InlineKeyboardButton("❓ Ask Question", callback_data="ai_chat"),
             InlineKeyboardButton("🏠 Home", callback_data="home")]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    async def ai_sports(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get AI sports knowledge"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        prompt = """
        Provide comprehensive sports betting knowledge including:
        1. Popular bet types (moneyline, spread, totals)
        2. How odds work
        3. Key factors in different sports
        4. Common mistakes to avoid
        5. Best practices for beginners
        
        Make it educational and easy to understand.
        """
        
        ai_response = ai_assistant.get_response(user_id, prompt)
        
        message = f"""
🏆 <b>Sports Betting Knowledge</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━
{ai_response}
━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>📚 Learn More:</b>
• Ask specific questions
• Get personalized tips
• Analyze matches
"""
        
        keyboard = [
            [InlineKeyboardButton("❓ Ask Question", callback_data="ai_chat"),
             InlineKeyboardButton("💡 Get Tips", callback_data="ai_tips")],
            [InlineKeyboardButton("🏆 Live Games", callback_data="live"),
             InlineKeyboardButton("🏠 Home", callback_data="home")]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle general messages for AI conversation"""
        user_id = update.effective_user.id
        user_message = update.message.text
        
        # Check if user is in AI chat mode
        if context.user_data.get('ai_chat_mode'):
            # Enhanced AI response for chat mode
            response = ai_assistant.get_response(user_id, f"User is in AI chat mode and said: {user_message}")
            
            # Create response with AI chat interface
            message = f"""
🤖 <b>AI Assistant Response</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━
{response}
━━━━━━━━━━━━━━━━━━━━━━━━━━

<i>Ask me anything about betting, sports, or strategies!</i>
"""
            
            keyboard = [
                [InlineKeyboardButton("💡 Get Tips", callback_data="ai_tips"),
                 InlineKeyboardButton("📊 Match Analysis", callback_data="ai_analysis")],
                [InlineKeyboardButton("💰 Bankroll Advice", callback_data="ai_bankroll"),
                 InlineKeyboardButton("🏆 Sports Knowledge", callback_data="ai_sports")],
                [InlineKeyboardButton("🏠 Home", callback_data="home")]
            ]
            
            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
        else:
            # Regular AI response
            response = ai_assistant.get_response(user_id, user_message)
            await update.message.reply_text(response, parse_mode="HTML")

    async def admin_approve_deposit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin command to approve deposit"""
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("❌ This command is only for admins.")
            return
        
        try:
            tx_id = context.args[0]
            
            if db.approve_transaction(tx_id, ADMIN_ID):
                await update.message.reply_text(f"✅ Deposit request #{tx_id} approved.")
                logger.info(f"Deposit approved: TX {tx_id}")
            else:
                await update.message.reply_text("❌ Transaction not found.")
        except (IndexError, ValueError):
            await update.message.reply_text("❌ Usage: /approve_deposit <tx_id>")

    async def admin_approve_withdraw(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin command to approve withdrawal"""
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("❌ This command is only for admins.")
            return
        
        try:
            tx_id = context.args[0]
            
            if db.approve_transaction(tx_id, ADMIN_ID):
                await update.message.reply_text(f"✅ Withdrawal request #{tx_id} approved.")
                logger.info(f"Withdrawal approved: TX {tx_id}")
            else:
                await update.message.reply_text("❌ Transaction not found.")
        except (IndexError, ValueError):
            await update.message.reply_text("❌ Usage: /approve_withdraw <tx_id>")

    async def admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin command to view statistics"""
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("❌ This command is only for admins.")
            return
        
        stats = db.get_stats()
        users = db.get_all_users()
        pending = db.get_pending_transactions()
        
        message = f"""
<b>📊 System Statistics</b>

━━━━━━━━━━━━━━━━━━

<b>👥 Users:</b>
• Total: {stats.get('total_users', 0)}
• Active: {len([u for u in users if u['balance'] > 0])}

<b>🎯 Betting Stats:</b>
• Total Bets: {stats.get('total_bets', 0)}
• Total Wins: {stats.get('total_wins', 0)}
• Total Losses: {stats.get('total_losses', 0)}

<b>💰 Financial:</b>
• Total Balance: {CURRENCY_SYMBOL} {stats.get('total_balance', 0):.0f}
• Pending: {len(pending)} transactions

━━━━━━━━━━━━━━━━━━

<b>🏆 Top 10 Users:</b>
"""
        
        sorted_users = sorted(users, key=lambda x: x['balance'], reverse=True)[:10]
        for idx, user in enumerate(sorted_users, 1):
            message += f"\n{idx}. @{user['username'] or user['user_id']} - {CURRENCY_SYMBOL} {user['balance']:.0f}"
        
        keyboard = [[InlineKeyboardButton("📋 Pending", callback_data="pending"),
                    InlineKeyboardButton("🏠 Home", callback_data="home")]]
        
        await update.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all callback queries"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "home":
            # Create a fake update object for start() to use
            fake_update = FakeUpdate(query)
            await self.start(fake_update, context)
        elif query.data == "help":
            fake_update = FakeUpdate(query)
            await self.help_command(fake_update, context)
        elif query.data == "live":
            fake_update = FakeUpdate(query)
            await self.live_matches(fake_update, context)
        elif query.data == "upcoming":
            fake_update = FakeUpdate(query)
            await self.upcoming_matches(fake_update, context)
        elif query.data == "balance":
            fake_update = FakeUpdate(query)
            await self.balance(fake_update, context)
        elif query.data == "mybets":
            fake_update = FakeUpdate(query)
            await self.my_bets(fake_update, context)
        elif query.data == "deposit":
            fake_update = FakeUpdate(query)
            await self.deposit(fake_update, context)
        elif query.data == "withdraw":
            fake_update = FakeUpdate(query)
            await self.withdraw(fake_update, context)
        elif query.data == "admin_panel":
            fake_update = FakeUpdate(query)
            await self.admin_panel(fake_update, context)
        elif query.data == "ai_chat":
            fake_update = FakeUpdate(query)
            await self.ai_chat(fake_update, context)
        elif query.data == "ai_tips":
            fake_update = FakeUpdate(query)
            await self.ai_tips(fake_update, context)
        elif query.data == "ai_analysis":
            fake_update = FakeUpdate(query)
            await self.ai_analysis(fake_update, context)
        elif query.data == "ai_bankroll":
            fake_update = FakeUpdate(query)
            await self.ai_bankroll(fake_update, context)
        elif query.data == "ai_sports":
            fake_update = FakeUpdate(query)
            await self.ai_sports(fake_update, context)
        elif query.data.startswith("approve_deposit_"):
            if query.from_user.id != ADMIN_ID:
                await query.answer("❌ Unauthorized", show_alert=True)
                return
            tx_id = query.data.split("_")[-1]
            if db.approve_transaction(tx_id, ADMIN_ID):
                await query.edit_message_caption(
                    caption=f"✅ Deposit #{tx_id} approved.",
                )
            else:
                await query.answer("❌ Transaction not found", show_alert=True)
        elif query.data.startswith("reject_deposit_"):
            if query.from_user.id != ADMIN_ID:
                await query.answer("❌ Unauthorized", show_alert=True)
                return
            tx_id = query.data.split("_")[-1]
            if db.reject_transaction(tx_id, ADMIN_ID):
                await query.edit_message_caption(
                    caption=f"❌ Deposit #{tx_id} rejected.",
                )
            else:
                await query.answer("❌ Transaction not found", show_alert=True)
        elif query.data.startswith("approve_withdraw_"):
            if query.from_user.id != ADMIN_ID:
                await query.answer("❌ Unauthorized", show_alert=True)
                return
            tx_id = query.data.split("_")[-1]
            if db.approve_transaction(tx_id, ADMIN_ID):
                await query.edit_message_text(
                    text=f"✅ Withdrawal #{tx_id} approved.",
                    parse_mode="HTML"
                )
            else:
                await query.answer("❌ Transaction not found", show_alert=True)
        elif query.data.startswith("reject_withdraw_"):
            if query.from_user.id != ADMIN_ID:
                await query.answer("❌ Unauthorized", show_alert=True)
                return
            tx_id = query.data.split("_")[-1]
            if db.reject_transaction(tx_id, ADMIN_ID):
                await query.edit_message_text(
                    text=f"❌ Withdrawal #{tx_id} rejected.",
                    parse_mode="HTML"
                )
            else:
                await query.answer("❌ Transaction not found", show_alert=True)
        elif query.data in ["settings", "about"]:
            message = f"""
<b>⚙️ Bot Settings</b>

━━━━━━━━━━━━━━━━━━
<b>Version:</b> 1.0.0
<b>Status:</b> ✅ Online
<b>AI:</b> ChatGPT (OpenAI)
<b>Voice:</b> ElevenLabs (English)
<b>Database:</b> SQLite
<b>Region:</b> USA 🇺🇸
<b>Currency:</b> USD ($)
━━━━━━━━━━━━━━━━━━
"""
            keyboard = [[InlineKeyboardButton("🏠 Home", callback_data="home")]]
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )

    def setup_handlers(self):
        """Setup all command and message handlers"""
        # User commands
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("live", self.live_matches))
        self.app.add_handler(CommandHandler("upcoming", self.upcoming_matches))
        self.app.add_handler(CommandHandler("mybets", self.my_bets))
        self.app.add_handler(CommandHandler("balance", self.balance))
        self.app.add_handler(CommandHandler("help", self.help_command))
        
        # Admin commands
        self.app.add_handler(CommandHandler("approve_deposit", self.admin_approve_deposit))
        self.app.add_handler(CommandHandler("approve_withdraw", self.admin_approve_withdraw))
        self.app.add_handler(CommandHandler("stats", self.admin_stats))
        
        # Betting conversation - MUST be added before generic callback handler
        bet_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.start_bet, pattern="^start_bet$")],
            states={
                ASKING_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_bet_amount)],
                ASKING_TEAM: [CallbackQueryHandler(self.team_selected, pattern="^team_")]
            },
            fallbacks=[CommandHandler("start", self.start)],
            per_message=True
        )
        self.app.add_handler(bet_conv)
        
        # Deposit conversation
        deposit_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.deposit, pattern="^deposit$")],
            states={
                ASKING_DEPOSIT_AMOUNT: [
                    CallbackQueryHandler(self.deposit_payment_method, pattern="^deposit_btc$|^deposit_eth$|^deposit_usdt$"),
                    CallbackQueryHandler(self.deposit_proof, pattern="^deposit_proof$"),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_deposit_amount)
                ],
                ASKING_MESSAGE: [
                    CallbackQueryHandler(self.deposit_proof, pattern="^deposit_proof$"),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_deposit_proof),
                    MessageHandler(filters.PHOTO, self.handle_deposit_proof)
                ]
            },
            fallbacks=[CommandHandler("start", self.start)],
            per_message=True
        )
        self.app.add_handler(deposit_conv)
        
        # Withdraw conversation
        withdraw_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.withdraw, pattern="^withdraw$")],
            states={
                ASKING_WITHDRAW_AMOUNT: [
                    CallbackQueryHandler(self.withdraw_payment_method, pattern="^withdraw_btc$|^withdraw_eth$|^withdraw_usdt$"),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_withdraw_amount)
                ]
            },
            fallbacks=[CommandHandler("start", self.start)],
            per_message=True
        )
        self.app.add_handler(withdraw_conv)
        
        # Wallet address setting conversation
        wallet_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.admin_set_wallet_crypto, pattern="^admin_set_btc$|^admin_set_eth$|^admin_set_usdt$")],
            states={
                ASKING_WALLET_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.admin_handle_wallet_address)]
            },
            fallbacks=[CommandHandler("start", self.start)],
            per_message=True
        )
        self.app.add_handler(wallet_conv)
        
        # Specific callback handlers - BEFORE generic handler
        self.app.add_handler(CallbackQueryHandler(self.match_callback, pattern="^match_"))
        self.app.add_handler(CallbackQueryHandler(self.team_selected, pattern="^team_"))
        self.app.add_handler(CallbackQueryHandler(self.get_ai_tip, pattern="^get_ai_tip$"))
        self.app.add_handler(CallbackQueryHandler(self.deposit_proof, pattern="^deposit_proof$"))
        
        # Admin callback handlers - BEFORE generic handler
        self.app.add_handler(CallbackQueryHandler(self.admin_panel, pattern="^admin_panel$"))
        self.app.add_handler(CallbackQueryHandler(self.admin_users, pattern="^admin_users$"))
        self.app.add_handler(CallbackQueryHandler(self.admin_transactions, pattern="^admin_transactions$"))
        self.app.add_handler(CallbackQueryHandler(self.admin_compliance, pattern="^admin_compliance$"))
        self.app.add_handler(CallbackQueryHandler(self.admin_security, pattern="^admin_security$"))
        self.app.add_handler(CallbackQueryHandler(self.admin_stats, pattern="^admin_stats$"))
        self.app.add_handler(CallbackQueryHandler(self.admin_kyc, pattern="^admin_kyc$"))
        self.app.add_handler(CallbackQueryHandler(self.admin_deposits, pattern="^admin_deposits$"))
        self.app.add_handler(CallbackQueryHandler(self.admin_withdrawals, pattern="^admin_withdrawals$"))
        self.app.add_handler(CallbackQueryHandler(self.admin_reports, pattern="^admin_reports$"))
        self.app.add_handler(CallbackQueryHandler(self.admin_settings, pattern="^admin_settings$"))
        self.app.add_handler(CallbackQueryHandler(self.admin_wallet_addresses, pattern="^admin_wallet_addresses$"))
        
        # Generic callback handler - LAST so specific patterns take priority
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))

    async def run(self):
        """Run the bot"""
        self.app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        self.setup_handlers()
        
        logger.info("🤖 Betting Bot is starting...")
        
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()


async def main():
    """Main entry point"""
    bot = BettingBot()
    await bot.run()
    
    # Keep the bot running
    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
