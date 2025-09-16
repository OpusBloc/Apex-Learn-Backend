# backend/app/services/notification_service.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from twilio.rest import Client
import redis
import random
import string
from datetime import datetime, timedelta
from jinja2 import Template

class NotificationService:
    def __init__(self, config):
        self.smtp_server = config.get('SMTP_SERVER')
        self.smtp_port = config.get('SMTP_PORT')
        self.smtp_username = config.get('SMTP_USERNAME')
        self.smtp_password = config.get('SMTP_PASSWORD')
        
        self.twilio_client = Client(
            config.get('TWILIO_ACCOUNT_SID'),
            config.get('TWILIO_AUTH_TOKEN')
        )
        self.twilio_phone = config.get('TWILIO_PHONE_NUMBER')
        
        self.redis_client = redis.Redis(
            host=config.get('REDIS_HOST'),
            port=config.get('REDIS_PORT'),
            decode_responses=True
        )
        
        self.whatsapp_api_url = config.get('WHATSAPP_API_URL')
        
    def send_email(self, to_email: str, subject: str, body: str, is_html: bool = False):
        """Send email notification"""
        msg = MIMEMultipart('alternative' if is_html else 'mixed')
        msg['Subject'] = subject
        msg['From'] = self.smtp_username
        msg['To'] = to_email
        
        if is_html:
            msg.attach(MIMEText(body, 'html'))
        else:
            msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)
    
    def send_sms(self, phone: str, message: str):
        """Send SMS notification"""
        self.twilio_client.messages.create(
            body=message,
            from_=self.twilio_phone,
            to=phone
        )
    
    def send_otp(self, phone_or_email: str, otp: str = None):
        """Send OTP for verification"""
        if not otp:
            otp = ''.join(random.choices(string.digits, k=6))
        
        # Store OTP in Redis with 10-minute expiry
        self.redis_client.setex(
            f"otp:{phone_or_email}",
            600,  # 10 minutes
            otp
        )
        
        if '@' in phone_or_email:
            # Send via email
            self.send_email(
                phone_or_email,
                "Your ApexLearn OTP",
                f"Your OTP is: {otp}\nValid for 10 minutes."
            )
        else:
            # Send via SMS
            self.send_sms(
                phone_or_email,
                f"Your ApexLearn OTP is: {otp}"
            )
        
        return otp
    
    def verify_otp(self, phone_or_email: str, otp: str) -> bool:
        """Verify OTP"""
        stored_otp = self.redis_client.get(f"otp:{phone_or_email}")
        
        if stored_otp and stored_otp == otp:
            self.redis_client.delete(f"otp:{phone_or_email}")
            return True
        
        return False
    
    def send_whatsapp(self, phone: str, message: str):
        """Send WhatsApp notification"""
        # Implementation depends on WhatsApp Business API provider
        pass
    
    def send_notification(self, user_id: int, notification_type: str, message: str):
        """Send in-app notification"""
        from ..models import db, Notification
        
        notification = Notification(
            user_id=user_id,
            type=notification_type,
            title=self._get_notification_title(notification_type),
            message=message,
            data={}
        )
        
        db.session.add(notification)
        db.session.commit()
        
        return notification
    
    def send_verification_email(self, email: str, name: str):
        """Send verification email"""
        otp = self.send_otp(email)
        
        template = """
        <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>Welcome to ApexLearn, {{ name }}!</h2>
                <p>Please verify your email address by entering this OTP:</p>
                <h1 style="color: #6366f1; font-size: 36px;">{{ otp }}</h1>
                <p>This code will expire in 10 minutes.</p>
                <p>If you didn't create an account, please ignore this email.</p>
            </body>
        </html>
        """
        
        body = Template(template).render(name=name, otp=otp)
        self.send_email(email, "Verify your ApexLearn account", body, is_html=True)
    
    def send_weekly_report(self, parent_email: str, child_name: str, report_data: dict):
        """Send weekly progress report to parent"""
        template = """
        <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>Weekly Progress Report for {{ child_name }}</h2>
                <div style="background: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3>Key Metrics</h3>
                    <ul>
                        <li>Overall Progress: {{ progress }}%</li>
                        <li>Study Streak: {{ streak }} days</li>
                        <li>Quizzes Completed: {{ quizzes }}</li>
                        <li>Average Score: {{ avg_score }}%</li>
                    </ul>
                </div>
                <div style="margin: 20px 0;">
                    <h3>Focus Areas</h3>
                    <p>{{ recommendations }}</p>
                </div>
                <a href="{{ dashboard_link }}" style="background: #6366f1; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                    View Full Dashboard
                </a>
            </body>
        </html>
        """
        
        body = Template(template).render(
            child_name=child_name,
            **report_data
        )
        
        self.send_email(parent_email, f"Weekly Report - {child_name}", body, is_html=True)
    
    def schedule_reminders(self, user_id: int, preferences: dict):
        """Schedule study reminders based on preferences"""
        from ..models import db, Notification
        
        # Daily study reminder
        if preferences.get('daily_reminder'):
            reminder_time = preferences.get('reminder_time', '18:00')
            
            notification = Notification(
                user_id=user_id,
                type='reminder',
                title='Study Time!',
                message="It's time for your daily study session",
                scheduled_for=self._get_next_reminder_time(reminder_time)
            )
            
            db.session.add(notification)
        
        # Weekend reminder
        if preferences.get('weekend_reminder'):
            notification = Notification(
                user_id=user_id,
                type='reminder',
                title='Weekend Practice',
                message="Don't forget to complete your weekend practice!",
                scheduled_for=self._get_next_weekend()
            )
            
            db.session.add(notification)
        
        db.session.commit()
    
    def _get_notification_title(self, notification_type: str) -> str:
        """Get notification title based on type"""
        titles = {
            'achievement': '🏆 Achievement Unlocked!',
            'reminder': '⏰ Study Reminder',
            'new_assignment': '📝 New Assignment',
            'quiz_result': '📊 Quiz Results',
            'parent_linked': '👨‍👩‍👧 Parent Account Linked',
            'streak_milestone': '🔥 Streak Milestone!',
            'weekly_report': '📈 Weekly Report'
        }
        
        return titles.get(notification_type, '📢 Notification')
    
    def _get_next_reminder_time(self, time_str: str) -> datetime:
        """Calculate next reminder time"""
        hour, minute = map(int, time_str.split(':'))
        now = datetime.now()
        reminder = now.replace(hour=hour, minute=minute, second=0)
        
        if reminder <= now:
            reminder += timedelta(days=1)
        
        return reminder
    
    def _get_next_weekend(self) -> datetime:
        """Get next weekend date"""
        today = datetime.now()
        days_until_saturday = (5 - today.weekday()) % 7
        
        if days_until_saturday == 0 and today.hour >= 10:
            days_until_saturday = 7
        
        return today + timedelta(days=days_until_saturday)


# backend/app/services/payment_service.py
import razorpay
import stripe
import hashlib
import hmac
from typing import Dict, Optional

class PaymentService:
    def __init__(self, config):
        # Razorpay setup (for India)
        self.razorpay_client = razorpay.Client(
            auth=(config.get('RAZORPAY_KEY_ID'), config.get('RAZORPAY_KEY_SECRET'))
        )
        self.razorpay_webhook_secret = config.get('RAZORPAY_WEBHOOK_SECRET')
        
        # Stripe setup (international)
        stripe.api_key = config.get('STRIPE_SECRET_KEY')
        self.stripe_webhook_secret = config.get('STRIPE_WEBHOOK_SECRET')
        
    async def create_order(self, amount: float, currency: str, user_id: int, plan_id: str) -> Dict:
        """Create payment order"""
        
        if currency == 'INR':
            # Use Razorpay for Indian payments
            order = self.razorpay_client.order.create({
                'amount': int(amount * 100),  # Convert to paise
                'currency': currency,
                'payment_capture': 1,
                'notes': {
                    'user_id': user_id,
                    'plan_id': plan_id
                }
            })
            
            return {
                'provider': 'razorpay',
                'order_id': order['id'],
                'amount': amount,
                'currency': currency,
                'key_id': self.razorpay_client.auth[0]
            }
        else:
            # Use Stripe for international payments
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Convert to cents
                currency=currency.lower(),
                metadata={
                    'user_id': user_id,
                    'plan_id': plan_id
                }
            )
            
            return {
                'provider': 'stripe',
                'client_secret': intent.client_secret,
                'amount': amount,
                'currency': currency
            }
    
    async def verify_payment(self, order_id: str, payment_id: str, signature: str) -> bool:
        """Verify Razorpay payment signature"""
        
        body = order_id + "|" + payment_id
        expected_signature = hmac.new(
            self.razorpay_webhook_secret.encode(),
            body.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)
    
    def process_webhook(self, provider: str, payload: Dict, signature: str) -> Dict:
        """Process payment webhook"""
        
        if provider == 'razorpay':
            # Verify Razorpay webhook signature
            webhook_signature = hmac.new(
                self.razorpay_webhook_secret.encode(),
                payload.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(webhook_signature, signature):
                raise ValueError("Invalid webhook signature")
            
            # Process event
            event = payload.get('event')
            if event == 'payment.captured':
                return self._handle_payment_success(payload['payload']['payment']['entity'])
            elif event == 'payment.failed':
                return self._handle_payment_failure(payload['payload']['payment']['entity'])
                
        elif provider == 'stripe':
            # Verify Stripe webhook signature
            try:
                event = stripe.Webhook.construct_event(
                    payload, signature, self.stripe_webhook_secret
                )
            except ValueError:
                raise ValueError("Invalid webhook payload")
            except stripe.error.SignatureVerificationError:
                raise ValueError("Invalid webhook signature")
            
            # Process event
            if event['type'] == 'payment_intent.succeeded':
                return self._handle_payment_success(event['data']['object'])
            elif event['type'] == 'payment_intent.payment_failed':
                return self._handle_payment_failure(event['data']['object'])
        
        return {'status': 'ignored'}
    
    def _handle_payment_success(self, payment_data: Dict) -> Dict:
        """Handle successful payment"""
        from ..models import db, Transaction, Subscription
        
        # Create transaction record
        transaction = Transaction(
            transaction_id=payment_data.get('id'),
            amount=payment_data.get('amount') / 100,  # Convert from paise/cents
            currency=payment_data.get('currency'),
            status='success',
            payment_method=payment_data.get('method', 'card'),
            gateway='razorpay' if 'razorpay' in str(payment_data.get('id', '')) else 'stripe',
            gateway_response=payment_data
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        return {'status': 'success', 'transaction_id': transaction.id}
    
    def _handle_payment_failure(self, payment_data: Dict) -> Dict:
        """Handle failed payment"""
        from ..models import db, Transaction
        
        # Create transaction record
        transaction = Transaction(
            transaction_id=payment_data.get('id'),
            amount=payment_data.get('amount') / 100,
            currency=payment_data.get('currency'),
            status='failed',
            payment_method=payment_data.get('method', 'card'),
            gateway='razorpay' if 'razorpay' in str(payment_data.get('id', '')) else 'stripe',
            gateway_response=payment_data
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        return {'status': 'failed', 'transaction_id': transaction.id}
    
    def create_coupon(self, code: str, discount_percent: int, valid_until: Optional[str] = None) -> Dict:
        """Create discount coupon"""
        # Implementation for coupon creation
        pass
    
    def apply_coupon(self, code: str, amount: float) -> float:
        """Apply coupon and return discounted amount"""
        # Implementation for coupon application
        pass


# backend/app/services/analytics_service.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import json

class AnalyticsService:
    def __init__(self):
        self.event_buffer = []
        self.buffer_size = 100
        
    def log_event(self, user_id: int, event_type: str, data: Dict = None):
        """Log analytics event"""
        from ..models import db, AnalyticsEvent
        
        event = AnalyticsEvent(
            user_id=user_id,
            event_type=event_type,
            event_data=data or {},
            session_id=self._get_session_id(),
            ip_address=self._get_ip_address(),
            user_agent=self._get_user_agent()
        )
        
        self.event_buffer.append(event)
        
        # Batch insert when buffer is full
        if len(self.event_buffer) >= self.buffer_size:
            db.session.bulk_save_objects(self.event_buffer)
            db.session.commit()
            self.event_buffer.clear()
    
    async def generate_student_report(self, student_id: int) -> Dict:
        """Generate comprehensive student report"""
        from ..models import StudentProgress, QuizResult, StudyTask, Gamification
        
        # Get student data
        progress = StudentProgress.query.filter_by(student_id=student_id).all()
        quizzes = QuizResult.query.filter_by(student_id=student_id)\
            .order_by(QuizResult.completed_at.desc()).limit(20).all()
        tasks = StudyTask.query.join(StudyPlan).filter(
            StudyPlan.student_id == student_id,
            StudyTask.scheduled_date >= datetime.utcnow() - timedelta(days=30)
        ).all()
        gamification = Gamification.query.filter_by(user_id=student_id).first()
        
        # Calculate metrics
        overall_progress = sum(p.syllabus_completion for p in progress) / len(progress) if progress else 0
        avg_quiz_score = sum(q.percentage for q in quizzes) / len(quizzes) if quizzes else 0
        task_completion_rate = len([t for t in tasks if t.status == 'completed']) / len(tasks) if tasks else 0
        
        # Trend analysis
        weekly_progress = self._calculate_weekly_progress(student_id)
        performance_trend = self._analyze_performance_trend(quizzes)
        
        # Subject-wise analysis
        subject_analysis = []
        for prog in progress:
            subject_data = {
                'subject_id': prog.subject_id,
                'completion': prog.syllabus_completion,
                'mastery': prog.mastery_level.value,
                'study_time': prog.total_study_time,
                'average_score': prog.average_score,
                'weak_topics': self._get_weak_topics(student_id, prog.subject_id)
            }
            subject_analysis.append(subject_data)
        
        return {
            'student_id': student_id,
            'report_date': datetime.utcnow().isoformat(),
            'overall_metrics': {
                'progress': overall_progress,
                'average_score': avg_quiz_score,
                'task_completion': task_completion_rate * 100,
                'study_streak': gamification.streak_days if gamification else 0,
                'total_xp': gamification.xp if gamification else 0
            },
            'trends': {
                'weekly_progress': weekly_progress,
                'performance_trend': performance_trend
            },
            'subject_analysis': subject_analysis,
            'recommendations': await self._generate_recommendations(student_id, subject_analysis)
        }
    
    async def generate_class_report(self, class_id: int) -> Dict:
        """Generate class-wide analytics report"""
        from ..models import Class, StudentProgress, Assignment, AssignmentSubmission
        
        class_obj = Class.query.get(class_id)
        students = class_obj.students
        
        # Class metrics
        class_metrics = {
            'total_students': len(students),
            'average_progress': 0,
            'at_risk_count': 0,
            'top_performers': [],
            'weak_areas': []
        }
        
        # Calculate averages
        total_progress = 0
        for student in students:
            progress = StudentProgress.query.filter_by(
                student_id=student.id,
                subject_id=class_obj.subject_id
            ).first()
            
            if progress:
                total_progress += progress.syllabus_completion
                if progress.syllabus_completion < 40:
                    class_metrics['at_risk_count'] += 1
                if progress.syllabus_completion > 80:
                    class_metrics['top_performers'].append({
                        'student_id': student.id,
                        'name': student.name,
                        'progress': progress.syllabus_completion
                    })
        
        class_metrics['average_progress'] = total_progress / len(students) if students else 0
        
        # Assignment analysis
        assignments = Assignment.query.filter_by(class_id=class_id).all()
        assignment_metrics = []
        
        for assignment in assignments:
            submissions = AssignmentSubmission.query.filter_by(assignment_id=assignment.id).all()
            
            assignment_metrics.append({
                'title': assignment.title,
                'submission_rate': len(submissions) / len(students) * 100 if students else 0,
                'average_score': sum(s.score for s in submissions) / len(submissions) if submissions else 0,
                'due_date': assignment.due_date.isoformat()
            })
        
        return {
            'class_id': class_id,
            'class_name': f"{class_obj.name} - {class_obj.section}",
            'metrics': class_metrics,
            'assignments': assignment_metrics,
            'heatmap_data': await self.generate_class_heatmap(class_id)
        }
    
    async def generate_class_heatmap(self, class_id: int) -> Dict:
        """Generate topic mastery heatmap for class"""
        from ..models import Class, TopicProgress, Topic
        
        class_obj = Class.query.get(class_id)
        students = class_obj.students
        topics = Topic.query.filter_by(subject_id=class_obj.subject_id).all()
        
        # Create matrix
        heatmap_data = []
        
        for topic in topics:
            topic_row = {
                'topic_name': topic.name,
                'student_scores': []
            }
            
            for student in students:
                progress = TopicProgress.query.filter_by(
                    student_id=student.id,
                    topic_id=topic.id
                ).first()
                
                score = progress.mastery_score if progress else 0
                topic_row['student_scores'].append({
                    'student_id': student.id,
                    'score': score
                })
            
            heatmap_data.append(topic_row)
        
        return {
            'topics': [t['topic_name'] for t in heatmap_data],
            'students': [s.name for s in students],
            'data': heatmap_data
        }
    
    async def create_pdf_report(self, report_data: Dict) -> BytesIO:
        """Create PDF report from data"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title = Paragraph(f"Progress Report - {report_data.get('report_date', '')}", styles['Title'])
        story.append(title)
        
        # Overall Metrics Table
        metrics_data = [
            ['Metric', 'Value'],
            ['Overall Progress', f"{report_data['overall_metrics']['progress']:.1f}%"],
            ['Average Score', f"{report_data['overall_metrics']['average_score']:.1f}%"],
            ['Study Streak', f"{report_data['overall_metrics']['study_streak']} days"],
            ['Total XP', str(report_data['overall_metrics']['total_xp'])]
        ]
        
        metrics_table = Table(metrics_data)
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(metrics_table)
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        return buffer
    
    def _calculate_weekly_progress(self, student_id: int) -> List[Dict]:
        """Calculate weekly progress trends"""
        from ..models import AnalyticsEvent
        
        # Get events for last 4 weeks
        start_date = datetime.utcnow() - timedelta(weeks=4)
        events = AnalyticsEvent.query.filter(
            AnalyticsEvent.user_id == student_id,
            AnalyticsEvent.timestamp >= start_date,
            AnalyticsEvent.event_type.in_(['lesson_completed', 'quiz_completed', 'task_completed'])
        ).all()
        
        # Group by week
        weekly_data = []
        for week in range(4):
            week_start = datetime.utcnow() - timedelta(weeks=week+1)
            week_end = datetime.utcnow() - timedelta(weeks=week)
            
            week_events = [e for e in events if week_start <= e.timestamp < week_end]
            
            weekly_data.append({
                'week': f"Week {4-week}",
                'activities': len(week_events),
                'study_time': sum(e.event_data.get('duration', 0) for e in week_events)
            })
        
        return weekly_data
    
    def _analyze_performance_trend(self, quizzes: List) -> str:
        """Analyze quiz performance trend"""
        if len(quizzes) < 3:
            return 'insufficient_data'
        
        # Get recent scores
        recent_scores = [q.percentage for q in quizzes[:10]]
        
        # Calculate trend
        if len(recent_scores) >= 2:
            trend = np.polyfit(range(len(recent_scores)), recent_scores, 1)[0]
            
            if trend > 2:
                return 'improving'
            elif trend < -2:
                return 'declining'
            else:
                return 'stable'
        
        return 'stable'
    
    def _get_weak_topics(self, student_id: int, subject_id: int) -> List[str]:
        """Get weak topics for a subject"""
        from ..models import TopicProgress, Topic
        
        weak_progress = TopicProgress.query.filter(
            TopicProgress.student_id == student_id,
            TopicProgress.mastery_score < 0.5
        ).join(Topic).filter(Topic.subject_id == subject_id).all()
        
        return [Topic.query.get(wp.topic_id).name for wp in weak_progress]
    
    async def _generate_recommendations(self, student_id: int, subject_analysis: List[Dict]) -> List[str]:
        """Generate personalized recommendations"""
        recommendations = []
        
        # Check overall progress
        avg_completion = sum(s['completion'] for s in subject_analysis) / len(subject_analysis) if subject_analysis else 0
        
        if avg_completion < 30:
            recommendations.append("Focus on completing basic topics before moving to advanced concepts")
        elif avg_completion < 60:
            recommendations.append("Maintain regular study schedule to improve syllabus coverage")
        else:
            recommendations.append("Good progress! Focus on revision and practice tests")
        
        # Check for weak subjects
        weak_subjects = [s for s in subject_analysis if s['mastery'] == 'weak']
        if weak_subjects:
            recommendations.append(f"Dedicate extra time to weak subjects")
        
        # Study time recommendations
        total_study_time = sum(s['study_time'] for s in subject_analysis)
        if total_study_time < 1800:  # Less than 30 hours total
            recommendations.append("Increase daily study time by 30 minutes")
        
        return recommendations
    
    def _get_session_id(self) -> str:
        """Get or create session ID"""
        # Implementation to get session ID from request context
        import uuid
        return str(uuid.uuid4())
    
    def _get_ip_address(self) -> str:
        """Get client IP address"""
        # Implementation to get IP from request
        return "127.0.0.1"
    
    def _get_user_agent(self) -> str:
        """Get user agent string"""
        # Implementation to get user agent from request
        return "Mozilla/5.0"


# backend/app/__init__.py
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO
from redis import Redis
import os
from dotenv import load_dotenv

load_dotenv()

def create_app(config_name='development'):
    app = Flask(__name__)
    
    # Configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)
    app.config['UPLOAD_FOLDER'] = 'uploads'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    
    # Redis configuration
    app.config['REDIS_HOST'] = os.getenv('REDIS_HOST', 'localhost')
    app.config['REDIS_PORT'] = int(os.getenv('REDIS_PORT', 6379))
    
    # Payment configuration
    app.config['RAZORPAY_KEY_ID'] = os.getenv('RAZORPAY_KEY_ID')
    app.config['RAZORPAY_KEY_SECRET'] = os.getenv('RAZORPAY_KEY_SECRET')
    app.config['STRIPE_SECRET_KEY'] = os.getenv('STRIPE_SECRET_KEY')
    
    # Initialize extensions
    from .models import db
    db.init_app(app)
    
    CORS(app, origins=['http://localhost:5173', 'https://apexlearn.in'])
    JWTManager(app)
    Migrate(app, db)
    
    # Rate limiting
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["1000 per hour"]
    )
    
    # Socket.IO for real-time features
    socketio = SocketIO(app, cors_allowed_origins="*")
    
    # Redis client
    app.redis = Redis(
        host=app.config['REDIS_HOST'],
        port=app.config['REDIS_PORT'],
        decode_responses=True
    )
    
    # Register blueprints
    from .routes.api_routes import (
        auth_bp, student_bp, parent_bp, teacher_bp,
        quiz_bp, study_bp, chat_bp, analytics_bp, payment_bp
    )
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(parent_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(quiz_bp)
    app.register_blueprint(study_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(payment_bp)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Resource not found'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return {'error': 'Internal server error'}, 500
    
    # Create tables
    with app.app_context():
        db.create_all()
        
        # Seed initial data
        from .utils.seed_data import seed_initial_data
        seed_initial_data()
    
    return app, socketio


# backend/requirements.txt
Flask==2.3.3
Flask-SQLAlchemy==3.0.5
Flask-Migrate==4.0.4
Flask-JWT-Extended==4.5.2
Flask-CORS==4.0.0
Flask-Limiter==3.3.1
Flask-SocketIO==5.3.4
python-socketio==5.9.0
SQLAlchemy==2.0.20
psycopg2-binary==2.9.7
redis==4.6.0
celery==5.3.1
python-dotenv==1.0.0
openai==1.3.0
sentence-transformers==2.2.2
scikit-learn==1.3.0
numpy==1.24.3
pandas==2.0.3
matplotlib==3.7.2
seaborn==0.12.2
reportlab==4.0.4
razorpay==1.4.1
stripe==6.5.0
twilio==8.8.0
boto3==1.28.25
Pillow==10.0.0
pytest==7.4.0
pytest-cov==4.1.0
gunicorn==21.2.0
eventlet==0.33.3
jinja2==3.1.2


# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: apexlearn
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: apexlearn
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - apexlearn_network

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    networks:
      - apexlearn_network

  backend:
    build: ./backend
    ports:
      - "5000:5000"
    environment:
      DATABASE_URL: postgresql://apexlearn:${DB_PASSWORD}@postgres:5432/apexlearn
      REDIS_HOST: redis
      REDIS_PORT: 6379
      JWT_SECRET_KEY: ${JWT_SECRET_KEY}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    depends_on:
      - postgres
      - redis
    volumes:
      - ./backend:/app
    networks:
      - apexlearn_network
    command: gunicorn -k eventlet -w 1 --bind 0.0.0.0:5000 app:app

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      VITE_API_URL: http://backend:5000
    depends_on:
      - backend
    volumes:
      - ./frontend:/app
      - /app/node_modules
    networks:
      - apexlearn_network

  celery:
    build: ./backend
    command: celery -A app.celery worker --loglevel=info
    environment:
      DATABASE_URL: postgresql://apexlearn:${DB_PASSWORD}@postgres:5432/apexlearn
      REDIS_HOST: redis
      REDIS_PORT: 6379
    depends_on:
      - postgres
      - redis
    networks:
      - apexlearn_network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - backend
      - frontend
    networks:
      - apexlearn_network

networks:
  apexlearn_network:
    driver: bridge

volumes:
  postgres_data: