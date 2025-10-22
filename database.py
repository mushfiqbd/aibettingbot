import sqlite3
import os
import logging
from datetime import datetime
from config import SQLITE_DB_PATH, INITIAL_BALANCE, DATABASE_TYPE

logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        self.db_path = SQLITE_DB_PATH
        self.init_db()

    def get_connection(self):
        """Get a database connection"""
        try:
            # Ensure the directory exists
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
            
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.OperationalError as e:
            logger.error(f"Database connection error: {e}")
            logger.error(f"Database path: {self.db_path}")
            logger.error(f"Current working directory: {os.getcwd()}")
            raise

    def init_db(self):
        """Initialize the database with required tables"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                first_name TEXT,
                last_name TEXT,
                balance REAL DEFAULT 0,
                total_bet INTEGER DEFAULT 0,
                total_win INTEGER DEFAULT 0,
                total_loss INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_verified BOOLEAN DEFAULT 0
            )
        """)

        # Create bets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bets (
                bet_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                match_id TEXT NOT NULL,
                team_name TEXT NOT NULL,
                odds REAL NOT NULL,
                amount REAL NOT NULL,
                potential_win REAL,
                status TEXT DEFAULT 'pending',
                result TEXT DEFAULT 'waiting',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # Create matches table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                match_id TEXT PRIMARY KEY,
                sport TEXT,
                home_team TEXT,
                away_team TEXT,
                commence_time TIMESTAMP,
                status TEXT DEFAULT 'pending',
                result TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create transactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                admin_approved_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                approved_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # Create audit log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER,
                action TEXT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create wallet addresses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wallet_addresses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crypto_type TEXT UNIQUE NOT NULL,
                wallet_address TEXT NOT NULL,
                updated_by INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (updated_by) REFERENCES users(user_id)
            )
        """)

        # Create deposits table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS deposits (
                tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                method TEXT DEFAULT 'BTC',
                status TEXT DEFAULT 'pending',
                transaction_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # Create withdrawals table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS withdrawals (
                tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                method TEXT NOT NULL,
                wallet_address TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # Create admin_logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        conn.commit()
        conn.close()

    def add_user(self, user_id, username, first_name, last_name):
        """Add a new user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (user_id, username, first_name, last_name, balance)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, username, first_name, last_name, INITIAL_BALANCE))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def user_exists(self, user_id):
        """Check if user exists"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result is not None

    def get_user_balance(self, user_id):
        """Get user balance"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0

    def get_user_info(self, user_id):
        """Get user information"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return dict(result) if result else None

    def update_balance(self, user_id, amount):
        """Update user balance"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET balance = balance + ? WHERE user_id = ?
        """, (amount, user_id))
        conn.commit()
        conn.close()

    def place_bet(self, user_id, match_id, team_name, odds, amount):
        """Place a new bet"""
        conn = self.get_connection()
        cursor = conn.cursor()
        potential_win = amount * odds
        cursor.execute("""
            INSERT INTO bets (user_id, match_id, team_name, odds, amount, potential_win)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, match_id, team_name, odds, amount, potential_win))
        conn.commit()
        
        # Update user balance (deduct bet amount)
        cursor.execute("UPDATE users SET balance = balance - ?, total_bet = total_bet + 1 WHERE user_id = ?", 
                      (amount, user_id))
        conn.commit()
        
        bet_id = cursor.lastrowid
        conn.close()
        return bet_id

    def get_user_bets(self, user_id, status=None):
        """Get user bets"""
        conn = self.get_connection()
        cursor = conn.cursor()
        if status:
            cursor.execute("""
                SELECT * FROM bets WHERE user_id = ? AND status = ? ORDER BY created_at DESC
            """, (user_id, status))
        else:
            cursor.execute("""
                SELECT * FROM bets WHERE user_id = ? ORDER BY created_at DESC
            """, (user_id,))
        results = cursor.fetchall()
        conn.close()
        return [dict(row) for row in results]

    def settle_bet(self, bet_id, result, win_amount=0):
        """Settle a bet (won or lost)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT user_id, amount FROM bets WHERE bet_id = ?", (bet_id,))
        bet = cursor.fetchone()
        
        if not bet:
            conn.close()
            return False
        
        user_id, bet_amount = bet[0], bet[1]
        
        cursor.execute("""
            UPDATE bets SET status = ?, result = ?, resolved_at = CURRENT_TIMESTAMP 
            WHERE bet_id = ?
        """, ('resolved', result, bet_id))
        
        if result == 'won':
            cursor.execute("""
                UPDATE users SET balance = balance + ?, total_win = total_win + 1 
                WHERE user_id = ?
            """, (win_amount, user_id))
        else:
            cursor.execute("""
                UPDATE users SET total_loss = total_loss + 1 WHERE user_id = ?
            """, (user_id,))
        
        conn.commit()
        conn.close()
        return True

    def request_deposit(self, user_id, amount):
        """Request a deposit"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO transactions (user_id, type, amount, status)
            VALUES (?, ?, ?, 'pending')
        """, (user_id, 'deposit', amount))
        conn.commit()
        tx_id = cursor.lastrowid
        conn.close()
        return tx_id

    def request_withdraw(self, user_id, amount):
        """Request a withdrawal"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO transactions (user_id, type, amount, status)
            VALUES (?, ?, ?, 'pending')
        """, (user_id, 'withdraw', amount))
        conn.commit()
        tx_id = cursor.lastrowid
        conn.close()
        return tx_id

    def approve_transaction(self, tx_id, admin_id):
        """Approve a transaction"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id, type, amount FROM transactions WHERE tx_id = ?
        """, (tx_id,))
        transaction = cursor.fetchone()
        
        if not transaction:
            conn.close()
            return False
        
        user_id, tx_type, amount = transaction
        
        cursor.execute("""
            UPDATE transactions SET status = ?, admin_approved_by = ?, approved_at = CURRENT_TIMESTAMP
            WHERE tx_id = ?
        """, ('approved', admin_id, tx_id))
        
        if tx_type == 'deposit':
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        else:  # withdraw
            cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
        
        conn.commit()
        conn.close()
        return True

    def reject_transaction(self, tx_id, admin_id):
        """Reject a transaction without changing balance"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # Ensure transaction exists
            cursor.execute("""
                SELECT tx_id FROM transactions WHERE tx_id = ?
            """, (tx_id,))
            row = cursor.fetchone()
            if not row:
                return False

            cursor.execute(
                """
                UPDATE transactions
                SET status = 'rejected', admin_approved_by = ?, approved_at = CURRENT_TIMESTAMP
                WHERE tx_id = ?
                """,
                (admin_id, tx_id),
            )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_pending_transactions(self):
        """Get all pending transactions"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.*, u.username FROM transactions t
            JOIN users u ON t.user_id = u.user_id
            WHERE t.status = 'pending'
            ORDER BY t.created_at DESC
        """)
        results = cursor.fetchall()
        conn.close()
        return [dict(row) for row in results]

    def get_pending_deposits(self):
        """Get all pending deposits"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.*, u.username FROM transactions t
            JOIN users u ON t.user_id = u.user_id
            WHERE t.status = 'pending' AND t.type = 'deposit'
            ORDER BY t.created_at DESC
        """)
        results = cursor.fetchall()
        conn.close()
        return [dict(row) for row in results]

    def get_pending_withdrawals(self):
        """Get all pending withdrawals"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.*, u.username FROM transactions t
            JOIN users u ON t.user_id = u.user_id
            WHERE t.status = 'pending' AND t.type = 'withdraw'
            ORDER BY t.created_at DESC
        """)
        results = cursor.fetchall()
        conn.close()
        return [dict(row) for row in results]

    def get_all_users(self):
        """Get all users"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
        results = cursor.fetchall()
        conn.close()
        return [dict(row) for row in results]

    def get_stats(self):
        """Get overall statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT user_id) as total_users,
                SUM(total_bet) as total_bets,
                SUM(total_win) as total_wins,
                SUM(total_loss) as total_losses,
                SUM(balance) as total_balance
            FROM users
        """)
        result = cursor.fetchone()
        conn.close()
        return dict(result) if result else {}

    def log_action(self, admin_id, action, details):
        """Log admin action"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_log (admin_id, action, details)
            VALUES (?, ?, ?)
        """, (admin_id, action, details))
        conn.commit()
        conn.close()

    def set_wallet_address(self, crypto_type, wallet_address, admin_id):
        """Set wallet address for a cryptocurrency"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO wallet_addresses (crypto_type, wallet_address, updated_by)
                VALUES (?, ?, ?)
            """, (crypto_type.upper(), wallet_address, admin_id))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error setting wallet address: {e}")
            return False
        finally:
            conn.close()

    def get_wallet_address(self, crypto_type):
        """Get wallet address for a cryptocurrency"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT wallet_address FROM wallet_addresses 
                WHERE crypto_type = ?
            """, (crypto_type.upper(),))
            result = cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting wallet address: {e}")
            return None
        finally:
            conn.close()

    def get_all_wallet_addresses(self):
        """Get all wallet addresses"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT crypto_type, wallet_address, updated_at 
                FROM wallet_addresses 
                ORDER BY crypto_type
            """)
            results = cursor.fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error getting wallet addresses: {e}")
            return []
        finally:
            conn.close()


    def get_all_users(self):
        """Get all users"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
            results = cursor.fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []
        finally:
            conn.close()

    def get_pending_deposits(self):
        """Get pending deposits"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT * FROM deposits 
                WHERE status = 'pending' 
                ORDER BY created_at DESC
            """)
            results = cursor.fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error getting pending deposits: {e}")
            return []
        finally:
            conn.close()

    def get_pending_withdrawals(self):
        """Get pending withdrawals"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT * FROM withdrawals 
                WHERE status = 'pending' 
                ORDER BY created_at DESC
            """)
            results = cursor.fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error getting pending withdrawals: {e}")
            return []
        finally:
            conn.close()

    def get_stats(self):
        """Get platform statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # Get user stats
            cursor.execute("SELECT COUNT(*) as total_users FROM users")
            total_users = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(balance) as total_balance FROM users")
            total_balance = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT COUNT(*) as total_bets FROM bets")
            total_bets = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) as total_wins FROM bets WHERE result = 'win'")
            total_wins = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) as total_losses FROM bets WHERE result = 'loss'")
            total_losses = cursor.fetchone()[0]
            
            return {
                'total_users': total_users,
                'total_balance': total_balance,
                'total_bets': total_bets,
                'total_wins': total_wins,
                'total_losses': total_losses
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}
        finally:
            conn.close()

    def request_deposit(self, user_id, amount):
        """Request a deposit"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO deposits (user_id, amount, status, created_at)
                VALUES (?, ?, 'pending', CURRENT_TIMESTAMP)
            """, (user_id, amount))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error requesting deposit: {e}")
            return None
        finally:
            conn.close()

    def request_withdrawal(self, user_id, amount, method, wallet_address):
        """Request a withdrawal"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO withdrawals (user_id, amount, method, wallet_address, status, created_at)
                VALUES (?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP)
            """, (user_id, amount, method, wallet_address))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error requesting withdrawal: {e}")
            return None
        finally:
            conn.close()

    def log_action(self, user_id, action, details):
        """Log admin action"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO admin_logs (user_id, action, details, created_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (user_id, action, details))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error logging action: {e}")
            return False
        finally:
            conn.close()


# Initialize database
db = Database()
