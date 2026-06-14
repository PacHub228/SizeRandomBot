"""
Модуль для работы с базой данных
"""
import aiosqlite
import json
from datetime import datetime
from typing import List, Optional, Dict, Any


class Database:
    """Класс для работы с SQLite базой данных"""
    
    def __init__(self, db_path: str = "sizerandom.db"):
        self.db_path = db_path
    
    async def init_db(self):
        """Инициализация базы данных и создание таблиц"""
        async with aiosqlite.connect(self.db_path) as db:
            # Таблица пользователей
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица розыгрышей
            await db.execute("""
                CREATE TABLE IF NOT EXISTS giveaways (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    creator_id INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    media_type TEXT,
                    media_file_id TEXT,
                    button_text TEXT DEFAULT '🎉 Участвовать!',
                    winners_count INTEGER NOT NULL,
                    required_channels TEXT,
                    end_time TIMESTAMP,
                    manual_end BOOLEAN DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    message_id INTEGER,
                    chat_id INTEGER,
                    target_chat_id INTEGER,
                    captcha_enabled BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (creator_id) REFERENCES users(user_id)
                )
            """)
            
            # Таблица участников розыгрышей
            await db.execute("""
                CREATE TABLE IF NOT EXISTS participants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    giveaway_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(giveaway_id, user_id),
                    FOREIGN KEY (giveaway_id) REFERENCES giveaways(id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            # Таблица победителей
            await db.execute("""
                CREATE TABLE IF NOT EXISTS winners (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    giveaway_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    selected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (giveaway_id) REFERENCES giveaways(id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            await db.commit()
    
    async def add_user(self, user_id: int, username: str = None, first_name: str = None):
        """Добавление или обновление пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO users (user_id, username, first_name)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name
            """, (user_id, username, first_name))
            await db.commit()
    
    async def create_giveaway(self, creator_id: int, description: str, 
                            button_text: str, winners_count: int,
                            required_channels: List[str], end_time: Optional[datetime],
                            manual_end: bool, media_type: str = None,
                            media_file_id: str = None, target_chat_id: int = None,
                            captcha_enabled: bool = False) -> int:
        """Создание нового розыгрыша"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO giveaways (
                    creator_id, description, media_type, media_file_id,
                    button_text, winners_count, required_channels,
                    end_time, manual_end, target_chat_id, captcha_enabled
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                creator_id, description, media_type, media_file_id,
                button_text, winners_count, json.dumps(required_channels),
                end_time, manual_end, target_chat_id, captcha_enabled
            ))
            await db.commit()
            return cursor.lastrowid
    
    async def update_target_chat_id(self, giveaway_id: int, target_chat_id: int):
        """Обновление целевого канала публикации"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE giveaways SET target_chat_id = ?
                WHERE id = ?
            """, (target_chat_id, giveaway_id))
            await db.commit()
    
    async def get_giveaway(self, giveaway_id: int) -> Optional[Dict[str, Any]]:
        """Получение информации о розыгрыше"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM giveaways WHERE id = ?
            """, (giveaway_id,))
            row = await cursor.fetchone()
            if row:
                result = dict(row)
                result['required_channels'] = json.loads(result['required_channels'])
                return result
            return None
    
    async def update_giveaway_message(self, giveaway_id: int, chat_id: int, message_id: int):
        """Обновление информации о сообщении розыгрыша"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE giveaways SET chat_id = ?, message_id = ?
                WHERE id = ?
            """, (chat_id, message_id, giveaway_id))
            await db.commit()
    
    async def add_participant(self, giveaway_id: int, user_id: int, 
                            username: str = None, first_name: str = None) -> bool:
        """Добавление участника в розыгрыш. Возвращает True если участник добавлен"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO participants (giveaway_id, user_id, username, first_name)
                    VALUES (?, ?, ?, ?)
                """, (giveaway_id, user_id, username, first_name))
                await db.commit()
                return True
        except aiosqlite.IntegrityError:
            return False  # Участник уже зарегистрирован
    
    async def get_participants_count(self, giveaway_id: int) -> int:
        """Получение количества участников розыгрыша"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT COUNT(*) FROM participants WHERE giveaway_id = ?
            """, (giveaway_id,))
            row = await cursor.fetchone()
            return row[0] if row else 0
    
    async def get_participants(self, giveaway_id: int) -> List[Dict[str, Any]]:
        """Получение списка всех участников розыгрыша"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT user_id, username, first_name FROM participants
                WHERE giveaway_id = ?
            """, (giveaway_id,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def is_participant(self, giveaway_id: int, user_id: int) -> bool:
        """Проверка, является ли пользователь участником розыгрыша"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT 1 FROM participants WHERE giveaway_id = ? AND user_id = ?
            """, (giveaway_id, user_id))
            row = await cursor.fetchone()
            return row is not None
    
    async def add_winners(self, giveaway_id: int, winners: List[Dict[str, Any]]):
        """Добавление победителей розыгрыша"""
        async with aiosqlite.connect(self.db_path) as db:
            for winner in winners:
                await db.execute("""
                    INSERT INTO winners (giveaway_id, user_id, username, first_name)
                    VALUES (?, ?, ?, ?)
                """, (giveaway_id, winner['user_id'], winner.get('username'), winner.get('first_name')))
            await db.commit()
    
    async def finish_giveaway(self, giveaway_id: int):
        """Завершение розыгрыша"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE giveaways SET status = 'finished' WHERE id = ?
            """, (giveaway_id,))
            await db.commit()

    async def delete_giveaway(self, giveaway_id: int):
        """Удаление розыгрыша и всех связанных данных"""
        async with aiosqlite.connect(self.db_path) as db:
            # Удаляем победителей
            await db.execute("DELETE FROM winners WHERE giveaway_id = ?", (giveaway_id,))
            # Удаляем участников
            await db.execute("DELETE FROM participants WHERE giveaway_id = ?", (giveaway_id,))
            # Удаляем сам розыгрыш
            await db.execute("DELETE FROM giveaways WHERE id = ?", (giveaway_id,))
            await db.commit()
    
    async def get_user_giveaways(self, user_id: int) -> List[Dict[str, Any]]:
        """Получение списка розыгрышей пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT id, description, winners_count, status, created_at,
                       (SELECT COUNT(*) FROM participants WHERE giveaway_id = giveaways.id) as participants_count
                FROM giveaways
                WHERE creator_id = ?
                ORDER BY created_at DESC
            """, (user_id,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_active_giveaways(self) -> List[Dict[str, Any]]:
        """Получение всех активных розыгрышей с автоматическим завершением"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM giveaways
                WHERE status = 'active' AND manual_end = 0 AND end_time IS NOT NULL
            """)
            rows = await cursor.fetchall()
            result = []
            for row in rows:
                data = dict(row)
                data['required_channels'] = json.loads(data['required_channels'])
                result.append(data)
            return result
    
    async def get_all_users(self) -> List[int]:
        """Получение списка всех пользователей бота"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT user_id FROM users")
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
    
    async def get_stats(self) -> Dict[str, int]:
        """Получение статистики бота"""
        async with aiosqlite.connect(self.db_path) as db:
            # Всего пользователей
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            users_count = (await cursor.fetchone())[0]
            
            # Всего розыгрышей
            cursor = await db.execute("SELECT COUNT(*) FROM giveaways")
            giveaways_count = (await cursor.fetchone())[0]
            
            # Активных розыгрышей
            cursor = await db.execute("SELECT COUNT(*) FROM giveaways WHERE status = 'active'")
            active_giveaways = (await cursor.fetchone())[0]
            
            return {
                'users_count': users_count,
                'giveaways_count': giveaways_count,
                'active_giveaways': active_giveaways
            }
