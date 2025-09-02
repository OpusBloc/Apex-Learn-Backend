import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  TrendingUp, 
  AlertTriangle, 
  Target, 
  Calendar,
  MessageCircle,
  Download,
  Clock,
  BookOpen,
  Award,
  Brain
} from 'lucide-react';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js';
import { Bar } from 'react-chartjs-2';
import { useAuth } from '../context/AuthContext';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const ParentDashboard: React.FC = () => {
  const { user } = useAuth();
  const [childProgress, setChildProgress] = useState({
    name: "Alex",
    completedTasks: 42,
    totalTasks: 67,
    weeklyGoal: 15,
    completedThisWeek: 12,
    averageScore: 78.5,
    studyStreak: 8,
    timeStudied: 24.5,
    upcomingTests: 3
  });

  const [weeklyData, setWeeklyData] = useState({
    Mon: Math.floor(Math.random() * 3) + 1,
    Tue: Math.floor(Math.random() * 4) + 2,
    Wed: Math.floor(Math.random() * 3) + 1,
    Thu: Math.floor(Math.random() * 4) + 3,
    Fri: Math.floor(Math.random() * 3) + 2,
    Sat: Math.floor(Math.random() * 5) + 2,
    Sun: Math.floor(Math.random() * 4) + 1
  });

  const [chatMessage, setChatMessage] = useState('');
  const [chatHistory, setChatHistory] = useState([
    { role: 'assistant', message: `Hi! I'm here to help you understand ${childProgress.name}'s learning progress. Feel free to ask me anything about their studies, performance, or how to better support them.` }
  ]);

  const progressPercentage = (childProgress.completedTasks / childProgress.totalTasks) * 100;
  const weeklyProgress = (childProgress.completedThisWeek / childProgress.weeklyGoal) * 100;

  const chartData = {
    labels: Object.keys(weeklyData),
    datasets: [
      {
        label: 'Hours Studied',
        data: Object.values(weeklyData),
        backgroundColor: 'rgba(59, 130, 246, 0.8)',
        borderColor: 'rgba(59, 130, 246, 1)',
        borderWidth: 2,
        borderRadius: 8,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: {
        display: false,
      },
      title: {
        display: false,
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        max: 8,
        ticks: {
          stepSize: 2,
        },
      },
    },
  };

  const risks = [
    "Alex has missed 2 tasks this week - consider discussing their schedule",
    "Chemistry scores below average - extra support might be helpful",
    "Study streak at risk - encourage daily practice sessions"
  ];

  const recommendations = [
    "Focus on Chemistry concepts this week",
    "Schedule regular study breaks to maintain motivation", 
    "Review Algebra fundamentals to strengthen foundation"
  ];

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatMessage.trim()) return;

    setChatHistory(prev => [...prev, { role: 'user', message: chatMessage }]);
    
    // Simulate AI response
    setTimeout(() => {
      const responses = [
        `Based on ${childProgress.name}'s current progress at ${progressPercentage.toFixed(1)}%, they're doing well overall. I recommend focusing on Chemistry where they scored ${Math.floor(Math.random() * 20) + 60}% in recent assessments.`,
        `${childProgress.name} has been consistent with their study schedule. Their ${childProgress.studyStreak}-day streak shows good discipline. Consider celebrating these small wins to maintain motivation.`,
        `Looking at the analytics, ${childProgress.name} performs best during ${Object.keys(weeklyData).find(day => weeklyData[day] === Math.max(...Object.values(weeklyData)))}s. You might want to schedule important study sessions during this time.`,
        `${childProgress.name}'s average score of ${childProgress.averageScore}% indicates solid understanding. To improve further, I suggest focusing on practice problems in weaker subjects.`
      ];
      
      const randomResponse = responses[Math.floor(Math.random() * responses.length)];
      setChatHistory(prev => [...prev, { role: 'assistant', message: randomResponse }]);
    }, 1000);

    setChatMessage('');
  };

  // Simulate real-time updates
  useEffect(() => {
    const interval = setInterval(() => {
      setWeeklyData(prev => ({
        ...prev,
        [Object.keys(prev)[Math.floor(Math.random() * 7)]]: Math.floor(Math.random() * 5) + 1
      }));
    }, 10000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-pink-50 pt-16">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="mb-8"
        >
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            {childProgress.name}'s Learning Journey 📊
          </h1>
          <p className="text-xl text-gray-600">
            Monitor progress, track achievements, and support their academic growth
          </p>
        </motion.div>

        {/* Key Metrics */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {[
            { 
              label: "Overall Progress", 
              value: `${progressPercentage.toFixed(1)}%`, 
              icon: "📈", 
              color: "from-blue-400 to-blue-600",
              change: `+${Math.floor(Math.random() * 5) + 2}% this week`
            },
            { 
              label: "Average Score", 
              value: `${childProgress.averageScore}%`, 
              icon: "🎯", 
              color: "from-green-400 to-green-600",
              change: `+${Math.floor(Math.random() * 3) + 1}% from last month`
            },
            { 
              label: "Study Streak", 
              value: `${childProgress.studyStreak} days`, 
              icon: "🔥", 
              color: "from-orange-400 to-orange-600",
              change: "Personal best!"
            },
            { 
              label: "Time Studied", 
              value: `${childProgress.timeStudied}h`, 
              icon: "⏱️", 
              color: "from-purple-400 to-purple-600",
              change: "This week"
            }
          ].map((metric, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              whileHover={{ scale: 1.05 }}
              className="card p-6 text-center relative overflow-hidden"
            >
              <div className={`absolute inset-0 bg-gradient-to-br ${metric.color} opacity-10`}></div>
              <div className="relative z-10">
                <div className="text-3xl mb-2">{metric.icon}</div>
                <div className="text-2xl font-bold text-gray-900 mb-1">{metric.value}</div>
                <div className="text-sm text-gray-600 mb-1">{metric.label}</div>
                <div className="text-xs text-green-600 font-medium">{metric.change}</div>
              </div>
            </motion.div>
          ))}
        </div>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Left Column - Charts and Analysis */}
          <div className="lg:col-span-2 space-y-8">
            {/* Weekly Study Pattern */}
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.2 }}
              className="card p-6"
            >
              <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
                <BarChart3 className="h-5 w-5 text-primary-600 mr-2" />
                Weekly Study Pattern
              </h2>
              <div className="h-64">
                <Bar data={chartData} options={chartOptions} />
              </div>
              <p className="text-sm text-gray-600 mt-4 text-center">
                📊 Total: {Object.values(weeklyData).reduce((a, b) => a + b, 0)} hours • 
                Average: {(Object.values(weeklyData).reduce((a, b) => a + b, 0) / 7).toFixed(1)} hours/day
              </p>
            </motion.div>

            {/* Progress Summary */}
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.4 }}
              className="card p-6"
            >
              <h2 className="text-xl font-bold text-gray-900 mb-4">
                AI Progress Analysis
              </h2>
              <div className="bg-gradient-to-r from-blue-50 to-purple-50 p-4 rounded-lg">
                <p className="text-gray-700 leading-relaxed">
                  🎉 {childProgress.name} is making excellent strides in their learning journey! 
                  They've completed <strong>{progressPercentage.toFixed(1)}%</strong> of their assigned quests, 
                  showing great dedication to mastering the syllabus. 
                  Their <strong>{childProgress.studyStreak}-day streak</strong> demonstrates consistent effort, 
                  and their average score of <strong>{childProgress.averageScore}%</strong> indicates solid understanding. 
                  Recent performance shows particular strength in Mathematics, while Chemistry could benefit from extra focus. 
                  Keep supporting their learning adventure! 🚀
                </p>
              </div>
            </motion.div>

            {/* Risk Detection */}
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.6 }}
              className="card p-6"
            >
              <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
                <AlertTriangle className="h-5 w-5 text-yellow-600 mr-2" />
                Areas Needing Attention
              </h2>
              <div className="space-y-3">
                {risks.map((risk, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.5, delay: index * 0.1 }}
                    className="flex items-start space-x-3 p-3 bg-yellow-50 border-l-4 border-yellow-400 rounded-r-lg"
                  >
                    <AlertTriangle className="h-5 w-5 text-yellow-600 mt-0.5 flex-shrink-0" />
                    <p className="text-gray-700 text-sm">{risk}</p>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          </div>

          {/* Right Column - Recommendations and Chat */}
          <div className="space-y-8">
            {/* Recommendations */}
            <motion.div
              initial={{ opacity: 0, x: 30 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8, delay: 0.3 }}
              className="card p-6"
            >
              <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
                <Target className="h-5 w-5 text-green-600 mr-2" />
                This Week's Focus
              </h2>
              <div className="space-y-3">
                {recommendations.map((recommendation, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.5, delay: index * 0.1 }}
                    className="flex items-start space-x-3 p-3 bg-green-50 border-l-4 border-green-400 rounded-r-lg"
                  >
                    <Target className="h-4 w-4 text-green-600 mt-1 flex-shrink-0" />
                    <p className="text-gray-700 text-sm">{recommendation}</p>
                  </motion.div>
                ))}
              </div>
            </motion.div>

            {/* AI Chat Assistant */}
            <motion.div
              initial={{ opacity: 0, x: 30 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8, delay: 0.5 }}
              className="card p-6"
            >
              <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
                <MessageCircle className="h-5 w-5 text-primary-600 mr-2" />
                Ask AI Assistant
              </h2>
              
              <div className="h-64 overflow-y-auto border border-gray-200 rounded-lg p-4 mb-4 space-y-3">
                {chatHistory.map((chat, index) => (
                  <div
                    key={index}
                    className={`flex ${chat.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-xs p-3 rounded-lg text-sm ${
                        chat.role === 'user'
                          ? 'bg-primary-600 text-white'
                          : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {chat.message}
                    </div>
                  </div>
                ))}
              </div>

              <form onSubmit={handleSendMessage} className="flex space-x-2">
                <input
                  type="text"
                  value={chatMessage}
                  onChange={(e) => setChatMessage(e.target.value)}
                  placeholder="Ask about your child's progress..."
                  className="flex-1 input-field text-sm"
                />
                <motion.button
                  type="submit"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="btn-primary px-4 py-2 text-sm"
                >
                  Send
                </motion.button>
              </form>
            </motion.div>

            {/* Quick Actions */}
            <motion.div
              initial={{ opacity: 0, x: 30 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8, delay: 0.7 }}
              className="card p-6"
            >
              <h2 className="text-xl font-bold text-gray-900 mb-4">Quick Actions</h2>
              <div className="space-y-3">
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className="w-full flex items-center justify-center space-x-2 py-3 bg-primary-50 text-primary-700 rounded-lg hover:bg-primary-100 transition-colors"
                >
                  <Download className="h-4 w-4" />
                  <span>Download Progress Report</span>
                </motion.button>
                
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className="w-full flex items-center justify-center space-x-2 py-3 bg-secondary-50 text-secondary-700 rounded-lg hover:bg-secondary-100 transition-colors"
                >
                  <Calendar className="h-4 w-4" />
                  <span>Schedule Parent-Teacher Meet</span>
                </motion.button>

                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className="w-full flex items-center justify-center space-x-2 py-3 bg-accent-50 text-accent-700 rounded-lg hover:bg-accent-100 transition-colors"
                >
                  <BookOpen className="h-4 w-4" />
                  <span>View Study Materials</span>
                </motion.button>
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ParentDashboard;