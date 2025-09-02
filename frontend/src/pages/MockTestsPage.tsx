import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Target, Clock, CheckCircle, XCircle, Brain, Award, Trophy, Zap, Star } from 'lucide-react';
import Nav from './Nav';
import axios from 'axios';

// Define interfaces for type safety
interface Test {
  id: number;
  title: string;
  subject: string;
  chapter: string;
  topic: string;
  questions: number;
  duration: number;
  difficulty: string;
  completed: boolean;
  lastScore: number | null;
  question_data?: Question[];
}

interface Question {
  question: string;
  options: string[];
  answer: string;
  explanation: string;
}

interface Progress {
  task_id: string;
  completed: boolean;
  score: number | null;
}

interface Answers {
  [key: number]: string;
}

const MockTestsPage: React.FC = () => {
  const [selectedTest, setSelectedTest] = useState<Test | null>(null);
  const [currentQuestion, setCurrentQuestion] = useState<number>(0);
  const [answers, setAnswers] = useState<Answers>({});
  const [showResults, setShowResults] = useState<boolean>(false);
  const [testResults, setTestResults] = useState<{
    score: number;
    correct: number;
    total: number;
    answers: Answers;
  } | null>(null);
  const [tests, setTests] = useState<Test[]>([]);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [gamifiedMode, setGamifiedMode] = useState<boolean>(false);
  const [progress, setProgress] = useState<Progress[]>([]);

  useEffect(() => {
    const fetchTests = async () => {
      try {
        const response = await axios.get('http://localhost:8000/quizzes', {
          headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
        });
        const fetchedTests: Test[] = response.data.map((quiz: any) => ({
          id: quiz.id,
          title: `${quiz.subject} ${quiz.chapter} ${gamifiedMode ? 'Challenge' : 'Test'}`,
          subject: quiz.subject,
          chapter: quiz.chapter,
          topic: quiz.topic,
          questions: quiz.question_data.length,
          duration: 30, // Could be dynamic from backend
          difficulty: quiz.question_data[0]?.difficulty || 'Medium',
          completed: false,
          lastScore: null,
          question_data: quiz.question_data,
        }));

        const progressResponse = await axios.get('http://localhost:8000/progress', {
          headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
        });
        const progressData: Progress[] = progressResponse.data;

        setProgress(progressData);
        setTests(
          fetchedTests.map(test => ({
            ...test,
            completed: progressData.some(p => p.task_id === `quiz_${test.id}` && p.completed),
            lastScore: progressData.find(p => p.task_id === `quiz_${test.id}`)?.score || null,
          }))
        );
      } catch (error) {
        console.error('Error fetching tests:', error);
      }
    };

    fetchTests();
  }, [gamifiedMode]);

  const startTest = async (test: Test) => {
    try {
      setSelectedTest(test);
      setQuestions(test.question_data || []);
      setCurrentQuestion(0);
      setAnswers({});
      setShowResults(false);
    } catch (error) {
      console.error('Error starting test:', error);
    }
  };

  const submitAnswer = async (answer: string) => {
    setAnswers(prev => ({
      ...prev,
      [currentQuestion]: answer,
    }));

    if (currentQuestion < questions.length - 1) {
      setCurrentQuestion(prev => prev + 1);
    } else {
      let correct = 0;
      questions.forEach((q, index) => {
        if (answers[index] === q.answer || (index === currentQuestion && answer === q.answer)) {
          correct++;
        }
      });

      const score = Math.round((correct / questions.length) * 100);
      const results = {
        score,
        correct,
        total: questions.length,
        answers: { ...answers, [currentQuestion]: answer },
      };
      setTestResults(results);

      try {
        await axios.put(
          'http://localhost:8000/progress',
          {
            task_id: `quiz_${selectedTest!.id}`,
            completed: true,
            score,
          },
          {
            headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
          }
        );

        setProgress(prev => [
          ...prev.filter(p => p.task_id !== `quiz_${selectedTest!.id}`),
          { task_id: `quiz_${selectedTest!.id}`, completed: true, score },
        ]);

        setTests(prevTests =>
          prevTests.map(t =>
            t.id === selectedTest!.id ? { ...t, completed: true, lastScore: score } : t
          )
        );
      } catch (error) {
        console.error('Error updating progress:', error);
      }

      setShowResults(true);
    }
  };

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'Easy':
        return 'text-green-600 bg-green-100';
      case 'Medium':
        return 'text-yellow-600 bg-yellow-100';
      case 'Hard':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getSubjectColor = (subject: string) => {
    const colors: { [key: string]: string } = {
      Mathematics: 'from-blue-500 to-blue-600',
      Physics: 'from-purple-500 to-purple-600',
      Chemistry: 'from-green-500 to-green-600',
      Biology: 'from-teal-500 to-teal-600',
      English: 'from-pink-500 to-pink-600',
      'Social Science': 'from-orange-500 to-orange-600',
    };
    return colors[subject] || 'from-gray-500 to-gray-600';
  };

  if (selectedTest && !showResults) {
    const question = questions[currentQuestion];
    return (
      <div className={`min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 ${gamifiedMode ? 'gamified-mode' : ''}`}>
        <style>
          {`
            .gamified-mode .map-node {
              background: linear-gradient(to right, #3b82f6, #8b5cf6);
              color: white;
              border-radius: 50%;
              width: 60px;
              height: 60px;
              display: flex;
              align-items: center;
              justify-content: center;
              font-weight: bold;
              cursor: pointer;
              transition: transform 0.3s ease;
            }
            .gamified-mode .map-node.completed {
              background: linear-gradient(to right, #22c55e, #16a34a);
            }
            .gamified-mode .map-node:hover {
              transform: scale(1.1);
            }
            .gamified-mode .map-path {
              width: 100%;
              height: 5px;
              background: #d1d5db;
              margin: 10px 0;
            }
            .gamified-mode .map-path.completed {
              background: #22c55e;
            }
            .badge {
              background: #fef3c7;
              color: #b45309;
              padding: 5px 10px;
              border-radius: 15px;
              display: inline-flex;
              align-items: center;
              gap: 5px;
              font-size: 0.75rem;
            }
          `}
        </style>
        <Nav />
        <div className="ml-64 p-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="max-w-4xl mx-auto"
          >
            <div className="flex items-center justify-between mb-6">
              <h1 className="text-2xl font-bold text-gray-900">{selectedTest.title}</h1>
              <button
                onClick={() => setGamifiedMode(!gamifiedMode)}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
              >
                {gamifiedMode ? 'Disable Gamified Mode' : 'Enable Gamified Mode'}
              </button>
            </div>
            <div className="flex items-center space-x-4 mb-6">
              <span className="text-gray-600">
                Question {currentQuestion + 1} of {questions.length}
              </span>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${((currentQuestion + 1) / questions.length) * 100}%` }}
                  transition={{ duration: 0.5 }}
                  className="bg-gradient-to-r from-primary-500 to-secondary-500 h-3 rounded-full"
                ></motion.div>
              </div>
            </div>
            <motion.div
              key={currentQuestion}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5 }}
              className="card p-6"
            >
              <p className="text-lg font-medium text-gray-900 mb-6">{question.question}</p>
              <div className="space-y-4">
                {question.options.map((option, index) => (
                  <motion.button
                    key={index}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => submitAnswer(option)}
                    className={`w-full text-left p-4 border border-gray-200 rounded-lg hover:border-primary-600 hover:bg-primary-50 transition-all duration-200 ${
                      gamifiedMode ? 'map-node' : ''
                    }`}
                  >
                    <span className="font-medium text-gray-900">
                      {String.fromCharCode(65 + index)}. {option}
                    </span>
                    {gamifiedMode && (
                      <span className="badge ml-2">+10 XP</span>
                    )}
                  </motion.button>
                ))}
              </div>
            </motion.div>
          </motion.div>
        </div>
      </div>
    );
  }

  if (showResults && testResults) {
    return (
      <div className={`min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 ${gamifiedMode ? 'gamified-mode' : ''}`}>
        <Nav />
        <div className="ml-64 p-8">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8 }}
            className="card p-8 text-center max-w-4xl mx-auto"
          >
            <motion.div
              animate={{ rotate: [0, 10, -10, 0] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="inline-block mb-6"
            >
              {testResults.score >= 80 ? (
                <Trophy className="h-20 w-20 text-yellow-500 mx-auto" />
              ) : testResults.score >= 60 ? (
                <Award className="h-20 w-20 text-blue-500 mx-auto" />
              ) : (
                <Target className="h-20 w-20 text-gray-500 mx-auto" />
              )}
            </motion.div>
            <h1 className="text-4xl font-bold text-gray-900 mb-4">
              {testResults.score >= 80
                ? gamifiedMode
                  ? 'Epic Victory! 🎉'
                  : 'Excellent Work! 🎉'
                : testResults.score >= 60
                ? gamifiedMode
                  ? 'Heroic Effort! 👏'
                  : 'Good Job! 👏'
                : gamifiedMode
                ? 'Keep Battling! 💪'
                : 'Keep Practicing! 💪'}
            </h1>
            <div className="text-6xl font-bold text-primary-600 mb-4">{testResults.score}%</div>
            <p className="text-xl text-gray-600 mb-8">
              You got {testResults.correct} out of {testResults.total} questions correct
              {gamifiedMode && testResults.score >= 60 && (
                <span className="badge ml-4">+{testResults.score * 10} XP <Star className="h-4 w-4" /></span>
              )}
            </p>
            <div className="bg-gradient-to-r from-blue-50 to-purple-50 p-6 rounded-lg mb-8 text-left">
              <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center">
                <Brain className="h-5 w-5 text-primary-600 mr-2" />
                {gamifiedMode ? 'Quest Analysis' : 'AI Feedback & Analysis'}
              </h3>
              <div className="space-y-3">
                <p className="text-gray-700">
                  <strong>Strengths:</strong> You demonstrated strong understanding of key concepts in {selectedTest!.subject}.
                </p>
                <p className="text-gray-700">
                  <strong>Areas to Improve:</strong> Review incorrect answers to strengthen your knowledge.
                </p>
                <p className="text-gray-700">
                  <strong>Recommendation:</strong> Practice similar problems or ask the AI Tutor for clarification.
                </p>
              </div>
            </div>
            <div className="space-y-4 mb-8">
              {questions.map((q, index) => {
                const userAnswer = testResults.answers[index];
                const isCorrect = userAnswer === q.answer;
                return (
                  <div key={index} className="text-left p-4 border border-gray-200 rounded-lg">
                    <div className="flex items-start space-x-3">
                      {isCorrect ? (
                        <CheckCircle className="h-5 w-5 text-green-600 mt-1 flex-shrink-0" />
                      ) : (
                        <XCircle className="h-5 w-5 text-red-600 mt-1 flex-shrink-0" />
                      )}
                      <div className="flex-1">
                        <p className="font-medium text-gray-900 mb-2">{q.question}</p>
                        <p className="text-sm text-gray-600 mb-2">
                          Your answer:{' '}
                          <span className={isCorrect ? 'text-green-600' : 'text-red-600'}>{userAnswer}</span>
                          {!isCorrect && (
                            <span className="text-green-600 ml-2">Correct: {q.answer}</span>
                          )}
                        </p>
                        <p className="text-sm text-gray-700 bg-gray-50 p-2 rounded italic">
                          {q.explanation}
                        </p>
                        {gamifiedMode && isCorrect && (
                          <span className="badge mt-2">+20 XP</span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="flex justify-center space-x-4">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => startTest(selectedTest!)}
                className="btn-primary px-6 py-3 flex items-center space-x-2"
              >
                <Zap className="h-5 w-5" />
                <span>{gamifiedMode ? 'Retry Challenge' : 'Retake Test'}</span>
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setShowResults(false)}
                className="btn-secondary px-6 py-3 flex items-center space-x-2"
              >
                <Target className="h-5 w-5" />
                <span>{gamifiedMode ? 'Back to Challenges' : 'Back to Tests'}</span>
              </motion.button>
            </div>
          </motion.div>
        </div>
      </div>
    );
  }

  return (
    <div className={`min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 ${gamifiedMode ? 'gamified-mode' : ''}`}>
      <style>
        {`
          .gamified-mode .map-node {
            background: linear-gradient(to right, #3b82f6, #8b5cf6);
            color: white;
            border-radius: 50%;
            width: 60px;
            height: 60px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.3s ease;
          }
          .gamified-mode .map-node.completed {
            background: linear-gradient(to right, #22c55e, #16a34a);
          }
          .gamified-mode .map-node:hover {
            transform: scale(1.1);
          }
          .gamified-mode .map-path {
            width: 100%;
            height: 5px;
            background: #d1d5db;
            margin: 10px 0;
          }
          .gamified-mode .map-path.completed {
            background: #22c55e;
          }
          .badge {
            background: #fef3c7;
            color: #b45309;
            padding: 5px 10px;
            border-radius: 15px;
            display: inline-flex;
            align-items: center;
            gap: 5px;
            font-size: 0.75rem;
          }
        `}
      </style>
      <Nav />
      <div className="ml-64 p-8">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="mb-8"
        >
          <div className="flex items-center justify-between">
            <h1 className="text-4xl font-bold text-gray-900 mb-2">
              {gamifiedMode ? 'Challenge Arena 🎯' : 'Mock Tests & Practice Arena 🎯'}
            </h1>
            <button
              onClick={() => setGamifiedMode(!gamifiedMode)}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              {gamifiedMode ? 'Disable Gamified Mode' : 'Enable Gamified Mode'}
            </button>
          </div>
          <p className="text-xl text-gray-600">
            {gamifiedMode
              ? 'Battle through epic challenges to conquer your subjects!'
              : 'Challenge yourself with AI-powered tests and get instant feedback'}
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="mb-8"
        >
          <h2 className="text-2xl font-bold text-gray-900 mb-6">
            {gamifiedMode ? 'Available Challenges' : 'Available Practice Tests'}
          </h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {tests.map((test, index) => (
              <React.Fragment key={test.id}>
                <motion.div
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: index * 0.1 }}
                  whileHover={{ y: -10 }}
                  className={`card p-6 relative overflow-hidden ${gamifiedMode ? 'map-node' : ''} ${
                    test.completed ? 'completed' : ''
                  }`}
                >
                  <div className={`absolute top-0 right-0 w-24 h-24 bg-gradient-to-br ${getSubjectColor(test.subject)} opacity-10 rounded-full -mr-12 -mt-12`}></div>
                  <div className="relative z-10">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-xl font-semibold text-gray-900">{test.title}</h3>
                      {test.completed && (
                        <CheckCircle className="h-6 w-6 text-green-600" />
                      )}
                    </div>
                    <p className="text-gray-600 mb-4">
                      {test.subject} • {test.chapter} • {test.topic}
                    </p>
                    <div className="space-y-2 mb-6">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-600">Questions:</span>
                        <span className="font-medium">{test.questions}</span>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-600">Duration:</span>
                        <span className="font-medium">{test.duration} min</span>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-600">Difficulty:</span>
                        <span
                          className={`px-2 py-1 rounded-full text-xs font-medium ${getDifficultyColor(
                            test.difficulty
                          )}`}
                        >
                          {test.difficulty}
                        </span>
                      </div>
                      {test.lastScore !== null && (
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-gray-600">Last Score:</span>
                          <span className="font-medium text-green-600">{test.lastScore}%</span>
                        </div>
                      )}
                      {gamifiedMode && test.completed && (
                        <span className="badge mt-2">+{test.lastScore !== null ? test.lastScore * 10 : 0} XP <Star className="h-4 w-4" /></span>
                      )}
                    </div>
                    <motion.button
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={() => startTest(test)}
                      className="w-full btn-primary flex items-center justify-center space-x-2"
                    >
                      <Brain className="h-5 w-5" />
                      <span>{test.completed ? (gamifiedMode ? 'Replay Challenge' : 'Retake Test') : (gamifiedMode ? 'Start Challenge' : 'Start Test')}</span>
                    </motion.button>
                  </div>
                </motion.div>
                {index < tests.length - 1 && gamifiedMode && (
                  <div className={`map-path ${test.completed ? 'completed' : ''}`}></div>
                )}
              </React.Fragment>
            ))}
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.4 }}
          className="mt-12 text-center"
        >
          <div className="card p-8 bg-gradient-to-r from-yellow-400 via-orange-500 to-red-500 text-white">
            <Trophy className="h-12 w-12 mx-auto mb-4" />
            <h2 className="text-2xl font-bold mb-4">
              {gamifiedMode ? 'Challenge Master!' : 'Test Champion!'}
            </h2>
            <p className="text-lg opacity-90">
              {gamifiedMode
                ? 'Conquer these challenges to earn epic rewards and climb the leaderboards!'
                : 'Complete tests to master your subjects and track your progress.'}
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default MockTestsPage;