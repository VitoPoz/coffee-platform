from app import app
from database import db, User

with app.app_context():
    employee = User.query.filter_by(email='employee@coffee.ru').first()
    if employee:
        employee.email = 'barista@coffee.ru'
        db.session.commit()
        print(f"✅ Email изменен: employee@coffee.ru → barista@coffee.ru")