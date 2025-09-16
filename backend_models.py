# backend/app/models/__init__.py
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON, ForeignKey, Table, Enum
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
import enum
import uuid

db = SQLAlchemy()

# Enums
class UserRole(enum.Enum):
    STUDENT = "student"
    PARENT = "parent"
    TEACHER = "teacher"
    ADMIN = "admin"

class Board(enum.Enum):
    CBSE = "CBSE"
    ICSE = "ICSE"
    ISC = "ISC"
    STATE_TS = "BSE_TELANGANA"
    STATE_AP = "BSE_ANDHRA_PRADESH"

class DifficultyLevel(enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"

class QuestionType(enum.Enum):
    MCQ = "mcq"
    SHORT_ANSWER = "short_answer"
    NUMERICAL = "numerical"
    LONG_ANSWER = "long_answer"
    TRUE_FALSE = "true_false"

class MasteryLevel(enum.Enum):
    WEAK = "weak"
    IMPROVING = "improving"
    STRONG = "strong"
    MASTERED = "mastered"

class TaskStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    OVERDUE = "overdue"

# Association Tables
teacher_class = Table('teacher_class', db.metadata,
    Column('teacher_id', Integer, ForeignKey('users.id')),
    Column('class_id', Integer, ForeignKey('classes.id'))
)

student_class = Table('student_class', db.metadata,
    Column('student_id', Integer, ForeignKey('users.id')),
    Column('class_id', Integer, ForeignKey('classes.id'))
)

# User Model
class User(db.Model):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), unique=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(120), unique=True, nullable=False)
    phone = Column(String(15), unique=True)
    password_hash = Column(String(255))
    role = Column(Enum(UserRole), nullable=False)
    name = Column(String(100), nullable=False)
    dob = Column(DateTime)
    grade = Column(Integer)  # 5-12
    board = Column(Enum(Board))
    stream = Column(String(50))  # Science, Commerce, Arts (for 11-12)
    school = Column(String(200))
    city = Column(String(100))
    state = Column(String(100))
    
    # OAuth fields
    google_id = Column(String(100))
    profile_picture = Column(String(500))
    
    # Settings
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    email_verified = Column(Boolean, default=False)
    phone_verified = Column(Boolean, default=False)
    parental_consent = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Relationships
    parent_relationships = relationship('ParentChild', foreign_keys='ParentChild.child_id', back_populates='child')
    child_relationships = relationship('ParentChild', foreign_keys='ParentChild.parent_id', back_populates='parent')
    study_plans = relationship('StudyPlan', back_populates='student')
    quiz_results = relationship('QuizResult', back_populates='student')
    progress_records = relationship('StudentProgress', back_populates='student')
    gamification = relationship('Gamification', back_populates='user', uselist=False)
    chat_sessions = relationship('ChatSession', back_populates='user')
    notifications = relationship('Notification', back_populates='user')
    subscriptions = relationship('Subscription', back_populates='user')
    
    # Teacher relationships
    taught_classes = relationship('Class', secondary=teacher_class, back_populates='teachers')
    created_assignments = relationship('Assignment', back_populates='teacher')
    
    # Student relationships  
    enrolled_classes = relationship('Class', secondary=student_class, back_populates='students')
    assignment_submissions = relationship('AssignmentSubmission', back_populates='student')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'email': self.email,
            'name': self.name,
            'role': self.role.value,
            'grade': self.grade,
            'board': self.board.value if self.board else None,
            'school': self.school
        }

# Parent-Child Relationship
class ParentChild(db.Model):
    __tablename__ = 'parent_child'
    
    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey('users.id'))
    child_id = Column(Integer, ForeignKey('users.id'))
    relationship_type = Column(String(50))  # mother, father, guardian
    is_primary = Column(Boolean, default=False)
    consent_given = Column(Boolean, default=False)
    consent_date = Column(DateTime)
    
    parent = relationship('User', foreign_keys=[parent_id], back_populates='child_relationships')
    child = relationship('User', foreign_keys=[child_id], back_populates='parent_relationships')

# Subject Model
class Subject(db.Model):
    __tablename__ = 'subjects'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    code = Column(String(20))
    board = Column(Enum(Board))
    grade = Column(Integer)
    is_core = Column(Boolean, default=True)
    icon = Column(String(100))
    color = Column(String(7))  # Hex color
    
    topics = relationship('Topic', back_populates='subject')
    chapters = relationship('Chapter', back_populates='subject')

# Chapter Model
class Chapter(db.Model):
    __tablename__ = 'chapters'
    
    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey('subjects.id'))
    name = Column(String(200), nullable=False)
    chapter_number = Column(Integer)
    description = Column(Text)
    estimated_hours = Column(Float)
    
    subject = relationship('Subject', back_populates='chapters')
    topics = relationship('Topic', back_populates='chapter')
    questions = relationship('Question', back_populates='chapter')

# Topic Model
class Topic(db.Model):
    __tablename__ = 'topics'
    
    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey('subjects.id'))
    chapter_id = Column(Integer, ForeignKey('chapters.id'))
    name = Column(String(200), nullable=False)
    description = Column(Text)
    difficulty_level = Column(Enum(DifficultyLevel))
    prerequisite_topics = Column(JSON)  # List of topic IDs
    learning_objectives = Column(JSON)
    keywords = Column(JSON)
    estimated_minutes = Column(Integer, default=30)
    
    subject = relationship('Subject', back_populates='topics')
    chapter = relationship('Chapter', back_populates='topics')
    content_items = relationship('Content', back_populates='topic')
    questions = relationship('Question', back_populates='topic')
    progress = relationship('TopicProgress', back_populates='topic')

# Content Model (for RAG)
class Content(db.Model):
    __tablename__ = 'content'
    
    id = Column(Integer, primary_key=True)
    topic_id = Column(Integer, ForeignKey('topics.id'))
    content_type = Column(String(50))  # notes, video, example, formula
    title = Column(String(200))
    body = Column(Text)
    source = Column(String(200))  # NCERT, reference book, etc.
    media_url = Column(String(500))
    embeddings = Column(JSON)  # Store vector embeddings for RAG
    metadata = Column(JSON)
    
    topic = relationship('Topic', back_populates='content_items')

# Question Bank
class Question(db.Model):
    __tablename__ = 'questions'
    
    id = Column(Integer, primary_key=True)
    topic_id = Column(Integer, ForeignKey('topics.id'))
    chapter_id = Column(Integer, ForeignKey('chapters.id'))
    question_type = Column(Enum(QuestionType))
    difficulty = Column(Enum(DifficultyLevel))
    question_text = Column(Text, nullable=False)
    question_image = Column(String(500))
    options = Column(JSON)  # For MCQ
    correct_answer = Column(Text)
    solution = Column(Text)
    solution_steps = Column(JSON)
    hints = Column(JSON)
    marks = Column(Float, default=1.0)
    time_limit = Column(Integer)  # in seconds
    skill_tags = Column(JSON)
    bloom_level = Column(String(20))  # Remember, Understand, Apply, Analyze
    usage_count = Column(Integer, default=0)
    accuracy_rate = Column(Float)
    
    topic = relationship('Topic', back_populates='questions')
    chapter = relationship('Chapter', back_populates='questions')
    quiz_questions = relationship('QuizQuestion', back_populates='question')

# Study Plan
class StudyPlan(db.Model):
    __tablename__ = 'study_plans'
    
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('users.id'))
    goal = Column(String(100))  # Boards, JEE, NEET, basics, homework
    target_exam_date = Column(DateTime)
    daily_study_minutes = Column(Integer, default=30)
    weekly_hours = Column(Integer)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    student = relationship('User', back_populates='study_plans')
    tasks = relationship('StudyTask', back_populates='plan')

# Study Task
class StudyTask(db.Model):
    __tablename__ = 'study_tasks'
    
    id = Column(Integer, primary_key=True)
    plan_id = Column(Integer, ForeignKey('study_plans.id'))
    topic_id = Column(Integer, ForeignKey('topics.id'))
    task_type = Column(String(50))  # learn, practice, revise, mock_test
    title = Column(String(200))
    description = Column(Text)
    scheduled_date = Column(DateTime)
    due_date = Column(DateTime)
    estimated_minutes = Column(Integer)
    actual_minutes = Column(Integer)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)
    priority = Column(Integer, default=1)  # 1-5, 5 being highest
    completion_date = Column(DateTime)
    is_rescheduled = Column(Boolean, default=False)
    
    plan = relationship('StudyPlan', back_populates='tasks')

# Quiz/Mock Test
class Quiz(db.Model):
    __tablename__ = 'quizzes'
    
    id = Column(Integer, primary_key=True)
    quiz_type = Column(String(50))  # diagnostic, practice, mock, chapter
    title = Column(String(200))
    description = Column(Text)
    total_marks = Column(Float)
    duration_minutes = Column(Integer)
    passing_percentage = Column(Float, default=40.0)
    is_adaptive = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    questions = relationship('QuizQuestion', back_populates='quiz')
    results = relationship('QuizResult', back_populates='quiz')

# Quiz Question Association
class QuizQuestion(db.Model):
    __tablename__ = 'quiz_questions'
    
    id = Column(Integer, primary_key=True)
    quiz_id = Column(Integer, ForeignKey('quizzes.id'))
    question_id = Column(Integer, ForeignKey('questions.id'))
    order = Column(Integer)
    marks = Column(Float)
    
    quiz = relationship('Quiz', back_populates='questions')
    question = relationship('Question', back_populates='quiz_questions')

# Quiz Result
class QuizResult(db.Model):
    __tablename__ = 'quiz_results'
    
    id = Column(Integer, primary_key=True)
    quiz_id = Column(Integer, ForeignKey('quizzes.id'))
    student_id = Column(Integer, ForeignKey('users.id'))
    score = Column(Float)
    percentage = Column(Float)
    time_taken = Column(Integer)  # in seconds
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    answers = Column(JSON)  # Store all answers with question_id
    weak_areas = Column(JSON)
    strong_areas = Column(JSON)
    feedback = Column(Text)
    
    quiz = relationship('Quiz', back_populates='results')
    student = relationship('User', back_populates='quiz_results')

# Student Progress
class StudentProgress(db.Model):
    __tablename__ = 'student_progress'
    
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('users.id'))
    subject_id = Column(Integer, ForeignKey('subjects.id'))
    syllabus_completion = Column(Float, default=0.0)
    average_score = Column(Float)
    total_study_time = Column(Integer, default=0)  # in minutes
    last_activity = Column(DateTime)
    mastery_level = Column(Enum(MasteryLevel), default=MasteryLevel.WEAK)
    
    student = relationship('User', back_populates='progress_records')
    topic_progress = relationship('TopicProgress', back_populates='overall_progress')

# Topic Progress
class TopicProgress(db.Model):
    __tablename__ = 'topic_progress'
    
    id = Column(Integer, primary_key=True)
    progress_id = Column(Integer, ForeignKey('student_progress.id'))
    topic_id = Column(Integer, ForeignKey('topics.id'))
    mastery_score = Column(Float, default=0.0)
    practice_count = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    time_spent = Column(Integer, default=0)  # in minutes
    last_practiced = Column(DateTime)
    needs_revision = Column(Boolean, default=False)
    
    overall_progress = relationship('StudentProgress', back_populates='topic_progress')
    topic = relationship('Topic', back_populates='progress')

# Gamification
class Gamification(db.Model):
    __tablename__ = 'gamification'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True)
    xp = Column(Integer, default=0)
    level = Column(Integer, default=1)
    coins = Column(Integer, default=0)
    streak_days = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_activity_date = Column(DateTime)
    total_study_minutes = Column(Integer, default=0)
    badges = Column(JSON, default=list)
    achievements = Column(JSON, default=list)
    leaderboard_rank = Column(Integer)
    weekly_rank = Column(Integer)
    
    user = relationship('User', back_populates='gamification')
    badges_earned = relationship('Badge', back_populates='gamification')

# Badge
class Badge(db.Model):
    __tablename__ = 'badges'
    
    id = Column(Integer, primary_key=True)
    gamification_id = Column(Integer, ForeignKey('gamification.id'))
    badge_type = Column(String(50))
    name = Column(String(100))
    description = Column(Text)
    icon = Column(String(200))
    xp_reward = Column(Integer)
    coin_reward = Column(Integer)
    earned_at = Column(DateTime, default=datetime.utcnow)
    
    gamification = relationship('Gamification', back_populates='badges_earned')

# Chat Session (AI Tutor)
class ChatSession(db.Model):
    __tablename__ = 'chat_sessions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    session_id = Column(String(50), unique=True, default=lambda: str(uuid.uuid4()))
    subject_id = Column(Integer, ForeignKey('subjects.id'))
    topic_id = Column(Integer, ForeignKey('topics.id'))
    title = Column(String(200))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship('User', back_populates='chat_sessions')
    messages = relationship('ChatMessage', back_populates='session')

# Chat Message
class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('chat_sessions.id'))
    role = Column(String(20))  # user, assistant, system
    content = Column(Text)
    mode = Column(String(50))  # explain, solve, similar, summary
    citations = Column(JSON)  # List of content IDs
    feedback_rating = Column(Integer)  # 1-5 stars
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    session = relationship('ChatSession', back_populates='messages')

# Class (for Teachers)
class Class(db.Model):
    __tablename__ = 'classes'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    section = Column(String(20))
    grade = Column(Integer)
    board = Column(Enum(Board))
    subject_id = Column(Integer, ForeignKey('subjects.id'))
    academic_year = Column(String(20))
    is_active = Column(Boolean, default=True)
    join_code = Column(String(10), unique=True)
    
    teachers = relationship('User', secondary=teacher_class, back_populates='taught_classes')
    students = relationship('User', secondary=student_class, back_populates='enrolled_classes')
    assignments = relationship('Assignment', back_populates='class_assigned')

# Assignment
class Assignment(db.Model):
    __tablename__ = 'assignments'
    
    id = Column(Integer, primary_key=True)
    class_id = Column(Integer, ForeignKey('classes.id'))
    teacher_id = Column(Integer, ForeignKey('users.id'))
    title = Column(String(200))
    description = Column(Text)
    assignment_type = Column(String(50))  # homework, worksheet, test
    questions = Column(JSON)  # List of question IDs
    total_marks = Column(Float)
    due_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    class_assigned = relationship('Class', back_populates='assignments')
    teacher = relationship('User', back_populates='created_assignments')
    submissions = relationship('AssignmentSubmission', back_populates='assignment')

# Assignment Submission
class AssignmentSubmission(db.Model):
    __tablename__ = 'assignment_submissions'
    
    id = Column(Integer, primary_key=True)
    assignment_id = Column(Integer, ForeignKey('assignments.id'))
    student_id = Column(Integer, ForeignKey('users.id'))
    answers = Column(JSON)
    score = Column(Float)
    feedback = Column(Text)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    graded_at = Column(DateTime)
    status = Column(String(20))  # submitted, graded, returned
    
    assignment = relationship('Assignment', back_populates='submissions')
    student = relationship('User', back_populates='assignment_submissions')

# Notification
class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    type = Column(String(50))  # reminder, achievement, update, alert
    title = Column(String(200))
    message = Column(Text)
    data = Column(JSON)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    scheduled_for = Column(DateTime)
    
    user = relationship('User', back_populates='notifications')

# Subscription
class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    plan_type = Column(String(50))  # monthly, annual, college
    status = Column(String(20))  # active, cancelled, expired
    amount = Column(Float)
    currency = Column(String(3), default='INR')
    payment_method = Column(String(50))
    payment_id = Column(String(100))
    started_at = Column(DateTime)
    expires_at = Column(DateTime)
    auto_renew = Column(Boolean, default=True)
    
    user = relationship('User', back_populates='subscriptions')
    transactions = relationship('Transaction', back_populates='subscription')

# Transaction
class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id'))
    transaction_id = Column(String(100), unique=True)
    amount = Column(Float)
    currency = Column(String(3), default='INR')
    status = Column(String(20))  # success, failed, pending
    payment_method = Column(String(50))
    gateway = Column(String(50))  # razorpay, stripe
    gateway_response = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    subscription = relationship('Subscription', back_populates='transactions')

# Analytics Event
class AnalyticsEvent(db.Model):
    __tablename__ = 'analytics_events'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    event_type = Column(String(100))
    event_data = Column(JSON)
    session_id = Column(String(50))
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    timestamp = Column(DateTime, default=datetime.utcnow)

# System Settings
class SystemSettings(db.Model):
    __tablename__ = 'system_settings'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True)
    value = Column(JSON)
    description = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)