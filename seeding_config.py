# backend/scripts/seed_data.py
"""
Seed initial data for ApexLearn platform
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import random
from datetime import datetime, timedelta
from faker import Faker
from app import create_app
from app.models import *

fake = Faker('en_IN')  # Use Indian locale

class DataSeeder:
    """Seed database with initial data"""
    
    def __init__(self, app):
        self.app = app
        self.subjects_data = {
            'CBSE': {
                9: ['Mathematics', 'Science', 'Social Science', 'English', 'Hindi'],
                10: ['Mathematics', 'Science', 'Social Science', 'English', 'Hindi'],
                11: {
                    'Science': ['Physics', 'Chemistry', 'Biology', 'Mathematics', 'English'],
                    'Commerce': ['Accountancy', 'Business Studies', 'Economics', 'Mathematics', 'English'],
                    'Arts': ['History', 'Political Science', 'Geography', 'Economics', 'English']
                },
                12: {
                    'Science': ['Physics', 'Chemistry', 'Biology', 'Mathematics', 'English'],
                    'Commerce': ['Accountancy', 'Business Studies', 'Economics', 'Mathematics', 'English'],
                    'Arts': ['History', 'Political Science', 'Geography', 'Economics', 'English']
                }
            },
            'ICSE': {
                9: ['Mathematics', 'Physics', 'Chemistry', 'Biology', 'History', 'Geography', 'English'],
                10: ['Mathematics', 'Physics', 'Chemistry', 'Biology', 'History', 'Geography', 'English']
            }
        }
        
        self.chapter_templates = {
            'Mathematics': [
                'Number Systems', 'Algebra', 'Coordinate Geometry', 'Geometry',
                'Trigonometry', 'Mensuration', 'Statistics', 'Probability'
            ],
            'Physics': [
                'Motion', 'Force and Laws of Motion', 'Gravitation', 'Work and Energy',
                'Sound', 'Light', 'Electricity', 'Magnetism'
            ],
            'Chemistry': [
                'Matter', 'Atoms and Molecules', 'Structure of Atom', 'Chemical Reactions',
                'Acids and Bases', 'Metals and Non-metals', 'Carbon Compounds', 'Periodic Table'
            ],
            'Biology': [
                'Life Processes', 'Control and Coordination', 'Reproduction',
                'Heredity and Evolution', 'Natural Resources', 'Environment'
            ]
        }
    
    def seed_all(self):
        """Seed all data"""
        with self.app.app_context():
            print("Starting data seeding...")
            
            # Create admin user
            self.create_admin_user()
            
            # Seed subjects and topics
            self.seed_subjects()
            
            # Create sample users
            self.create_sample_users(50)
            
            # Create sample questions
            self.seed_questions(500)
            
            # Create sample quizzes
            self.create_sample_quizzes(20)
            
            # Create sample classes
            self.create_sample_classes(10)
            
            # Generate sample progress data
            self.generate_progress_data()
            
            print("Data seeding completed!")
    
    def create_admin_user(self):
        """Create admin user"""
        admin = User.query.filter_by(email='admin@apexlearn.in').first()
        
        if not admin:
            admin = User(
                email='admin@apexlearn.in',
                name='Admin User',
                role=UserRole.ADMIN,
                is_active=True,
                is_verified=True,
                email_verified=True
            )
            admin.set_password('Admin@123')
            
            db.session.add(admin)
            db.session.commit()
            
            print("Admin user created: admin@apexlearn.in / Admin@123")
    
    def seed_subjects(self):
        """Seed subjects, chapters, and topics"""
        colors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899']
        
        for board_name, grades in self.subjects_data.items():
            board = Board[board_name]
            
            for grade, subjects in grades.items():
                if isinstance(subjects, dict):  # Grade 11-12 with streams
                    for stream, stream_subjects in subjects.items():
                        for subject_name in stream_subjects:
                            self._create_subject_structure(
                                subject_name, board, grade, stream, 
                                random.choice(colors)
                            )
                else:  # Grade 9-10
                    for subject_name in subjects:
                        self._create_subject_structure(
                            subject_name, board, grade, None,
                            random.choice(colors)
                        )
        
        db.session.commit()
        print(f"Created {Subject.query.count()} subjects")
    
    def _create_subject_structure(self, subject_name, board, grade, stream, color):
        """Create subject with chapters and topics"""
        subject = Subject.query.filter_by(
            name=subject_name,
            board=board,
            grade=grade
        ).first()
        
        if not subject:
            subject = Subject(
                name=subject_name,
                board=board,
                grade=grade,
                color=color,
                is_core=True
            )
            db.session.add(subject)
            db.session.flush()
            
            # Create chapters
            chapters = self.chapter_templates.get(subject_name, [f'Chapter {i+1}' for i in range(8)])
            
            for i, chapter_name in enumerate(chapters):
                chapter = Chapter(
                    subject_id=subject.id,
                    name=chapter_name,
                    chapter_number=i + 1,
                    estimated_hours=random.randint(8, 15)
                )
                db.session.add(chapter)
                db.session.flush()
                
                # Create topics for each chapter
                for j in range(random.randint(3, 6)):
                    topic = Topic(
                        subject_id=subject.id,
                        chapter_id=chapter.id,
                        name=f"{chapter_name} - Topic {j+1}",
                        difficulty_level=random.choice(list(DifficultyLevel)),
                        estimated_minutes=random.randint(30, 90),
                        learning_objectives=[
                            f"Understand concept {j+1}",
                            f"Apply formula {j+1}",
                            f"Solve problems related to {chapter_name}"
                        ]
                    )
                    db.session.add(topic)
    
    def create_sample_users(self, count):
        """Create sample users"""
        # Create students
        students = []
        for i in range(count):
            student = User(
                email=fake.email(),
                name=fake.name(),
                phone=fake.phone_number()[:15],
                role=UserRole.STUDENT,
                grade=random.choice([9, 10, 11, 12]),
                board=random.choice(list(Board)),
                school=fake.company(),
                city=fake.city(),
                state=fake.state(),
                dob=fake.date_of_birth(minimum_age=13, maximum_age=18),
                is_active=True,
                email_verified=random.choice([True, False]),
                phone_verified=random.choice([True, False])
            )
            student.set_password('password123')
            
            # Create gamification profile
            gamification = Gamification(
                user=student,
                xp=random.randint(0, 5000),
                level=random.randint(1, 10),
                coins=random.randint(0, 1000),
                streak_days=random.randint(0, 30),
                longest_streak=random.randint(0, 60),
                total_study_minutes=random.randint(0, 10000)
            )
            
            db.session.add(student)
            db.session.add(gamification)
            students.append(student)
        
        # Create parents for some students
        for student in students[:count//2]:
            parent = User(
                email=fake.email(),
                name=fake.name(),
                phone=fake.phone_number()[:15],
                role=UserRole.PARENT,
                city=student.city,
                state=student.state,
                is_active=True
            )
            parent.set_password('password123')
            db.session.add(parent)
            
            # Link parent to child
            relationship = ParentChild(
                parent=parent,
                child=student,
                relationship_type='parent',
                is_primary=True,
                consent_given=True,
                consent_date=datetime.utcnow()
            )
            db.session.add(relationship)
        
        # Create teachers
        for i in range(10):
            teacher = User(
                email=f"teacher{i}@apexlearn.in",
                name=fake.name(),
                phone=fake.phone_number()[:15],
                role=UserRole.TEACHER,
                school=fake.company(),
                city=fake.city(),
                state=fake.state(),
                is_active=True
            )
            teacher.set_password('password123')
            db.session.add(teacher)
        
        db.session.commit()
        print(f"Created {count} students, {count//2} parents, and 10 teachers")
    
    def seed_questions(self, count):
        """Create sample questions"""
        topics = Topic.query.all()
        question_types = list(QuestionType)
        difficulty_levels = list(DifficultyLevel)
        
        for i in range(count):
            topic = random.choice(topics)
            q_type = random.choice(question_types)
            
            question = Question(
                topic_id=topic.id,
                chapter_id=topic.chapter_id,
                question_type=q_type,
                difficulty=random.choice(difficulty_levels),
                question_text=f"Sample question {i+1} for {topic.name}?",
                marks=random.choice([1.0, 2.0, 3.0, 4.0, 5.0]),
                time_limit=random.randint(60, 300),
                bloom_level=random.choice(['Remember', 'Understand', 'Apply', 'Analyze'])
            )
            
            if q_type == QuestionType.MCQ:
                question.options = ['Option A', 'Option B', 'Option C', 'Option D']
                question.correct_answer = random.choice(['A', 'B', 'C', 'D'])
            elif q_type == QuestionType.TRUE_FALSE:
                question.options = ['True', 'False']
                question.correct_answer = random.choice(['True', 'False'])
            elif q_type == QuestionType.NUMERICAL:
                question.correct_answer = str(random.randint(1, 100))
            else:
                question.correct_answer = f"Sample answer for question {i+1}"
            
            question.solution = f"Solution explanation for question {i+1}"
            question.hints = [
                f"Hint 1 for question {i+1}",
                f"Hint 2 for question {i+1}"
            ]
            
            db.session.add(question)
        
        db.session.commit()
        print(f"Created {count} questions")
    
    def create_sample_quizzes(self, count):
        """Create sample quizzes"""
        for i in range(count):
            quiz = Quiz(
                quiz_type=random.choice(['diagnostic', 'practice', 'mock', 'chapter']),
                title=f"Sample Quiz {i+1}",
                description=f"This is a sample quiz for testing",
                total_marks=random.randint(20, 100),
                duration_minutes=random.randint(15, 120),
                is_adaptive=random.choice([True, False]),
                created_by=1  # Admin user
            )
            db.session.add(quiz)
            db.session.flush()
            
            # Add random questions to quiz
            questions = Question.query.order_by(db.func.random()).limit(
                random.randint(5, 20)
            ).all()
            
            for order, question in enumerate(questions):
                quiz_question = QuizQuestion(
                    quiz_id=quiz.id,
                    question_id=question.id,
                    order=order + 1,
                    marks=question.marks
                )
                db.session.add(quiz_question)
        
        db.session.commit()
        print(f"Created {count} quizzes")
    
    def create_sample_classes(self, count):
        """Create sample classes for teachers"""
        teachers = User.query.filter_by(role=UserRole.TEACHER).all()
        subjects = Subject.query.all()
        
        for i in range(count):
            teacher = random.choice(teachers)
            subject = random.choice(subjects)
            
            class_obj = Class(
                name=f"{subject.name} Batch {i+1}",
                section=random.choice(['A', 'B', 'C']),
                grade=subject.grade,
                board=subject.board,
                subject_id=subject.id,
                academic_year='2024-25',
                join_code=f"CLS{i:04d}"
            )
            db.session.add(class_obj)
            db.session.flush()
            
            # Add teacher to class
            class_obj.teachers.append(teacher)
            
            # Add random students to class
            students = User.query.filter_by(
                role=UserRole.STUDENT,
                grade=subject.grade
            ).order_by(db.func.random()).limit(
                random.randint(20, 40)
            ).all()
            
            for student in students:
                class_obj.students.append(student)
        
        db.session.commit()
        print(f"Created {count} classes")
    
    def generate_progress_data(self):
        """Generate sample progress data for students"""
        students = User.query.filter_by(role=UserRole.STUDENT).all()
        
        for student in students[:20]:  # Generate for first 20 students
            subjects = Subject.query.filter_by(grade=student.grade).all()
            
            for subject in subjects:
                progress = StudentProgress(
                    student_id=student.id,
                    subject_id=subject.id,
                    syllabus_completion=random.uniform(10, 90),
                    average_score=random.uniform(40, 95),
                    total_study_time=random.randint(100, 5000),
                    mastery_level=random.choice(list(MasteryLevel)),
                    last_activity=datetime.utcnow() - timedelta(days=random.randint(0, 7))
                )
                db.session.add(progress)
                
                # Create topic progress
                topics = Topic.query.filter_by(subject_id=subject.id).limit(10).all()
                
                for topic in topics:
                    topic_progress = TopicProgress(
                        progress_id=progress.id,
                        topic_id=topic.id,
                        mastery_score=random.uniform(0, 1),
                        practice_count=random.randint(0, 50),
                        correct_count=random.randint(0, 40),
                        time_spent=random.randint(0, 300),
                        last_practiced=datetime.utcnow() - timedelta(days=random.randint(0, 30))
                    )
                    db.session.add(topic_progress)
            
            # Create study plan
            study_plan = StudyPlan(
                student_id=student.id,
                goal=random.choice(['Boards', 'JEE', 'NEET', 'basics']),
                target_exam_date=datetime.utcnow() + timedelta(days=random.randint(30, 365)),
                daily_study_minutes=random.choice([30, 45, 60, 90, 120]),
                weekly_hours=random.randint(10, 30),
                is_active=True
            )
            db.session.add(study_plan)
            db.session.flush()
            
            # Create study tasks
            for i in range(10):
                task = StudyTask(
                    plan_id=study_plan.id,
                    topic_id=random.choice(topics).id if topics else None,
                    task_type=random.choice(['learn', 'practice', 'revise', 'mock_test']),
                    title=f"Task {i+1}",
                    description=f"Complete this task to improve your understanding",
                    scheduled_date=datetime.utcnow() + timedelta(days=i),
                    estimated_minutes=random.choice([15, 30, 45, 60]),
                    priority=random.randint(1, 5),
                    status=random.choice(list(TaskStatus))
                )
                db.session.add(task)
        
        db.session.commit()
        print("Generated progress data for students")


# backend/scripts/setup_database.py
"""
Database setup script
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db

def setup_database():
    """Setup database with tables"""
    app = create_app('development')
    
    with app.app_context():
        # Create all tables
        db.create_all()
        print("Database tables created successfully!")
        
        # Create indexes for better performance
        create_indexes()
        
        print("Database setup completed!")

def create_indexes():
    """Create database indexes for performance"""
    indexes = [
        'CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)',
        'CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)',
        'CREATE INDEX IF NOT EXISTS idx_student_progress_student ON student_progress(student_id)',
        'CREATE INDEX IF NOT EXISTS idx_quiz_results_student ON quiz_results(student_id)',
        'CREATE INDEX IF NOT EXISTS idx_analytics_events_user ON analytics_events(user_id)',
        'CREATE INDEX IF NOT EXISTS idx_analytics_events_timestamp ON analytics_events(timestamp)',
        'CREATE INDEX IF NOT EXISTS idx_content_embeddings ON content USING GIN(embeddings)'
    ]
    
    for index in indexes:
        try:
            db.session.execute(index)
        except Exception as e:
            print(f"Index creation skipped: {e}")
    
    db.session.commit()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Setup ApexLearn database')
    parser.add_argument('--seed', action='store_true', help='Seed with sample data')
    parser.add_argument('--reset', action='store_true', help='Reset database')
    
    args = parser.parse_args()
    
    if args.reset:
        app = create_app('development')
        with app.app_context():
            db.drop_all()
            print("Database reset completed!")
    
    setup_database()
    
    if args.seed:
        from seed_data import DataSeeder
        app = create_app('development')
        seeder = DataSeeder(app)
        seeder.seed_all()


# backend/config.py
"""
Application configuration
"""

import os
from datetime import timedelta

class Config:
    """Base configuration"""
    
    # App
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://localhost/apexlearn'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-key'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=7)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # Redis
    REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
    
    # File uploads
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'docx', 'xlsx'}
    
    # CORS
    CORS_ORIGINS = ['http://localhost:3000', 'http://localhost:5173']
    
    # Rate limiting
    RATELIMIT_STORAGE_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}"
    
    # Email
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    
    # Pagination
    ITEMS_PER_PAGE = 20

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # Use stronger keys in production
    SECRET_KEY = os.environ.get('SECRET_KEY')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    
    # SSL
    PREFERRED_URL_SCHEME = 'https'
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}