import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  Users, 
  BookOpen, 
  TrendingUp, 
  Calendar,
  MessageCircle,
  FileText,
  Award,
  Clock
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const TeacherDashboard: React.FC = () => {
  const { user } = useAuth();
  const [selectedClass, setSelectedClass] = useState('10-A');

  const classStats = {
    totalStudents: 45,
    activeToday: 38,
    averageScore: 82.3,
    completionRate: 76.8,
    upcomingAssignments: 12,
    pendingGrading: 23
  };

  const recentActivity = [
    { student: "Priya Sharma", action: "Completed Algebra Quiz", score: "95%", time: "2 hours ago" },
    { student: "Rahul Patel", action: "Submitted Physics Assignment", score: "88%", time: "4 hours ago" },
    { student: "Ananya Singh", action: "Asked question in Chemistry", score: "-", time: "6 hours ago" },
    { student: "Kiran Kumar", action: "Completed Study Plan", score: "92%", time: "1 day ago" },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-white to-blue-50 pt-16">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="mb-8"
        >
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Welcome, {user?.firstName}! 👨‍🏫
          </h1>
          <p className="text-xl text-gray-600">
            Manage your classes and track student progress with AI insights
          </p>
        </motion.div>

        {/* Class Selector */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="mb-8"
        >
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Select Class
          </label>
          <select
            value={selectedClass}
            onChange={(e) => setSelectedClass(e.target.value)}
            className="input-field max-w-xs"
          >
            <option value="10-A">Class 10-A</option>
            <option value="10-B">Class 10-B</option>
            <option value="11-A">Class 11-A</option>
            <option value="12-A">Class 12-A</option>
          </select>
        </motion.div>

        {/* Stats Overview */}
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          {[
            { label: "Total Students", value: classStats.totalStudents, icon: Users, color: "text-blue-600" },
            { label: "Active Today", value: classStats.activeToday, icon: TrendingUp, color: "text-green-600" },
            { label: "Average Score", value: `${classStats.averageScore}%`, icon: Award, color: "text-yellow-600" },
            { label: "Completion Rate", value: `${classStats.completionRate}%`, icon: BookOpen, color: "text-purple-600" },
            { label: "Pending Grading", value: classStats.pendingGrading, icon: FileText, color: "text-red-600" },
            { label: "Upcoming Assignments", value: classStats.upcomingAssignments, icon: Calendar, color: "text-indigo-600" }
          ].map((stat, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              whileHover={{ scale: 1.05 }}
              className="card p-6"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 mb-1">{stat.label}</p>
                  <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
                </div>
                <stat.icon className={`h-8 w-8 ${stat.color}`} />
              </div>
            </motion.div>
          ))}
        </div>

        <div className="grid lg:grid-cols-2 gap-8">
          {/* Recent Activity */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.3 }}
            className="card p-6"
          >
            <h2 className="text-xl font-bold text-gray-900 mb-6 flex items-center">
              <Clock className="h-5 w-5 text-primary-600 mr-2" />
              Recent Student Activity
            </h2>
            
            <div className="space-y-4">
              {recentActivity.map((activity, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.5, delay: index * 0.1 }}
                  className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900">{activity.student}</h3>
                    <p className="text-sm text-gray-600">{activity.action}</p>
                    <p className="text-xs text-gray-500">{activity.time}</p>
                  </div>
                  {activity.score !== "-" && (
                    <div className="text-right">
                      <span className="font-bold text-green-600">{activity.score}</span>
                    </div>
                  )}
                </motion.div>
              ))}
            </div>
          </motion.div>

          {/* Quick Actions */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.5 }}
            className="card p-6"
          >
            <h2 className="text-xl font-bold text-gray-900 mb-6">Quick Actions</h2>
            
            <div className="space-y-4">
              {[
                { title: "Create Assignment", description: "Add new tasks for students", icon: FileText, color: "from-blue-500 to-blue-600" },
                { title: "Grade Submissions", description: "Review pending student work", icon: Award, color: "from-green-500 to-green-600" },
                { title: "Class Analytics", description: "View detailed performance reports", icon: TrendingUp, color: "from-purple-500 to-purple-600" },
                { title: "Send Announcement", description: "Communicate with your class", icon: MessageCircle, color: "from-orange-500 to-orange-600" }
              ].map((action, index) => (
                <motion.button
                  key={index}
                  whileHover={{ scale: 1.02, x: 5 }}
                  whileTap={{ scale: 0.98 }}
                  className="w-full flex items-center space-x-4 p-4 bg-gradient-to-r from-gray-50 to-gray-100 hover:from-gray-100 hover:to-gray-200 rounded-lg transition-all duration-200"
                >
                  <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${action.color} flex items-center justify-center`}>
                    <action.icon className="h-5 w-5 text-white" />
                  </div>
                  <div className="text-left flex-1">
                    <h3 className="font-semibold text-gray-900">{action.title}</h3>
                    <p className="text-sm text-gray-600">{action.description}</p>
                  </div>
                </motion.button>
              ))}
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default TeacherDashboard;