import React, { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Send, Brain, MessageCircle, Lightbulb, BookOpen, Calculator, Atom, Globe } from 'lucide-react';
import Nav from './Nav';
import axios from 'axios';

const TutorChatPage: React.FC = () => {
  const [message, setMessage] = useState('');
  const [chatHistory, setChatHistory] = useState([
    {
      role: 'assistant',
      message: 'Hi there, young scholar! 🌟 I\'m your AI tutor, ready to help you conquer any academic challenge. What subject or topic would you like to explore today?',
      timestamp: new Date(Date.now() - 5000)
    }
  ]);
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatHistory]);

  const quickPrompts = [
    { text: "Explain Quadratic Equations", icon: Calculator, subject: "Math" },
    { text: "Help with Chemical Bonding", icon: Atom, subject: "Chemistry" },
    { text: "Photosynthesis Process", icon: BookOpen, subject: "Biology" },
    { text: "Indian Freedom Movement", icon: Globe, subject: "History" }
  ];

  const sendMessage = async (messageText: string = message) => {
    if (!messageText.trim()) return;

    const userMessage = {
      role: 'user' as const,
      message: messageText,
      timestamp: new Date()
    };

    setChatHistory(prev => [...prev, userMessage]);
    setMessage('');
    setIsTyping(true);

    try {
      const response = await axios.post('http://localhost:8000/tutor', {
        message: messageText,
        board: 'CBSE', // Could be dynamic from user context
        class_num: 10,
        subject: quickPrompts.find(p => p.text === messageText)?.subject || 'General'
      }, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });

      setChatHistory(prev => [...prev, {
        role: 'assistant' as const,
        message: response.data.response,
        timestamp: new Date()
      }]);
      setIsTyping(false);
    } catch (error) {
      console.error('Error fetching AI response:', error);
      setChatHistory(prev => [...prev, {
        role: 'assistant' as const,
        message: 'Sorry, I couldn\'t process that challenge. Try another question!',
        timestamp: new Date()
      }]);
      setIsTyping(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50">
      <Nav />
      <div className="ml-64 p-8">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="mb-8 text-center"
        >
          <motion.div
            animate={{ rotate: [0, 10, -10, 0] }}
            transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
            className="inline-block mb-4"
          >
            <Brain className="h-16 w-16 text-primary-600 mx-auto" />
          </motion.div>
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Your Personal AI Tutor 🤖
          </h1>
          <p className="text-xl text-gray-600">
            Ask anything, get detailed explanations, and master your subjects!
          </p>
        </motion.div>

        <div className="grid lg:grid-cols-4 gap-8">
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="lg:col-span-1"
          >
            <div className="card p-6 sticky top-24">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <Lightbulb className="h-5 w-5 text-yellow-500 mr-2" />
                Quick Topics
              </h3>
              <div className="space-y-3">
                {quickPrompts.map((prompt, index) => (
                  <motion.button
                    key={index}
                    whileHover={{ scale: 1.05, x: 5 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => sendMessage(prompt.text)}
                    className="w-full flex items-center space-x-3 p-3 bg-gradient-to-r from-gray-50 to-gray-100 hover:from-primary-50 hover:to-primary-100 rounded-lg transition-all duration-200 text-left"
                  >
                    <prompt.icon className="h-5 w-5 text-primary-600" />
                    <div>
                      <div className="font-medium text-gray-900 text-sm">{prompt.text}</div>
                      <div className="text-xs text-gray-500">{prompt.subject}</div>
                    </div>
                  </motion.button>
                ))}
              </div>
              <div className="mt-6 p-4 bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg">
                <h4 className="font-semibold text-gray-900 mb-2">💡 Pro Tip</h4>
                <p className="text-sm text-gray-600">
                  Ask specific questions for better explanations!
                </p>
              </div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.4 }}
            className="lg:col-span-3"
          >
            <div className="card p-6 h-[600px] flex flex-col">
              <div className="flex items-center space-x-3 pb-4 border-b border-gray-200 mb-4">
                <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-secondary-500 rounded-full flex items-center justify-center">
                  <Brain className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900">AI Tutor</h3>
                  <p className="text-sm text-green-600">● Online and ready to help</p>
                </div>
              </div>
              <div className="flex-1 overflow-y-auto space-y-4 mb-4">
                {chatHistory.map((chat, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                    className={`flex ${chat.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div className={`max-w-3xl p-4 rounded-lg ${
                      chat.role === 'user'
                        ? 'bg-primary-600 text-white'
                        : 'bg-gray-100 text-gray-900'
                    }`}>
                      {chat.role === 'assistant' && (
                        <div className="flex items-center space-x-2 mb-2">
                          <Brain className="h-4 w-4 text-primary-600" />
                          <span className="text-xs font-medium text-primary-600">AI Tutor</span>
                        </div>
                      )}
                      <div className="whitespace-pre-line">{chat.message}</div>
                      <div className={`text-xs mt-2 ${
                        chat.role === 'user' ? 'text-blue-100' : 'text-gray-500'
                      }`}>
                        {chat.timestamp.toLocaleTimeString()}
                      </div>
                    </div>
                  </motion.div>
                ))}
                {isTyping && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="flex justify-start"
                  >
                    <div className="bg-gray-100 p-4 rounded-lg">
                      <div className="flex items-center space-x-2">
                        <Brain className="h-4 w-4 text-primary-600" />
                        <span className="text-xs font-medium text-primary-600">AI Tutor is thinking...</span>
                      </div>
                      <div className="flex space-x-1 mt-2">
                        <motion.div
                          animate={{ scale: [1, 1.2, 1] }}
                          transition={{ duration: 0.6, repeat: Infinity, delay: 0 }}
                          className="w-2 h-2 bg-primary-600 rounded-full"
                        />
                        <motion.div
                          animate={{ scale: [1, 1.2, 1] }}
                          transition={{ duration: 0.6, repeat: Infinity, delay: 0.2 }}
                          className="w-2 h-2 bg-primary-600 rounded-full"
                        />
                        <motion.div
                          animate={{ scale: [1, 1.2, 1] }}
                          transition={{ duration: 0.6, repeat: Infinity, delay: 0.4 }}
                          className="w-2 h-2 bg-primary-600 rounded-full"
                        />
                      </div>
                    </div>
                  </motion.div>
                )}
                <div ref={messagesEndRef} />
              </div>
              <form onSubmit={handleSubmit} className="flex space-x-3">
                <input
                  type="text"
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Ask me anything about your studies..."
                  className="flex-1 input-field"
                  disabled={isTyping}
                />
                <motion.button
                  type="submit"
                  disabled={isTyping || !message.trim()}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="btn-primary px-6 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Send className="h-5 w-5" />
                </motion.button>
              </form>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default TutorChatPage;