import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Home, BookOpen, Target, MessageCircle, LogOut } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const Nav: React.FC<{ onLogout?: () => void }> = ({ onLogout }) => {
  const { user, logout } = useAuth();
  const location = useLocation();

  const navItems = [
    { path: '/student/dashboard', label: 'Dashboard', icon: Home },
    { path: '/student/study-plan', label: 'Study Plan', icon: BookOpen },
    { path: '/student/mock-tests', label: 'Mock Tests', icon: Target },
    { path: '/student/tutor-chat', label: 'AI Tutor', icon: MessageCircle },
  ];

  const handleLogout = () => {
    if (onLogout) {
      onLogout(); // Trigger parent component's logout logic first
    }
    logout(); // Handle AuthContext logout (e.g., clear token, redirect)
  };

  return (
    <nav className="fixed top-16 left-0 w-64 h-[calc(100vh-4rem)] bg-gradient-to-b from-indigo-800 to-purple-800 text-white p-6 flex flex-col">
      <div className="mb-8">
        <h2 className="text-xl font-bold">AI Study Tutor</h2>
        <p className="text-sm opacity-80">{user?.firstName}'s Journey</p>
      </div>
      
      <div className="flex-1 space-y-2">
        {navItems.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            className={`flex items-center space-x-3 p-3 rounded-lg transition-all duration-200 ${
              location.pathname === item.path
                ? 'bg-white/20'
                : 'hover:bg-white/10'
            }`}
          >
            <item.icon className="h-5 w-5" />
            <span>{item.label}</span>
          </Link>
        ))}
      </div>
      
      <button
        onClick={handleLogout}
        className="flex items-center space-x-3 p-3 rounded-lg hover:bg-red-500/50 transition-all duration-200"
      >
        <LogOut className="h-5 w-5" />
        <span>Logout</span>
      </button>
    </nav>
  );
};

export default Nav;