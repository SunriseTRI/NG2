import pandas as pd
import logging
from typing import List, Tuple
import os
import sqlite3

DATABASE_NAME = os.path.join(os.path.dirname(__file__), "DT_bot.db")
print(f"Database path: {DATABASE_NAME}")

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def create_tables():
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS faq (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            question TEXT NOT NULL,
                            answer TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            username TEXT NOT NULL,
                            name TEXT NOT NULL,
                            surname TEXT NOT NULL,
                            age INTEGER NOT NULL,
                            phone TEXT NOT NULL,
                            email TEXT NOT NULL,
                            user_type TEXT NOT NULL,
                            password TEXT NOT NULL)''')
        conn.commit()

def insert_user(user_data: Tuple) -> None:
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO users (username, name, surname, age, phone, email, user_type, password)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', user_data)
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
