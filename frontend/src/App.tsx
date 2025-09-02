import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import Layout from './components/Layout';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import AboutPage from './pages/AboutPage';
import CareersPage from './pages/CareersPage';
import StudentDashboard from './pages/StudentDashboard';
import ParentDashboard from './pages/ParentDashboard';
import TeacherDashboard from './pages/TeacherDashboard';
import StudyPlanPage from './pages/StudyPlanPage';
import MockTestsPage from './pages/MockTestsPage';
import TutorChatPage from './pages/TutorChatPage';

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="login" element={<LoginPage />} />
          <Route path="register" element={<RegisterPage />} />
          <Route path="about" element={<AboutPage />} />
          <Route path="careers" element={<CareersPage />} />
          <Route path="student/dashboard" element={<StudentDashboard />} />
          <Route path="student/study-plan" element={<StudyPlanPage />} />
          <Route path="student/mock-tests" element={<MockTestsPage />} />
          <Route path="student/tutor-chat" element={<TutorChatPage />} />
          <Route path="parent/dashboard" element={<ParentDashboard />} />
          <Route path="teacher/dashboard" element={<TeacherDashboard />} />
        </Route>
      </Routes>
    </AuthProvider>
  );
}

export default App;