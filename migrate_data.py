# migrate_data.py
from app import app, db
from database import Course, Section, Material, Lesson

def migrate_data():
    """Перенос существующих данных в новую структуру"""
    print("=" * 50)
    print("🔄 ЗАПУСК МИГРАЦИИ ДАННЫХ")
    print("=" * 50)
    
    with app.app_context():
        # Получаем все курсы
        courses = Course.query.all()
        print(f"📚 Найдено курсов: {len(courses)}")
        
        for course in courses:
            print(f"\n📖 Обрабатываем курс: {course.title} (ID: {course.id})")
            
            # Проверяем, есть ли уже разделы в новой структуре
            existing_sections = Section.query.filter_by(course_id=course.id).first()
            
            if existing_sections:
                print(f"   ⏩ Уже есть разделы, пропускаем...")
                continue
            
            # Проверяем, есть ли старые материалы (Material)
            materials = Material.query.filter_by(course_id=course.id).order_by(Material.order).all()
            
            if materials:
                print(f"   📄 Найдено материалов (Material): {len(materials)}")
                
                # Создаем корневой раздел для материалов
                root_section = Section(
                    course_id=course.id,
                    title="Материалы курса",
                    description="Основные материалы курса",
                    type='folder',
                    order=0,
                    is_required=True
                )
                db.session.add(root_section)
                db.session.flush()  # Получаем ID
                
                # Переносим каждый материал как урок
                for i, material in enumerate(materials):
                    lesson_section = Section(
                        course_id=course.id,
                        parent_id=root_section.id,
                        title=material.title,
                        description=material.content[:200] if material.content else "",
                        type='lesson',
                        content=material.content,
                        media_url=material.file_path,
                        order=i,
                        is_required=material.is_required if hasattr(material, 'is_required') else True
                    )
                    db.session.add(lesson_section)
                    print(f"      ➕ Добавлен урок: {material.title}")
            
            # Проверяем, есть ли уроки (Lesson) без разделов
            orphan_lessons = Lesson.query.filter(
                Lesson.section_id == None,
                Lesson.course_id == course.id
            ).all()
            
            if orphan_lessons:
                print(f"   📄 Найдено уроков без разделов: {len(orphan_lessons)}")
                
                # Если нет корневого раздела, создаем
                if not materials:
                    root_section = Section(
                        course_id=course.id,
                        title="Уроки",
                        description="Уроки курса",
                        type='folder',
                        order=0,
                        is_required=True
                    )
                    db.session.add(root_section)
                    db.session.flush()
                
                # Привязываем уроки к разделу
                for i, lesson in enumerate(orphan_lessons):
                    # Создаем раздел-урок на основе Lesson
                    lesson_section = Section(
                        course_id=course.id,
                        parent_id=root_section.id,
                        title=lesson.title,
                        description=lesson.content[:200] if lesson.content else "",
                        type='lesson',
                        content=lesson.content,
                        media_url=lesson.media_url,
                        duration=lesson.duration,
                        order=i + len(materials),
                        is_required=lesson.is_required if hasattr(lesson, 'is_required') else True
                    )
                    db.session.add(lesson_section)
                    print(f"      ➕ Перенесен урок: {lesson.title}")
            
            # Если ничего не найдено
            if not materials and not orphan_lessons:
                print("   ⚠️ Нет материалов для переноса")
        
        # Сохраняем все изменения
        db.session.commit()
        print("\n✅ Миграция данных завершена!")
        print("=" * 50)

if __name__ == "__main__":
    migrate_data()