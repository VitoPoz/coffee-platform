from app import app
from database import db, User

with app.app_context():
    # Проверяем, есть ли уже barista
    barista = User.query.filter_by(email='barista@coffee.ru').first()
    
    if barista:
        print(f"Бариста уже существует: {barista.name}")
        print(f"Пароль: {barista.password}")
    else:
        # Создаем нового бариста
        new_barista = User(
            name='Бариста Иван',
            email='barista@coffee.ru',
            password='123456',
            position='Бариста-универсал',
            is_admin=False
        )
        
        db.session.add(new_barista)
        db.session.commit()
        
        print("✅ Бариста создан!")
        print(f"Email: barista@coffee.ru")
        print(f"Пароль: 123456")
        print(f"Должность: Бариста-универсал")