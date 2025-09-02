import React from 'react';
import { motion } from 'framer-motion';
import { CheckCircle, Clock, Star, Zap } from 'lucide-react';

interface StudyTask {
  id: number;
  topic: string;
  subject: string;
  subtopic: string;
  date: string;
  time: number;
  difficulty: string;
  quest_type: string;
  rewards: string;
  description: string;
  completed: boolean;
  progress: number;
  chapter: string;
}

interface StudyPlan {
  [key: string]: StudyTask[];
}

interface StudyPlanMapProps {
  studyPlan: StudyPlan;
  onTaskClick: (week: string, taskId: number) => void;
  onTaskComplete: (week: string, taskId: number) => void;
}

const StudyPlanMap: React.FC<StudyPlanMapProps> = ({ studyPlan, onTaskClick, onTaskComplete }) => {
  return (
    <div className="space-y-8">
      {Object.keys(studyPlan).sort((a, b) => Number(a) - Number(b)).map(week => (
        <div key={week} className="bg-gradient-to-r from-indigo-50 to-purple-50 p-6 rounded-xl shadow-lg">
          <h3 className="text-2xl font-bold text-indigo-600 mb-4 flex items-center">
            <Zap className="mr-2" /> Week {week} Quest
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {studyPlan[week].map(task => (
              <motion.div
                key={task.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                whileHover={{ scale: 1.03 }}
                className={`p-5 rounded-xl border-2 ${
                  task.completed
                    ? 'bg-green-100 border-green-500'
                    : 'bg-white border-indigo-200 hover:bg-indigo-50'
                } shadow-md cursor-pointer transition-all duration-300`}
                onClick={() => onTaskClick(week, task.id)}
              >
                <div className="flex justify-between items-center mb-2">
                  <h4 className="text-lg font-semibold text-indigo-700">{task.subtopic}</h4>
                  {task.completed ? (
                    <CheckCircle className="text-green-500 h-6 w-6" />
                  ) : (
                    <button
                      onClick={e => {
                        e.stopPropagation();
                        onTaskComplete(week, task.id);
                      }}
                      className="text-indigo-600 hover:text-indigo-800 text-sm font-medium"
                    >
                      Mark Complete
                    </button>
                  )}
                </div>
                <p className="text-sm text-gray-600">Chapter: {task.chapter}</p>
                <p className="text-sm text-gray-600">Topic: {task.topic}</p>
                <div className="flex items-center text-sm text-gray-500 mt-2">
                  <Clock className="mr-1 h-4 w-4" />
                  {task.date} | {task.time}h
                </div>
                <div className="flex items-center text-sm text-yellow-500 mt-1">
                  <Star className="mr-1 h-4 w-4" />
                  {task.rewards}
                </div>
                <p className="text-sm text-gray-600 mt-1">{task.description}</p>
                <div className="mt-3">
                  <div className="w-full bg-gray-200 rounded-full h-3">
                    <div
                      className="bg-indigo-600 h-3 rounded-full transition-all duration-300"
                      style={{ width: `${task.progress}%` }}
                    ></div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};

export default StudyPlanMap;