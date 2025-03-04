import sqlite3
import os
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)
DATABASE_NAME = os.path.join(os.path.dirname(__file__), "DT_bot.db")


def create_tables():
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS faq (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        question TEXT NOT NULL UNIQUE,
                        answer TEXT)''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL UNIQUE,
                        name TEXT NOT NULL,
                        surname TEXT NOT NULL,
                        age INTEGER NOT NULL,
                        phone TEXT NOT NULL UNIQUE,
                        email TEXT NOT NULL UNIQUE,
                        user_type TEXT NOT NULL,
                        password TEXT NOT NULL)''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS generated_responses (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        question TEXT NOT NULL,
                        response TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        conn.commit()
        logger.info("Tables created/verified")


def insert_user(user_data: Tuple) -> bool:
    try:
        with sqlite3.connect(DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO users 
                            (username, name, surname, age, phone, email, user_type, password)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', user_data)
            conn.commit()
            return True
    except sqlite3.IntegrityError as e:
        logger.error(f"Duplicate entry error: {e}")
        return False


def save_generated_response(question: str, response: str) -> None:
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO generated_responses (question, response) VALUES (?, ?)',
                       (question, response))
        conn.commit()

def get_all_faq_entries() -> List[Tuple[str, str]]:
    """Возвращает все записи FAQ в виде списка кортежей (question, answer)."""
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT question, answer FROM faq')
        results = cursor.fetchall()
        return results

def insert_faq_entry(question: str, answer: str) -> None:
    """Добавляет новую запись FAQ."""
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO faq (question, answer) VALUES (?, ?)', (question, answer))
        conn.commit()

def merge_faq_from_excel(file_path: str) -> Tuple[int, int]:
    try:
        df = pd.read_excel(file_path)
        new_entries = 0
        updated_entries = 0
        with sqlite3.connect(DATABASE_NAME) as conn:
            cursor = conn.cursor()
            for _, row in df.iterrows():
                question = row['question']
                answer = row['answer']
                cursor.execute('SELECT id FROM faq WHERE question = ?', (question,))
                result = cursor.fetchone()
                if result:
                    cursor.execute('UPDATE faq SET answer = ? WHERE question = ?', (answer, question))
                    updated_entries += 1
                else:
                    cursor.execute('INSERT INTO faq (question, answer) VALUES (?, ?)', (question, answer))
                    new_entries += 1
            conn.commit()
        return new_entries, updated_entries
    except Exception as e:
        print(f"Ошибка при обновлении FAQ: {e}")
        return 0, 0

def update_faq_from_excel(file_path: str) -> None:
    try:
        df = pd.read_excel(file_path)
        with sqlite3.connect(DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM faq')
            for _, row in df.iterrows():
                cursor.execute('INSERT INTO faq (question, answer) VALUES (?, ?)', (row['question'], row['answer']))
            conn.commit()
    except Exception as e:
        print(f"Ошибка при обновлении FAQ: {e}")
