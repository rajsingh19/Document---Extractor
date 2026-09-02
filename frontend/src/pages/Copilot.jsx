import React, { useState } from 'react';
import CopilotHeader from '../components/copilot/CopilotHeader';
import ChatWindow from '../components/copilot/ChatWindow';
import ChatInput from '../components/copilot/ChatInput';
import SuggestedQuestions from '../components/copilot/SuggestedQuestions';
import { askCopilot } from '../services/api';

export default function Copilot({ onNavigate, onSelectDocument, attentionData, onRefreshAttention }) {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [lastFailedMessage, setLastFailedMessage] = useState(null);

  const handleSendMessage = async (text) => {
    const question = text.trim();
    if (!question || isLoading) return;

    // Prepare conversational history turns (last 6 messages)
    const historyPayload = messages.slice(-6).map((m) => ({
      role: m.role,
      content: m.content
    }));

    // Append user message immediately
    const newMessages = [...messages, { role: 'user', content: question }];
    setMessages(newMessages);
    setIsLoading(true);
    setErrorMessage(null);
    setLastFailedMessage(null);

    try {
      const response = await askCopilot(question, historyPayload);
      setMessages([
        ...newMessages,
        {
          role: 'assistant',
          content: response.answer || 'No response received from Copilot.',
          intent: response.intent || null,
          sources: response.sources || [],
          actions: response.actions || [],
          recommendations: response.recommendations || []
        }
      ]);
      // Refresh attention state on message completion
      if (onRefreshAttention) {
        onRefreshAttention();
      }
    } catch (err) {
      console.error('Copilot request error:', err);
      setLastFailedMessage(question);
      setErrorMessage("Unable to reach the Copilot service. Please try again.");
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
    if (onRefreshAttention) {
      onRefreshAttention();
    }
  };

  const handleSelectSource = (docId) => {
    if (docId && onSelectDocument) {
      onSelectDocument({ id: docId });
    }
  };

  const handleSelectAction = (action) => {
    if (typeof action === 'string') {
      handleSendMessage(action);
      return;
    }

    if (action.target) {
      if (action.target.startsWith('/documents/')) {
        const idStr = action.target.replace('/documents/', '');
        const docId = parseInt(idStr, 10);
        if (docId && onSelectDocument) {
          onSelectDocument({ id: docId });
          return;
        }
      }
      if (action.target === '/documents' && onNavigate) {
        onNavigate('documents');
        return;
      }
      if (action.target === '/metrics' && onNavigate) {
        onNavigate('metrics');
        return;
      }
    }

    if (action.label) {
      handleSendMessage(action.label);
    }
  };

  return (
    <div className="space-y-4 pb-16 w-full max-w-4xl mx-auto flex flex-col min-h-[calc(100vh-140px)]">
      
      {/* 1. COPILOT HEADER */}
      <CopilotHeader
        onClearChat={handleClearChat}
        messageCount={messages.length}
      />

      {/* 2. MAIN CHAT WINDOW (PROACTIVE ATTENTION LANDING + CHAT STREAM) */}
      <ChatWindow
        messages={messages}
        isLoading={isLoading}
        errorMessage={errorMessage}
        attentionData={attentionData}
        onRetry={handleRetry}
        onSelectQuestion={handleSendMessage}
        onSelectAction={handleSelectAction}
        onSelectSource={handleSelectSource}
        onUploadClick={() => onNavigate && onNavigate('documents')}
      />

      {/* 3. SUGGESTED QUESTIONS (SHOWN ONCE CONVERSATION ACTIVE) */}
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
