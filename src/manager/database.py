import sqlite3
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecurityDatabase:
    def __init__(self, db_path="data/security.db"):
        self.db_path = db_path
        Path("data").mkdir(exist_ok=True)
        self.init_database()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_database(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        # Таблица разрешенных сервисов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS allowed_services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url_pattern TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица запрещенных сервисов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blocked_services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url_pattern TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица инцидентов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source_ip TEXT NOT NULL,
                destination_url TEXT NOT NULL,
                action TEXT NOT NULL,
                severity TEXT DEFAULT 'medium',
                description TEXT
            )
        ''')

        # Добавляем тестовые данные
        cursor.execute('''
            INSERT OR IGNORE INTO allowed_services (url_pattern) 
            VALUES 
                ('https://github.com/test/Test_KR_2'),
                ('https://api.trusted-service.com/v1/'),
                ('https://internal-api.local/')
        ''')

        cursor.execute('''
            INSERT OR IGNORE INTO blocked_services (url_pattern) 
            VALUES 
                ('https://github.com/test/Test_KR'),
                ('https://api.twitter.com/'),
                ('https://api.telegram.org/'),
                ('https://*.cloudstorage.com/'),
                ('https://vk.com/api/')
        ''')

        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")

    def is_url_allowed(self, url):
        """Проверяет, разрешен ли URL"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Сначала проверяем в запрещенных (более высокий приоритет)
        cursor.execute('''
            SELECT url_pattern FROM blocked_services 
            WHERE ? LIKE replace(replace(url_pattern, '*', '%'), '?', '_')
        ''', (url,))

        if cursor.fetchone():
            conn.close()
            return False

        # Проверяем в разрешенных
        cursor.execute('''
            SELECT url_pattern FROM allowed_services 
            WHERE ? LIKE replace(replace(url_pattern, '*', '%'), '?', '_')
        ''', (url,))

        result = cursor.fetchone() is not None
        conn.close()
        return result

    def log_incident(self, source_ip, destination_url, action, description="", severity="medium"):
        """Логирует инцидент безопасности"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO incidents 
            (source_ip, destination_url, action, severity, description) 
            VALUES (?, ?, ?, ?, ?)
        ''', (source_ip, destination_url, action, severity, description))

        conn.commit()
        conn.close()
        logger.warning(f"Security incident logged: {action} for {destination_url}")

    def get_incidents(self, limit=100):
        """Получает последние инциденты"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM incidents 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))

        incidents = cursor.fetchall()
        conn.close()
        return incidents

    def add_allowed_service(self, url_pattern):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO allowed_services (url_pattern) VALUES (?)', (url_pattern,))
        conn.commit()
        conn.close()

    def add_blocked_service(self, url_pattern):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO blocked_services (url_pattern) VALUES (?)', (url_pattern,))
        conn.commit()
        conn.close()