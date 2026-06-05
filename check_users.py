from app import app
from database import db, User

with app.app_context():
    print("=== ПРОВЕРКА ПОЛЬЗОВАТЕЛЕЙ В БАЗЕ ===")
    
    users = User.query.all()
    print(f"Всего пользователей: {len(users)}\n")
    
    for user in users:
        print(f"✅ ID: {user.id}, Имя: {user.name}, Email: {user.email}, Пароль: {user.password}, Должность: {user.position}")