import React, { useState, useEffect, Fragment, ReactNode } from 'react';
import { motion } from 'framer-motion';
import { Calendar, Clock, BookOpen, CheckCircle, Target, Star, Zap, Trophy, Brain } from 'lucide-react';
import { api } from '../services/api'; // Assume Axios setup
import Nav from './Nav';
import { AxiosError } from 'axios';
import { Dialog, Transition } from '@headlessui/react';
import StudyPlanMap from '../components/StudyPlanMap';
import AIChatInterface from '../components/AIChatInterface';
import QuizInterface from '../components/QuizInterface';

interface StudyTask {
  id: number;
  topic: string;
  subject: string;
  subtopic: string;
  date: string;
  time: number;
  difficulty: string;
  quest_type: string;
  rewards: string;
  description: string;
  completed: boolean;
  progress: number;
  chapter: string;
}

interface StudyPlan {
  [key: string]: StudyTask[];
}

interface Progress {
  task_id: string;
  completed: boolean;
  score: number | null;
}

interface Stats {
  completedTasks: number;
  totalTasks: number;
  currentStreak: number;
  weeklyGoal: number;
  totalPoints: number;
  completedThisWeek: number;
  averageScore: number;
}

interface Subject {
  name: string;
  board: string;
  class_num: number;
}

interface Chapter {
  name: string;
  topics: Array<{ name: string; subtopics: string[] }>;
}

interface QuizQuestion {
  question: string;
  options: string[];
  answer: string;
  chapter?: string;
  topic?: string;
  marks?: number;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

class ErrorBoundary extends React.Component<{ children: ReactNode }, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 p-8">
          <h1 className="text-2xl font-bold text-red-600">Something went wrong.</h1>
          <p className="text-gray-600">Please try refreshing the page or contact support.</p>
        </div>
      );
    }
    return this.props.children;
  }
}

const StudyPlanPage: React.FC = () => {
  const [step, setStep] = useState<number>(0);
  const [board, setBoard] = useState<string>('');
  const [classNum, setClassNum] = useState<number>(9);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [selectedSubject, setSelectedSubject] = useState<string>('');
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [extraChapters, setExtraChapters] = useState<string[]>([]);
  const [weakChapters, setWeakChapters] = useState<string[]>([]);
  const [studyPlan, setStudyPlan] = useState<StudyPlan>({});
  const [progress, setProgress] = useState<Progress[]>([]);
  const [gamifiedMode, setGamifiedMode] = useState<boolean>(true);
  const [stats, setStats] = useState<Stats>({
    completedTasks: 0,
    totalTasks: 0,
    currentStreak: 0,
    weeklyGoal: 0,
    totalPoints: 0,
    completedThisWeek: 0,
    averageScore: 0,
  });
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [authModalOpen, setAuthModalOpen] = useState<boolean>(true);
  const [isLogin, setIsLogin] = useState<boolean>(true);
  const [authLoading, setAuthLoading] = useState<boolean>(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [user, setUser] = useState<any>(null);
  const [authForm, setAuthForm] = useState({
    email: '',
    password: '',
    firstName: '',
    lastName: '',
    middleName: '',
    role: 'student',
    schoolName: '',
    childUsername: '',
  });
  const [previousMarks, setPreviousMarks] = useState<number | null>(null);
  const [knowledgeLevel, setKnowledgeLevel] = useState<string>('beginner');
  const [initialQuiz, setInitialQuiz] = useState<QuizQuestion[]>([]);
  const [topicQuiz, setTopicQuiz] = useState<QuizQuestion[]>([]);
  const [chapterQuiz, setChapterQuiz] = useState<QuizQuestion[]>([]);
  const [threeChapterQuiz, setThreeChapterQuiz] = useState<QuizQuestion[]>([]);
  const [quizAnswers, setQuizAnswers] = useState<{ [key: number]: string }>({});
  const [topicQuizAnswers, setTopicQuizAnswers] = useState<{ [key: number]: string }>({});
  const [chapterQuizAnswers, setChapterQuizAnswers] = useState<{ [key: number]: string }>({});
  const [threeChapterQuizAnswers, setThreeChapterQuizAnswers] = useState<{ [key: number]: string }>({});
  const [quizScore, setQuizScore] = useState<number | null>(null);
  const [syllabusConfirmed, setSyllabusConfirmed] = useState<boolean>(false);
  const [selectedChapter, setSelectedChapter] = useState<string | null>(null);
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);
  const [selectedSubtopic, setSelectedSubtopic] = useState<string | null>(null);
  const [chatHistory, setChatHistory] = useState<any[]>([]);
  const [currentSubtopic, setCurrentSubtopic] = useState<string | null>(null);
  const [subtopics, setSubtopics] = useState<string[]>([]);
  const [completedChapters, setCompletedChapters] = useState<string[]>([]);
  const [completedTopics, setCompletedTopics] = useState<string[]>([]);
  const [missedDate, setMissedDate] = useState<string>('');
  const [nudge, setNudge] = useState<string>('');

  // Check authentication
  useEffect(() => {
    const token = localStorage.getItem('jwt');
    const userData = localStorage.getItem('user');
    if (token && userData) {
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      setUser(JSON.parse(userData));
      setAuthModalOpen(false);
      setStep(0);
    } else {
      setAuthModalOpen(true);
      setStep(-1);
    }
  }, []);

  // Data fetching for each step
  useEffect(() => {
    let mounted = true;
    const fetchData = async () => {
      setLoading(true);
      try {
        if (step === 1 && board && classNum) {
          const res = await api.get('/subjects', { params: { board, class_num: classNum } });
          setSubjects(res.data);
        } else if (step === 2 && selectedSubject) {
          const res = await api.get('/syllabus', { params: { board, class_num: classNum, subject: selectedSubject } });
          setChapters(res.data.chapters || []);
        } else if (step === 4) {
          const res = await api.post('/quizzes', {
            board, class_num: classNum, subject: selectedSubject,
            chapters: chapters.map(c => c.name), level: knowledgeLevel, type: 'initial'
          });
          setInitialQuiz(res.data.questions || []);
        } else if (step === 6) {
          const res = await api.get('/study-plans');
          const planData = res.data.find((p: { subject: string; }) => p.subject === selectedSubject)?.plan_data || {};
          setStudyPlan(planData);
          let completed = 0, total = 0, missed = 0;
          const today = new Date();
          for (const week in planData) {
            planData[week].forEach((task: { completed: any; date: string | number | Date; }) => {
              total++;
              if (task.completed) completed++;
              if (!task.completed && new Date(task.date) < today) missed++;
            });
          }
          setStats({ ...stats, completedTasks: completed, totalTasks: total });
          setNudge(generateNudge(completed, total, missed, weakChapters));
        } else if (step === 7 && selectedChapter && selectedTopic) {
          const res = await api.get('/subtopics', { params: { board, class_num: classNum, subject: selectedSubject, chapter: selectedChapter, topic: selectedTopic } });
          setSubtopics(res.data.subtopics || []);
          if (res.data.subtopics.length > 0) setCurrentSubtopic(res.data.subtopics[0]);
        } else if (step === 8 && selectedChapter && selectedTopic) {
          const res = await api.post('/quizzes', {
            board, class_num: classNum, subject: selectedSubject,
            chapter: selectedChapter, topic: selectedTopic, level: knowledgeLevel, type: 'topic'
          });
          setTopicQuiz(res.data.questions || []);
        } else if (step === 9 && selectedChapter) {
          const topics = chapters.find(c => c.name === selectedChapter)?.topics.map(t => t.name) || [];
          const res = await api.post('/quizzes', {
            board, class_num: classNum, subject: selectedSubject,
            chapter: selectedChapter, topics, level: knowledgeLevel, type: 'chapter'
          });
          setChapterQuiz(res.data.questions || []);
        } else if (step === 10 && completedChapters.length >= 3) {
          const lastThree = completedChapters.slice(-3);
          const res = await api.post('/quizzes', {
            board, class_num: classNum, subject: selectedSubject,
            chapters: lastThree, level: knowledgeLevel, type: 'three_chapter'
          });
          setThreeChapterQuiz(res.data.questions || []);
        }
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load data');
      } finally {
        if (mounted) setLoading(false);
      }
    };
    fetchData();
    return () => { mounted = false; };
  }, [step, board, classNum, selectedSubject, knowledgeLevel, selectedChapter, selectedTopic, completedChapters]);

  // Fetch user progress and stats
  useEffect(() => {
    const fetchProgressAndStats = async () => {
      try {
        const progressRes = await api.get('/progress');
        setProgress(progressRes.data);
        const statsRes = await api.get('/dashboard/stats');
        setStats(statsRes.data);
      } catch (err) {
        setError('Failed to load progress or stats');
      }
    };
    if (user) fetchProgressAndStats();
  }, [user]);

  // Nudge generator
  const generateNudge = (completed: number, total: number, missed: number, weak: string[]) => {
    const rate = total > 0 ? completed / total : 0;
    if (missed > 0) return `Oops, you missed ${missed} tasks! Let's focus on ${weak.slice(0, 2).join(', ') || 'your studies'} and conquer them together!`;
    if (weak.length) return `You're making progress, but let's strengthen your skills in ${weak.slice(0, 2).join(', ')}. Keep pushing, brave scholar!`;
    if (rate > 0.8) return "You're dominating the knowledge kingdom like a true champion! Keep ruling!";
    if (rate > 0.5) return "Great progress, adventurer! You're halfway to mastering this realm. Let's keep exploring!";
    return "Every step counts, young scholar! Let's dive into the next quest and build your skills!";
  };

  // Handlers
  const handleAuthSubmit = async () => {
    setAuthLoading(true);
    try {
      const endpoint = isLogin ? '/auth/login' : '/auth/register';
      const res = await api.post(endpoint, authForm);
      localStorage.setItem('jwt', res.data.token);
      localStorage.setItem('user', JSON.stringify(res.data.user));
      api.defaults.headers.common['Authorization'] = `Bearer ${res.data.token}`;
      setUser(res.data.user);
      setAuthModalOpen(false);
      setStep(0);
    } catch (err: any) {
      setAuthError(err.response?.data?.detail || 'Authentication failed');
    } finally {
      setAuthLoading(false);
    }
  };

  const handleConfirmSyllabus = async (correct: boolean) => {
    if (correct) {
      setSyllabusConfirmed(true);
      setStep(3);
    } else {
      setLoading(true);
      try {
        const res = await api.get('/syllabus', { params: { board, class_num: classNum, subject: selectedSubject } });
        setChapters(res.data.chapters || []);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to regenerate syllabus');
      } finally {
        setLoading(false);
      }
    }
  };

  const handleMarksSubmit = () => {
    if (previousMarks !== null) {
      const level = previousMarks < 60 ? 'beginner' : previousMarks <= 75 ? 'intermediate' : 'advanced';
      setKnowledgeLevel(level);
      setStep(4);
    } else {
      setError('Please enter your marks');
    }
  };

  const handleInitialQuizSubmit = async () => {
    let score = 0;
    const weak: string[] = [];
    initialQuiz.forEach((q, i) => {
      if (quizAnswers[i] === q.answer) score++;
      else if (q.chapter) weak.push(q.chapter);
    });
    setQuizScore(score);
    setWeakChapters(weak);
    try {
      const startDate = new Date().toISOString().split('T')[0];
      const endDate = new Date(new Date().setMonth(new Date().getMonth() + 6)).toISOString().split('T')[0];
      const res = await api.post('/study-plans', {
        subject: selectedSubject,
        board,
        class_num: classNum,
        start_date: startDate,
        end_date: endDate,
        extra_chapters: extraChapters,
        weak_chapters: weak,
        personality_type: 'balanced',
      });
      setStudyPlan(res.data.plan_data);
      setStep(6);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to generate study plan');
    }
  };

  const handleTaskCompletion = async (week: string, taskId: number) => {
    try {
      const task = studyPlan[week]?.find(t => t.id === taskId);
      if (!task) return;
      const res = await api.put('/task-progress', {
        subject: selectedSubject,
        week,
        task_id: taskId,
        completed: true,
        progress: 100,
      });
      setStudyPlan(res.data.plan_data);
      // Update progress
      const progressRes = await api.put('/progress', {
        task_id: String(taskId),
        completed: true,
        score: null,
      });
      setProgress([...progress, progressRes.data]);
      // Check for topic/chapter completion
      const topicTasks = Object.values(studyPlan).flat().filter(t => t.topic === task.topic && t.chapter === task.chapter);
      if (topicTasks.every(t => t.completed)) {
        setCompletedTopics([...new Set([...completedTopics, task.topic])]);
        setSelectedTopic(task.topic);
        setSelectedChapter(task.chapter);
        setStep(8);
      }
      const chapterTasks = Object.values(studyPlan).flat().filter(t => t.chapter === task.chapter);
      if (chapterTasks.every(t => t.completed)) {
        setCompletedChapters([...new Set([...completedChapters, task.chapter])]);
        setSelectedChapter(task.chapter);
        setStep(9);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update task progress');
    }
  };

  const handleChatSubmit = async (message: string) => {
    if (!selectedChapter || !selectedTopic || !currentSubtopic) {
      setError('Please select a chapter, topic, and subtopic before chatting');
      return;
    }
    try {
      const res = await api.post('/chat', {
        board,
        class_num: classNum,
        subject: selectedSubject,
        chapter: selectedChapter,
        topic: selectedTopic,
        subtopic: currentSubtopic,
        message,
      });
      setChatHistory([...chatHistory, { role: 'user', content: message }, { role: 'assistant', content: res.data.response }]);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to get chat response');
    }
  };

  const handleReschedule = async () => {
    if (!missedDate) {
      setError('Please select a missed date');
      return;
    }
    try {
      const res = await api.put('/reschedule', { subject: selectedSubject, missed_date: missedDate });
      setStudyPlan(res.data.plan_data);
      setNudge(generateNudge(stats.completedTasks, stats.totalTasks, 0, weakChapters));
      setMissedDate('');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to reschedule tasks');
    }
  };

  const handleQuizSubmit = async (type: 'initial' | 'topic' | 'chapter' | 'three_chapter') => {
    let score = 0;
    const weak: string[] = [...weakChapters];
    const answers = type === 'initial' ? quizAnswers : type === 'topic' ? topicQuizAnswers : type === 'chapter' ? chapterQuizAnswers : threeChapterQuizAnswers;
    const quiz = type === 'initial' ? initialQuiz : type === 'topic' ? topicQuiz : type === 'chapter' ? chapterQuiz : threeChapterQuiz;
    quiz.forEach((q, i) => {
      if (answers[i] === q.answer) score++;
      else if ((type === 'initial' || type === 'three_chapter') && q.chapter) weak.push(q.chapter);
      else if (type === 'chapter' && q.topic) weak.push(q.chapter || selectedChapter || '');
    });
    setQuizScore(score);
    if (score / quiz.length < 0.6) setWeakChapters([...new Set(weak)]);
    if (type === 'initial') {
      await handleInitialQuizSubmit();
    } else if (type === 'topic') {
      setStep(6);
      setCurrentSubtopic(null);
    } else if (type === 'chapter' && completedChapters.length >= 3) {
      setStep(10);
    } else if (type === 'chapter') {
      setStep(6);
    } else if (type === 'three_chapter') {
      setStep(6);
    }
    // Update progress with quiz score
    if (type !== 'initial') {
      try {
        await api.put('/progress', {
          task_id: `${type}_quiz_${Date.now()}`,
          completed: true,
          score: (score / quiz.length) * 100,
        });
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to save quiz progress');
      }
    }
  };

  const handleLogout = async () => {
    try {
      await api.post('/auth/logout');
      localStorage.removeItem('jwt');
      localStorage.removeItem('user');
      setUser(null);
      setAuthModalOpen(true);
      setStep(-1);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to logout');
    }
  };

  // Render
  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 p-8">
        <Nav onLogout={handleLogout} />
        {loading && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-b-4 border-indigo-600"></div>
          </div>
        )}
        {error && (
          <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-4" role="alert">
            <p>{error}</p>
            <button onClick={() => setError(null)} className="text-sm underline">Dismiss</button>
          </div>
        )}
        <Transition show={authModalOpen} as={Fragment}>
          <Dialog onClose={() => { }} className="relative z-50">
            <div className="fixed inset-0 bg-black bg-opacity-30" />
            <div className="fixed inset-0 flex items-center justify-center p-4">
              <Dialog.Panel className="bg-white rounded-lg p-6 w-full max-w-md">
                <Dialog.Title className="text-2xl font-bold text-indigo-600">
                  {isLogin ? 'Login to Your Quest' : 'Join the Knowledge Adventure'}
                </Dialog.Title>
                <div className="mt-4 space-y-4">
                  <input
                    type="email"
                    value={authForm.email}
                    onChange={e => setAuthForm({ ...authForm, email: e.target.value })}
                    placeholder="Email"
                    className="w-full p-2 border rounded"
                  />
                  <input
                    type="password"
                    value={authForm.password}
                    onChange={e => setAuthForm({ ...authForm, password: e.target.value })}
                    placeholder="Password"
                    className="w-full p-2 border rounded"
                  />
                  {!isLogin && (
                    <>
                      <input
                        type="text"
                        value={authForm.firstName}
                        onChange={e => setAuthForm({ ...authForm, firstName: e.target.value })}
                        placeholder="First Name"
                        className="w-full p-2 border rounded"
                      />
                      <input
                        type="text"
                        value={authForm.lastName}
                        onChange={e => setAuthForm({ ...authForm, lastName: e.target.value })}
                        placeholder="Last Name"
                        className="w-full p-2 border rounded"
                      />
                      <input
                        type="text"
                        value={authForm.schoolName}
                        onChange={e => setAuthForm({ ...authForm, schoolName: e.target.value })}
                        placeholder="School Name"
                        className="w-full p-2 border rounded"
                      />
                      <select
                        value={authForm.role}
                        onChange={e => setAuthForm({ ...authForm, role: e.target.value })}
                        className="w-full p-2 border rounded"
                      >
                        <option value="student">Student</option>
                        <option value="teacher">Teacher</option>
                        <option value="parent">Parent</option>
                      </select>
                      {authForm.role === 'parent' && (
                        <input
                          type="text"
                          value={authForm.childUsername}
                          onChange={e => setAuthForm({ ...authForm, childUsername: e.target.value })}
                          placeholder="Child's Username"
                          className="w-full p-2 border rounded"
                        />
                      )}
                    </>
                  )}
                  <button
                    onClick={handleAuthSubmit}
                    disabled={authLoading}
                    className="w-full bg-indigo-600 text-white p-2 rounded hover:bg-indigo-700 disabled:bg-gray-400"
                  >
                    {authLoading ? 'Loading...' : isLogin ? 'Login' : 'Register'}
                  </button>
                  <button
                    onClick={() => { setIsLogin(!isLogin); setAuthError(null); }}
                    className="w-full text-indigo-600 underline"
                  >
                    {isLogin ? 'Need to register?' : 'Already have an account?'}
                  </button>
                  {authError && <p className="text-red-500 text-sm">{authError}</p>}
                </div>
              </Dialog.Panel>
            </div>
          </Dialog>
        </Transition>

        {step === 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-2xl mx-auto bg-white p-8 rounded-xl shadow-lg"
          >
            <h2 className="text-3xl font-bold text-indigo-600 mb-6 flex items-center">
              <Trophy className="mr-2" /> Begin Your Learning Quest
            </h2>
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Board</label>
                <select
                  value={board}
                  onChange={e => setBoard(e.target.value)}
                  className="w-full p-3 border border-indigo-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                >
                  <option value="">Select Board</option>
                  <option value="CBSE">CBSE</option>
                  <option value="ICSE">ICSE</option>
                  <option value="ISC">ISC</option>
                  <option value="BSE Telangana">BSE Telangana</option>
                  <option value="BSE Andhra Pradesh">BSE Andhra Pradesh</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Class</label>
                <select
                  value={classNum}
                  onChange={e => setClassNum(Number(e.target.value))}
                  className="w-full p-3 border border-indigo-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                >
                  {[9, 10, 11, 12].map(n => (
                    <option key={n} value={n}>Class {n}</option>
                  ))}
                </select>
              </div>
              <button
                onClick={() => setStep(1)}
                disabled={!board || !classNum}
                className="w-full bg-indigo-600 text-white p-3 rounded-lg hover:bg-indigo-700 disabled:bg-gray-400 transition-colors duration-300"
              >
                Start Your Quest
              </button>
            </div>
          </motion.div>
        )}

        {step === 1 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-4xl mx-auto"
          >
            <h2 className="text-3xl font-bold text-indigo-600 mb-6">Choose Your Subject Quest</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {subjects.map(subject => (
                <motion.div
                  key={subject.name}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className={`p-6 rounded-xl shadow-lg cursor-pointer transition-colors duration-300 ${selectedSubject === subject.name
                    ? 'bg-indigo-600 text-white'
                    : 'bg-white text-gray-800 hover:bg-indigo-100'
                    }`}
                  onClick={() => setSelectedSubject(subject.name)}
                >
                  <div className="flex items-center space-x-3">
                    <BookOpen className="h-8 w-8" />
                    <h3 className="text-lg font-semibold">{subject.name}</h3>
                  </div>
                </motion.div>
              ))}
            </div>
            <button
              onClick={() => setStep(2)}
              disabled={!selectedSubject}
              className="mt-6 w-full bg-indigo-600 text-white p-3 rounded-lg hover:bg-indigo-700 disabled:bg-gray-400 transition-colors duration-300"
            >
              Embark on {selectedSubject || 'Subject'} Quest
            </button>
          </motion.div>
        )}

        {step === 2 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-3xl mx-auto"
          >
            <h2 className="text-3xl font-bold text-indigo-600 mb-6 flex items-center">
              <BookOpen className="mr-2" /> Confirm Your Syllabus
            </h2>
            <div className="bg-white p-6 rounded-xl shadow-lg">
              <ul className="space-y-3">
                {chapters.map((ch, i) => (
                  <li key={i} className="text-gray-700 p-3 bg-indigo-50 rounded-lg">
                    <strong className="text-indigo-700">{ch.name}</strong>: {ch.topics.map(t => t.name).join(', ')}
                  </li>
                ))}
              </ul>
              <div className="mt-6 flex space-x-4">
                <button
                  onClick={() => handleConfirmSyllabus(true)}
                  className="flex-1 bg-green-500 text-white p-3 rounded-lg hover:bg-green-600 transition-colors duration-300"
                >
                  Confirm Syllabus
                </button>
                <button
                  onClick={() => handleConfirmSyllabus(false)}
                  className="flex-1 bg-yellow-500 text-white p-3 rounded-lg hover:bg-yellow-600 transition-colors duration-300"
                >
                  Regenerate Syllabus
                </button>
              </div>
              {syllabusConfirmed && (
                <button
                  onClick={() => setStep(3)}
                  className="mt-4 w-full bg-indigo-600 text-white p-3 rounded-lg hover:bg-indigo-700 transition-colors duration-300"
                >
                  Proceed to Assessment
                </button>
              )}
            </div>
          </motion.div>
        )}

        {step === 3 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-2xl mx-auto"
          >
            <h2 className="text-3xl font-bold text-indigo-600 mb-6">Enter Previous Marks</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Marks (0-100)</label>
                <input
                  type="number"
                  value={previousMarks || ''}
                  onChange={e => setPreviousMarks(Number(e.target.value))}
                  placeholder="Enter your marks"
                  className="w-full p-2 border rounded"
                  min="0"
                  max="100"
                />
              </div>
              <button
                onClick={handleMarksSubmit}
                className="w-full bg-indigo-600 text-white p-2 rounded hover:bg-indigo-700"
              >
                Submit Marks
              </button>
            </div>
          </motion.div>
        )}

        {step === 4 && (
          <QuizInterface
            quiz={initialQuiz}
            answers={quizAnswers}
            setAnswers={setQuizAnswers}
            onSubmit={() => handleQuizSubmit('initial')}
            title="Initial Assessment Quest"
          />
        )}

        {step === 5 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-2xl mx-auto"
          >
            <h2 className="text-3xl font-bold text-indigo-600 mb-6">Select Extra Chapters</h2>
            <div className="space-y-4">
              {chapters.map(ch => (
                <label key={ch.name} className="flex items-center">
                  <input
                    type="checkbox"
                    checked={extraChapters.includes(ch.name)}
                    onChange={() => {
                      if (extraChapters.includes(ch.name)) {
                        setExtraChapters(extraChapters.filter(c => c !== ch.name));
                      } else {
                        setExtraChapters([...extraChapters, ch.name]);
                      }
                    }}
                    className="mr-2"
                  />
                  {ch.name}
                </label>
              ))}
              <button
                onClick={() => setStep(6)}
                className="w-full bg-indigo-600 text-white p-2 rounded hover:bg-indigo-700"
              >
                Generate Study Plan
              </button>
            </div>
          </motion.div>
        )}

        {step === 6 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-4xl mx-auto"
          >
            <h2 className="text-3xl font-bold text-indigo-600 mb-6">Your Study Plan Quest</h2>
            <div className="bg-white p-6 rounded-lg shadow-md mb-6">
              <h3 className="text-xl font-semibold mb-4 flex items-center">
                <Star className="mr-2 text-yellow-500" /> Progress Stats
              </h3>
              <div className="grid grid-cols-2 gap-4">
                <p>Completed Tasks: {stats.completedTasks}/{stats.totalTasks}</p>
                <p>Current Streak: {stats.currentStreak} days</p>
                <p>Weekly Goal: {stats.completedThisWeek}/{stats.weeklyGoal}</p>
                <p>Total Points: {stats.totalPoints} XP</p>
                <p>Average Score: {typeof stats.averageScore === 'number' ? stats.averageScore.toFixed(1) : 'N/A'}%</p>
              </div>
              {nudge && (
                <p className="mt-4 text-indigo-600 font-medium">{nudge}</p>
              )}
            </div>
            <div className="bg-white p-6 rounded-lg shadow-md mb-6">
              <h3 className="text-xl font-semibold mb-4">Reschedule Missed Tasks</h3>
              <input
                type="date"
                value={missedDate}
                onChange={e => setMissedDate(e.target.value)}
                className="p-2 border rounded mr-2"
              />
              <button
                onClick={handleReschedule}
                className="bg-yellow-500 text-white p-2 rounded hover:bg-yellow-600"
              >
                Reschedule
              </button>
            </div>
            <StudyPlanMap
              studyPlan={studyPlan}
              onTaskClick={(week: string | number, taskId: number) => {
                const task = studyPlan[week]?.find(t => t.id === taskId);
                if (task) {
                  setSelectedChapter(task.chapter);
                  setSelectedTopic(task.topic);
                  setCurrentSubtopic(task.subtopic);
                  setStep(7);
                }
              }}
              onTaskComplete={handleTaskCompletion}
            />
          </motion.div>
        )}

        {step === 7 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-4xl mx-auto"
          >
            <h2 className="text-3xl font-bold text-indigo-600 mb-6">Learn: {currentSubtopic}</h2>
            <div className="bg-white p-6 rounded-lg shadow-md mb-6">
              <h3 className="text-xl font-semibold mb-4">Subtopics</h3>
              <div className="space-y-2">
                {subtopics.map(sub => (
                  <button
                    key={sub}
                    onClick={async () => {
                      setCurrentSubtopic(sub);
                      try {
                        const res = await api.post('/explanation', {
                          board,
                          class_num: classNum,
                          subject: selectedSubject,
                          chapter: selectedChapter,
                          topic: sub,
                        });
                        setChatHistory([{ role: 'assistant', content: res.data.explanation }]);
                      } catch (err: any) {
                        setError(err.response?.data?.detail || 'Failed to load explanation');
                      }
                    }}
                    className={`w-full p-2 rounded text-left ${currentSubtopic === sub ? 'bg-indigo-100' : 'bg-gray-100'} hover:bg-indigo-50`}
                  >
                    {sub}
                  </button>
                ))}
              </div>
            </div>
            <AIChatInterface
              chatHistory={chatHistory}
              onSendMessage={handleChatSubmit}
              subject={selectedSubject}
              topic={selectedTopic || ''}
              subtopic={currentSubtopic || ''}
            />
            <button
              onClick={() => setStep(8)}
              className="mt-4 bg-indigo-600 text-white p-2 rounded hover:bg-indigo-700"
            >
              Take Topic Quiz
            </button>
          </motion.div>
        )}

        {step === 8 && (
          <QuizInterface
            quiz={topicQuiz}
            answers={topicQuizAnswers}
            setAnswers={setTopicQuizAnswers}
            onSubmit={() => handleQuizSubmit('topic')}
            title={`Topic Quiz: ${selectedTopic}`}
          />
        )}

        {step === 9 && (
          <QuizInterface
            quiz={chapterQuiz}
            answers={chapterQuizAnswers}
            setAnswers={setChapterQuizAnswers}
            onSubmit={() => handleQuizSubmit('chapter')}
            title={`Chapter Quiz: ${selectedChapter}`}
          />
        )}

        {step === 10 && (
          <QuizInterface
            quiz={threeChapterQuiz}
            answers={threeChapterQuizAnswers}
            setAnswers={setThreeChapterQuizAnswers}
            onSubmit={() => handleQuizSubmit('three_chapter')}
            title="Three-Chapter Mastery Quiz"
          />
        )}
      </div>
    </ErrorBoundary>
  );
};

export default StudyPlanPage;