import React, { useState } from 'react';
import CopilotHeader from '../components/copilot/CopilotHeader';
import ChatWindow from '../components/copilot/ChatWindow';
import ChatInput from '../components/copilot/ChatInput';
import SuggestedQuestions from '../components/copilot/SuggestedQuestions';
import { askCopilot } from '../services/api';

export default function Copilot({ onNavigate }) {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [lastFailedMessage, setLastFailedMessage] = useState(null);

  const handleSendMessage = async (text) => {
    const question = text.trim();
    if (!question || isLoading) return;

    // Append user message immediately
    const newMessages = [...messages, { role: 'user', content: question }];
    setMessages(newMessages);
    setIsLoading(true);
    setErrorMessage(null);
    setLastFailedMessage(null);

    try {
      const response = await askCopilot(question);
      setMessages([
        ...newMessages,
        {
          role: 'assistant',
          content: response.answer || 'No response received from Copilot.',
          intent: response.intent || null,
          sources: response.sources || [],
          actions: response.actions || []
        }
      ]);
    } catch (err) {
      console.error('Copilot request error:', err);
      setLastFailedMessage(question);
      // Safe, user-friendly error without stack traces
      setErrorMessage("Unable to reach the Copilot service.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleRetry = () => {
    if (lastFailedMessage) {
      handleSendMessage(lastFailedMessage);
    }
  };

  const handleClearChat = () => {
    setMessages([]);
    setErrorMessage(null);
    setLastFailedMessage(null);
  };

  const handleSelectAction = (actionText) => {
    handleSendMessage(actionText);
  };

  return (
    <div className="space-y-4 pb-16 w-full max-w-4xl mx-auto flex flex-col min-h-[calc(100vh-140px)]">
      
      {/* 1. COPILOT HEADER */}
      <CopilotHeader
        onClearChat={handleClearChat}
        messageCount={messages.length}
      />

      {/* 2. MAIN CHAT WINDOW */}
      <ChatWindow
        messages={messages}
        isLoading={isLoading}
        errorMessage={errorMessage}
        onRetry={handleRetry}
        onSelectQuestion={handleSendMessage}
        onSelectAction={handleSelectAction}
      />

      {/* 3. SUGGESTED QUESTIONS (SHOW ONCE CONVERSATION ACTIVE) */}
      {messages.length > 0 && (
        <div className="pt-1">
          <SuggestedQuestions
            onSelectQuestion={handleSendMessage}
            disabled={isLoading}
          />
        </div>
      )}

      {/* 4. CHAT INPUT */}
      <div className="pt-1">
        <ChatInput
          onSendMessage={handleSendMessage}
          isLoading={isLoading}
          placeholder="Ask about your documents, metrics, and emissions..."
        />
      </div>

    </div>
  );
}
