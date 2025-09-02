import React from 'react';
import { motion } from 'framer-motion';
import { 
  Brain, 
  Target, 
  Users, 
  Award,
  Lightbulb,
  Shield,
  Zap,
  Heart
} from 'lucide-react';

const AboutPage: React.FC = () => {
  return (
    <div className="pt-16">
      {/* Hero Section */}
      <section className="py-20 px-4">
        <div className="max-w-6xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6">
              About{' '}
              <span className="bg-gradient-to-r from-primary-600 to-secondary-600 bg-clip-text text-transparent">
                AI Study Tutor
              </span>
            </h1>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              We're revolutionizing education through artificial intelligence, 
              making personalized learning accessible to every student in India.
            </p>
          </motion.div>
        </div>
      </section>

      {/* Mission Section */}
      <section className="py-20 bg-white">
        <div className="max-w-6xl mx-auto px-4">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <motion.div
              initial={{ opacity: 0, x: -30 }}
              whileInView={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8 }}
            >
              <h2 className="text-4xl font-bold text-gray-900 mb-6">Our Mission</h2>
              <p className="text-lg text-gray-600 mb-6">
                We believe every student deserves access to world-class education. 
                Our AI-powered platform adapts to individual learning styles, 
                providing personalized tutoring that helps students excel in their studies.
              </p>
              <p className="text-lg text-gray-600">
                From CBSE to state boards, we support the diverse educational 
                landscape of India with curriculum-aligned content and intelligent assessment tools.
              </p>
            </motion.div>
            
            <motion.div
              initial={{ opacity: 0, x: 30 }}
              whileInView={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8 }}
              className="relative"
            >
              <div className="bg-gradient-to-br from-primary-100 to-secondary-100 rounded-2xl p-8">
                <Brain className="h-24 w-24 text-primary-600 mx-auto mb-4" />
                <div className="text-center">
                  <h3 className="text-2xl font-bold text-gray-900 mb-2">
                    AI-Powered Learning
                  </h3>
                  <p className="text-gray-600">
                    Advanced algorithms that understand how you learn best
                  </p>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Values Section */}
      <section className="py-20 px-4">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              Our Core Values
            </h2>
            <p className="text-xl text-gray-600">
              The principles that guide our mission to transform education
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {[
              {
                icon: Target,
                title: "Personalized Learning",
                description: "Every student learns differently. Our AI adapts to individual needs and pace.",
                color: "text-primary-600"
              },
              {
                icon: Shield,
                title: "Safe Environment",
                description: "Privacy and security are paramount. We protect student data with enterprise-grade security.",
                color: "text-secondary-600"
              },
              {
                icon: Lightbulb,
                title: "Innovation",
                description: "We constantly push the boundaries of educational technology to enhance learning.",
                color: "text-accent-600"
              },
              {
                icon: Heart,
                title: "Accessibility",
                description: "Quality education should be accessible to all students, regardless of their background.",
                color: "text-pink-600"
              }
            ].map((value, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                whileHover={{ y: -10 }}
                className="card p-6 text-center"
              >
                <value.icon className={`h-12 w-12 ${value.color} mx-auto mb-4`} />
                <h3 className="text-xl font-semibold text-gray-900 mb-3">
                  {value.title}
                </h3>
                <p className="text-gray-600">
                  {value.description}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Statistics Section */}
      <section className="py-20 bg-gradient-to-r from-primary-600 to-secondary-600">
        <div className="max-w-6xl mx-auto px-4">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center text-white"
          >
            <h2 className="text-4xl font-bold mb-4">Our Impact</h2>
            <p className="text-xl text-blue-100 mb-12">
              Numbers that reflect our commitment to educational excellence
            </p>
            
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
              {[
                { number: "15,742", label: "Active Students", suffix: "+" },
                { number: "1,250", label: "Partnered Schools", suffix: "+" },
                { number: "98.5", label: "Student Satisfaction", suffix: "%" },
                { number: "45", label: "Average Score Improvement", suffix: "%" }
              ].map((stat, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, scale: 0.5 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.5, delay: index * 0.1 }}
                  className="text-center"
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

      {/* Team Section */}
      <section className="py-20 px-4">
        <div className="max-w-6xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              Built by Educators & Technologists
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Our team combines deep educational expertise with cutting-edge AI technology 
              to create the most effective learning platform for Indian students.
            </p>
          </motion.div>
        </div>
      </section>
    </div>
  );
};

export default AboutPage;