# backend/app/services/ai_service.py
import openai
import numpy as np
from typing import List, Dict, Any, Optional
import json
from datetime import datetime, timedelta
import redis
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import asyncio
import aiohttp

class AIService:
    def __init__(self, config):
        self.openai_client = openai.Client(api_key=config['OPENAI_API_KEY'])
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        self.redis_client = redis.Redis(
            host=config['REDIS_HOST'],
            port=config['REDIS_PORT'],
            decode_responses=True
        )
        self.rag_index = {}  # In production, use vector DB like Pinecone/Weaviate
        
    async def generate_adaptive_questions(self, 
                                         student_id: int, 
                                         topic_id: int, 
                                         difficulty: str,
                                         count: int = 5) -> List[Dict]:
        """Generate adaptive questions based on student performance"""
        
        # Get student's performance history
        performance = await self._get_student_performance(student_id, topic_id)
        
        # Adjust difficulty based on performance
        adjusted_difficulty = self._adjust_difficulty(performance, difficulty)
        
        prompt = f"""
        Generate {count} {adjusted_difficulty} level questions for topic ID {topic_id}.
        Consider student's weak areas: {performance.get('weak_areas', [])}
        
        Format each question as JSON with:
        - question_text
        - question_type (mcq/short_answer/numerical)
        - options (if MCQ)
        - correct_answer
        - solution_steps
        - hints
        - skill_tags
        """
        
        response = self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert educator for Indian curriculum."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        questions = json.loads(response.choices[0].message.content)
        
        # Add distractors for MCQs using AI
        for q in questions:
            if q['question_type'] == 'mcq':
                q['options'] = await self._generate_distractors(q)
                
        return questions
    
    async def _generate_distractors(self, question: Dict) -> List[str]:
        """Generate plausible wrong answers for MCQs"""
        prompt = f"""
        For this question: {question['question_text']}
        Correct answer: {question['correct_answer']}
        
        Generate 3 plausible but incorrect options that students might confuse with the correct answer.
        """
        
        response = self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8
        )
        
        distractors = json.loads(response.choices[0].message.content)
        options = [question['correct_answer']] + distractors
        np.random.shuffle(options)
        
        return options
    
    async def chat_with_tutor(self, 
                             user_id: int,
                             message: str,
                             mode: str,
                             subject_context: Optional[Dict] = None) -> Dict:
        """RAG-powered AI tutor chat"""
        
        # Retrieve relevant content
        relevant_content = await self.retrieve_content(message, subject_context)
        
        # Build context
        context = self._build_context(relevant_content)
        
        # Generate response based on mode
        system_prompt = self._get_system_prompt(mode)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context: {context}\n\nQuestion: {message}"}
        ]
        
        response = self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.6
        )
        
        # Extract citations
        answer = response.choices[0].message.content
        citations = self._extract_citations(answer, relevant_content)
        
        return {
            'response': answer,
            'citations': citations,
            'mode': mode,
            'confidence': self._calculate_confidence(answer, relevant_content)
        }
    
    async def retrieve_content(self, query: str, context: Optional[Dict] = None) -> List[Dict]:
        """RAG retrieval for curriculum content"""
        
        # Generate embedding for query
        query_embedding = self.embedder.encode(query)
        
        # Search in vector store (simplified - use proper vector DB in production)
        results = []
        
        # Get cached content embeddings
        cache_key = f"content_embeddings:{context.get('subject_id', 'all')}" if context else "content_embeddings:all"
        cached_embeddings = self.redis_client.get(cache_key)
        
        if cached_embeddings:
            embeddings_data = json.loads(cached_embeddings)
            
            # Calculate similarities
            similarities = []
            for item in embeddings_data:
                similarity = cosine_similarity(
                    [query_embedding],
                    [item['embedding']]
                )[0][0]
                
                similarities.append({
                    'content_id': item['id'],
                    'similarity': similarity,
                    'content': item['content']
                })
            
            # Sort by similarity and get top 5
            results = sorted(similarities, key=lambda x: x['similarity'], reverse=True)[:5]
        
        return results
    
    def _get_system_prompt(self, mode: str) -> str:
        """Get system prompt based on chat mode"""
        prompts = {
            'explain': """You are an expert tutor for Indian curriculum (CBSE/ICSE).
                         Explain concepts clearly with examples relevant to Indian students.
                         Use simple language and build up complexity gradually.""",
            
            'solve': """You are a math and science problem solver.
                       Show step-by-step solutions with clear reasoning.
                       Highlight important formulas and concepts used.""",
            
            'similar': """You are a practice problem generator.
                         Create similar problems with varying difficulty.
                         Provide hints without giving away the answer.""",
            
            'summary': """You are a study guide creator.
                         Provide concise summaries focusing on key points.
                         Include important formulas, definitions, and concepts."""
        }
        
        return prompts.get(mode, prompts['explain'])
    
    async def generate_study_plan(self, 
                                  student_id: int,
                                  goal: str,
                                  target_date: datetime,
                                  daily_minutes: int) -> Dict:
        """Generate personalized study plan using AI"""
        
        # Get student's current progress
        progress = await self._get_overall_progress(student_id)
        
        # Get syllabus topics
        syllabus = await self._get_syllabus(student_id)
        
        prompt = f"""
        Create a personalized study plan for:
        - Goal: {goal}
        - Target date: {target_date}
        - Daily study time: {daily_minutes} minutes
        - Current progress: {json.dumps(progress)}
        - Syllabus topics: {json.dumps(syllabus)}
        
        Prioritize weak areas and ensure complete syllabus coverage.
        Balance between learning new topics and revision.
        
        Return as JSON with daily/weekly tasks.
        """
        
        response = self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert study planner."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5
        )
        
        plan = json.loads(response.choices[0].message.content)
        
        # Add adaptive rescheduling logic
        plan['rescheduling_rules'] = self._create_rescheduling_rules()
        
        return plan
    
    async def analyze_weak_areas(self, student_id: int) -> Dict:
        """AI-powered weak area detection"""
        
        # Get quiz results and practice data
        performance_data = await self._get_detailed_performance(student_id)
        
        prompt = f"""
        Analyze this student's performance data:
        {json.dumps(performance_data)}
        
        Identify:
        1. Top 5 weak topics with reasons
        2. Common mistake patterns
        3. Recommended focus areas
        4. Suggested remediation strategies
        """
        
        response = self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        analysis = json.loads(response.choices[0].message.content)
        
        # Generate heat map data
        analysis['heatmap'] = self._generate_heatmap_data(performance_data)
        
        return analysis
    
    async def grade_subjective_answer(self, 
                                     question: str,
                                     student_answer: str,
                                     rubric: Dict) -> Dict:
        """AI-powered subjective answer grading"""
        
        prompt = f"""
        Grade this answer based on the rubric:
        
        Question: {question}
        Student Answer: {student_answer}
        Rubric: {json.dumps(rubric)}
        
        Provide:
        1. Score (out of {rubric['total_marks']})
        2. Detailed feedback
        3. Areas of improvement
        4. What was done well
        """
        
        response = self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a fair and constructive grader."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        
        grading = json.loads(response.choices[0].message.content)
        
        return grading
    
    async def predict_exam_readiness(self, student_id: int, exam_type: str) -> Dict:
        """ML-based exam readiness prediction"""
        
        # Get comprehensive student data
        features = await self._extract_student_features(student_id)
        
        # Simple prediction model (in production, use trained ML model)
        readiness_score = self._calculate_readiness_score(features, exam_type)
        
        # Generate recommendations
        recommendations = await self._generate_readiness_recommendations(
            readiness_score,
            features,
            exam_type
        )
        
        return {
            'readiness_score': readiness_score,
            'confidence_level': self._get_confidence_level(readiness_score),
            'predicted_score_range': self._predict_score_range(features, exam_type),
            'recommendations': recommendations,
            'weak_areas_to_focus': features['weak_topics'][:5],
            'estimated_preparation_time': self._estimate_prep_time(readiness_score)
        }
    
    def _calculate_readiness_score(self, features: Dict, exam_type: str) -> float:
        """Calculate exam readiness score"""
        
        weights = {
            'syllabus_completion': 0.25,
            'average_accuracy': 0.25,
            'mock_test_performance': 0.20,
            'consistency': 0.15,
            'time_management': 0.15
        }
        
        score = 0
        for key, weight in weights.items():
            if key in features:
                score += features[key] * weight
                
        # Adjust for exam type
        if exam_type == 'JEE':
            score *= 0.9  # JEE is harder
        elif exam_type == 'NEET':
            score *= 0.92
            
        return min(max(score, 0), 100)
    
    def _adjust_difficulty(self, performance: Dict, current_difficulty: str) -> str:
        """Dynamically adjust difficulty based on performance"""
        
        accuracy = performance.get('recent_accuracy', 0.5)
        
        difficulty_map = {
            'easy': {'threshold': 0.8, 'next': 'medium'},
            'medium': {'threshold_up': 0.75, 'threshold_down': 0.4, 
                      'next_up': 'hard', 'next_down': 'easy'},
            'hard': {'threshold_up': 0.7, 'threshold_down': 0.3,
                    'next_up': 'expert', 'next_down': 'medium'},
            'expert': {'threshold': 0.3, 'prev': 'hard'}
        }
        
        if current_difficulty == 'easy' and accuracy > difficulty_map['easy']['threshold']:
            return difficulty_map['easy']['next']
        elif current_difficulty == 'medium':
            if accuracy > difficulty_map['medium']['threshold_up']:
                return difficulty_map['medium']['next_up']
            elif accuracy < difficulty_map['medium']['threshold_down']:
                return difficulty_map['medium']['next_down']
        elif current_difficulty == 'hard':
            if accuracy > difficulty_map['hard']['threshold_up']:
                return difficulty_map['hard']['next_up']
            elif accuracy < difficulty_map['hard']['threshold_down']:
                return difficulty_map['hard']['next_down']
        elif current_difficulty == 'expert' and accuracy < difficulty_map['expert']['threshold']:
            return difficulty_map['expert']['prev']
            
        return current_difficulty
    
    async def _get_student_performance(self, student_id: int, topic_id: int) -> Dict:
        """Get student's performance data"""
        # Implementation to fetch from database
        pass
    
    async def _get_overall_progress(self, student_id: int) -> Dict:
        """Get overall progress data"""
        # Implementation to fetch from database
        pass
    
    async def _get_syllabus(self, student_id: int) -> List[Dict]:
        """Get syllabus based on student's grade and board"""
        # Implementation to fetch from database
        pass
    
    async def _get_detailed_performance(self, student_id: int) -> Dict:
        """Get detailed performance metrics"""
        # Implementation to fetch from database
        pass
    
    async def _extract_student_features(self, student_id: int) -> Dict:
        """Extract features for ML predictions"""
        # Implementation to fetch and process data
        pass
    
    def _generate_heatmap_data(self, performance_data: Dict) -> Dict:
        """Generate heatmap visualization data"""
        # Implementation for heatmap generation
        pass
    
    def _build_context(self, relevant_content: List[Dict]) -> str:
        """Build context from retrieved content"""
        context_parts = []
        for item in relevant_content:
            if item['similarity'] > 0.5:  # Relevance threshold
                context_parts.append(item['content'])
        
        return "\n\n".join(context_parts)
    
    def _extract_citations(self, answer: str, relevant_content: List[Dict]) -> List[Dict]:
        """Extract citations from answer"""
        citations = []
        for i, item in enumerate(relevant_content):
            if item['similarity'] > 0.6:  # Citation threshold
                citations.append({
                    'content_id': item['content_id'],
                    'relevance': item['similarity']
                })
        
        return citations
    
    def _calculate_confidence(self, answer: str, relevant_content: List[Dict]) -> float:
        """Calculate confidence score for answer"""
        if not relevant_content:
            return 0.3
        
        max_similarity = max([item['similarity'] for item in relevant_content])
        return min(max_similarity + 0.2, 1.0)
    
    def _create_rescheduling_rules(self) -> Dict:
        """Create adaptive rescheduling rules"""
        return {
            'missed_task': {
                'priority_boost': 2,
                'reschedule_within_days': 2
            },
            'failed_quiz': {
                'add_revision_task': True,
                'increase_practice': 1.5
            },
            'ahead_of_schedule': {
                'add_advanced_topics': True,
                'reduce_revision': 0.8
            }
        }
    
    async def _generate_readiness_recommendations(self, 
                                                 score: float,
                                                 features: Dict,
                                                 exam_type: str) -> List[str]:
        """Generate personalized recommendations"""
        recommendations = []
        
        if score < 40:
            recommendations.append("Focus on fundamentals and basic concepts")
            recommendations.append("Increase daily study time by 30 minutes")
        elif score < 70:
            recommendations.append("Practice more mock tests")
            recommendations.append("Work on time management skills")
        else:
            recommendations.append("Focus on advanced problem-solving")
            recommendations.append("Attempt previous year papers")
            
        return recommendations
    
    def _predict_score_range(self, features: Dict, exam_type: str) -> Dict:
        """Predict expected score range"""
        base_score = features.get('average_accuracy', 0.5) * 100
        variance = 10  # +/- 10%
        
        return {
            'min': max(0, base_score - variance),
            'max': min(100, base_score + variance),
            'expected': base_score
        }
    
    def _estimate_prep_time(self, readiness_score: float) -> str:
        """Estimate remaining preparation time needed"""
        if readiness_score < 30:
            return "3-4 months intensive preparation"
        elif readiness_score < 50:
            return "2-3 months focused preparation"
        elif readiness_score < 70:
            return "1-2 months of practice and revision"
        else:
            return "2-4 weeks of final preparation"
    
    def _get_confidence_level(self, score: float) -> str:
        """Get confidence level description"""
        if score < 30:
            return "Needs significant improvement"
        elif score < 50:
            return "Below average - requires focused effort"
        elif score < 70:
            return "Average - on track with improvements needed"
        elif score < 85:
            return "Good - well prepared"
        else:
            return "Excellent - highly prepared"


# backend/app/services/gamification_service.py
class GamificationService:
    def __init__(self):
        self.xp_rules = {
            'complete_lesson': 10,
            'complete_quiz': 20,
            'perfect_score': 50,
            'daily_streak': 5,
            'weekly_streak': 25,
            'help_peer': 15,
            'complete_chapter': 100
        }
        
        self.badge_definitions = {
            'quickstarter': {
                'name': 'Quick Starter',
                'description': 'Complete 7 days streak',
                'icon': '🚀',
                'xp_reward': 100,
                'condition': lambda stats: stats['streak_days'] >= 7
            },
            'mock_master': {
                'name': 'Mock Master',
                'description': 'Complete 10 mock tests',
                'icon': '🏆',
                'xp_reward': 200,
                'condition': lambda stats: stats['mock_tests_completed'] >= 10
            },
            'topic_tamer': {
                'name': 'Topic Tamer',
                'description': 'Master 5 topics',
                'icon': '🎯',
                'xp_reward': 150,
                'condition': lambda stats: stats['topics_mastered'] >= 5
            },
            'night_owl': {
                'name': 'Night Owl',
                'description': 'Study after 10 PM for 5 days',
                'icon': '🦉',
                'xp_reward': 50,
                'condition': lambda stats: stats['night_study_days'] >= 5
            },
            'early_bird': {
                'name': 'Early Bird',
                'description': 'Study before 6 AM for 5 days',
                'icon': '🐦',
                'xp_reward': 50,
                'condition': lambda stats: stats['morning_study_days'] >= 5
            }
        }
        
        self.level_thresholds = [
            0, 100, 250, 500, 1000, 1750, 2750, 4000, 5500, 7500, 10000
        ]
    
    async def award_xp(self, user_id: int, action: str, metadata: Dict = None) -> Dict:
        """Award XP for an action"""
        xp_earned = self.xp_rules.get(action, 0)
        
        # Apply multipliers
        if metadata:
            if metadata.get('perfect_score'):
                xp_earned *= 1.5
            if metadata.get('first_attempt'):
                xp_earned *= 1.2
                
        # Update user's gamification record
        gamification = await self._get_user_gamification(user_id)
        
        old_level = self._calculate_level(gamification['xp'])
        gamification['xp'] += int(xp_earned)
        new_level = self._calculate_level(gamification['xp'])
        
        # Check for level up
        level_up = new_level > old_level
        
        # Check for new badges
        new_badges = await self._check_badges(user_id, gamification)
        
        # Update database
        await self._update_gamification(user_id, gamification)
        
        return {
            'xp_earned': int(xp_earned),
            'total_xp': gamification['xp'],
            'level': new_level,
            'level_up': level_up,
            'new_badges': new_badges,
            'next_level_xp': self.level_thresholds[new_level] if new_level < len(self.level_thresholds) else None
        }
    
    async def update_streak(self, user_id: int) -> Dict:
        """Update user's study streak"""
        gamification = await self._get_user_gamification(user_id)
        
        last_activity = gamification.get('last_activity_date')
        today = datetime.now().date()
        
        if last_activity:
            last_date = last_activity.date()
            
            if last_date == today:
                # Already studied today
                return {'streak': gamification['streak_days'], 'updated': False}
            elif last_date == today - timedelta(days=1):
                # Continuing streak
                gamification['streak_days'] += 1
                if gamification['streak_days'] > gamification['longest_streak']:
                    gamification['longest_streak'] = gamification['streak_days']
            else:
                # Streak broken
                gamification['streak_days'] = 1
        else:
            # First activity
            gamification['streak_days'] = 1
            gamification['longest_streak'] = 1
            
        gamification['last_activity_date'] = datetime.now()
        
        # Award streak XP
        if gamification['streak_days'] % 7 == 0:
            await self.award_xp(user_id, 'weekly_streak')
        else:
            await self.award_xp(user_id, 'daily_streak')
            
        await self._update_gamification(user_id, gamification)
        
        return {
            'streak': gamification['streak_days'],
            'longest_streak': gamification['longest_streak'],
            'updated': True
        }
    
    async def get_leaderboard(self, 
                            user_id: int,
                            scope: str = 'class',
                            period: str = 'weekly') -> Dict:
        """Get leaderboard rankings"""
        
        # Get user's context (class, school, etc.)
        user_context = await self._get_user_context(user_id)
        
        # Build leaderboard query based on scope
        if scope == 'class':
            user_ids = user_context['classmate_ids']
        elif scope == 'school':
            user_ids = user_context['schoolmate_ids']
        else:  # global
            user_ids = None
            
        # Get rankings
        rankings = await self._get_rankings(user_ids, period)
        
        # Get user's position
        user_rank = next((i + 1 for i, r in enumerate(rankings) 
                         if r['user_id'] == user_id), None)
        
        return {
            'rankings': rankings[:50],  # Top 50
            'user_rank': user_rank,
            'total_participants': len(rankings),
            'scope': scope,
            'period': period
        }
    
    async def _check_badges(self, user_id: int, gamification: Dict) -> List[Dict]:
        """Check and award new badges"""
        new_badges = []
        
        # Get user stats
        stats = await self._get_user_stats(user_id)
        
        current_badges = set(gamification.get('badges', []))
        
        for badge_id, badge_def in self.badge_definitions.items():
            if badge_id not in current_badges:
                if badge_def['condition'](stats):
                    # Award badge
                    new_badges.append({
                        'id': badge_id,
                        'name': badge_def['name'],
                        'description': badge_def['description'],
                        'icon': badge_def['icon'],
                        'xp_reward': badge_def['xp_reward']
                    })
                    
                    # Add to user's badges
                    gamification['badges'].append(badge_id)
                    
                    # Award badge XP
                    gamification['xp'] += badge_def['xp_reward']
                    
        return new_badges
    
    def _calculate_level(self, xp: int) -> int:
        """Calculate level from XP"""
        for i, threshold in enumerate(self.level_thresholds):
            if xp < threshold:
                return i
        return len(self.level_thresholds)
    
    async def _get_user_gamification(self, user_id: int) -> Dict:
        """Get user's gamification data"""
        # Implementation to fetch from database
        pass
    
    async def _update_gamification(self, user_id: int, data: Dict):
        """Update gamification data"""
        # Implementation to update database
        pass
    
    async def _get_user_context(self, user_id: int) -> Dict:
        """Get user's context for leaderboard"""
        # Implementation to fetch classmates, schoolmates
        pass
    
    async def _get_rankings(self, user_ids: Optional[List[int]], period: str) -> List[Dict]:
        """Get rankings for specified users and period"""
        # Implementation to calculate rankings
        pass
    
    async def _get_user_stats(self, user_id: int) -> Dict:
        """Get comprehensive user statistics"""
        # Implementation to fetch user stats
        pass