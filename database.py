# database.py - Улучшенная версия с исправлениями

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# Таблица пользователей
class User(db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(50), default='Бариста')  # Должность
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связи
    progress = db.relationship('UserProgress', backref='user', lazy=True, cascade='all, delete-orphan')
    lesson_progress = db.relationship('LessonProgress', backref='user', lazy=True, cascade='all, delete-orphan')
    test_results = db.relationship('TestResult', backref='user', lazy=True, cascade='all, delete-orphan')

# Таблица курсов
class Course(db.Model):
    __tablename__ = 'course'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    video_url = db.Column(db.String(500))
    category = db.Column(db.String(50), default='Базовый')  # Базовый/Для должности
    required_position = db.Column(db.String(50), default='Все')  # Для кого курс
    order = db.Column(db.Integer, default=0)  # Порядок в обучении
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Индексы
    __table_args__ = (
        db.Index('idx_course_order', 'order'),
        db.Index('idx_course_category', 'category'),
    )
    
    # Связи
    materials = db.relationship('Material', backref='course', lazy=True, cascade='all, delete-orphan')
    sections = db.relationship('Section', backref='course', lazy=True, cascade='all, delete-orphan')
    tests = db.relationship('Test', backref='course', lazy=True, cascade='all, delete-orphan')
    user_progress = db.relationship('UserProgress', backref='course', lazy=True, cascade='all, delete-orphan')

# Разделы курса (могут быть вложенными)
class Section(db.Model):
    __tablename__ = 'section'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id', ondelete='CASCADE'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('section.id', ondelete='CASCADE'), nullable=True)  # NEW: для вложенности
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    type = db.Column(db.String(20), default='folder')  # NEW: 'folder' для модуля, 'lesson' для урока без модуля
    content = db.Column(db.Text)  # NEW: если type='lesson', здесь будет контент
    media_url = db.Column(db.String(500))  # NEW: если type='lesson'
    duration = db.Column(db.Integer)  # NEW: если type='lesson'
    is_required = db.Column(db.Boolean, default=True)  # NEW
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Индексы
    __table_args__ = (
        db.Index('idx_section_course_order', 'course_id', 'order'),
        db.Index('idx_section_parent', 'parent_id'),  # NEW
    )
    
    # Связи
    parent = db.relationship('Section', remote_side=[id], backref='children', lazy=True)  # NEW
    lessons = db.relationship('Lesson', backref='section', lazy=True, cascade='all, delete-orphan')
    tests = db.relationship('Test', backref='section', lazy=True, cascade='all, delete-orphan')

    # Метод для проверки, является ли раздел модулем
    def is_folder(self):
        return self.type == 'folder'
    
    # Метод для проверки, является ли раздел уроком
    def is_lesson(self):
        return self.type == 'lesson'

# Уроки внутри раздела (как страницы в главе)
class Lesson(db.Model):
    __tablename__ = 'lesson'
    
    id = db.Column(db.Integer, primary_key=True)
    section_id = db.Column(db.Integer, db.ForeignKey('section.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)  # Текст урока или HTML
    type = db.Column(db.String(50), default='text')  # 'text', 'video', 'presentation', 'pdf'
    media_url = db.Column(db.String(500))  # Ссылка на видео/презентацию/файл
    duration = db.Column(db.Integer)  # Длительность в минутах (для видео)
    order = db.Column(db.Integer, default=0)  # Порядок в разделе
    is_required = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Индексы
    __table_args__ = (
        db.Index('idx_lesson_section_order', 'section_id', 'order'),
    )
    
    # Связи
    lesson_progress = db.relationship('LessonProgress', backref='lesson', lazy=True, cascade='all, delete-orphan')

# Материалы (оставляем для обратной совместимости)
class Material(db.Model):
    __tablename__ = 'material'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)  # Текст или описание
    type = db.Column(db.String(20), default='text')  # text, pdf, video, link, image
    file_path = db.Column(db.String(500))  # Путь к загруженному файлу
    order = db.Column(db.Integer, default=0)
    is_required = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Индекс
    __table_args__ = (
        db.Index('idx_material_course_order', 'course_id', 'order'),
    )

# Тесты (могут быть для курса или для раздела)
class Test(db.Model):
    __tablename__ = 'test'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id', ondelete='CASCADE'), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('section.id', ondelete='CASCADE'))  # Если None - тест для всего курса
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    passing_score = db.Column(db.Integer, default=70)  # Процент для зачета (0-100)
    order = db.Column(db.Integer, default=0)
    is_final = db.Column(db.Boolean, default=False)  # Финальный тест курса?
    
    # Добавляем только эти поля:
    time_limit = db.Column(db.Integer, nullable=True)  # время в минутах, NULL = без ограничения
    is_required = db.Column(db.Boolean, default=True)  # обязательно ли проходить тест
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связи (оставляем как было)
    questions = db.relationship('Question', backref='test', lazy=True, cascade='all, delete-orphan')
    test_results = db.relationship('TestResult', backref='test', lazy=True, cascade='all, delete-orphan')
    
    # УДАЛИТЬ ЭТУ СТРОКУ (она создает конфликт):
    # course = db.relationship('Course', backref='tests')

# Вопросы тестов
class Question(db.Model):
    __tablename__ = 'question'
    
    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id', ondelete='CASCADE'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), default='single_choice')  # single_choice, multiple_choice, text
    options = db.Column(db.Text)  # Варианты через | или JSON
    correct_answer = db.Column(db.Text)  # Может быть строка или JSON для нескольких ответов
    points = db.Column(db.Integer, default=1)
    explanation = db.Column(db.Text)  # Объяснение правильного ответа
    order = db.Column(db.Integer, default=0)
    
    # Индекс
    __table_args__ = (
        db.Index('idx_question_test_order', 'test_id', 'order'),
    )
    
    # Связи
    user_answers = db.relationship('UserAnswer', backref='question', lazy=True, cascade='all, delete-orphan')

# Прогресс пользователей по курсам
class UserProgress(db.Model):
    __tablename__ = 'user_progress'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.String(20), default='not_started')  # not_started, in_progress, completed
    score = db.Column(db.Integer, default=0)  # Баллы за тест
    completed_at = db.Column(db.DateTime)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Уникальный индекс и индексы
    __table_args__ = (
        db.UniqueConstraint('user_id', 'course_id', name='unique_user_course'),
        db.Index('idx_user_progress_status', 'user_id', 'status'),
    )

# Прогресс по урокам
class LessonProgress(db.Model):
    __tablename__ = 'lesson_progress'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lesson.id', ondelete='CASCADE'), nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'lesson_id', name='unique_user_lesson'),
    )

# Результаты тестов
class TestResult(db.Model):
    __tablename__ = 'test_result'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id', ondelete='CASCADE'), nullable=False)
    score = db.Column(db.Integer, default=0)  # Набранные баллы
    max_score = db.Column(db.Integer, default=0)  # Максимально возможные баллы
    percentage = db.Column(db.Float, default=0.0)  # Процент правильных ответов
    passed = db.Column(db.Boolean, default=False)  # Прошел ли тест
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Индексы
    __table_args__ = (
        db.Index('idx_test_result_user_test', 'user_id', 'test_id'),
        db.Index('idx_test_result_passed', 'user_id', 'passed'),
    )
    
    # Связь с ответами пользователя
    answers = db.relationship('UserAnswer', backref='test_result', lazy=True, cascade='all, delete-orphan')

# Ответы пользователя на вопросы теста
class UserAnswer(db.Model):
    __tablename__ = 'user_answer'
    
    id = db.Column(db.Integer, primary_key=True)
    test_result_id = db.Column(db.Integer, db.ForeignKey('test_result.id', ondelete='CASCADE'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id', ondelete='CASCADE'), nullable=False)
    user_answer = db.Column(db.Text)  # Ответ пользователя
    is_correct = db.Column(db.Boolean, default=False)
    points_earned = db.Column(db.Integer, default=0)
    answered_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Индекс
    __table_args__ = (
        db.Index('idx_user_answer_test_result', 'test_result_id'),
    )

# Библиотека стандартов
class Standard(db.Model):
    __tablename__ = 'standard'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)
    category = db.Column(db.String(50))  # Кофе, Сервис, Безопасность и т.д.
    file_url = db.Column(db.String(500))  # Ссылка на файл
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Индекс
    __table_args__ = (
        db.Index('idx_standard_category', 'category'),
    )

# Настройки сайта (для смены тем оформления)
class SiteSettings(db.Model):
    __tablename__ = 'site_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    theme_name = db.Column(db.String(50), default='default')
    primary_color = db.Column(db.String(7), default='#007bff')  # Основной цвет
    secondary_color = db.Column(db.String(7), default='#6c757d')  # Вторичный цвет
    accent_color = db.Column(db.String(7), default='#28a745')  # Акцентный цвет
    font_family = db.Column(db.String(100), default='Arial, sans-serif')
    logo_url = db.Column(db.String(500))  # Ссылка на логотип
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)