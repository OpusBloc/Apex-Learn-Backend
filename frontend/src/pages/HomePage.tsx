import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Brain, 
  BookOpen, 
  Users, 
  TrendingUp, 
  Zap, 
  Shield,
  Star,
  CheckCircle
} from 'lucide-react';
import AnimatedBackground from '../components/AnimatedBackground';

const HomePage: React.FC = () => {
  return (
    <div className="relative">
      <AnimatedBackground />
      
      {/* Hero Section */}
      <section className="relative min-h-screen flex items-center justify-center px-4">
        <div className="max-w-6xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="mb-8"
          >
            <motion.div
              className="inline-block mb-6"
              animate={{ rotate: [0, 10, -10, 0] }}
              transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
            >
              <Brain className="h-20 w-20 text-primary-600 mx-auto" />
            </motion.div>
            
            <h1 className="text-5xl md:text-7xl font-bold text-gray-900 mb-6">
              AI Study{' '}
              <span className="bg-gradient-to-r from-primary-600 to-secondary-600 bg-clip-text text-transparent">
                Tutor
              </span>
            </h1>
            
            <p className="text-xl md:text-2xl text-gray-600 mb-8 max-w-3xl mx-auto">
              Transform your learning journey with personalized AI tutoring, 
              adaptive study plans, and intelligent progress tracking
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link to="/register" className="btn-primary text-lg px-8 py-4">
                Start Learning Free
              </Link>
              <Link to="/about" className="border-2 border-primary-600 text-primary-600 hover:bg-primary-600 hover:text-white px-8 py-4 rounded-lg font-medium transition-all duration-200">
                Learn More
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 px-4">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              Powerful Features for Every Learner
            </h2>
            <p className="text-xl text-gray-600">
              Discover how AI can revolutionize your educational experience
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {[
              {
                icon: Brain,
                title: "AI-Powered Tutoring",
                description: "Get instant, personalized explanations for any topic with our advanced AI tutor",
                color: "text-primary-600"
              },
              {
                icon: BookOpen,
                title: "Adaptive Study Plans",
                description: "Customized learning paths that adapt to your progress and learning style",
                color: "text-secondary-600"
              },
              {
                icon: TrendingUp,
                title: "Progress Analytics",
                description: "Track your improvement with detailed analytics and performance insights",
                color: "text-accent-600"
              },
              {
                icon: Users,
                title: "Parent Dashboard",
                description: "Parents can monitor progress and support their child's learning journey",
                color: "text-purple-600"
              },
              {
                icon: Zap,
                title: "Interactive Quizzes",
                description: "Engaging mock tests with AI-generated feedback and explanations",
                color: "text-pink-600"
              },
              {
                icon: Shield,
                title: "Safe Learning Environment",
                description: "Secure platform with age-appropriate content and privacy protection",
                color: "text-green-600"
              }
            ].map((feature, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                whileHover={{ y: -10 }}
                className="card p-6"
              >
                <feature.icon className={`h-12 w-12 ${feature.color} mb-4`} />
                <h3 className="text-xl font-semibold text-gray-900 mb-3">
                  {feature.title}
                </h3>
                <p className="text-gray-600">
                  {feature.description}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-20 bg-gradient-to-r from-primary-600 to-secondary-600">
        <div className="max-w-6xl mx-auto px-4 text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <h2 className="text-4xl font-bold text-white mb-4">
              Join Thousands of Successful Students
            </h2>
            <p className="text-xl text-blue-100 mb-12">
              Our AI-powered platform has helped students achieve their academic goals
            </p>
            
            <div className="grid md:grid-cols-4 gap-8">
              {[
                { number: "15,742", label: "Active Students", suffix: "+" },
                { number: "98.5", label: "Success Rate", suffix: "%" },
                { number: "2.8M", label: "Questions Answered", suffix: "" },
                { number: "45", label: "Average Score Improvement", suffix: "%" }
              ].map((stat, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, scale: 0.5 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.5, delay: index * 0.1 }}
                  className="text-white"
                >
                  <div className="text-4xl font-bold mb-2">
                    {stat.number}{stat.suffix}
                  </div>
                  <div className="text-blue-100">
                    {stat.label}
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <h2 className="text-4xl font-bold text-gray-900 mb-6">
              Ready to Transform Your Learning?
            </h2>
            <p className="text-xl text-gray-600 mb-8">
              Join our AI-powered educational platform and experience personalized learning like never before
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link to="/register" className="btn-primary text-lg px-10 py-4">
                Get Started Today
              </Link>
              <Link to="/about" className="border-2 border-gray-300 text-gray-700 hover:border-primary-600 hover:text-primary-600 px-10 py-4 rounded-lg font-medium transition-all duration-200">
                Learn More
              </Link>
            </div>
          </motion.div>
        </div>
      </section>
    </div>
  );
};

export default HomePage;