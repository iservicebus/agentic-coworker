'use client';

import { useState, useRef, KeyboardEvent } from 'react';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export default function ChatInput({ 
  onSendMessage, 
  disabled = false, 
  placeholder = "Type your message..." 
}: ChatInputProps) {
  const [message, setMessage] = useState('');
  const [isComposing, setIsComposing] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = () => {
    if (message.trim() && !disabled) {
      onSendMessage(message.trim());
      setMessage('');
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !isComposing) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setMessage(e.target.value);
    
    // Auto-resize textarea
    const textarea = e.target;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
  };

  return (
    <div className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4">
      <div className="flex items-end space-x-3 max-w-4xl mx-auto">
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            onCompositionStart={() => setIsComposing(true)}
            onCompositionEnd={() => setIsComposing(false)}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            className="
              w-full resize-none rounded-lg border border-gray-300 dark:border-gray-600
              bg-white dark:bg-gray-800
              px-4 py-3 text-sm
              placeholder:text-gray-400 dark:placeholder:text-gray-500
              focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
              disabled:cursor-not-allowed disabled:opacity-50
              transition-colors duration-200
            "
            style={{ 
              minHeight: '44px',
              maxHeight: '200px',
            }}
          />
          
          {/* Character count indicator for long messages */}
          {message.length > 500 && (
            <div className="absolute -top-6 right-2 text-xs text-gray-500 dark:text-gray-400">
              {message.length}/2000
            </div>
          )}
        </div>
        
        <button
          onClick={handleSubmit}
          disabled={disabled || !message.trim()}
          className="
            flex items-center justify-center
            w-11 h-11 rounded-lg
            bg-blue-600 text-white
            hover:bg-blue-700 focus:bg-blue-700
            focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
            disabled:cursor-not-allowed disabled:opacity-50
            transition-all duration-200
            shrink-0
          "
          title="Send message (Enter)"
        >
          {disabled ? (
            <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
          ) : (
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
              />
            </svg>
          )}
        </button>
      </div>
      
      {/* Help text */}
      <div className="flex justify-between items-center mt-2 text-xs text-gray-500 dark:text-gray-400 max-w-4xl mx-auto">
        <span>Press Enter to send, Shift+Enter for new line</span>
        {disabled && (
          <span className="text-blue-600 dark:text-blue-400">Processing...</span>
        )}
      </div>
    </div>
  );
}
