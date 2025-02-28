import sqlite3
from datetime import datetime
import os
import pickle
import json

class MessageDatabase:
    def __init__(self):
        self.db_path = "message_history.db"
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create messages history table (without message_text)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS message_history (
                    profile_url TEXT PRIMARY KEY,
                    sent_at TIMESTAMP,
                    status TEXT
                )
            """)
            
            # Create settings table for storing credentials and preferences
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            # Create cookies table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cookies (
                    domain TEXT,
                    cookie_data BLOB,
                    updated_at TIMESTAMP,
                    PRIMARY KEY (domain)
                )
            """)
            
            conn.commit()
    
    def save_message_status(self, profile_url: str, status: str):
        """Record a message attempt in the database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO message_history 
                (profile_url, sent_at, status) 
                VALUES (?, ?, ?)
            """, (profile_url, datetime.now(), status))
            conn.commit()
    
    def has_messaged_profile(self, profile_url: str) -> bool:
        """Check if a profile has been messaged successfully before"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT status FROM message_history 
                WHERE profile_url = ? AND status = 'success'
            """, (profile_url,))
            return cursor.fetchone() is not None
    
    def get_message_history(self):
        """Get all message history"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT profile_url, status, sent_at FROM message_history ORDER BY sent_at DESC")
            return cursor.fetchall()
    
    def save_setting(self, key: str, value: str):
        """Save a setting to the database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO settings (key, value) 
                VALUES (?, ?)
            """, (key, value))
            conn.commit()
    
    def get_setting(self, key: str, default: str = None) -> str:
        """Get a setting from the database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            result = cursor.fetchone()
            return result[0] if result else default
    
    def clear_history(self):
        """Clear all message history"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM message_history")
            conn.commit()

    def save_cookies(self, domain: str, cookies: list):
        """Save browser cookies to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Serialize cookies using pickle
                cookie_data = pickle.dumps(cookies)
                cursor.execute("""
                    INSERT OR REPLACE INTO cookies 
                    (domain, cookie_data, updated_at) 
                    VALUES (?, ?, ?)
                """, (domain, cookie_data, datetime.now()))
                conn.commit()
            return True
        except Exception as e:
            print(f"Error saving cookies: {str(e)}")
            return False

    def get_cookies(self, domain: str) -> list:
        """Get saved cookies for a domain"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT cookie_data FROM cookies WHERE domain = ?", (domain,))
                result = cursor.fetchone()
                if result:
                    return pickle.loads(result[0])
        except Exception as e:
            print(f"Error loading cookies: {str(e)}")
        return None

    def clear_cookies(self, domain: str = None):
        """Clear saved cookies for a domain or all domains"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if domain:
                cursor.execute("DELETE FROM cookies WHERE domain = ?", (domain,))
            else:
                cursor.execute("DELETE FROM cookies")
            conn.commit() 