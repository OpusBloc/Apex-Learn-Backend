import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { ChevronLeft, ChevronRight, CheckCircle, Target } from 'lucide-react';

interface QuizQuestion {
  question: string;
  options: string[];
  answer: string;
  chapter?: string;
  topic?: string;
  marks?: number;
}

interface QuizInterfaceProps {
  quiz: QuizQuestion[];
  answers: { [key: number]: string };
  setAnswers: (answers: { [key: number]: string }) => void;
  onSubmit: () => void;
  title: string;
}

const QuizInterface: React.FC<QuizInterfaceProps> = ({ quiz, answers, setAnswers, onSubmit, title }) => {
  const [currentQuestion, setCurrentQuestion] = useState(0);

  const handleAnswer = (option: string) => {
    setAnswers({ ...answers, [currentQuestion]: option });
  };

  const handleNext = () => {
    if (currentQuestion < quiz.length - 1) {
      setCurrentQuestion(currentQuestion + 1);
    }
  };

  const handlePrevious = () => {
    if (currentQuestion > 0) {
      setCurrentQuestion(currentQuestion - 1);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-3xl mx-auto"
    >
      <h2 className="text-3xl font-bold text-indigo-600 mb-6 flex items-center">
        <Target className="mr-2" /> {title}
      </h2>
      <div className="bg-white p-6 rounded-xl shadow-lg">
        {quiz.length > 0 ? (
          <>
            <div className="mb-4">
              <p className="font-medium text-lg text-gray-800">
                {quiz[currentQuestion].question}
                {quiz[currentQuestion].chapter && (
                  <span className="text-sm text-gray-500"> ({quiz[currentQuestion].chapter})</span>
                )}
              </p>
              <div className="space-y-3 mt-4">
                {quiz[currentQuestion].options.map((opt, j) => (
                  <label key={j} className="flex items-center">
                    <input
                      type="radio"
                      name={`quiz-${currentQuestion}`}
                      value={opt}
                      checked={answers[currentQuestion] === opt}
                      onChange={() => handleAnswer(opt)}
                      className="mr-2 h-5 w-5 text-indigo-600 focus:ring-indigo-500"
                    />
                    <span className="text-gray-700">{opt}</span>
                  </label>
                ))}
              </div>
            </div>
            <div className="flex justify-between items-center">
              <button
                onClick={handlePrevious}
                disabled={currentQuestion === 0}
                className="flex items-center bg-gray-200 text-gray-700 p-2 rounded-lg hover:bg-gray-300 disabled:bg-gray-100 disabled:text-gray-400 transition-colors duration-300"
              >
                <ChevronLeft className="h-5 w-5 mr-1" /> Previous
              </button>
              {currentQuestion === quiz.length - 1 ? (
                <button
                  onClick={onSubmit}
                  disabled={Object.keys(answers).length !== quiz.length}
                  className="flex items-center bg-indigo-600 text-white p-2 rounded-lg hover:bg-indigo-700 disabled:bg-gray-400 transition-colors duration-300"
                >
                  <CheckCircle className="h-5 w-5 mr-1" /> Submit Quiz
                </button>
              ) : (
                <button
                  onClick={handleNext}
                  className="flex items-center bg-indigo-600 text-white p-2 rounded-lg hover:bg-indigo-700 transition-colors duration-300"
                >
                  Next <ChevronRight className="h-5 w-5 ml-1" />
                </button>
              )}
            </div>
          </>
        ) : (
          <p className="text-gray-500 text-center">No questions available</p>
        )}
      </div>
    </motion.div>
  );
};

export default QuizInterface;