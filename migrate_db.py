# migrate_db.py
from app import app, db
from database import Section
import sqlite3
import os

def migrate_database():
    """Миграция базы данных - добавление новых полей в таблицу section"""
    print("=" * 50)
    print("🔄 ЗАПУСК МИГРАЦИИ БАЗЫ ДАННЫХ")
    print("=" * 50)
    
    # Путь к файлу базы данных
    db_path = 'instance/coffee_training.db' if os.path.exists('instance') else 'coffee_training.db'
    
    # Подключаемся напрямую к SQLite
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Получаем информацию о текущей структуре таблицы section
    cursor.execute("PRAGMA table_info(section)")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    
    print(f"📊 Текущие колонки в таблице section: {column_names}")
    
    # Добавляем новые колонки, если их нет
    new_columns = [
        ('parent_id', 'INTEGER'),
        ('type', 'VARCHAR(20) DEFAULT "folder"'),
        ('content', 'TEXT'),
        ('media_url', 'VARCHAR(500)'),
        ('duration', 'INTEGER'),
        ('is_required', 'BOOLEAN DEFAULT 1')
    ]
    
    for col_name, col_type in new_columns:
        if col_name not in column_names:
            try:
                cursor.execute(f"ALTER TABLE section ADD COLUMN {col_name} {col_type}")
                print(f"✅ Добавлена колонка: {col_name}")
            except Exception as e:
                print(f"❌ Ошибка при добавлении {col_name}: {e}")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Миграция модели завершена!")
    print("=" * 50)

if __name__ == "__main__":
    migrate_database()