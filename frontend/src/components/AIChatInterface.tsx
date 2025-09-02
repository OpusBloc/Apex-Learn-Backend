import React, { useState, useEffect, useRef } from 'react';
import { Send, Brain } from 'lucide-react';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

interface AIChatInterfaceProps {
  chatHistory: ChatMessage[];
  onSendMessage: (message: string) => void;
  subject: string;
  topic: string;
  subtopic: string;
}

const AIChatInterface: React.FC<AIChatInterfaceProps> = ({ chatHistory, onSendMessage, subject, topic, subtopic }) => {
  const [message, setMessage] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);

  const handleSend = () => {
    if (message.trim()) {
      onSendMessage(message);
      setMessage('');
    }
  };

  return (
    <div className="bg-gradient-to-br from-white to-indigo-50 p-6 rounded-xl shadow-lg">
      <h3 className="text-xl font-bold text-indigo-600 mb-4 flex items-center">
        <Brain className="mr-2 h-6 w-6" /> AI Tutor: {subtopic || topic}
      </h3>
      <div className="h-96 overflow-y-auto mb-4 p-4 bg-white rounded-lg border border-indigo-100">
        {chatHistory.length === 0 ? (
          <p className="text-gray-500 text-center">Embark on your {subtopic || topic} quest! Ask a question to begin!</p>
        ) : (
          chatHistory.map((msg, i) => (
            <div
              key={i}
              className={`mb-4 ${msg.role === 'user' ? 'text-right' : 'text-left'}`}
            >
              <div
                className={`inline-block p-3 rounded-lg shadow-sm ${
                  msg.role === 'user' ? 'bg-indigo-100 text-indigo-800' : 'bg-gray-100 text-gray-800'
                } max-w-[80%]`}
              >
                <p className="text-sm">{msg.content}</p>
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={message}
          onChange={e => setMessage(e.target.value)}
          placeholder={`Ask about ${subtopic || topic}...`}
          className="flex-1 p-3 border border-indigo-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
          onKeyPress={e => e.key === 'Enter' && handleSend()}
        />
        <button
          onClick={handleSend}
          className="bg-indigo-600 text-white p-3 rounded-lg hover:bg-indigo-700 transition-colors duration-300"
        >
          <Send className="h-5 w-5" />
        </button>
      </div>
    </div>
  );
};

export default AIChatInterface;