import React, { useRef, useEffect } from 'react';
import { Sparkles, AlertCircle, RefreshCw, Loader2 } from 'lucide-react';
import ChatMessage from './ChatMessage';
import SuggestedQuestions from './SuggestedQuestions';

export default function ChatWindow({
  messages = [],
  isLoading = false,
  errorMessage = null,
  onRetry,
  onSelectQuestion,
  onSelectAction
}) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading, errorMessage]);

  const isEmpty = messages.length === 0;

  return (
    <div className="flex-1 bg-slate-50/50 rounded-lg border border-slate-200 p-4 sm:p-6 overflow-y-auto min-h-[380px] max-h-[600px] flex flex-col justify-between">
      
      {isEmpty ? (
        /* Empty State */
        <div className="my-auto max-w-lg mx-auto text-center py-8 space-y-6">
          <div className="w-10 h-10 rounded-lg bg-emerald-50 text-[#0f6b56] border border-emerald-200 flex items-center justify-center mx-auto shadow-2xs">
            <Sparkles className="w-5 h-5" />
          </div>

          <div className="space-y-1.5">
            <h2 className="text-base font-bold text-slate-900">AI Copilot</h2>
            <p className="text-xs text-slate-500 leading-relaxed max-w-sm mx-auto">
              Ask questions about your documents, metrics, and sustainability data.
            </p>
          </div>

          <div className="pt-2 text-left">
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
            />
          ))}

          {/* Loading Indicator */}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-white border border-slate-200 rounded-lg px-4 py-3 text-xs text-slate-600 shadow-2xs flex items-center space-x-2">
                <Loader2 className="w-3.5 h-3.5 text-[#0f6b56] animate-spin shrink-0" />
                <span>Analyzing your data...</span>
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
