'use client';

import { useState } from 'react';
import { ChatMessage as ChatMessageType } from '@/lib/apiClient';

interface ChatMessageProps {
  message: ChatMessageType;
  isStreaming?: boolean;
}

export default function ChatMessage({ message, isStreaming = false }: ChatMessageProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  const formatTimestamp = (timestamp: Date) => {
    return new Intl.DateTimeFormat('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }).format(timestamp);
  };

  const renderContent = (content: string) => {
    // Simple markdown-like rendering for code blocks and basic formatting
    const lines = content.split('\n');
    const elements: React.ReactElement[] = [];
    let inCodeBlock = false;
    let codeBlockContent: string[] = [];
    let codeBlockLanguage = '';

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      // Handle code blocks
      if (line.startsWith('```')) {
        if (inCodeBlock) {
          // End code block
          elements.push(
            <pre key={`code-${i}`} className="bg-gray-100 dark:bg-gray-800 rounded-lg p-4 my-2 overflow-x-auto">
              <code className={`language-${codeBlockLanguage}`}>
                {codeBlockContent.join('\n')}
              </code>
            </pre>
          );
          codeBlockContent = [];
          codeBlockLanguage = '';
          inCodeBlock = false;
        } else {
          // Start code block
          codeBlockLanguage = line.slice(3).trim();
          inCodeBlock = true;
        }
        continue;
      }

      if (inCodeBlock) {
        codeBlockContent.push(line);
        continue;
      }

      // Process line to create React elements
      const processedElements = processLineWithFormatting(line, i);

      if (line.trim()) {
        elements.push(
          <p key={i} className="mb-2 last:mb-0">
            {processedElements}
          </p>
        );
      } else {
        elements.push(<br key={i} />);
      }
    }

    return elements;
  };

  const processLineWithFormatting = (line: string, lineIndex: number): React.ReactNode[] => {
    const elements: React.ReactNode[] = [];
    let currentIndex = 0;
    let elementKey = 0;

    // URL regex - matches http:// or https:// followed by valid URL characters
    const urlRegex = /(https?:\/\/[^\s<>"{}|\\^`\[\]]+)/g;
    // Inline code regex
    const codeRegex = /`([^`]+)`/g;
    // Bold regex
    const boldRegex = /\*\*([^*]+)\*\*/g;
    // Italic regex (but not part of bold)
    const italicRegex = /(?<!\*)\*([^*]+)\*(?!\*)/g;

    // Find all special patterns in the line
    const patterns: Array<{ start: number; end: number; type: string; content: string; match: string }> = [];

    // Find all URLs
    let match;
    while ((match = urlRegex.exec(line)) !== null) {
      patterns.push({
        start: match.index,
        end: match.index + match[0].length,
        type: 'url',
        content: match[1],
        match: match[0],
      });
    }

    // Find all inline code
    while ((match = codeRegex.exec(line)) !== null) {
      patterns.push({
        start: match.index,
        end: match.index + match[0].length,
        type: 'code',
        content: match[1],
        match: match[0],
      });
    }

    // Find all bold text
    while ((match = boldRegex.exec(line)) !== null) {
      patterns.push({
        start: match.index,
        end: match.index + match[0].length,
        type: 'bold',
        content: match[1],
        match: match[0],
      });
    }

    // Find all italic text
    while ((match = italicRegex.exec(line)) !== null) {
      patterns.push({
        start: match.index,
        end: match.index + match[0].length,
        type: 'italic',
        content: match[1],
        match: match[0],
      });
    }

    // Sort patterns by start position
    patterns.sort((a, b) => a.start - b.start);

    // Remove overlapping patterns (prefer the first one)
    const filteredPatterns = [];
    let lastEnd = -1;
    for (const pattern of patterns) {
      if (pattern.start >= lastEnd) {
        filteredPatterns.push(pattern);
        lastEnd = pattern.end;
      }
    }

    // Build the elements
    for (const pattern of filteredPatterns) {
      // Add text before the pattern
      if (currentIndex < pattern.start) {
        const text = line.substring(currentIndex, pattern.start);
        elements.push(<span key={`${lineIndex}-${elementKey++}`}>{text}</span>);
      }

      // Add the pattern element
      switch (pattern.type) {
        case 'url':
          elements.push(
            <a
              key={`${lineIndex}-${elementKey++}`}
              href={pattern.content}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 dark:text-blue-400 hover:underline"
            >
              {pattern.content}
            </a>
          );
          break;
        case 'code':
          elements.push(
            <code
              key={`${lineIndex}-${elementKey++}`}
              className="bg-gray-100 dark:bg-gray-800 px-1 rounded"
            >
              {pattern.content}
            </code>
          );
          break;
        case 'bold':
          elements.push(
            <strong key={`${lineIndex}-${elementKey++}`}>
              {pattern.content}
            </strong>
          );
          break;
        case 'italic':
          elements.push(
            <em key={`${lineIndex}-${elementKey++}`}>
              {pattern.content}
            </em>
          );
          break;
      }

      currentIndex = pattern.end;
    }

    // Add remaining text
    if (currentIndex < line.length) {
      const text = line.substring(currentIndex);
      elements.push(<span key={`${lineIndex}-${elementKey++}`}>{text}</span>);
    }

    return elements.length > 0 ? elements : [line];
  };

  const getMessageClasses = () => {
    const baseClasses = "rounded-lg p-4 max-w-[80%] shadow-sm";
    
    if (message.role === 'user') {
      return `${baseClasses} ml-auto bg-blue-600 text-white`;
    }
    
    return `${baseClasses} mr-auto bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700`;
  };

  // Check if this is a tool call message
  const isToolMessage = message.metadata?.type === 'tool';
  const toolName = message.metadata?.name || 'Tool';

  return (
    <div className="flex flex-col mb-4">
      <div className={getMessageClasses()}>
        <div className="flex items-start justify-between mb-2">
          <span className="text-xs font-medium opacity-75">
            {message.role === 'user' ? 'You' : isToolMessage ? `🔧 ${toolName}` : 'Assistant'}
          </span>
          <span className="text-xs opacity-50 ml-2">
            {formatTimestamp(message.timestamp)}
          </span>
        </div>
        
        {!isToolMessage && (
          <div className="prose prose-sm max-w-none dark:prose-invert">
            {renderContent(message.content)}
          </div>
        )}

        {isStreaming && (
          <div className="flex items-center mt-2 text-xs opacity-75">
            <div className="flex space-x-1">
              <div className="w-1 h-1 bg-current rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
              <div className="w-1 h-1 bg-current rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
              <div className="w-1 h-1 bg-current rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
            </div>
            <span className="ml-2">Typing...</span>
          </div>
        )}

        {message.metadata && Object.keys(message.metadata).length > 0 && (
          <div className="mt-2 pt-2 border-t border-current/20">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-xs opacity-75 hover:opacity-100 transition-opacity"
            >
              {isExpanded ? '▼' : '▶'} Metadata
            </button>
            {isExpanded && (
              <pre className="mt-2 text-xs opacity-75 overflow-x-auto">
                {JSON.stringify(message.metadata, null, 2)}
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
