import React, { useState, useEffect, Component, ReactNode } from 'react';
import { motion } from 'framer-motion';
import { Trophy, Star, Zap, Target, Award, CheckCircle } from 'lucide-react';
import Nav from './Nav';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';

// Define interfaces for type safety
interface User {
  id: number;
  name: string;
  email: string;
  xp: number;
  role: string;
}

interface Progress {
  task_id: string;
  completed: boolean;
  score: number | null;
  last_updated: string | null;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

// Error Boundary Component
class ErrorBoundary extends Component<{ children: ReactNode }, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 ml-64 p-8">
          <h1 className="text-2xl font-bold text-red-600">Something went wrong.</h1>
          <p className="text-gray-600">Please try refreshing the page or contact support.</p>
        </div>
      );
    }
    return this.props.children;
  }
}

const StudentDashboard: React.FC = () => {
  const { user } = useAuth() as { user: User | null };
  const [progress, setProgress] = useState<Progress[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [gamifiedMode, setGamifiedMode] = useState<boolean>(true);

  useEffect(() => {
    const fetchProgress = async () => {
      try {
        setLoading(true);
        const response = await api.get('/progress');
        setProgress(response.data);
        setLoading(false);
      } catch (err) {
        setError('Failed to load progress data');
        setLoading(false);
      }
    };

    fetchProgress();
  }, []);

  const calculateTotalXP = () => {
    return progress.reduce((total, p) => total + (p.score ? p.score * 10 : 0), 0);
  };

  const getProgressStats = () => {
    const completed = progress.filter(p => p.completed).length;
    const total = progress.length;
    const averageScore =
      progress.reduce((sum, p) => sum + (p.score || 0), 0) / (completed || 1);
    return { completed, total, averageScore: Math.round(averageScore) };
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 ml-64 p-8">
        <Nav />
        <div className="text-center">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
          >
            <Zap className="h-12 w-12 text-primary-600 mx-auto" />
          </motion.div>
          <p className="text-gray-600 mt-4">Loading your dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 ml-64 p-8">
        <Nav />
        <div className="text-center">
          <h1 className="text-2xl font-bold text-red-600">Error</h1>
          <p className="text-gray-600">{error}</p>
        </div>
      </div>
    );
  }

  const stats = getProgressStats();

  return (
    <ErrorBoundary>
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
              <h1 className="text-4xl font-bold text-gray-900">
                Welcome, {user?.name || 'Student'}! 🎓
              </h1>
              <button
                onClick={() => setGamifiedMode(!gamifiedMode)}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
              >
                {gamifiedMode ? 'Disable Gamified Mode' : 'Enable Gamified Mode'}
              </button>
            </div>
            <p className="text-xl text-gray-600 mt-2">
              {gamifiedMode ? 'Ready to conquer your learning quests?' : 'Track your progress and master your subjects!'}
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="grid md:grid-cols-3 gap-6 mb-8"
          >
            <div className="card p-6 bg-gradient-to-r from-blue-500 to-blue-600 text-white">
              <Trophy className="h-8 w-8 mb-4" />
              <h2 className="text-2xl font-bold">{calculateTotalXP()}</h2>
              <p className="text-sm opacity-90">Total XP Earned</p>
            </div>
            <div className="card p-6 bg-gradient-to-r from-green-500 to-green-600 text-white">
              <Award className="h-8 w-8 mb-4" />
              <h2 className="text-2xl font-bold">{stats.completed}/{stats.total}</h2>
              <p className="text-sm opacity-90">Tasks Completed</p>
            </div>
            <div className="card p-6 bg-gradient-to-r from-purple-500 to-purple-600 text-white">
              <Star className="h-8 w-8 mb-4" />
              <h2 className="text-2xl font-bold">{stats.averageScore}%</h2>
              <p className="text-sm opacity-90">Average Score</p>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.4 }}
            className="mb-8"
          >
            <h2 className="text-2xl font-bold text-gray-900 mb-6">
              {gamifiedMode ? 'Your Quest Progress' : 'Your Progress'}
            </h2>
            <div className="space-y-4">
              {progress.map((item, index) => (
                <motion.div
                  key={item.task_id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.5, delay: index * 0.1 }}
                  className={`card p-6 flex items-center justify-between ${gamifiedMode ? 'map-node' : ''} ${item.completed ? 'completed' : ''}`}
                >
                  <div className="flex items-center space-x-4">
                    {item.completed ? (
                      <CheckCircle className="h-6 w-6 text-green-600" />
                    ) : (
                      <Target className="h-6 w-6 text-gray-600" />
                    )}
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">{item.task_id.replace('quiz_', '')}</h3>
                      <p className="text-sm text-gray-600">
                        Last Updated: {item.last_updated ? new Date(item.last_updated).toLocaleString() : 'N/A'}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium text-gray-600">
                      Score: {item.score !== null ? `${item.score}%` : 'N/A'}
                    </p>
                    {gamifiedMode && item.completed && item.score !== null && (
                      <span className="badge">+{item.score * 10} XP <Star className="h-4 w-4" /></span>
                    )}
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.6 }}
            className="text-center"
          >
            <div className="card p-8 bg-gradient-to-r from-yellow-400 via-orange-500 to-red-500 text-white">
              <Trophy className="h-12 w-12 mx-auto mb-4" />
              <h2 className="text-2xl font-bold mb-4">
                {gamifiedMode ? 'Quest Champion!' : 'Keep Learning!'}
              </h2>
              <p className="text-lg opacity-90">
                {gamifiedMode
                  ? 'Complete more quests to climb the leaderboards!'
                  : 'Keep completing tests and study plans to master your subjects.'}
              </p>
            </div>
          </motion.div>
        </div>
      </div>
    </ErrorBoundary>
  );
};

export default StudentDashboard;