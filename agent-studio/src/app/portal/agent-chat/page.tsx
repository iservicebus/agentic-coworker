'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useUserData } from '@/lib/contexts/UserDataContext';
import Layout from '@/components/Layout';
import ChatMessage from '@/components/chat/ChatMessage';
import ChatInput from '@/components/chat/ChatInput';
import {
  createChatSession,
  sendChatMessage,
  listChatSessions,
  deleteChatSession,
  ChatMessage as ChatMessageType,
  ChatSessionInfo as SessionInfo,
} from '@/lib/apiClient';

const AgentChatPage: React.FC = () => {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { userData, isLoading: userDataLoading, error: userDataError } = useUserData();
  
  // Get agent_id from URL parameter or fall back to userData
  const agentIdFromUrl = searchParams.get('agent_id');
  const agentId = userData?.user_type === 'agent' ? userData.username : agentIdFromUrl;

  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load sessions
  const loadSessions = useCallback(async () => {
    if (!agentId) return;

    try {
      const sessionList = await listChatSessions(agentId);
      setSessions(sessionList);
    } catch (err) {
      console.error('Failed to load sessions:', err);
    }
  }, [agentId]);

  useEffect(() => {
    if (agentId) {
      loadSessions();
    }
  }, [agentId, loadSessions]);

  // Create new session
  const handleNewSession = async () => {
    if (!agentId) {
      setError('Agent ID not available');
      return;
    }

    try {
      setIsLoading(true);
      setError(null);
      const session = await createChatSession(undefined, agentId);
      setCurrentSessionId(session.session_id);
      setMessages([]);
      await loadSessions();
    } catch (err) {
      console.error('Failed to create session:', err);
      setError(err instanceof Error ? err.message : 'Failed to create session');
    } finally {
      setIsLoading(false);
    }
  };

  // Select existing session
  const handleSelectSession = (sessionId: string) => {
    setCurrentSessionId(sessionId);
    setMessages([]);
    setError(null);
  };

  // Delete session
  const handleDeleteSession = async (sessionId: string) => {
    if (!agentId) return;

    try {
      await deleteChatSession(sessionId, agentId);
      if (currentSessionId === sessionId) {
        setCurrentSessionId(null);
        setMessages([]);
      }
      await loadSessions();
    } catch (err) {
      console.error('Failed to delete session:', err);
      setError(err instanceof Error ? err.message : 'Failed to delete session');
    }
  };

  // Send message
  const handleSendMessage = async (content: string) => {
    if (!currentSessionId || !agentId) {
      setError('No active session');
      return;
    }

    // Add user message immediately
    const userMessage: ChatMessageType = {
      id: `user-${Date.now()}`,
      content,
      role: 'user',
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsSending(true);
    setError(null);

    try {
      const response = await sendChatMessage(currentSessionId, content, agentId);

      // Process all messages from the response
      // The backend returns messages array containing all messages between the user message and AI response
      const newMessages: ChatMessageType[] = [];
      
      if (response.messages && response.messages.length > 0) {
        // Convert backend messages to frontend ChatMessageType format
        response.messages.forEach((msg, index) => {
          // Determine message type and role
          let messageRole: 'user' | 'assistant' = 'assistant';
          let messageContent = '';
          
          // Handle different message types from LangChain
          if (msg.type === 'human' || msg.role === 'user') {
            messageRole = 'user';
            messageContent = msg.content || '';
          } else if (msg.type === 'ai' || msg.role === 'assistant') {
            messageRole = 'assistant';
            messageContent = msg.content || '';
          } else if (msg.type === 'tool') {
            // Tool call messages - let ChatMessage component handle the display
            messageRole = 'assistant';
            messageContent = msg.content || '';
          } else {
            // Default to assistant for unknown types
            messageRole = 'assistant';
            messageContent = msg.content || JSON.stringify(msg);
          }
          
          newMessages.push({
            id: `msg-${Date.now()}-${index}`,
            content: messageContent,
            role: messageRole,
            timestamp: new Date(),
            metadata: msg,
          });
        });
        
        // Replace the temporary user message with all messages from the backend
        setMessages((prev) => {
          // Remove the temporary user message we added
          const withoutTemp = prev.filter((msg) => msg.id !== userMessage.id);
          // Add all messages from the response
          return [...withoutTemp, ...newMessages];
        });
      } else {
        // Fallback to old behavior if messages array is empty
        const assistantMessage: ChatMessageType = {
          id: `assistant-${Date.now()}`,
          content: response.agent_response,
          role: 'assistant',
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, assistantMessage]);
      }
    } catch (err) {
      console.error('Failed to send message:', err);
      setError(err instanceof Error ? err.message : 'Failed to send message');
      // Remove the user message if sending failed
      setMessages((prev) => prev.filter((msg) => msg.id !== userMessage.id));
    } finally {
      setIsSending(false);
    }
  };

  if (userDataLoading) {
    return (
      <Layout>
        <div className="container mx-auto p-4 text-center">Loading agent chat...</div>
      </Layout>
    );
  }

  if (userDataError) {
    return (
      <Layout>
        <div className="container mx-auto p-4">
          <p className="text-red-500 bg-red-100 p-3 rounded mb-4">Error loading user data: {userDataError}</p>
        </div>
      </Layout>
    );
  }

  if (!userData && !userDataLoading) {
    return (
      <Layout>
        <div className="container mx-auto p-4">
          <p className="text-gray-900">No user data available or user not authenticated.</p>
        </div>
      </Layout>
    );
  }

  if (!agentId) {
    return (
      <Layout>
        <div className="container mx-auto p-4">
          <p className="text-red-500 bg-red-100 p-3 rounded mb-4">Agent ID is required to access this page.</p>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="flex h-[calc(100vh-64px)]">
        {/* Sessions Sidebar */}
        <div className="w-64 border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 flex flex-col">
          <div className="p-4 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
              Agent: {agentId}
            </h2>
            <button
              onClick={handleNewSession}
              disabled={isLoading || !agentId}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? 'Creating...' : '+ New Chat'}
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-2">
            {sessions.length === 0 ? (
              <div className="text-center text-gray-500 dark:text-gray-400 text-sm mt-4">
                No sessions yet
              </div>
            ) : (
              <div className="space-y-1">
                {sessions.map((session) => (
                  <div
                    key={session.session_id}
                    className={`
                      group flex items-center justify-between p-3 rounded-lg cursor-pointer
                      ${
                        currentSessionId === session.session_id
                          ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800'
                          : 'hover:bg-gray-100 dark:hover:bg-gray-800'
                      }
                    `}
                    onClick={() => handleSelectSession(session.session_id)}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium truncate">
                        Session
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        {new Date(session.created_at).toLocaleDateString()}
                      </div>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteSession(session.session_id);
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-100 dark:hover:bg-red-900/20 rounded transition-opacity"
                      title="Delete session"
                    >
                      <svg
                        className="w-4 h-4 text-red-600 dark:text-red-400"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                        />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Chat Area */}
        <div className="flex-1 flex flex-col bg-gray-50 dark:bg-gray-800">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-6">
            <div className="max-w-4xl mx-auto">
              {!currentSessionId ? (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center text-gray-500 dark:text-gray-400">
                    <div className="text-6xl mb-4">💬</div>
                    <h2 className="text-2xl font-semibold mb-2">Welcome to Agent Chat</h2>
                    <p className="mb-4">Start a new conversation to begin</p>
                    <button
                      onClick={handleNewSession}
                      disabled={isLoading || !agentId}
                      className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      Start New Chat
                    </button>
                  </div>
                </div>
              ) : messages.length === 0 ? (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center text-gray-500 dark:text-gray-400">
                    <div className="text-4xl mb-4">👋</div>
                    <p>Send a message to start the conversation</p>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  {messages.map((message, index) => (
                    <ChatMessage
                      key={message.id}
                      message={message}
                      isStreaming={isSending && index === messages.length - 1 && message.role === 'assistant'}
                    />
                  ))}
                  <div ref={messagesEndRef} />
                </div>
              )}

              {error && (
                <div className="mt-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                  <div className="flex items-center">
                    <svg
                      className="w-5 h-5 text-red-600 dark:text-red-400 mr-2"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                    <span className="text-sm text-red-600 dark:text-red-400">{error}</span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Input */}
          <ChatInput
            onSendMessage={handleSendMessage}
            disabled={!currentSessionId || isSending || !agentId}
            placeholder={
              !currentSessionId
                ? 'Start a new chat to begin...'
                : isSending
                ? 'AI is responding...'
                : 'Type your message...'
            }
          />
        </div>
      </div>
    </Layout>
  );
};

export default AgentChatPage;
