from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from database import db, User, Course, Material, Question, UserProgress, Standard
from datetime import datetime
import os
from functools import wraps
from sqlalchemy import text

app = Flask(__name__)
app.secret_key = 'coffee_secret_key_12345'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///coffee_training.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# ✅ ОДИН РАЗ: ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ
with app.app_context():
    print("=" * 50)
    print("🚀 ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ")
    print("=" * 50)
    
    # 1. УДАЛЯЕМ СТАРУЮ БАЗУ (если нужно)
    print("🧹 Удаляем старую базу для чистоты...")
    db.drop_all()
    
    # 2. СОЗДАЕМ НОВУЮ БАЗУ С ПРАВИЛЬНОЙ СТРУКТУРОЙ
    print("🔄 Создаем таблицы...")
    db.create_all()
    
    # 3. ПРОВЕРЯЕМ СТРУКТУРУ
    try:
        result = db.session.execute(text("PRAGMA table_info(material)"))
        columns = [row[1] for row in result]
        print(f"📊 Колонки в таблице material: {columns}")
        
        if 'file_path' in columns:
            print("✅ Колонка file_path присутствует")
        else:
            print("❌ ОШИБКА: Колонка file_path отсутствует!")
            
    except Exception as e:
        print(f"⚠️ Ошибка проверки: {e}")
    
    # 4. СОЗДАЕМ ТЕСТОВЫЕ ДАННЫЕ
    print("➕ Создаем тестовые данные...")
    
    # Администратор
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
    
    # Тестовый сотрудник
    if not User.query.filter_by(email='employee@coffee.ru').first():
        employee = User(
            name='Тестовый Сотрудник',
            email='employee@coffee.ru',
            password='123456',
            position='Бариста-универсал',
            is_admin=False
        )
        db.session.add(employee)
        print("👤 Тестовый сотрудник создан")
    
    # Тестовые курсы
    if Course.query.count() == 0:
        basic_course = Course(
            title='Введение в работу кофейни',
            description='Основные правила, стандарты и безопасность',
            category='Базовый',
            required_position='Все',
            order=1,
            is_published=True
        )
        db.session.add(basic_course)
        
        barista_course = Course(
            title='Профессия Бариста',
            description='Все о кофе: от зерна до чашки',
            category='Профессиональный',
            required_position='Бариста-универсал',
            order=2,
            is_published=True
        )
        db.session.add(barista_course)
        print("📚 2 тестовых курса созданы")
    
    db.session.commit()
    print("✅ База данных успешно инициализирована!")
    print("=" * 50)

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
    materials = Material.query.filter_by(course_id=course_id).order_by(Material.order).all()
    questions = Question.query.filter_by(course_id=course_id).all()
    
    if not session.get('is_admin'):
        user_position = session.get('position', 'Бариста')
        if course.required_position != 'Все' and course.required_position != user_position:
            flash('У вас нет доступа к этому курсу', 'danger')
            return redirect(url_for('view_courses'))
    
    return render_template('course_detail.html', 
                         course=course, 
                         materials=materials,
                         questions=questions)

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
            file_path=request.form.get('file_path', '')  # Добавляем file_path
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
        material.file_path = request.form.get('file_path', '')  # Обновляем file_path
        
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

# Управление пользователями
@app.route('/admin/users')
@admin_required
def admin_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin_users.html', users=users, positions=POSITIONS)

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
    print("🌐 Сервер запущен: http://127.0.0.1:5000")
    print("=" * 50 + "\n")
    
    app.run(debug=True, port=5000, host='0.0.0.0')