import React, { useRef, useEffect } from 'react';
import { Sparkles, AlertCircle, RefreshCw, Loader2 } from 'lucide-react';
import ChatMessage from './ChatMessage';
import SuggestedQuestions from './SuggestedQuestions';
import AttentionCards from './AttentionCards';

export default function ChatWindow({
  messages = [],
  isLoading = false,
  errorMessage = null,
  attentionData = null,
  isLoadingAttention = false,
  onRetry,
  onSelectQuestion,
  onSelectAction,
  onSelectSource,
  onUploadClick
}) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading, errorMessage]);

  const isEmpty = messages.length === 0;

  return (
    <div className="flex-1 bg-slate-50/50 rounded-lg border border-slate-200 p-4 sm:p-6 overflow-y-auto min-h-[380px] max-h-[600px] flex flex-col justify-between space-y-4">
      
      {isEmpty ? (
        /* Proactive Landing State */
        <div className="w-full space-y-5">
          {/* 1. Proactive Attention Cards */}
          <AttentionCards
            attentionData={attentionData}
            isLoading={isLoadingAttention}
            onSelectAction={onSelectAction}
            onSelectSource={onSelectSource}
            onUploadClick={onUploadClick}
          />

          {/* 2. Suggested Prompts */}
          <div className="pt-2">
            <SuggestedQuestions onSelectQuestion={onSelectQuestion} disabled={isLoading} />
          </div>
        </div>
      ) : (
        /* Active Conversation Thread */
        <div className="space-y-4">
          {messages.map((msg, index) => (
            <ChatMessage
              key={index}
              message={msg}
              onSelectAction={onSelectAction}
              onSelectSource={onSelectSource}
            />
          ))}

          {/* Loading Indicator */}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-white border border-slate-200 rounded-lg px-4 py-3 text-xs text-slate-600 shadow-2xs flex items-center space-x-2">
                <Loader2 className="w-3.5 h-3.5 text-[#0f6b56] animate-spin shrink-0" />
                <span>Analyzing your Senseible data...</span>
              </div>
            </div>
          )}

          {/* Error Message with Retry */}
          {errorMessage && (
            <div className="flex justify-start">
              <div className="bg-rose-50 border border-rose-200 text-rose-800 rounded-lg p-3 text-xs shadow-2xs space-y-2 max-w-md">
                <div className="flex items-center space-x-1.5">
                  <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                  <span className="font-semibold">{errorMessage}</span>
                </div>
                {onRetry && (
                  <button
                    onClick={onRetry}
                    className="inline-flex items-center space-x-1 px-2.5 py-1 bg-white hover:bg-rose-100/50 border border-rose-200 rounded text-rose-700 text-xs font-medium transition-colors"
                  >
                    <RefreshCw className="w-3 h-3" />
                    <span>Try Again</span>
                  </button>
                )}
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      )}

    </div>
  );
}
