# Файл для быстрого добавления тестов в базу данных
# Запусти: python add_test.py

from app import app
from database import db, Course, Question

with app.app_context():
    # Найди курс "Введение в работу кофейни"
    course = Course.query.filter_by(title='Введение в работу кофейни').first()
    
    if course:
        print(f"Найден курс: {course.title} (ID: {course.id})")
        
        # Добавим тестовые вопросы
        questions = [
            {
                'question': 'Что такое правило "Пять секунд"?',
                'option1': 'Время подачи напитка',
                'option2': 'Правило гигиены при падении предмета',
                'option3': 'Время ожидания клиента',
                'option4': 'Правило общения с гостями',
                'correct': 2,
                'points': 2
            },
            {
                'question': 'Какой должна быть температура в холодильнике для молока?',
                'option1': '0-2°C',
                'option2': '2-4°C',
                'option3': '4-6°C',
                'option4': '6-8°C',
                'correct': 2,
                'points': 1
            },
            {
                'question': 'Что нужно делать при начале каждой смены?',
                'option1': 'Проверять оборудование',
                'option2': 'Делать тестовый эспрессо',
                'option3': 'Проверять сроки годности продуктов',
                'option4': 'Все вышеперечисленное',
                'correct': 4,
                'points': 2
            }
        ]
        
        for i, q_data in enumerate(questions):
            question = Question(
                course_id=course.id,
                question=q_data['question'],
                option1=q_data['option1'],
                option2=q_data['option2'],
                option3=q_data.get('option3', ''),
                option4=q_data.get('option4', ''),
                correct_answer=q_data['correct'],
                points=q_data['points']
            )
            db.session.add(question)
        
        db.session.commit()
        print(f"Добавлено {len(questions)} вопросов в курс '{course.title}'")
    else:
        print("Курс не найден. Сначала создайте курс через админку.")