import pandas as pd
import logging
from typing import List, Tuple
import os
import sqlite3
# Имя базы данных
DATABASE_NAME = os.path.join(os.path.dirname(__file__), "DT_bot.db")
print(f"Database path: {DATABASE_NAME}")

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def create_tables():
    """Создание таблиц в базе данных."""
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        # Таблица для FAQ
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS faq (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                answer TEXT
            )
        ''')
        # Таблица для пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                name TEXT NOT NULL,
                surname TEXT NOT NULL,
                age INTEGER NOT NULL,
                phone TEXT NOT NULL,
                email TEXT NOT NULL,
                user_type TEXT NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        conn.commit()

def insert_user(user_data: Tuple) -> None:
    """Добавление пользователя в базу данных."""
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (username, name, surname, age, phone, email, user_type, password)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', user_data)
        conn.commit()

def get_user_by_username(username: str) -> dict:
    """Получение данных пользователя по username."""
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        result = cursor.fetchone()
        if result:
            return {
                "id": result[0],
                "username": result[1],
                "name": result[2],
                "surname": result[3],
                "age": result[4],
                "phone": result[5],
                "email": result[6],
                "user_type": result[7],
                "password": result[8]
            }
        return None


def merge_faq_from_excel(file_path: str) -> Tuple[int, int]:
    """Обновление таблицы faq из Excel-файла слиянием."""
    try:
        df = pd.read_excel(file_path)
        new_entries = 0
        updated_entries = 0
        with sqlite3.connect(DATABASE_NAME) as conn:
            cursor = conn.cursor()
            for _, row in df.iterrows():
                question = row['question']
                answer = row['answer']
                # Проверяем, существует ли вопрос в таблице
                cursor.execute('SELECT id FROM faq WHERE question = ?', (question,))
                result = cursor.fetchone()
                if result:
                    # Если вопрос существует, обновляем ответ
                    cursor.execute('''
                        UPDATE faq SET answer = ? WHERE question = ?
                    ''', (answer, question))
                    updated_entries += 1
                else:
                    # Если вопрос не существует, добавляем новый
                    cursor.execute('''
                        INSERT INTO faq (question, answer)
                        VALUES (?, ?)
                    ''', (question, answer))
                    new_entries += 1
            conn.commit()

        return new_entries, updated_entries  # Возвращаем добавленные и обновленные вопросы
    except Exception as e:
        print(f"Ошибка при обновлении FAQ: {e}")
        return 0, 0  # Если возникла ошибка, возвращаем 0

    # Функция для получения данных из базы данных (например, SQLite или любой другой)

def update_faq_from_excel(file_path: str) -> None:
    try:
        df = pd.read_excel(file_path)
        with sqlite3.connect(DATABASE_NAME) as conn:
            cursor = conn.cursor()
            # Очистка таблицы перед обновлением
            cursor.execute('DELETE FROM faq')
            # Вставка новых данных
            for _, row in df.iterrows():
                cursor.execute('''
                    INSERT INTO faq (question, answer)
                    VALUES (?, ?)
                ''', (row['question'], row['answer']))
            conn.commit()
    except Exception as e:
        print(f"Ошибка при обновлении FAQ: {e}")

def get_faq_answer(question: str) -> str:
    """Получение ответа на вопрос из таблицы faq."""
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT answer FROM faq WHERE question = ?', (question,))
        result = cursor.fetchone()
        if result:
            return result[0]
        else:
            # Если вопрос не найден, добавляем его в таблицу
            cursor.execute('''
                INSERT INTO faq (question, answer)
                VALUES (?, ?)
            ''', (question, "Необходим ответ от @админ"))
            conn.commit()
            return "Необходим ответ от @админ"