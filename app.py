from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename  # <-- ДОБАВЬ ЭТУ СТРОКУ
# from flask_migrate import Migrate
from database import db, User, Course, Material, Question, UserProgress, Standard, Section, Lesson, Test, LessonProgress, TestResult, UserAnswer, SiteSettings
from datetime import datetime
import os
from functools import wraps
from sqlalchemy import text, inspect

# Настройки для загрузки PDF
UPLOAD_FOLDER = 'static/presentations'
ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 МБ

# Создаем папку если нет
import os
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app = Flask(__name__)
app.secret_key = 'coffee_secret_key_12345'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///coffee_training.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# migrate = Migrate(app, db)

# ✅ ПРОСТАЯ И БЕЗОПАСНАЯ ИНИЦИАЛИЗАЦИЯ
def safe_initialize_database():
    """Безопасная инициализация с минимальными изменениями"""
    print("=" * 50)
    print("🚀 ПРОСТАЯ ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ")
    print("=" * 50)
    
    with app.app_context():
        try:
            # 1. Просто создаем таблицы
            db.create_all()
            print("✅ Все таблицы созданы/проверены")
            
            # 2. Проверяем основные настройки
            if SiteSettings.query.count() == 0:
                default_settings = SiteSettings(
                    theme_name='default',
                    primary_color='#007bff',
                    secondary_color='#6c757d',
                    accent_color='#28a745',
                    font_family='Arial, sans-serif'
                )
                db.session.add(default_settings)
                print("🎨 Настройки сайта созданы")
            
            # 3. Создаем тестовых пользователей если их нет
            if not User.query.filter_by(email='admin@coffee.ru').first():
                admin = User(
                    name='Администратор',
                    email='admin@coffee.ru',
                    password='admin123',
                    position='Администратор',
                    is_admin=True
                )
                db.session.add(admin)
                print("👤 Администратор создан")
            
            if not User.query.filter_by(email='employee@coffee.ru').first():
                employee = User(
                    name='Тестовый Сотрудник',
                    email='employee@coffee.ru',
                    password='123456',
                    position='Бариста-универсал',
                    is_admin=False
                )
                db.session.add(employee)
                print("👤 Сотрудник создан")
            
            # 4. СОЗДАЕМ ПРОСТОЙ ПРИМЕР КУРСА В НОВОЙ СТРУКТУРЕ
            # Но только если совсем нет курсов!
            if Course.query.count() == 0:
                print("\n📚 Создаем пример курса...")
                
                # Создаем курс
                course = Course(
                    title='Пример курса: Основы работы бариста',
                    description='Научитесь готовить идеальный кофе',
                    category='Базовый',
                    required_position='Бариста-универсал',
                    order=1,
                    is_published=True
                )
                db.session.add(course)
                db.session.flush()
                
                # Создаем раздел
                section = Section(
                    course_id=course.id,
                    title='Введение',
                    description='Основные понятия',
                    order=1
                )
                db.session.add(section)
                db.session.flush()
                
                # Создаем урок
                lesson = Lesson(
                    section_id=section.id,
                    title='Добро пожаловать!',
                    content='<h2>Приветствуем в обучении!</h2><p>Это пример курса...</p>',
                    type='text',
                    order=1
                )
                db.session.add(lesson)
                
                print("📚 Пример курса создан")
            
            db.session.commit()
            print("\n✅ База данных готова к работе!")
            print("=" * 50)
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()

# ✅ ИНИЦИАЛИЗИРУЕМ БАЗУ ПРИ ЗАПУСКЕ ПРИЛОЖЕНИЯ
with app.app_context():
    safe_initialize_database()

# Декоратор для проверки авторизации
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Декоратор для проверки админа
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if not session.get('is_admin'):
            flash('Требуются права администратора', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Список должностей
POSITIONS = [
    'Бариста-универсал',
    'Управляющий',
    'Официант',
    'Пекарь',
    'SMM',
    'Менеджер отдела продаж',
    'Дизайнер',
    'HR'
]

# ========== ОСНОВНЫЕ МАРШРУТЫ ==========

@app.route('/')
def index():
    courses = Course.query.filter_by(is_published=True).order_by(Course.order).limit(3).all()
    return render_template('index.html', courses=courses)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(email=email, password=password).first()
        
        if user:
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['is_admin'] = user.is_admin
            session['position'] = user.position
            flash('Вход выполнен успешно!', 'success')
            return redirect(url_for('dashboard'))
        
        flash('Неверный email или пароль', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    user_position = session.get('position', 'Бариста')
    
    if user_position == 'Все' or session.get('is_admin'):
        courses = Course.query.filter_by(is_published=True).order_by(Course.order).all()
    else:
        courses = Course.query.filter(
            (Course.required_position == 'Все') | 
            (Course.required_position == user_position),
            Course.is_published == True
        ).order_by(Course.order).all()
    
    progress = {}
    for course in courses:
        user_progress = UserProgress.query.filter_by(
            user_id=user_id, 
            course_id=course.id
        ).first()
        progress[course.id] = user_progress.status if user_progress else 'not_started'
    
    return render_template('dashboard.html', 
                         courses=courses, 
                         progress=progress,
                         positions=POSITIONS)

# ========== СТРАНИЦЫ КУРСОВ ==========

@app.route('/courses')
@login_required
def view_courses():
    user_position = session.get('position', 'Бариста')
    
    if session.get('is_admin'):
        courses = Course.query.order_by(Course.order).all()
    else:
        courses = Course.query.filter(
            (Course.required_position == 'Все') | 
            (Course.required_position == user_position),
            Course.is_published == True
        ).order_by(Course.order).all()
    
    return render_template('courses.html', courses=courses)

@app.route('/course/<int:course_id>')
@login_required
def course_detail(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Получаем все разделы курса
    all_sections = Section.query.filter_by(course_id=course_id).all()
    
    # Строим древовидную структуру
    def build_tree(parent_id=None):
        result = []
        for section in all_sections:
            if section.parent_id == parent_id:
                # Рекурсивно получаем детей
                children = build_tree(section.id)
                result.append({
                    'id': section.id,
                    'title': section.title,
                    'description': section.description,
                    'type': section.type if hasattr(section, 'type') else 'folder',
                    'content': section.content if hasattr(section, 'content') else None,
                    'media_url': section.media_url if hasattr(section, 'media_url') else None,
                    'duration': section.duration if hasattr(section, 'duration') else None,
                    'is_required': section.is_required if hasattr(section, 'is_required') else True,
                    'order': section.order,
                    'children': sorted(children, key=lambda x: x['order'])
                })
        return sorted(result, key=lambda x: x['order'])
    
    # Строим дерево, начиная с корневых элементов (parent_id = None)
    structure = build_tree()
    
    # Получаем тесты курса
    tests = Test.query.filter_by(course_id=course_id).order_by(Test.order).all()
    
    # Вопросы получаем через тесты
    all_questions = []
    for test in tests:
        all_questions.extend(test.questions)
    
    if not session.get('is_admin'):
        user_position = session.get('position', 'Бариста')
        if course.required_position != 'Все' and course.required_position != user_position:
            flash('У вас нет доступа к этому курсу', 'danger')
            return redirect(url_for('view_courses'))
    
    # Передаем в шаблон structure вместо sections
    return render_template('course_detail.html', 
                         course=course, 
                         structure=structure,  # ← ВАЖНО: теперь передаем structure
                         tests=tests,
                         questions=all_questions)

# ========== МАТЕРИАЛЫ КУРСОВ ==========

@app.route('/admin/course/<int:course_id>/materials')
@admin_required
def admin_course_materials(course_id):
    course = Course.query.get_or_404(course_id)
    materials = Material.query.filter_by(course_id=course_id).order_by(Material.order).all()
    return render_template('admin_materials.html', 
                         course=course, 
                         materials=materials)

@app.route('/admin/material/new/<int:course_id>', methods=['GET', 'POST'])
@admin_required
def admin_new_material(course_id):
    course = Course.query.get_or_404(course_id)
    
    if request.method == 'POST':
        material = Material(
            course_id=course_id,
            title=request.form['title'],
            content=request.form.get('content', ''),
            type=request.form['type'],
            order=int(request.form.get('order', 0)),
            is_required=bool(request.form.get('is_required')),
            file_path=request.form.get('file_path', '')
        )
        
        db.session.add(material)
        db.session.commit()
        flash('Материал добавлен!', 'success')
        return redirect(url_for('admin_course_materials', course_id=course_id))
    
    return render_template('admin_edit_material.html', 
                         course=course, 
                         material=None)

@app.route('/admin/material/<int:material_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_material(material_id):
    material = Material.query.get_or_404(material_id)
    course = Course.query.get_or_404(material.course_id)
    
    if request.method == 'POST':
        material.title = request.form['title']
        material.content = request.form.get('content', '')
        material.type = request.form['type']
        material.order = int(request.form.get('order', 0))
        material.is_required = bool(request.form.get('is_required'))
        material.file_path = request.form.get('file_path', '')
        
        db.session.commit()
        flash('Материал обновлен!', 'success')
        return redirect(url_for('admin_course_materials', course_id=material.course_id))
    
    return render_template('admin_edit_material.html', 
                         course=course, 
                         material=material)

@app.route('/admin/material/<int:material_id>/delete')
@admin_required
def admin_delete_material(material_id):
    material = Material.query.get_or_404(material_id)
    course_id = material.course_id
    
    db.session.delete(material)
    db.session.commit()
    flash('Материал удален!', 'success')
    return redirect(url_for('admin_course_materials', course_id=course_id))

# ========== НОВЫЕ МАРШРУТЫ ДЛЯ УРОКОВ ==========

@app.route('/course/<int:course_id>/lesson/<int:lesson_id>')
@login_required
def view_lesson(course_id, lesson_id):
    """Просмотр конкретного урока"""
    course = Course.query.get_or_404(course_id)
    lesson = Lesson.query.get_or_404(lesson_id)
    
    # Проверка доступа
    if not session.get('is_admin'):
        user_position = session.get('position', 'Бариста')
        if course.required_position != 'Все' and course.required_position != user_position:
            flash('У вас нет доступа к этому курсу', 'danger')
            return redirect(url_for('view_courses'))
    
    # Получаем следующий и предыдущий уроки для навигации
    section_lessons = Lesson.query.filter_by(section_id=lesson.section_id).order_by(Lesson.order).all()
    lesson_index = next((i for i, l in enumerate(section_lessons) if l.id == lesson.id), -1)
    
    prev_lesson = section_lessons[lesson_index - 1] if lesson_index > 0 else None
    next_lesson = section_lessons[lesson_index + 1] if lesson_index < len(section_lessons) - 1 else None
    
    return render_template('view_lesson.html',
                         course=course,
                         lesson=lesson,
                         prev_lesson=prev_lesson,
                         next_lesson=next_lesson)

@app.route('/api/lesson/<int:lesson_id>/complete', methods=['POST'])
@login_required
def complete_lesson(lesson_id):
    """Отметить урок как пройденный"""
    lesson = Lesson.query.get_or_404(lesson_id)
    
    # Проверяем, существует ли уже запись о прогрессе
    progress = LessonProgress.query.filter_by(
        user_id=session['user_id'],
        lesson_id=lesson_id
    ).first()
    
    if not progress:
        progress = LessonProgress(
            user_id=session['user_id'],
            lesson_id=lesson_id,
            is_completed=True,
            completed_at=datetime.utcnow()
        )
        db.session.add(progress)
    else:
        progress.is_completed = True
        progress.completed_at = datetime.utcnow()
    
    db.session.commit()
    
    # Обновляем общий прогресс по курсу
    update_course_progress(lesson.section.course_id)
    
    return jsonify({'status': 'success'})

def update_course_progress(course_id):
    """Обновление общего прогресса по курсу"""
    user_id = session['user_id']
    
    # Получаем все уроки курса
    sections = Section.query.filter_by(course_id=course_id).all()
    total_lessons = 0
    completed_lessons = 0
    
    for section in sections:
        lessons = Lesson.query.filter_by(section_id=section.id).all()
        total_lessons += len(lessons)
        
        for lesson in lessons:
            progress = LessonProgress.query.filter_by(
                user_id=user_id,
                lesson_id=lesson.id,
                is_completed=True
            ).first()
            if progress:
                completed_lessons += 1
    
    # Рассчитываем процент выполнения
    if total_lessons > 0:
        completion_percentage = int((completed_lessons / total_lessons) * 100)
        
        # Обновляем или создаем запись UserProgress
        user_progress = UserProgress.query.filter_by(
            user_id=user_id,
            course_id=course_id
        ).first()
        
        if not user_progress:
            user_progress = UserProgress(
                user_id=user_id,
                course_id=course_id,
                status='in_progress',
                progress_percentage=completion_percentage
            )
            db.session.add(user_progress)
        else:
            user_progress.progress_percentage = completion_percentage
            if completion_percentage == 100:
                user_progress.status = 'completed'
            elif completion_percentage > 0:
                user_progress.status = 'in_progress'
        
        db.session.commit()

# ===== НОВЫЕ ФУНКЦИИ ДЛЯ УПРАВЛЕНИЯ СТРУКТУРОЙ КУРСА =====

# Управление структурой курса (разделы/уроки)
@app.route('/admin/course/<int:course_id>/structure')
@login_required
@admin_required
def course_structure(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Получаем все разделы курса (включая вложенные)
    sections = Section.query.filter_by(course_id=course_id).order_by(Section.order).all()
    
    # Формируем древовидную структуру
    def build_tree(parent_id=None):
        result = []
        for section in sections:
            if section.parent_id == parent_id:
                children = build_tree(section.id)
                result.append({
                    'id': section.id,
                    'title': section.title,
                    'type': section.type if hasattr(section, 'type') else 'folder',
                    'description': section.description,
                    'order': section.order,
                    'is_required': section.is_required if hasattr(section, 'is_required') else True,
                    'children': children
                })
        return sorted(result, key=lambda x: x['order'])
    
    tree = build_tree()
    
    return render_template('admin/course_structure.html', 
                         course=course,
                         tree=tree)

# Добавление раздела/урока
@app.route('/admin/course/<int:course_id>/add_section', methods=['GET', 'POST'])
@login_required
@admin_required
def add_section(course_id):
    course = Course.query.get_or_404(course_id)
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        section_type = request.form.get('type', 'folder')
        parent_id = request.form.get('parent_id')
        content = request.form.get('content')
        media_url = request.form.get('media_url')
        duration = request.form.get('duration')
        is_required = request.form.get('is_required') == 'on'
        order = request.form.get('order', 0)
        
        # Проверяем parent_id
        if parent_id:
            parent_section = Section.query.get(parent_id)
            if not parent_section or parent_section.course_id != course_id:
                flash('Некорректный родительский раздел', 'danger')
                return redirect(url_for('course_structure', course_id=course_id))
        
        new_section = Section(
            course_id=course_id,
            parent_id=parent_id if parent_id else None,
            title=title,
            description=description,
            type=section_type,
            content=content if section_type == 'lesson' else None,
            media_url=media_url if section_type == 'lesson' else None,
            duration=int(duration) if duration and section_type == 'lesson' else None,
            is_required=is_required,
            order=order
        )
        
        db.session.add(new_section)
        db.session.commit()
        
        flash(f'{"Урок" if section_type == "lesson" else "Раздел"} успешно добавлен', 'success')
        return redirect(url_for('course_structure', course_id=course_id))
    
    # GET запрос - показываем форму
    section_type = request.args.get('type', 'folder')
    parent_id = request.args.get('parent_id')
    
    return render_template('admin/add_section.html', 
                         course=course, 
                         section_type=section_type,
                         parent_id=parent_id)

# Редактирование раздела/урока
@app.route('/admin/section/<int:section_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_section(section_id):
    section = Section.query.get_or_404(section_id)
    course = Course.query.get(section.course_id)
    
    if request.method == 'POST':
        section.title = request.form.get('title')
        section.description = request.form.get('description')
        section.content = request.form.get('content') if hasattr(section, 'type') and section.type == 'lesson' else None
        section.media_url = request.form.get('media_url') if hasattr(section, 'type') and section.type == 'lesson' else None
        section.duration = int(request.form.get('duration')) if request.form.get('duration') and hasattr(section, 'type') and section.type == 'lesson' else None
        section.is_required = request.form.get('is_required') == 'on'
        section.order = request.form.get('order', 0)
        
        db.session.commit()
        flash('Изменения сохранены', 'success')
        return redirect(url_for('course_structure', course_id=section.course_id))
    
    return render_template('admin/edit_section.html', section=section, course=course)

# Удаление раздела/урока
@app.route('/admin/section/<int:section_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_section(section_id):
    section = Section.query.get_or_404(section_id)
    course_id = section.course_id
    
    # Проверяем, есть ли дочерние элементы
    children = Section.query.filter_by(parent_id=section_id).count()
    if children > 0:
        flash('Нельзя удалить раздел, содержащий другие элементы', 'danger')
        return redirect(url_for('course_structure', course_id=course_id))
    
    db.session.delete(section)
    db.session.commit()
    flash('Элемент успешно удален', 'success')
    return redirect(url_for('course_structure', course_id=course_id))

# Изменение порядка (drag-and-drop)
@app.route('/admin/section/reorder', methods=['POST'])
@login_required
@admin_required
def reorder_sections():
    data = request.get_json()
    course_id = data.get('course_id')
    
    for item in data.get('items', []):
        section = Section.query.get(item['id'])
        if section and section.course_id == int(course_id):
            section.order = item['order']
            section.parent_id = item.get('parent_id')
    
    db.session.commit()
    return jsonify({'success': True})

# ===== КОНЕЦ НОВЫХ ФУНКЦИЙ =====

# ========== НОВЫЕ МАРШРУТЫ ДЛЯ ТЕСТОВ ==========

@app.route('/course/<int:course_id>/test/<int:test_id>')
@login_required
def view_test(course_id, test_id):
    """Страница прохождения теста"""
    course = Course.query.get_or_404(course_id)
    test = Test.query.get_or_404(test_id)
    
    # Проверка доступа
    if not session.get('is_admin'):
        user_position = session.get('position', 'Бариста')
        if course.required_position != 'Все' and course.required_position != user_position:
            flash('У вас нет доступа к этому курсу', 'danger')
            return redirect(url_for('view_courses'))
    
    # Получаем вопросы теста
    questions = Question.query.filter_by(test_id=test_id).order_by(Question.order).all()
    
    return render_template('view_test.html',
                         course=course,
                         test=test,
                         questions=questions)

@app.route('/course/<int:course_id>/test/<int:test_id>/submit', methods=['POST'])
@login_required
def submit_test(course_id, test_id):
    """Отправка результатов теста"""
    test = Test.query.get_or_404(test_id)
    user_id = session['user_id']
    
    # Получаем вопросы теста
    questions = Question.query.filter_by(test_id=test_id).all()
    
    total_points = 0
    earned_points = 0
    answers_data = []
    
    # Обрабатываем ответы
    for question in questions:
        total_points += question.points
        
        # Получаем ответ пользователя
        answer_key = f'question_{question.id}'
        user_answer = request.form.get(answer_key)
        
        # Проверяем правильность ответа
        is_correct = False
        
        # ИСПРАВЛЯЕМ ТУТ: 'single' → 'single_choice', 'multiple' → 'multiple_choice'
        if question.question_type == 'single_choice':
            is_correct = user_answer == question.correct_answer
        elif question.question_type == 'multiple_choice':
            # Для multiple_choice ответы могут приходить как список
            user_answers = request.form.getlist(answer_key)
            # Правильные ответы могут быть через запятую или |
            correct_answer_str = question.correct_answer or ''
            correct_answers = []
            if '|' in correct_answer_str:
                correct_answers = [ans.strip() for ans in correct_answer_str.split('|') if ans.strip()]
            elif ',' in correct_answer_str:
                correct_answers = [ans.strip() for ans in correct_answer_str.split(',') if ans.strip()]
            else:
                correct_answers = [correct_answer_str.strip()]
            
            # Сравниваем множества (порядок не важен)
            is_correct = set(user_answers) == set(correct_answers)
        elif question.question_type == 'text':
            # Для текстовых ответов сравниваем без учета регистра и пробелов
            user_answer_clean = (user_answer or '').strip().lower()
            correct_answer_clean = (question.correct_answer or '').strip().lower()
            is_correct = user_answer_clean == correct_answer_clean
        
        if is_correct:
            earned_points += question.points
        
        # Сохраняем ответ пользователя
        user_answer_record = UserAnswer(
            user_id=user_id,
            question_id=question.id,
            answer=user_answer if user_answer else '',
            is_correct=is_correct,
            points_earned=question.points if is_correct else 0
        )
        db.session.add(user_answer_record)
        answers_data.append(user_answer_record)
    
    # Рассчитываем результат
    percentage = int((earned_points / total_points) * 100) if total_points > 0 else 0
    passed = percentage >= test.passing_score
    
    # Сохраняем результат теста
    test_result = TestResult(
        user_id=user_id,
        test_id=test_id,
        score=earned_points,
        total_score=total_points,
        percentage=percentage,
        passed=passed,
        completed_at=datetime.utcnow()
    )
    db.session.add(test_result)
    
    db.session.commit()
    
    # Обновляем прогресс курса
    update_course_progress(course_id)
    
    return render_template('test_result.html',
                         test=test,
                         test_result=test_result,
                         answers=answers_data,
                         questions=questions)

@app.route('/course/<int:course_id>/test/<int:test_id>/results')
@login_required
def test_results(course_id, test_id):
    """Просмотр результатов теста"""
    test = Test.query.get_or_404(test_id)
    user_id = session['user_id']
    
    # Получаем последний результат пользователя
    test_result = TestResult.query.filter_by(
        user_id=user_id,
        test_id=test_id
    ).order_by(TestResult.completed_at.desc()).first()
    
    if not test_result:
        flash('Вы еще не проходили этот тест', 'info')
        return redirect(url_for('view_test', course_id=course_id, test_id=test_id))
    
    # ИСПРАВЛЯЕМ ЗДЕСЬ: неправильный фильтр
    # Было:
    # user_answers = UserAnswer.query.filter_by(
    #     user_id=user_id,
    #     question_id=Question.test_id == test_id
    # ).all()
    
    # Стало:
    user_answers = UserAnswer.query.filter(
        UserAnswer.user_id == user_id,
        UserAnswer.question_id.in_([q.id for q in test.questions])
    ).all()
    
    questions = Question.query.filter_by(test_id=test_id).all()
    
    return render_template('test_results_detail.html',
                         test=test,
                         test_result=test_result,
                         user_answers=user_answers,
                         questions=questions)


# ========== АДМИН-ПАНЕЛЬ ==========

@app.route('/admin')
@admin_required
def admin_panel():
    stats = {
        'users': User.query.count(),
        'courses': Course.query.count(),
        'active_courses': Course.query.filter_by(is_published=True).count(),
        'completed': UserProgress.query.filter_by(status='completed').count()
    }
    
    users = User.query.order_by(User.created_at.desc()).limit(10).all()
    recent_courses = Course.query.order_by(Course.created_at.desc()).limit(5).all()
    
    return render_template('admin_panel.html',
                         stats=stats,
                         users=users,
                         recent_courses=recent_courses,
                         positions=POSITIONS)

# Управление курсами
@app.route('/admin/courses')
@admin_required
def admin_courses():
    courses = Course.query.order_by(Course.order).all()
    return render_template('admin_courses.html', courses=courses)

@app.route('/admin/course/new', methods=['GET', 'POST'])
@admin_required
def admin_new_course():
    if request.method == 'POST':
        course = Course(
            title=request.form['title'],
            description=request.form['description'],
            video_url=request.form.get('video_url', ''),
            category=request.form['category'],
            required_position=request.form['required_position'],
            order=int(request.form.get('order', 0)),
            is_published=bool(request.form.get('is_published'))
        )
        db.session.add(course)
        db.session.commit()
        flash('Курс создан успешно!', 'success')
        return redirect(url_for('admin_courses'))
    
    return render_template('admin_edit_course.html', 
                         course=None,
                         positions=['Все'] + POSITIONS)

@app.route('/admin/course/<int:course_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_course(course_id):
    course = Course.query.get_or_404(course_id)
    
    if request.method == 'POST':
        course.title = request.form['title']
        course.description = request.form['description']
        course.video_url = request.form.get('video_url', '')
        course.category = request.form['category']
        course.required_position = request.form['required_position']
        course.order = int(request.form.get('order', 0))
        course.is_published = bool(request.form.get('is_published'))
        db.session.commit()
        flash('Курс обновлен!', 'success')
        return redirect(url_for('admin_courses'))
    
    return render_template('admin_edit_course.html', 
                         course=course,
                         positions=['Все'] + POSITIONS)

@app.route('/admin/course/<int:course_id>/delete')
@admin_required
def admin_delete_course(course_id):
    course = Course.query.get_or_404(course_id)
    db.session.delete(course)
    db.session.commit()
    flash('Курс удален!', 'success')
    return redirect(url_for('admin_courses'))

# ========== КОНСТРУКТОР КУРСОВ ==========

@app.route('/admin/course/<int:course_id>/builder')
@admin_required
def admin_course_builder(course_id):
    """Конструктор курсов - редактирование структуры"""
    course = Course.query.get_or_404(course_id)
    sections = Section.query.filter_by(course_id=course_id).order_by(Section.order).all()
    
    # Для каждого раздела получаем уроки
    sections_with_lessons = []
    total_lessons_count = 0
    for section in sections:
        lessons = Lesson.query.filter_by(section_id=section.id).order_by(Lesson.order).all()
        total_lessons_count += len(lessons)
        sections_with_lessons.append({
            'section': section,
            'lessons': lessons
        })
    
    # Получаем тесты курса
    tests = Test.query.filter_by(course_id=course_id).order_by(Test.order).all()
    
    # Считаем общее количество вопросов
    total_questions_count = 0
    for test in tests:
        total_questions_count += len(test.questions)
    
    return render_template('admin_course_builder.html',
                         course=course,
                         sections_with_lessons=sections_with_lessons,
                         total_lessons_count=total_lessons_count,
                         tests=tests,
                         total_questions_count=total_questions_count)

# ========== УПРАВЛЕНИЕ РАЗДЕЛАМИ ==========

@app.route('/admin/section/new/<int:course_id>', methods=['POST'])
@admin_required
def admin_new_section(course_id):
    """Создание нового раздела"""
    try:
        section = Section(
            course_id=course_id,
            title=request.form.get('title', 'Новый раздел'),
            description=request.form.get('description', ''),
            order=int(request.form.get('order', 0))
        )
        db.session.add(section)
        db.session.commit()
        flash('Раздел создан успешно!', 'success')
    except Exception as e:
        flash(f'Ошибка при создании раздела: {str(e)}', 'danger')
    
    return redirect(url_for('admin_course_builder', course_id=course_id))

@app.route('/admin/section/<int:section_id>/edit', methods=['POST'])
@admin_required
def admin_edit_section(section_id):
    """Редактирование раздела"""
    section = Section.query.get_or_404(section_id)
    
    try:
        section.title = request.form.get('title', section.title)
        section.description = request.form.get('description', section.description)
        section.order = int(request.form.get('order', section.order))
        db.session.commit()
        flash('Раздел обновлен успешно!', 'success')
    except Exception as e:
        flash(f'Ошибка при обновлении раздела: {str(e)}', 'danger')
    
    return redirect(url_for('admin_course_builder', course_id=section.course_id))

@app.route('/admin/section/<int:section_id>/delete')
@admin_required
def admin_delete_section(section_id):
    """Удаление раздела (с уроками)"""
    section = Section.query.get_or_404(section_id)
    course_id = section.course_id
    
    try:
        db.session.delete(section)
        db.session.commit()
        flash('Раздел удален успешно!', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении раздела: {str(e)}', 'danger')
    
    return redirect(url_for('admin_course_builder', course_id=course_id))

# ========== УПРАВЛЕНИЕ УРОКАМИ ==========

@app.route('/admin/lesson/new/<int:section_id>', methods=['POST'])
@admin_required
def admin_new_lesson(section_id):
    """Создание нового урока"""
    section = Section.query.get_or_404(section_id)
    
    try:
        # Сначала создаем урок
        lesson = Lesson(
            section_id=section_id,
            title=request.form.get('title', 'Новый урок'),
            content=request.form.get('content', ''),
            type=request.form.get('type', 'text'),
            media_url=request.form.get('media_url', ''),
            duration=int(request.form.get('duration', 0)) if request.form.get('duration') else None,
            order=int(request.form.get('order', 0)),
            is_required=bool(request.form.get('is_required'))
        )
        db.session.add(lesson)
        db.session.flush()  # Получаем ID урока
        
        # Если тип - презентация/PDF и есть загруженный файл
        if lesson.type in ['presentation', 'pdf'] and 'pdf_file' in request.files:
            pdf_file = request.files['pdf_file']
            if pdf_file and pdf_file.filename != '' and allowed_file(pdf_file.filename):
                # Проверка размера файла
                pdf_file.seek(0, os.SEEK_END)
                file_size = pdf_file.tell()
                pdf_file.seek(0)
                
                if file_size > MAX_FILE_SIZE:
                    flash('Файл слишком большой (макс. 50 МБ)', 'danger')
                else:
                    # Сохраняем файл
                    import time
                    timestamp = int(time.time())
                    filename = secure_filename(f"{timestamp}_{pdf_file.filename}")
                    filepath = os.path.join(UPLOAD_FOLDER, filename)
                    pdf_file.save(filepath)
                    
                    # Обновляем media_url
                    lesson.media_url = f'/static/presentations/{filename}'
                    
                    # Добавь:
                    print(f"DEBUG: PDF сохранен как {filename}")
                    print(f"DEBUG: media_url = {lesson.media_url}")
                    print(f"DEBUG: Полный путь: {os.path.abspath(filepath)}")
                    
        
        db.session.commit()
        flash('Урок создан успешно!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при создании урока: {str(e)}', 'danger')
    
    return redirect(url_for('admin_course_builder', course_id=section.course_id))

@app.route('/admin/lesson/<int:lesson_id>/edit', methods=['POST'])
@admin_required
def admin_edit_lesson(lesson_id):
    """Редактирование урока"""
    lesson = Lesson.query.get_or_404(lesson_id)
    
    try:
        lesson.title = request.form.get('title', lesson.title)
        lesson.content = request.form.get('content', lesson.content)
        lesson.type = request.form.get('type', lesson.type)
        
        # Обработка PDF файла
        if lesson.type in ['presentation', 'pdf'] and 'pdf_file' in request.files:
            pdf_file = request.files['pdf_file']
            if pdf_file and pdf_file.filename != '' and allowed_file(pdf_file.filename):
                # Проверка размера файла
                pdf_file.seek(0, os.SEEK_END)
                file_size = pdf_file.tell()
                pdf_file.seek(0)
                
                if file_size > MAX_FILE_SIZE:
                    flash('Файл слишком большой (макс. 50 МБ)', 'danger')
                else:
                    # Удаляем старый файл если есть
                    if lesson.media_url and lesson.media_url.startswith('/static/presentations/'):
                        old_filename = lesson.media_url.replace('/static/presentations/', '')
                        old_filepath = os.path.join(UPLOAD_FOLDER, old_filename)
                        if os.path.exists(old_filepath):
                            os.remove(old_filepath)
                    
                    # Сохраняем новый файл
                    import time
                    timestamp = int(time.time())
                    filename = secure_filename(f"{timestamp}_{pdf_file.filename}")
                    filepath = os.path.join(UPLOAD_FOLDER, filename)
                    pdf_file.save(filepath)
                    
                    # Обновляем media_url
                    lesson.media_url = f'/static/presentations/{filename}'

                    # Добавь:
                    print(f"DEBUG: PDF сохранен как {filename}")
                    print(f"DEBUG: media_url = {lesson.media_url}")
                    print(f"DEBUG: Полный путь: {os.path.abspath(filepath)}")

            else:
                # Если файл не загружен, но тип - презентация, используем старый media_url или форму
                if request.form.get('media_url'):
                    lesson.media_url = request.form.get('media_url')
        else:
            # Для других типов или если нет файла
            lesson.media_url = request.form.get('media_url', lesson.media_url)
        
        lesson.duration = int(request.form.get('duration', 0)) if request.form.get('duration') else None
        lesson.order = int(request.form.get('order', lesson.order))
        lesson.is_required = bool(request.form.get('is_required'))
        
        db.session.commit()
        flash('Урок обновлен успешно!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при обновлении урока: {str(e)}', 'danger')
    
    return redirect(url_for('admin_course_builder', course_id=lesson.section.course_id))

@app.route('/admin/lesson/<int:lesson_id>/delete')
@admin_required
def admin_delete_lesson(lesson_id):
    """Удаление урока"""
    lesson = Lesson.query.get_or_404(lesson_id)
    course_id = lesson.section.course_id
    
    try:
        db.session.delete(lesson)
        db.session.commit()
        flash('Урок удален успешно!', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении урока: {str(e)}', 'danger')
    
    return redirect(url_for('admin_course_builder', course_id=course_id))

# ========== УПРАВЛЕНИЕ ТЕСТАМИ ==========

@app.route('/admin/test/new/<int:course_id>', methods=['POST'])
@admin_required
def admin_new_test(course_id):
    """Создание нового теста"""
    try:
        test = Test(
            course_id=course_id,
            title=request.form.get('title', 'Новый тест'),
            description=request.form.get('description', ''),
            order=int(request.form.get('order', 0)),
            passing_score=int(request.form.get('passing_score', 70)),
            time_limit=int(request.form.get('time_limit', 0)) if request.form.get('time_limit') else None,
            is_required=bool(request.form.get('is_required'))
        )
        db.session.add(test)
        db.session.commit()
        flash('Тест создан успешно!', 'success')
    except Exception as e:
        flash(f'Ошибка при создании теста: {str(e)}', 'danger')
    
    return redirect(url_for('admin_course_builder', course_id=course_id))

@app.route('/admin/test/<int:test_id>/edit', methods=['POST'])
@admin_required
def admin_edit_test(test_id):
    """Редактирование теста"""
    test = Test.query.get_or_404(test_id)
    
    try:
        test.title = request.form.get('title', test.title)
        test.description = request.form.get('description', test.description)
        test.order = int(request.form.get('order', test.order))
        test.passing_score = int(request.form.get('passing_score', test.passing_score))
        test.time_limit = int(request.form.get('time_limit', 0)) if request.form.get('time_limit') else None
        test.is_required = bool(request.form.get('is_required'))
        db.session.commit()
        flash('Тест обновлен успешно!', 'success')
    except Exception as e:
        flash(f'Ошибка при обновлении теста: {str(e)}', 'danger')
    
    return redirect(url_for('admin_course_builder', course_id=test.course_id))

@app.route('/admin/test/<int:test_id>/delete')
@admin_required
def admin_delete_test(test_id):
    """Удаление теста (с вопросами)"""
    test = Test.query.get_or_404(test_id)
    course_id = test.course_id
    
    try:
        db.session.delete(test)
        db.session.commit()
        flash('Тест удален успешно!', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении теста: {str(e)}', 'danger')
    
    return redirect(url_for('admin_course_builder', course_id=course_id))

# ========== УПРАВЛЕНИЕ ВОПРОСАМИ ==========

@app.route('/admin/question/new/<int:test_id>', methods=['POST'])
@admin_required
def admin_new_question(test_id):
    """Создание нового вопроса"""
    test = Test.query.get_or_404(test_id)
    
    try:
        question = Question(
            test_id=test_id,
            question_text=request.form.get('question_text', 'Новый вопрос'),  # ← ПРАВИЛЬНО
            question_type=request.form.get('question_type', 'single_choice'),  # ← тоже исправьте!
            options=request.form.get('options', ''),
            correct_answer=request.form.get('correct_answer', ''),
            points=int(request.form.get('points', 1)),
            explanation=request.form.get('explanation', ''),
            order=int(request.form.get('order', 0))
        )
        db.session.add(question)
        db.session.commit()
        flash('Вопрос добавлен успешно!', 'success')
    except Exception as e:
        flash(f'Ошибка при добавлении вопроса: {str(e)}', 'danger')
    
    return redirect(url_for('admin_course_builder', course_id=test.course_id))

@app.route('/admin/question/<int:question_id>/edit', methods=['POST'])
@admin_required
def admin_edit_question(question_id):
    """Редактирование вопроса"""
    question = Question.query.get_or_404(question_id)
    
    try:
        question.question_text = request.form.get('question_text', question.question_text)
        question.question_type = request.form.get('question_type', question.question_type)
        question.options = request.form.get('options', question.options)
        question.correct_answer = request.form.get('correct_answer', question.correct_answer)
        question.points = int(request.form.get('points', question.points))
        question.explanation = request.form.get('explanation', question.explanation)
        question.order = int(request.form.get('order', question.order))
        db.session.commit()
        flash('Вопрос обновлен успешно!', 'success')
    except Exception as e:
        flash(f'Ошибка при обновлении вопроса: {str(e)}', 'danger')
    
    return redirect(url_for('admin_course_builder', course_id=question.test.course_id))

@app.route('/admin/question/<int:question_id>/delete')
@admin_required
def admin_delete_question(question_id):
    """Удаление вопроса"""
    question = Question.query.get_or_404(question_id)
    course_id = question.test.course_id
    
    try:
        db.session.delete(question)
        db.session.commit()
        flash('Вопрос удален успешно!', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении вопроса: {str(e)}', 'danger')
    
    return redirect(url_for('admin_course_builder', course_id=course_id))

# ========== УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ ==========

@app.route('/admin/users')
@admin_required
def admin_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin_users.html', users=users, positions=POSITIONS)

@app.route('/admin/user/new', methods=['GET', 'POST'])
@admin_required
def admin_new_user():
    if request.method == 'POST':
        # Проверяем, нет ли уже пользователя с таким email
        existing_user = User.query.filter_by(email=request.form['email']).first()
        if existing_user:
            flash('Пользователь с таким email уже существует!', 'danger')
            return redirect(url_for('admin_new_user'))
        
        # Создаем нового пользователя
        new_user = User(
            name=request.form['name'],
            email=request.form['email'],
            password=request.form['password'],  # В реальном приложении нужно хэшировать пароль!
            position=request.form['position'],
            is_admin=bool(request.form.get('is_admin'))
        )
        db.session.add(new_user)
        db.session.commit()
        flash('Пользователь создан успешно!', 'success')
        return redirect(url_for('admin_users'))
    
    return render_template('admin_edit_user.html', user=None, positions=POSITIONS)

@app.route('/admin/user/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.name = request.form['name']
        user.email = request.form['email']
        user.position = request.form['position']
        user.is_admin = bool(request.form.get('is_admin'))
        db.session.commit()
        flash('Пользователь обновлен!', 'success')
        return redirect(url_for('admin_users'))
    
    return render_template('admin_edit_user.html', user=user, positions=POSITIONS)

@app.route('/admin/user/<int:user_id>/delete')
@admin_required
def admin_delete_user(user_id):
    # Не даем удалить самого себя
    if user_id == session.get('user_id'):
        flash('Нельзя удалить свой собственный аккаунт!', 'danger')
        return redirect(url_for('admin_users'))
    
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('Пользователь удален!', 'success')
    return redirect(url_for('admin_users'))

# ========== БИБЛИОТЕКА СТАНДАРТОВ ==========

@app.route('/library')
@login_required
def library():
    standards = Standard.query.order_by(Standard.category).all()
    categories = db.session.query(Standard.category).distinct().all()
    return render_template('library.html', 
                         standards=standards,
                         categories=[c[0] for c in categories if c[0]])

@app.route('/admin/library')
@admin_required
def admin_library():
    standards = Standard.query.order_by(Standard.category).all()
    return render_template('admin_library.html', standards=standards)

@app.route('/admin/library/new', methods=['GET', 'POST'])
@admin_required
def admin_new_standard():
    if request.method == 'POST':
        standard = Standard(
            title=request.form['title'],
            content=request.form['content'],
            category=request.form['category'],
            file_url=request.form.get('file_url', '')
        )
        db.session.add(standard)
        db.session.commit()
        flash('Стандарт добавлен!', 'success')
        return redirect(url_for('admin_library'))
    
    return render_template('admin_edit_standard.html', standard=None)

# ========== API ДЛЯ ПРОГРЕССА ==========

@app.route('/api/start_course/<int:course_id>', methods=['POST'])
@login_required
def start_course(course_id):
    progress = UserProgress.query.filter_by(
        user_id=session['user_id'],
        course_id=course_id
    ).first()
    
    if not progress:
        progress = UserProgress(
            user_id=session['user_id'],
            course_id=course_id,
            status='in_progress'
        )
        db.session.add(progress)
    elif progress.status == 'not_started':
        progress.status = 'in_progress'
    
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/api/complete_material/<int:material_id>', methods=['POST'])
@login_required
def complete_material(material_id):
    return jsonify({'status': 'success'})

# ========== ЗАПУСК ==========

if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("☕ COFFEE TRAINING PLATFORM")
    print("=" * 50)
    print("📁 База данных: coffee_training.db")
    print("🔒 Режим: ПОЛНАЯ ЗАЩИТА ДАННЫХ")
    print("✅ Тестовые аккаунты: admin@coffee.ru / employee@coffee.ru")
    print("🌐 Сервер запущен: http://127.0.0.1:5000")
    print("=" * 50 + "\n")
    
    app.run(debug=True, port=5000, host='0.0.0.0')