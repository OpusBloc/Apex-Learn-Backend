import React from 'react';
import { motion } from 'framer-motion';
import { 
  Briefcase, 
  MapPin, 
  Clock, 
  Users, 
  Code, 
  Brain,
  Palette,
  BarChart3,
  Shield,
  Heart
} from 'lucide-react';

const CareersPage: React.FC = () => {
  const jobOpenings = [
    {
      title: "AI/ML Engineer",
      department: "Engineering",
      location: "Bangalore",
      type: "Full-time",
      description: "Build and optimize AI models for personalized learning experiences.",
      requirements: ["Python", "TensorFlow", "Machine Learning", "NLP"],
      icon: Brain
    },
    {
      title: "Frontend Developer",
      department: "Engineering",
      location: "Mumbai",
      type: "Full-time",
      description: "Create beautiful, responsive user interfaces for our learning platform.",
      requirements: ["React", "TypeScript", "Tailwind CSS", "Animation"],
      icon: Code
    },
    {
      title: "UX/UI Designer",
      department: "Design",
      location: "Delhi",
      type: "Full-time",
      description: "Design intuitive and engaging learning experiences for students.",
      requirements: ["Figma", "User Research", "Prototyping", "Design Systems"],
      icon: Palette
    },
    {
      title: "Educational Content Creator",
      department: "Content",
      location: "Hyderabad",
      type: "Full-time",
      description: "Develop curriculum-aligned educational content for various Indian boards.",
      requirements: ["Teaching Experience", "Subject Expertise", "Content Writing"],
      icon: Users
    },
    {
      title: "Data Scientist",
      department: "Analytics",
      location: "Bangalore",
      type: "Full-time",
      description: "Analyze learning patterns to improve student outcomes and platform effectiveness.",
      requirements: ["Python", "Statistics", "Data Visualization", "SQL"],
      icon: BarChart3
    },
    {
      title: "DevOps Engineer",
      department: "Infrastructure",
      location: "Remote",
      type: "Full-time",
      description: "Ensure reliable, scalable infrastructure for millions of students.",
      requirements: ["AWS", "Docker", "Kubernetes", "CI/CD"],
      icon: Shield
    }
  ];

  const benefits = [
    {
      icon: Heart,
      title: "Health & Wellness",
      description: "Comprehensive health insurance and wellness programs"
    },
    {
      icon: Users,
      title: "Learning & Growth",
      description: "Continuous learning opportunities and conference allowances"
    },
    {
      icon: Briefcase,
      title: "Work-Life Balance",
      description: "Flexible working hours and remote work options"
    },
    {
      icon: BarChart3,
      title: "Equity & Ownership",
      description: "Employee stock options and performance bonuses"
    }
  ];

  return (
    <div className="pt-16">
      {/* Hero Section */}
      <section className="py-20 px-4 bg-gradient-to-br from-primary-50 to-secondary-50">
        <div className="max-w-6xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6">
              Join Our{' '}
              <span className="bg-gradient-to-r from-primary-600 to-secondary-600 bg-clip-text text-transparent">
                Mission
              </span>
            </h1>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto mb-8">
              Help us transform education in India. Join a team of passionate educators 
              and technologists building the future of learning.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button className="btn-primary text-lg px-8 py-4">
                View Open Positions
              </button>
              <button className="border-2 border-primary-600 text-primary-600 hover:bg-primary-600 hover:text-white px-8 py-4 rounded-lg font-medium transition-all duration-200">
                Learn About Culture
              </button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Benefits Section */}
      <section className="py-20 px-4">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              Why Work With Us?
            </h2>
            <p className="text-xl text-gray-600">
              We offer comprehensive benefits and a culture focused on growth and impact
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {benefits.map((benefit, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                whileHover={{ y: -10 }}
                className="card p-6 text-center"
              >
                <benefit.icon className="h-12 w-12 text-primary-600 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-gray-900 mb-3">
                  {benefit.title}
                </h3>
                <p className="text-gray-600">
                  {benefit.description}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Job Openings Section */}
      <section className="py-20 px-4 bg-gray-50">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              Open Positions
            </h2>
            <p className="text-xl text-gray-600">
              Find your perfect role and help us shape the future of education
            </p>
          </motion.div>

          <div className="space-y-6">
            {jobOpenings.map((job, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                whileHover={{ y: -5 }}
                className="card p-6"
              >
                <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-4 mb-3">
                      <job.icon className="h-8 w-8 text-primary-600" />
                      <div>
                        <h3 className="text-2xl font-semibold text-gray-900">
                          {job.title}
                        </h3>
                        <div className="flex items-center space-x-4 text-gray-600 mt-1">
                          <span className="flex items-center space-x-1">
                            <Briefcase className="h-4 w-4" />
                            <span>{job.department}</span>
                          </span>
                          <span className="flex items-center space-x-1">
                            <MapPin className="h-4 w-4" />
                            <span>{job.location}</span>
                          </span>
                          <span className="flex items-center space-x-1">
                            <Clock className="h-4 w-4" />
                            <span>{job.type}</span>
                          </span>
                        </div>
                      </div>
                    </div>
                    
                    <p className="text-gray-600 mb-4">
                      {job.description}
                    </p>
                    
                    <div className="flex flex-wrap gap-2">
                      {job.requirements.map((req, reqIndex) => (
                        <span
                          key={reqIndex}
                          className="px-3 py-1 bg-primary-100 text-primary-700 rounded-full text-sm font-medium"
                        >
                          {req}
                        </span>
                      ))}
                    </div>
                  </div>
                  
                  <div className="mt-6 lg:mt-0 lg:ml-6">
                    <motion.button
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      className="btn-primary"
                    >
                      Apply Now
                    </motion.button>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Culture Section */}
      <section className="py-20 px-4">
        <div className="max-w-6xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <h2 className="text-4xl font-bold text-gray-900 mb-6">
              Our Culture
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto mb-12">
              We foster an environment of innovation, collaboration, and continuous learning. 
              Every team member contributes to our mission of democratizing quality education.
            </p>
            
            <div className="grid md:grid-cols-3 gap-8">
              {[
                {
                  title: "Innovation First",
                  description: "We encourage creative thinking and embrace new technologies to solve educational challenges."
                },
                {
                  title: "Student-Centric",
                  description: "Every decision we make is guided by what's best for student learning and success."
                },
                {
                  title: "Continuous Growth",
                  description: "We invest in our team's professional development and provide opportunities for advancement."
                }
              ].map((culture, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 30 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: index * 0.1 }}
                  className="card p-6"
                >
                  <h3 className="text-xl font-semibold text-gray-900 mb-3">
                    {culture.title}
                  </h3>
                  <p className="text-gray-600">
                    {culture.description}
                  </p>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>
      </section>
    </div>
  );
};

export default CareersPage;