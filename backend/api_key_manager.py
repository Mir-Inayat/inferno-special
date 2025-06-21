"""
API Key Pool Management for Gemini API
Handles multiple API keys for rate limit management and auto-rotation
"""

import random
import time
import sqlite3
from typing import List, Optional, Dict
import google.generativeai as genai

class APIKeyManager:
    def __init__(self, db_path: str = "inferno_documents.db"):
        self.db_path = db_path
        self.current_key_index = 0
        self._init_key_storage()
        
        # Default API keys pool - in production, store these securely
        self.default_keys = [
            "AIzaSyA-ZoIsJwcQ9j2HAPGcFIIVbyIuknIsPtw",  # Original key
            "AIzaSyCh9vqgzPp3tLAYGedMRtVjV2eQ5g26lZU",
            "AIzaSyAIi6EH9jGXiYgX6c0_leMpmRzcGAmz5Zo",
            "AIzaSyCl3Yd3FtYpVZIDGco0OIZitQTxEy9U9Ro"
            # Add 4 more keys here for production use
            # "AIzaSyB-...",  # Key 2
            # "AIzaSyC-...",  # Key 3
            # "AIzaSyD-...",  # Key 4
            # "AIzaSyE-...",  # Key 5
        ]
        
        # Initialize with default keys if no keys exist
        if not self.get_active_keys():
            for i, key in enumerate(self.default_keys):
                self.add_api_key(key, f"Default Key {i+1}", is_active=True)
    
    def _init_key_storage(self):
        """Initialize database table for API key management"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_name TEXT NOT NULL,
                api_key TEXT NOT NULL UNIQUE,
                is_active BOOLEAN DEFAULT TRUE,
                quota_exceeded BOOLEAN DEFAULT FALSE,
                last_used TIMESTAMP,
                usage_count INTEGER DEFAULT 0,
                error_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_usage_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_key_id INTEGER,
                operation_type TEXT,
                success BOOLEAN,
                error_message TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (api_key_id) REFERENCES api_keys (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_api_key(self, api_key: str, name: str, is_active: bool = True, notes: str = ""):
        """Add a new API key to the pool"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO api_keys (key_name, api_key, is_active, notes)
                VALUES (?, ?, ?, ?)
            ''', (name, api_key, is_active, notes))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            print(f"API key already exists: {name}")
            return None
        finally:
            conn.close()
    
    def get_active_keys(self) -> List[Dict]:
        """Get all active API keys"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, key_name, api_key, quota_exceeded, usage_count, error_count
            FROM api_keys 
            WHERE is_active = TRUE 
            ORDER BY usage_count ASC, error_count ASC
        ''')
        
        keys = []
        for row in cursor.fetchall():
            keys.append({
                'id': row[0],
                'name': row[1],
                'key': row[2],
                'quota_exceeded': bool(row[3]),
                'usage_count': row[4],
                'error_count': row[5]
            })
        
        conn.close()
        return keys
    
    def get_current_key(self) -> Optional[str]:
        """Get the current API key to use"""
        active_keys = self.get_active_keys()
        
        if not active_keys:
            print("No active API keys available!")
            return None
        
        # Filter out quota exceeded keys
        available_keys = [k for k in active_keys if not k['quota_exceeded']]
        
        if not available_keys:
            # If all keys are quota exceeded, reset them (new day cycle)
            self._reset_quota_status()
            available_keys = [k for k in active_keys if not k['quota_exceeded']]
        
        if not available_keys:
            print("All API keys have quota issues!")
            return active_keys[0]['key']  # Fallback to first key
        
        # Use round-robin selection with preference for least used keys
        if self.current_key_index >= len(available_keys):
            self.current_key_index = 0
        
        selected_key = available_keys[self.current_key_index]
        return selected_key['key']
    
    def mark_key_quota_exceeded(self, api_key: str):
        """Mark an API key as quota exceeded"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE api_keys 
            SET quota_exceeded = TRUE 
            WHERE api_key = ?
        ''', (api_key,))
        
        conn.commit()
        conn.close()
        
        # Move to next key
        self.current_key_index += 1
        print(f"API key quota exceeded, switching to next key")
    
    def log_api_usage(self, api_key: str, operation: str, success: bool, error_message: str = None):
        """Log API usage for monitoring"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get key ID
        cursor.execute('SELECT id FROM api_keys WHERE api_key = ?', (api_key,))
        key_result = cursor.fetchone()
        
        if not key_result:
            conn.close()
            return
        
        key_id = key_result[0]
        
        # Log usage
        cursor.execute('''
            INSERT INTO api_usage_log (api_key_id, operation_type, success, error_message)
            VALUES (?, ?, ?, ?)
        ''', (key_id, operation, success, error_message))
        
        # Update key statistics
        if success:
            cursor.execute('''
                UPDATE api_keys 
                SET usage_count = usage_count + 1, last_used = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (key_id,))
        else:
            cursor.execute('''
                UPDATE api_keys 
                SET error_count = error_count + 1
                WHERE id = ?
            ''', (key_id,))
        
        conn.commit()
        conn.close()
    
    def _reset_quota_status(self):
        """Reset quota exceeded status for all keys (new day/cycle)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('UPDATE api_keys SET quota_exceeded = FALSE')
        conn.commit()
        conn.close()
        print("Reset quota status for all API keys")
    
    def get_key_statistics(self) -> List[Dict]:
        """Get usage statistics for all keys"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT k.key_name, k.is_active, k.quota_exceeded, k.usage_count, 
                   k.error_count, k.last_used,
                   COUNT(l.id) as total_operations,
                   SUM(CASE WHEN l.success THEN 1 ELSE 0 END) as successful_operations
            FROM api_keys k
            LEFT JOIN api_usage_log l ON k.id = l.api_key_id
            GROUP BY k.id
            ORDER BY k.usage_count ASC
        ''')
        
        stats = []
        for row in cursor.fetchall():
            stats.append({
                'name': row[0],
                'active': bool(row[1]),
                'quota_exceeded': bool(row[2]),
                'usage_count': row[3],
                'error_count': row[4],
                'last_used': row[5],
                'total_operations': row[6] or 0,
                'successful_operations': row[7] or 0
            })
        
        conn.close()
        return stats
    
    def configure_genai(self) -> bool:
        """Configure Gemini AI with current key"""
        current_key = self.get_current_key()
        if current_key:
            genai.configure(api_key=current_key)
            return True
        return False
    
    def switch_to_next_key(self):
        """Manually switch to the next available key"""
        self.current_key_index += 1
        return self.configure_genai()


# Enhanced DocumentProcessor with API key management
class EnhancedDocumentProcessor:
    def __init__(self, db_path: str = "inferno_documents.db"):
        self.db_path = db_path
        self.api_manager = APIKeyManager(db_path)
        
        # Configure initial API key
        if not self.api_manager.configure_genai():
            raise Exception("No valid API keys available")
        
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.max_retries = 3
        self.retry_delay = 2  # seconds
    
    def _make_api_call_with_retry(self, operation: str, func, *args, **kwargs):
        """Make API call with automatic retry and key switching"""
        current_key = self.api_manager.get_current_key()
        
        for attempt in range(self.max_retries):
            try:
                result = func(*args, **kwargs)
                
                # Log successful usage
                self.api_manager.log_api_usage(
                    current_key, operation, True
                )
                
                return result
                
            except Exception as e:
                error_msg = str(e)
                print(f"API call attempt {attempt + 1} failed: {error_msg}")
                
                # Check if it's a quota error
                if "quota" in error_msg.lower() or "limit" in error_msg.lower():
                    self.api_manager.mark_key_quota_exceeded(current_key)
                    self.api_manager.log_api_usage(
                        current_key, operation, False, error_msg
                    )
                    
                    # Try to switch to next key
                    if self.api_manager.switch_to_next_key():
                        current_key = self.api_manager.get_current_key()
                        self.model = genai.GenerativeModel('gemini-1.5-flash')
                        continue
                    else:
                        raise Exception("All API keys exhausted")
                
                # For other errors, log and retry with delay
                self.api_manager.log_api_usage(
                    current_key, operation, False, error_msg
                )
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    raise e
    
    def generate_content(self, prompt: str):
        """Generate content with automatic API key management"""
        return self._make_api_call_with_retry(
            "generate_content",
            self.model.generate_content,
            prompt
        )
    
    def analyze_image(self, image_data, prompt: str):
        """Analyze image with automatic API key management"""
        return self._make_api_call_with_retry(
            "analyze_image",
            self.model.generate_content,
            [prompt, image_data]
        )


if __name__ == "__main__":
    # Test the API key manager
    manager = APIKeyManager()
    
    print("API Key Statistics:")
    stats = manager.get_key_statistics()
    for stat in stats:
        print(f"  {stat['name']}: {stat['usage_count']} uses, {stat['error_count']} errors")
    
    print(f"\nCurrent key: {manager.get_current_key()[:20]}...")
