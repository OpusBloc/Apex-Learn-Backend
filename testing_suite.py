# backend/tests/test_auth.py
"""
Authentication and authorization tests
"""

import pytest
import json
from datetime import datetime, timedelta
from app import create_app
from app.models import db, User, UserRole

@pytest.fixture
def app():
    """Create application for testing"""
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()

@pytest.fixture
def auth_headers(client):
    """Get authentication headers"""
    # Create test user
    user = User(
        email='test@example.com',
        name='Test User',
        role=UserRole.STUDENT,
        grade=10,
        board='CBSE'
    )
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()
    
    # Login
    response = client.post('/api/auth/login', json={
        'username': 'test@example.com',
        'password': 'password123'
    })
    
    token = json.loads(response.data)['access_token']
    
    return {'Authorization': f'Bearer {token}'}

class TestAuthentication:
    """Test authentication endpoints"""
    
    def test_user_registration(self, client):
        """Test user registration"""
        response = client.post('/api/auth/register', json={
            'email': 'new@example.com',
            'password': 'SecurePass123!',
            'name': 'New User',
            'role': 'student',
            'grade': 9,
            'board': 'CBSE'
        })
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'access_token' in data
        assert data['user']['email'] == 'new@example.com'
    
    def test_duplicate_email_registration(self, client):
        """Test registration with duplicate email"""
        # First registration
        client.post('/api/auth/register', json={
            'email': 'duplicate@example.com',
            'password': 'password123',
            'name': 'User 1',
            'role': 'student'
        })
        
        # Duplicate registration
        response = client.post('/api/auth/register', json={
            'email': 'duplicate@example.com',
            'password': 'password456',
            'name': 'User 2',
            'role': 'student'
        })
        
        assert response.status_code == 409
        assert b'already registered' in response.data
    
    def test_user_login(self, client):
        """Test user login"""
        # Create user
        user = User(
            email='login@example.com',
            name='Login User',
            role=UserRole.STUDENT
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        
        # Login
        response = client.post('/api/auth/login', json={
            'username': 'login@example.com',
            'password': 'password123'
        })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'access_token' in data
    
    def test_invalid_login(self, client):
        """Test login with invalid credentials"""
        response = client.post('/api/auth/login', json={
            'username': 'invalid@example.com',
            'password': 'wrongpassword'
        })
        
        assert response.status_code == 401
        assert b'Invalid credentials' in response.data
    
    def test_protected_endpoint(self, client, auth_headers):
        """Test accessing protected endpoint"""
        response = client.get('/api/student/dashboard', headers=auth_headers)
        assert response.status_code == 200
    
    def test_protected_endpoint_without_token(self, client):
        """Test accessing protected endpoint without token"""
        response = client.get('/api/student/dashboard')
        assert response.status_code == 401


# backend/tests/test_quiz.py
"""
Quiz and assessment tests
"""

import pytest
import json
from app.models import db, User, Quiz, Question, QuizResult

class TestQuizFunctionality:
    """Test quiz-related features"""
    
    @pytest.fixture
    def setup_quiz_data(self, app):
        """Setup quiz test data"""
        with app.app_context():
            # Create test questions
            questions = []
            for i in range(5):
                q = Question(
                    topic_id=1,
                    question_type='mcq',
                    difficulty='medium',
                    question_text=f'Test Question {i+1}',
                    options=['A', 'B', 'C', 'D'],
                    correct_answer='A',
                    marks=2.0
                )
                db.session.add(q)
                questions.append(q)
            
            db.session.commit()
            return questions
    
    def test_create_mock_test(self, client, auth_headers, setup_quiz_data):
        """Test creating a mock test"""
        response = client.post('/api/quiz/mock-test/create', 
            headers=auth_headers,
            json={
                'title': 'Mathematics Mock Test',
                'chapter_ids': [1, 2],
                'question_count': 10,
                'duration': 60
            }
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'quiz_id' in data
        assert 'questions' in data
    
    def test_submit_quiz(self, client, auth_headers):
        """Test quiz submission"""
        # Create a quiz first
        quiz = Quiz(
            quiz_type='practice',
            title='Test Quiz',
            total_marks=10,
            duration_minutes=30
        )
        db.session.add(quiz)
        db.session.commit()
        
        # Submit quiz
        response = client.post('/api/quiz/submit',
            headers=auth_headers,
            json={
                'quiz_id': quiz.id,
                'answers': [
                    {'question_id': 1, 'answer': 'A'},
                    {'question_id': 2, 'answer': 'B'}
                ],
                'time_taken': 1200,
                'started_at': '2024-01-01 10:00:00'
            }
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'result' in data
        assert 'gamification' in data
    
    def test_adaptive_practice(self, client, auth_headers):
        """Test adaptive practice generation"""
        response = client.post('/api/student/practice/adaptive',
            headers=auth_headers,
            json={
                'topic_id': 1,
                'difficulty': 'medium',
                'count': 5
            }
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'quiz_id' in data
        assert 'questions' in data
        assert len(data['questions']) <= 5


# backend/tests/test_ai_service.py
"""
AI service tests
"""

import pytest
from unittest.mock import Mock, patch
from app.services.ai_service import AIService

class TestAIService:
    """Test AI service functionality"""
    
    @pytest.fixture
    def ai_service(self):
        """Create AI service instance"""
        config = {
            'OPENAI_API_KEY': 'test_key',
            'REDIS_HOST': 'localhost',
            'REDIS_PORT': 6379
        }
        return AIService(config)
    
    @patch('openai.ChatCompletion.create')
    def test_chat_with_tutor(self, mock_openai, ai_service):
        """Test AI tutor chat"""
        mock_openai.return_value = Mock(
            choices=[Mock(message=Mock(content='Test response'))]
        )
        
        response = ai_service.chat_with_tutor(
            user_id=1,
            message='Explain photosynthesis',
            mode='explain'
        )
        
        assert 'response' in response
        assert response['response'] == 'Test response'
        assert response['mode'] == 'explain'
    
    def test_adjust_difficulty(self, ai_service):
        """Test difficulty adjustment logic"""
        # High accuracy should increase difficulty
        performance = {'recent_accuracy': 0.85}
        new_difficulty = ai_service._adjust_difficulty(performance, 'medium')
        assert new_difficulty == 'hard'
        
        # Low accuracy should decrease difficulty
        performance = {'recent_accuracy': 0.35}
        new_difficulty = ai_service._adjust_difficulty(performance, 'medium')
        assert new_difficulty == 'easy'
    
    @patch('openai.ChatCompletion.create')
    def test_generate_adaptive_questions(self, mock_openai, ai_service):
        """Test adaptive question generation"""
        mock_openai.return_value = Mock(
            choices=[Mock(message=Mock(content=json.dumps([
                {
                    'question_text': 'Test question',
                    'question_type': 'mcq',
                    'correct_answer': 'A',
                    'options': ['A', 'B', 'C', 'D']
                }
            ])))]
        )
        
        questions = ai_service.generate_adaptive_questions(
            student_id=1,
            topic_id=1,
            difficulty='medium',
            count=1
        )
        
        assert len(questions) == 1
        assert questions[0]['question_text'] == 'Test question'


# backend/tests/test_payment.py
"""
Payment service tests
"""

import pytest
from unittest.mock import Mock, patch
from app.services.payment_service import PaymentService

class TestPaymentService:
    """Test payment functionality"""
    
    @pytest.fixture
    def payment_service(self):
        """Create payment service instance"""
        config = {
            'RAZORPAY_KEY_ID': 'test_key',
            'RAZORPAY_KEY_SECRET': 'test_secret',
            'STRIPE_SECRET_KEY': 'sk_test_key'
        }
        return PaymentService(config)
    
    @patch('razorpay.Client')
    def test_create_razorpay_order(self, mock_razorpay, payment_service):
        """Test Razorpay order creation"""
        mock_client = Mock()
        mock_client.order.create.return_value = {
            'id': 'order_123',
            'amount': 49900,
            'currency': 'INR'
        }
        mock_razorpay.return_value = mock_client
        
        order = payment_service.create_order(
            amount=499,
            currency='INR',
            user_id=1,
            plan_id='monthly'
        )
        
        assert order['provider'] == 'razorpay'
        assert order['order_id'] == 'order_123'
        assert order['amount'] == 499
    
    def test_verify_payment_signature(self, payment_service):
        """Test payment signature verification"""
        # Test with valid signature
        import hmac
        import hashlib
        
        order_id = 'order_123'
        payment_id = 'pay_456'
        secret = payment_service.razorpay_webhook_secret
        
        body = order_id + "|" + payment_id
        expected_signature = hmac.new(
            secret.encode(),
            body.encode(),
            hashlib.sha256
        ).hexdigest()
        
        is_valid = payment_service.verify_payment(
            order_id, 
            payment_id, 
            expected_signature
        )
        
        assert is_valid == True


# backend/tests/load/locustfile.py
"""
Load testing configuration
"""

from locust import HttpUser, task, between

class ApexLearnUser(HttpUser):
    """Simulated user for load testing"""
    
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login before testing"""
        response = self.client.post('/api/auth/login', json={
            'username': 'loadtest@example.com',
            'password': 'password123'
        })
        
        if response.status_code == 200:
            self.token = response.json()['access_token']
            self.headers = {'Authorization': f'Bearer {self.token}'}
        else:
            self.headers = {}
    
    @task(3)
    def view_dashboard(self):
        """View student dashboard"""
        self.client.get('/api/student/dashboard', headers=self.headers)
    
    @task(2)
    def take_quiz(self):
        """Take a practice quiz"""
        self.client.post('/api/student/practice/adaptive',
            headers=self.headers,
            json={
                'topic_id': 1,
                'difficulty': 'medium',
                'count': 5
            }
        )
    
    @task(1)
    def chat_with_tutor(self):
        """Chat with AI tutor"""
        self.client.post('/api/chat/tutor',
            headers=self.headers,
            json={
                'message': 'Explain a random concept',
                'mode': 'explain'
            }
        )
    
    @task(1)
    def view_progress(self):
        """View progress analytics"""
        self.client.get('/api/analytics/progress/heatmap',
            headers=self.headers
        )


# frontend/src/tests/components/Dashboard.test.tsx
"""
React component tests
"""

import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { BrowserRouter } from 'react-router-dom';
import StudentDashboard from '../../components/Dashboard/StudentDashboard';
import { AuthProvider } from '../../contexts/AuthContext';
import { apiClient } from '../../services/api';

// Mock API client
jest.mock('../../services/api');

describe('StudentDashboard', () => {
  beforeEach(() => {
    // Mock API responses
    apiClient.get.mockResolvedValue({
      data: {
        user: { name: 'Test Student', grade: 10, board: 'CBSE' },
        progress: { overall_completion: 75, subjects: [] },
        study_plan: { active: true, today_tasks: [], daily_goal: 60 },
        gamification: { level: 5, xp: 500, streak: 7, badges: [] },
        recent_quizzes: []
      }
    });
  });

  test('renders dashboard with user data', async () => {
    render(
      <BrowserRouter>
        <AuthProvider>
          <StudentDashboard />
        </AuthProvider>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Welcome back, Test Student!/)).toBeInTheDocument();
      expect(screen.getByText(/Grade 10/)).toBeInTheDocument();
      expect(screen.getByText(/7 day streak/)).toBeInTheDocument();
    });
  });

  test('displays loading state', () => {
    render(
      <BrowserRouter>
        <AuthProvider>
          <StudentDashboard />
        </AuthProvider>
      </BrowserRouter>
    );

    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });

  test('handles API errors gracefully', async () => {
    apiClient.get.mockRejectedValue(new Error('API Error'));

    render(
      <BrowserRouter>
        <AuthProvider>
          <StudentDashboard />
        </AuthProvider>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Failed to load dashboard/)).toBeInTheDocument();
    });
  });
});


# frontend/src/tests/services/auth.test.ts
"""
Service layer tests
"""

import { authService } from '../../services/auth.service';
import { apiClient } from '../../services/api';

jest.mock('../../services/api');

describe('AuthService', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  test('login stores tokens and user data', async () => {
    const mockResponse = {
      access_token: 'test_token',
      user: { id: 1, email: 'test@example.com', role: 'student' }
    };

    apiClient.post.mockResolvedValue(mockResponse);

    const user = await authService.login({
      username: 'test@example.com',
      password: 'password123'
    });

    expect(localStorage.getItem('access_token')).toBe('test_token');
    expect(user.email).toBe('test@example.com');
  });

  test('logout clears storage and redirects', async () => {
    localStorage.setItem('access_token', 'test_token');
    
    // Mock window.location.href
    delete window.location;
    window.location = { href: '' };

    await authService.logout();

    expect(localStorage.getItem('access_token')).toBeNull();
    expect(window.location.href).toBe('/login');
  });

  test('isAuthenticated returns correct status', () => {
    expect(authService.isAuthenticated()).toBe(false);
    
    localStorage.setItem('access_token', 'test_token');
    
    expect(authService.isAuthenticated()).toBe(true);
  });
});